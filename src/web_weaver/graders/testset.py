"""Fabricate a test set of agent-output candidates at known quality tiers.

Given an existing harbor task (the canonical "ground truth"), this module
generates a set of synthetic "agent outputs" at known quality tiers and
captures full-page screenshots of each. The result is a directory of test
cases that can be fed to every grader; comparing the graders' rankings to
the known tier order tells us which grader best preserves quality
ordering.

Tiers (per ``graders_plan.md``):

- Tier 1 — verbatim copy of the reference site (target score ~1.0)
- Tier 2 — minor perturbation: small CSS tweak, hue shift, font-size +5%
- Tier 3 — one ``<section>`` removed from each page
- Tier 4 — section order shuffled and palette repainted to grayscale
- Tier 5 — blank pages with only ``<html><body></body></html>``

Adversarial cases:

- A1 — blank body with the reference's dominant background color
- A2 — a single full-viewport colored block, no content
- A3 — raw text dump from reference HTML, no styling

Each tier is rendered via Playwright at the same 1440x1000 viewport used
to capture the prompt screenshots. The fabricator writes:

    output_root/
      truth/page_NN.png                  # copy of the reference per-page PNG
      tier_01_verbatim/page_NN.png       # screenshot of mutated agent output
      tier_02_minor/page_NN.png
      tier_03_section_removed/page_NN.png
      tier_04_shuffle_repaint/page_NN.png
      tier_05_blank/page_NN.png
      adv_01_brand_color_blank/page_NN.png
      adv_02_color_block/page_NN.png
      adv_03_text_dump/page_NN.png
      manifest.json                      # all TestCase rows for compare.py

The corresponding mutated HTML directories are kept under
``output_root/<tier>/site/`` so failures can be inspected.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

from web_weaver.graders.capture import (
    SliceCapture,
    capture_page_full_and_slices,
    serve_directory,
)


VIEWPORT_WIDTH = 1440
VIEWPORT_HEIGHT = 1000


@dataclass(frozen=True)
class TestCase:
    """One ``(tier, page)`` pair to be scored by every grader.

    ``agent_screenshot`` and ``truth_screenshot`` always point at the tall
    full-page PNG (``*_full.png``). Sliced graders discover sibling slice
    files via :func:`web_weaver.graders.capture.find_slice_siblings`.
    """

    task_id: str
    tier: str
    tier_index: int
    page_index: int
    page_filename: str
    agent_screenshot: Path
    truth_screenshot: Path

    def serializable(self) -> dict:
        d = asdict(self)
        d["agent_screenshot"] = str(self.agent_screenshot)
        d["truth_screenshot"] = str(self.truth_screenshot)
        return d


TIER_DEFINITIONS: list[tuple[int, str, str]] = [
    (1, "tier_01_verbatim", "verbatim copy of reference"),
    (2, "tier_02_minor", "minor CSS/hue perturbation"),
    (3, "tier_03_section_removed", "one section removed per page"),
    (4, "tier_04_shuffle_repaint", "shuffled sections and grayscale palette"),
    (5, "tier_05_blank", "empty <body>"),
    (6, "tier_06_within_block_drift", "same structure, drifted colors/fonts/icons"),
    (7, "adv_01_brand_color_blank", "blank body with reference dominant bg color"),
    (8, "adv_02_color_block", "single full-viewport colored block"),
    (9, "adv_03_text_dump", "raw text dump, no styling"),
]


def fabricate_test_set(
    *,
    harbor_task_dir: Path,
    output_root: Path,
    task_id: str | None = None,
    seed: int = 7,
) -> list[TestCase]:
    """Build the test set under ``output_root`` and return all test cases."""

    harbor_task_dir = harbor_task_dir.resolve()
    reference_site_dir = harbor_task_dir / "solution" / "site"
    prompt_screenshots_dir = harbor_task_dir / "environment" / "prompt" / "screenshots"
    if not reference_site_dir.is_dir():
        raise FileNotFoundError(f"Missing reference site at {reference_site_dir}")
    if not prompt_screenshots_dir.is_dir():
        raise FileNotFoundError(
            f"Missing prompt screenshots at {prompt_screenshots_dir}"
        )

    if task_id is None:
        task_id = harbor_task_dir.parent.parent.name  # ww-NNNNN

    output_root = output_root.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=False)

    page_filenames = _expected_page_filenames(prompt_screenshots_dir)
    page_count = len(page_filenames)

    truth_dir = output_root / "truth"
    truth_dir.mkdir(parents=True, exist_ok=False)

    test_cases: list[TestCase] = []
    rng = random.Random(seed)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            # Re-render the canonical solution/site to get a fresh tall
            # PNG plus matching slices for the truth side. This guarantees
            # the truth and all tier captures share the same Playwright
            # mechanics and slice geometry.
            with serve_directory(reference_site_dir) as truth_port:
                for page_index, filename in enumerate(page_filenames, start=1):
                    out_prefix = truth_dir / f"page_{page_index:02d}"
                    capture_page_full_and_slices(
                        browser=browser,
                        url=f"http://127.0.0.1:{truth_port}/{filename}",
                        out_prefix=out_prefix,
                        viewport_width=VIEWPORT_WIDTH,
                        viewport_height=VIEWPORT_HEIGHT,
                    )

            for tier_index, tier_label, _description in TIER_DEFINITIONS:
                tier_dir = output_root / tier_label
                site_dir = tier_dir / "site"
                site_dir.mkdir(parents=True, exist_ok=False)

                _materialize_tier(
                    tier_label=tier_label,
                    reference_site_dir=reference_site_dir,
                    out_site_dir=site_dir,
                    page_filenames=page_filenames,
                    rng=rng,
                )

                with serve_directory(site_dir) as tier_port:
                    for page_index, filename in enumerate(page_filenames, start=1):
                        out_prefix = tier_dir / f"page_{page_index:02d}"
                        capture_page_full_and_slices(
                            browser=browser,
                            url=f"http://127.0.0.1:{tier_port}/{filename}",
                            out_prefix=out_prefix,
                            viewport_width=VIEWPORT_WIDTH,
                            viewport_height=VIEWPORT_HEIGHT,
                        )
                        agent_full = tier_dir / f"page_{page_index:02d}_full.png"
                        truth_full = truth_dir / f"page_{page_index:02d}_full.png"
                        test_cases.append(
                            TestCase(
                                task_id=task_id,
                                tier=tier_label,
                                tier_index=tier_index,
                                page_index=page_index,
                                page_filename=filename,
                                agent_screenshot=agent_full,
                                truth_screenshot=truth_full,
                            )
                        )
        finally:
            browser.close()

    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "harbor_task_dir": str(harbor_task_dir),
                "page_count": page_count,
                "tier_definitions": [
                    {"index": idx, "label": label, "description": desc}
                    for idx, label, desc in TIER_DEFINITIONS
                ],
                "test_cases": [tc.serializable() for tc in test_cases],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return test_cases


def load_manifest(output_root: Path) -> list[TestCase]:
    """Re-load test cases from a previously fabricated test set."""
    manifest = json.loads((output_root / "manifest.json").read_text(encoding="utf-8"))
    cases = []
    for raw in manifest["test_cases"]:
        cases.append(
            TestCase(
                task_id=raw["task_id"],
                tier=raw["tier"],
                tier_index=raw["tier_index"],
                page_index=raw["page_index"],
                page_filename=raw["page_filename"],
                agent_screenshot=Path(raw["agent_screenshot"]),
                truth_screenshot=Path(raw["truth_screenshot"]),
            )
        )
    return cases


def _expected_page_filenames(prompt_screenshots_dir: Path) -> list[str]:
    indices = sorted(
        int(match.group(1))
        for entry in prompt_screenshots_dir.iterdir()
        if entry.is_file() and (match := re.match(r"^page_(\d+)\.png$", entry.name))
    )
    if not indices:
        raise FileNotFoundError(
            f"No page_NN.png files in {prompt_screenshots_dir}"
        )
    if indices != list(range(1, max(indices) + 1)):
        raise ValueError(
            f"Prompt screenshot indices are not contiguous 1..N: {indices}"
        )
    filenames = []
    for index in indices:
        filenames.append("index.html" if index == 1 else f"page_{index:02d}.html")
    return filenames


def _materialize_tier(
    *,
    tier_label: str,
    reference_site_dir: Path,
    out_site_dir: Path,
    page_filenames: list[str],
    rng: random.Random,
) -> None:
    if tier_label.startswith("tier_05") or tier_label.startswith("adv_"):
        for filename in page_filenames:
            html = _build_minimal_page(
                tier_label=tier_label,
                filename=filename,
                reference_site_dir=reference_site_dir,
                page_filenames=page_filenames,
            )
            (out_site_dir / filename).write_text(html, encoding="utf-8")
        return

    for entry in reference_site_dir.iterdir():
        target = out_site_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)

    for filename in page_filenames:
        path = out_site_dir / filename
        original = path.read_text(encoding="utf-8")
        if tier_label == "tier_01_verbatim":
            mutated = original
        elif tier_label == "tier_02_minor":
            mutated = _apply_minor_perturbation(original)
        elif tier_label == "tier_03_section_removed":
            mutated = _drop_last_section(original)
        elif tier_label == "tier_04_shuffle_repaint":
            mutated = _shuffle_and_repaint(original, rng=rng)
        elif tier_label == "tier_06_within_block_drift":
            mutated = _within_block_drift(original)
        else:
            raise ValueError(f"Unknown tier {tier_label!r}")
        path.write_text(mutated, encoding="utf-8")


def _within_block_drift(html_text: str) -> str:
    """Mutation that preserves section structure but drifts within-block details.

    Simulates the production failure mode where the agent gets the high-level
    layout right but renders accent colors, typography, and iconography
    differently from the reference. We:

    - Force a markedly different font family stack.
    - Apply a hue rotation + saturation drift to drift accent colors.
    - Replace any inline ``<svg>`` with a simple grey rectangle so icon /
      illustration content is gone but bbox is preserved.
    - Lift heading sizes and weights so typography hierarchy looks different.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    for svg in soup.find_all("svg"):
        for child in list(svg.children):
            child.extract()
        svg["style"] = (svg.get("style", "") + ";background:#bdbdbd;").lstrip(";")
        svg.append(soup.new_tag("title"))
    drift_style = (
        "<style data-test-set=\"within-block-drift\">\n"
        "  html, body, * {\n"
        "    font-family: 'Times New Roman', Georgia, serif !important;\n"
        "  }\n"
        "  html { filter: hue-rotate(140deg) saturate(0.6); }\n"
        "  h1, h2, h3, h4, h5, h6 {\n"
        "    font-family: 'Courier New', monospace !important;\n"
        "    font-weight: 900 !important;\n"
        "    letter-spacing: -0.02em !important;\n"
        "  }\n"
        "  h2 { font-size: 1.2rem !important; }\n"
        "  h3 { font-size: 1.6rem !important; }\n"
        "</style>\n"
    )
    return _inject_into_head(str(soup), drift_style)


def _apply_minor_perturbation(html_text: str) -> str:
    style = (
        "<style data-test-set=\"minor\">\n"
        "  html { filter: hue-rotate(10deg) saturate(1.05); }\n"
        "  body { font-size: 105% !important; }\n"
        "</style>\n"
    )
    return _inject_into_head(html_text, style)


def _drop_last_section(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    sections = soup.find_all("section")
    if sections:
        sections[-1].decompose()
    return str(soup)


def _shuffle_and_repaint(html_text: str, *, rng: random.Random) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    body = soup.find("body")
    if body is not None:
        sections = body.find_all("section", recursive=False)
        if len(sections) > 1:
            order = list(range(len(sections)))
            rng.shuffle(order)
            extracted = [section.extract() for section in sections]
            for index in order:
                body.append(extracted[index])
    grayscale_style = (
        "<style data-test-set=\"shuffle-repaint\">\n"
        "  html { filter: grayscale(1); }\n"
        "</style>\n"
    )
    return _inject_into_head(str(soup), grayscale_style)


def _build_minimal_page(
    *,
    tier_label: str,
    filename: str,
    reference_site_dir: Path,
    page_filenames: list[str],
) -> str:
    if tier_label == "tier_05_blank":
        body = "<body></body>"
    elif tier_label == "adv_01_brand_color_blank":
        color = _detect_dominant_color(reference_site_dir / filename)
        body = f"<body style=\"background:{color};\"></body>"
    elif tier_label == "adv_02_color_block":
        body = (
            "<body style=\"margin:0;\">"
            "<div style=\"width:100vw;height:100vh;background:#f0f0f0;\"></div>"
            "</body>"
        )
    elif tier_label == "adv_03_text_dump":
        text_chunks = _extract_text(reference_site_dir / filename)
        joined = "\n".join(f"<p>{chunk}</p>" for chunk in text_chunks)
        body = f"<body>{joined}</body>"
    else:
        raise ValueError(f"Unknown minimal tier {tier_label!r}")
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head><meta charset=\"utf-8\"><title>test set</title></head>\n"
        f"{body}\n"
        "</html>\n"
    )


def _detect_dominant_color(reference_html_path: Path) -> str:
    if not reference_html_path.is_file():
        return "#ffffff"
    sibling_screenshot = (
        reference_html_path.parent.parent.parent
        / "environment"
        / "prompt"
        / "screenshots"
    )
    if not sibling_screenshot.is_dir():
        return "#ffffff"
    pages = sorted(sibling_screenshot.glob("page_*.png"))
    if not pages:
        return "#ffffff"
    digest = hashlib.sha1(reference_html_path.name.encode()).digest()
    chosen = pages[digest[0] % len(pages)]
    with Image.open(chosen) as image:
        thumb = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
        counter = Counter(thumb.getdata())
    (r, g, b), _ = counter.most_common(1)[0]
    return f"#{r:02x}{g:02x}{b:02x}"


def _extract_text(reference_html_path: Path) -> list[str]:
    if not reference_html_path.is_file():
        return []
    soup = BeautifulSoup(reference_html_path.read_text(encoding="utf-8"), "html.parser")
    chunks: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "a", "button", "span"]):
        text = element.get_text(strip=True)
        if text:
            chunks.append(text)
    return chunks[:200]


def _inject_into_head(html_text: str, style_block: str) -> str:
    if "</head>" in html_text:
        return html_text.replace("</head>", style_block + "</head>", 1)
    if "<body" in html_text:
        return html_text.replace("<body", "<head>" + style_block + "</head>\n<body", 1)
    return style_block + html_text


def cases_by_page(test_cases: Iterable[TestCase]) -> dict[int, list[TestCase]]:
    by_page: dict[int, list[TestCase]] = {}
    for case in test_cases:
        by_page.setdefault(case.page_index, []).append(case)
    return by_page
