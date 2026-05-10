"""Run all graders against a fabricated test set and produce a comparison report.

Outputs:

- ``<output_root>/scores.csv`` — every (grader, test_case) row with the
  score, per-component sub-scores, and timing.
- ``<output_root>/report.md`` — human-readable summary with tier means,
  inversion rate, tier separation, adversarial catch rate, and runtime.

Definitions used in the report:

- **Tier mean** — mean score per ``(grader, tier)``.
- **Inversion rate** — fraction of pairs ``(higher_tier, lower_tier)`` where
  the grader gave the lower-tier example a higher score, considered over
  all quality-tier pairs (1 vs 5, 1 vs 4, ..., 4 vs 5). Lower is better;
  0 means the grader's ordering matches the gold tier ordering.
- **Tier separation** — ``mean(tier_01) - mean(tier_05)``. Larger means the
  grader uses more of the score range; tiny means it's saturated.
- **Adversarial catch rate** — fraction of adversarial cases scored at or
  below the highest tier-5 score. Higher is better.
- **Runtime / pair (median ms)** — robust central tendency over all calls.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path

from web_weaver.graders.base import Grader
from web_weaver.graders.testset import (
    TIER_DEFINITIONS,
    TestCase,
    fabricate_test_set,
    load_manifest,
)


QUALITY_TIERS = [
    "tier_01_verbatim",
    "tier_02_minor",
    "tier_03_section_removed",
    "tier_04_shuffle_repaint",
    "tier_05_blank",
]
ADVERSARIAL_TIERS = [
    "adv_01_brand_color_blank",
    "adv_02_color_block",
    "adv_03_text_dump",
]


def build_default_graders() -> list[Grader]:
    from web_weaver.graders.clip_only import CLIPOnlyGrader
    from web_weaver.graders.design2code import Design2CodeGrader
    from web_weaver.graders.design2code_vlm import Design2CodeVLMGrader
    from web_weaver.graders.design2code_vlm_sliced import Design2CodeVLMSlicedGrader
    from web_weaver.graders.perceptual import PerceptualGrader
    from web_weaver.graders.vlm_judge import VLMJudgeGrader
    from web_weaver.graders.waffle import WaffleGrader

    return [
        Design2CodeGrader(),
        Design2CodeVLMGrader(),
        Design2CodeVLMSlicedGrader(),
        WaffleGrader(),
        PerceptualGrader(),
        CLIPOnlyGrader(),
        VLMJudgeGrader(),
    ]


def run_comparison(
    *,
    test_cases: list[TestCase],
    graders: list[Grader],
    output_root: Path,
) -> dict:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for grader in graders:
        for case in test_cases:
            started_at = time.perf_counter()
            result = grader.grade_safely(case.agent_screenshot, case.truth_screenshot)
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            rows.append(
                {
                    "grader": grader.name,
                    "task_id": case.task_id,
                    "tier": case.tier,
                    "tier_index": case.tier_index,
                    "page_index": case.page_index,
                    "page_filename": case.page_filename,
                    "score": result.score,
                    "components": result.components,
                    "elapsed_ms": elapsed_ms,
                    "metadata": result.metadata,
                }
            )
            print(
                f"  {grader.name:14s}  {case.tier:30s}  page {case.page_index}  "
                f"score={result.score:.3f}  {elapsed_ms:.0f}ms"
            )

    _write_scores_csv(rows, output_root / "scores.csv")
    summary = _summarize(rows, graders=graders)
    _write_report(summary, output_root / "report.md")
    return summary


def _write_scores_csv(rows: list[dict], path: Path) -> None:
    component_keys: list[str] = []
    for row in rows:
        for key in row["components"]:
            if key not in component_keys:
                component_keys.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = [
            "grader",
            "task_id",
            "tier",
            "tier_index",
            "page_index",
            "page_filename",
            "score",
            "elapsed_ms",
        ] + [f"component:{k}" for k in component_keys]
        writer.writerow(header)
        for row in rows:
            line = [
                row["grader"],
                row["task_id"],
                row["tier"],
                row["tier_index"],
                row["page_index"],
                row["page_filename"],
                f"{row['score']:.6f}",
                f"{row['elapsed_ms']:.2f}",
            ]
            for key in component_keys:
                value = row["components"].get(key, "")
                line.append(f"{value:.6f}" if value != "" else "")
            writer.writerow(line)


def _summarize(rows: list[dict], *, graders: list[Grader]) -> dict:
    by_grader: dict[str, list[dict]] = {grader.name: [] for grader in graders}
    for row in rows:
        by_grader.setdefault(row["grader"], []).append(row)

    summary: dict = {"graders": {}}
    for grader_name, grader_rows in by_grader.items():
        tier_means: dict[str, float] = {}
        for tier_label in [t[1] for t in TIER_DEFINITIONS]:
            scores = [r["score"] for r in grader_rows if r["tier"] == tier_label]
            tier_means[tier_label] = statistics.fmean(scores) if scores else float("nan")

        quality_rows = [r for r in grader_rows if r["tier"] in QUALITY_TIERS]
        inversion_rate = _inversion_rate(quality_rows)

        if QUALITY_TIERS[0] in tier_means and QUALITY_TIERS[-1] in tier_means:
            tier_separation = tier_means[QUALITY_TIERS[0]] - tier_means[QUALITY_TIERS[-1]]
        else:
            tier_separation = float("nan")

        tier_5_scores = [r["score"] for r in grader_rows if r["tier"] == QUALITY_TIERS[-1]]
        if tier_5_scores:
            tier_5_max = max(tier_5_scores)
            adv_rows = [r for r in grader_rows if r["tier"] in ADVERSARIAL_TIERS]
            if adv_rows:
                catch_rate = sum(
                    1 for r in adv_rows if r["score"] <= tier_5_max
                ) / len(adv_rows)
            else:
                catch_rate = float("nan")
        else:
            catch_rate = float("nan")

        elapsed_values = [r["elapsed_ms"] for r in grader_rows]
        median_ms = statistics.median(elapsed_values) if elapsed_values else float("nan")

        summary["graders"][grader_name] = {
            "tier_means": tier_means,
            "inversion_rate": inversion_rate,
            "tier_separation": tier_separation,
            "adversarial_catch_rate": catch_rate,
            "median_ms_per_pair": median_ms,
            "n_calls": len(grader_rows),
        }
    return summary


def _inversion_rate(rows: list[dict]) -> float:
    quality_rows = [r for r in rows if r["tier"] in QUALITY_TIERS]
    if len(quality_rows) < 2:
        return float("nan")
    pairs = 0
    inversions = 0
    for i in range(len(quality_rows)):
        for j in range(i + 1, len(quality_rows)):
            a, b = quality_rows[i], quality_rows[j]
            if a["tier_index"] == b["tier_index"]:
                continue
            higher_tier = a if a["tier_index"] < b["tier_index"] else b
            lower_tier = b if a["tier_index"] < b["tier_index"] else a
            pairs += 1
            if higher_tier["score"] < lower_tier["score"]:
                inversions += 1
    return inversions / pairs if pairs else float("nan")


def _write_report(summary: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("# Grader comparison report\n")
    lines.append(
        "Test set: 5 quality tiers + 3 adversarial cases × N pages, fabricated\n"
        "by `src/web_weaver/graders/testset.py`. Each grader scored every test\n"
        "case via `Grader.grade_safely`.\n\n"
    )

    grader_names = list(summary["graders"].keys())
    tier_labels = [t[1] for t in TIER_DEFINITIONS]

    lines.append("## Tier means\n")
    header = ["tier"] + grader_names
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for tier_label in tier_labels:
        row = [tier_label]
        for grader_name in grader_names:
            value = summary["graders"][grader_name]["tier_means"].get(tier_label, float("nan"))
            row.append(f"{value:.3f}" if value == value else "n/a")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## Headline metrics\n")
    headline_header = [
        "grader",
        "inversion_rate",
        "tier_separation",
        "adversarial_catch_rate",
        "median_ms_per_pair",
    ]
    lines.append("| " + " | ".join(headline_header) + " |")
    lines.append("| " + " | ".join(["---"] * len(headline_header)) + " |")
    for grader_name in grader_names:
        info = summary["graders"][grader_name]
        lines.append(
            "| "
            + " | ".join(
                [
                    grader_name,
                    f"{info['inversion_rate']:.3f}"
                    if info["inversion_rate"] == info["inversion_rate"]
                    else "n/a",
                    f"{info['tier_separation']:.3f}"
                    if info["tier_separation"] == info["tier_separation"]
                    else "n/a",
                    f"{info['adversarial_catch_rate']:.3f}"
                    if info["adversarial_catch_rate"] == info["adversarial_catch_rate"]
                    else "n/a",
                    f"{info['median_ms_per_pair']:.0f}",
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## Notes\n")
    lines.append(
        "- **inversion_rate** counts how often the grader scored a lower\n"
        "  quality tier above a higher one across all quality-tier pairs.\n"
        "  Lower is better. 0 means the grader exactly matches the gold tier\n"
        "  ordering.\n"
        "- **tier_separation** is `mean(tier_01) - mean(tier_05)`. Larger\n"
        "  means the grader uses more of the score range.\n"
        "- **adversarial_catch_rate** is the fraction of adversarial cases\n"
        "  scored at or below the highest tier-05 score; higher is better.\n"
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--harbor-task-dir",
        type=Path,
        help=(
            "If provided, fabricate a fresh test set under --output-root from this "
            "harbor task directory. Otherwise --output-root must already contain a "
            "manifest.json."
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory to write (or read) the test set and the comparison report.",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="Override the task id stamped into the manifest.",
    )
    parser.add_argument(
        "--exclude-vlm-judge",
        action="store_true",
        help="Skip the Anthropic API grader (useful for offline runs).",
    )
    args = parser.parse_args()

    if args.harbor_task_dir:
        cases = fabricate_test_set(
            harbor_task_dir=args.harbor_task_dir,
            output_root=args.output_root,
            task_id=args.task_id,
        )
    else:
        cases = load_manifest(args.output_root)

    graders = build_default_graders()
    if args.exclude_vlm_judge:
        graders = [g for g in graders if g.name != "vlm_judge"]

    summary = run_comparison(
        test_cases=cases, graders=graders, output_root=args.output_root
    )
    print()
    print("Tier separation per grader:")
    for grader_name, info in summary["graders"].items():
        print(f"  {grader_name:14s}  separation={info['tier_separation']:.3f}  "
              f"inversion={info['inversion_rate']:.3f}  "
              f"catch={info['adversarial_catch_rate']:.3f}  "
              f"median_ms={info['median_ms_per_pair']:.0f}")
    print()
    print(f"Wrote {args.output_root / 'scores.csv'}")
    print(f"Wrote {args.output_root / 'report.md'}")


if __name__ == "__main__":
    main()
