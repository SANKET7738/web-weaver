#!/usr/bin/env python3
"""Placeholder grader: completeness-only.

Conforms to the locked harbor grader interface:
    --agent-site DIR        path to /app/site
    --prompt DIR            path to /app/prompt (agent-readable; the screenshot
                            count drives the expected page count)
    --solution DIR          path to /opt/solution (root-only; rich ground-truth
                            assets: screenshots/ and screenrecordings/ for
                            future visual / motion graders. Placeholder ignores)
    --captures-out DIR      where a real grader would write captured screenshots
                            (placeholder ignores)
    --reward-out PATH       where to write reward.json

Score = (number of expected pages that exist and parse with non-trivial body
content) / (number of expected pages).
"""
import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup


PROMPT_FILENAME_RE = re.compile(r"^page_(\d+)\.png$")


def expected_page_count(prompt_dir):
    screenshots_dir = prompt_dir / "screenshots"
    if not screenshots_dir.is_dir():
        raise SystemExit(f"Missing prompt screenshots at {screenshots_dir}")
    indices = []
    for entry in screenshots_dir.iterdir():
        if not entry.is_file():
            continue
        match = PROMPT_FILENAME_RE.match(entry.name)
        if match:
            indices.append(int(match.group(1)))
    if not indices:
        raise SystemExit(
            f"No prompt screenshots named page_NN.png found in {screenshots_dir}"
        )
    indices.sort()
    expected = list(range(1, max(indices) + 1))
    if indices != expected:
        raise SystemExit(
            f"Prompt screenshots have non-contiguous indices: got {indices}, "
            f"expected {expected}"
        )
    return len(indices)


def expected_page_filenames(page_count):
    filenames = []
    for index in range(1, page_count + 1):
        if index == 1:
            filenames.append("index.html")
        else:
            filenames.append(f"page_{index:02d}.html")
    return filenames


def html_has_non_trivial_body(html_text):
    try:
        soup = BeautifulSoup(html_text, "html.parser")
    except Exception:
        return False
    body = soup.find("body")
    if body is None:
        return False
    text = body.get_text(strip=True)
    if len(text) >= 20:
        return True
    descendant_count = sum(1 for _ in body.descendants)
    return descendant_count >= 5


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-site", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--solution", required=True, type=Path)
    parser.add_argument("--captures-out", required=True, type=Path)
    parser.add_argument("--reward-out", required=True, type=Path)
    return parser.parse_args()


def main():
    args = parse_args()

    page_count = expected_page_count(args.prompt)
    expected_filenames = expected_page_filenames(page_count)

    present_pages = 0
    non_empty_pages = 0
    missing = []
    parse_failures = []
    empty_body = []

    for filename in expected_filenames:
        path = args.agent_site / filename
        if not path.is_file():
            missing.append(filename)
            continue
        present_pages += 1
        try:
            html_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            parse_failures.append(filename)
            continue
        if html_has_non_trivial_body(html_text):
            non_empty_pages += 1
        else:
            empty_body.append(filename)

    score = non_empty_pages / page_count if page_count else 0.0

    reward = {
        "score": score,
        "expected_pages": page_count,
        "present_pages": present_pages,
        "non_empty_pages": non_empty_pages,
        "missing": missing,
        "empty_body": empty_body,
        "parse_failures": parse_failures,
        "grader": "placeholder-completeness-v1",
    }

    args.reward_out.parent.mkdir(parents=True, exist_ok=True)
    args.reward_out.write_text(json.dumps(reward, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reward, indent=2))


if __name__ == "__main__":
    main()
