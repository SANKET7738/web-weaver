"""Score a single Harbor `harbor run` job against the harbor task's prompt screenshots.

Usage:
    python -m web_weaver.graders.score_harbor_run \
        --job-dir   jobs/<timestamp>__/harbor__<trial> \
        --harbor-task-dir Runs/SiteGeneration/<id>/attempt-NNN/harbor

Pairs the agent screenshots from
``<job-dir>/verifier/agent_screenshots/page_NN_full.png`` (and slices)
with the truth screenshots from
``<harbor-task-dir>/environment/prompt/screenshots/page_NN_full.png``
(and slices), runs every default grader, and prints a per-page table
plus per-grader means.

This is the bridge between a real Harbor run and the grader package.
For synthetic comparison reports use ``compare.py``; for one-off real
runs use this.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

from web_weaver.graders.base import Grader
from web_weaver.graders.compare import build_default_graders


PAGE_FULL_RE = re.compile(r"^page_(\d+)_full\.png$")
PAGE_LEGACY_RE = re.compile(r"^page_(\d+)\.png$")


def discover_pages(directory: Path) -> dict[int, Path]:
    """Map page index → tall PNG path. Prefers ``page_NN_full.png``,
    falls back to legacy ``page_NN.png`` for older captures."""
    pages: dict[int, Path] = {}
    if not directory.is_dir():
        return pages
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        match = PAGE_FULL_RE.match(entry.name)
        if match:
            pages[int(match.group(1))] = entry
    if not pages:
        for entry in sorted(directory.iterdir()):
            if not entry.is_file():
                continue
            match = PAGE_LEGACY_RE.match(entry.name)
            if match:
                pages[int(match.group(1))] = entry
    return pages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--job-dir",
        type=Path,
        required=True,
        help=(
            "Path to a single trial directory (e.g. "
            "jobs/2026-05-10__18-19-43/harbor__NRPpg2o)."
        ),
    )
    parser.add_argument(
        "--harbor-task-dir",
        type=Path,
        required=True,
        help="Path to the harbor task directory whose prompt screenshots are the truth.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional path to write the full results as JSON.",
    )
    parser.add_argument(
        "--exclude-vlm-judge",
        action="store_true",
        help="Skip the Anthropic API grader.",
    )
    args = parser.parse_args()

    agent_dir = args.job_dir / "verifier" / "agent_screenshots"
    truth_dir = args.harbor_task_dir / "environment" / "prompt" / "screenshots"
    if not agent_dir.is_dir():
        raise SystemExit(f"missing agent screenshots at {agent_dir}")
    if not truth_dir.is_dir():
        raise SystemExit(f"missing truth screenshots at {truth_dir}")

    agent_pages = discover_pages(agent_dir)
    truth_pages = discover_pages(truth_dir)
    if not agent_pages:
        raise SystemExit(f"no agent page screenshots found in {agent_dir}")
    if not truth_pages:
        raise SystemExit(f"no truth page screenshots found in {truth_dir}")

    common = sorted(set(agent_pages) & set(truth_pages))
    missing_agent = sorted(set(truth_pages) - set(agent_pages))
    if missing_agent:
        print(f"Warning: agent missing pages: {missing_agent}")

    graders = build_default_graders()
    if args.exclude_vlm_judge:
        graders = [g for g in graders if g.name != "vlm_judge"]

    print(f"Scoring {len(common)} page(s) against {len(graders)} grader(s)\n")
    rows: list[dict] = []
    for grader in graders:
        for page_index in common:
            agent_path = agent_pages[page_index]
            truth_path = truth_pages[page_index]
            started = time.perf_counter()
            result = grader.grade_safely(agent_path, truth_path)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            rows.append(
                {
                    "grader": grader.name,
                    "page_index": page_index,
                    "agent": str(agent_path),
                    "truth": str(truth_path),
                    "score": result.score,
                    "components": result.components,
                    "elapsed_ms": elapsed_ms,
                    "metadata": {
                        k: v
                        for k, v in result.metadata.items()
                        if k != "vlm_reasons"
                    },
                }
            )
            print(
                f"  {grader.name:25s}  page_{page_index:02d}  "
                f"score={result.score:.3f}  {elapsed_ms:>6.0f}ms"
            )
        print()

    print("=== Per-grader means ===")
    by_grader: dict[str, list[float]] = {}
    for row in rows:
        by_grader.setdefault(row["grader"], []).append(row["score"])
    print(f"{'grader':25s}  {'mean':>6s}  {'pages':>5s}")
    print("-" * 40)
    for grader_name, scores in by_grader.items():
        print(f"{grader_name:25s}  {statistics.fmean(scores):>6.3f}  {len(scores):>5d}")

    if args.out_json is not None:
        args.out_json.write_text(
            json.dumps(
                {
                    "job_dir": str(args.job_dir),
                    "harbor_task_dir": str(args.harbor_task_dir),
                    "rows": rows,
                    "per_grader_mean": {
                        g: statistics.fmean(s) for g, s in by_grader.items()
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {args.out_json}")


if __name__ == "__main__":
    main()
