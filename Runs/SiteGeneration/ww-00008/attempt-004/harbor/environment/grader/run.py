#!/usr/bin/env python3
"""Placeholder grader: completeness-only.

Conforms to the locked harbor grader interface:
    --agent-site DIR        path to /app/site
    --ground-truth DIR      path to /ground_truth
    --captures-out DIR      where a real grader would write captured screenshots
                            (placeholder ignores)
    --reward-out PATH       where to write reward.json

Score = (number of expected pages that exist and parse with non-trivial body
content) / (number of expected pages).
"""
import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup


def expected_page_filenames(slugs):
    filenames = []
    for index, _slug in enumerate(slugs, start=1):
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
    parser.add_argument("--ground-truth", required=True, type=Path)
    parser.add_argument("--captures-out", required=True, type=Path)
    parser.add_argument("--reward-out", required=True, type=Path)
    return parser.parse_args()


def main():
    args = parse_args()

    page_order_path = args.ground_truth / "page_order.json"
    if not page_order_path.is_file():
        raise SystemExit(f"Missing {page_order_path}")
    page_order = json.loads(page_order_path.read_text(encoding="utf-8"))
    slugs = page_order["slugs"]

    expected_filenames = expected_page_filenames(slugs)
    expected_pages = len(expected_filenames)

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

    score = non_empty_pages / expected_pages if expected_pages else 0.0

    reward = {
        "score": score,
        "expected_pages": expected_pages,
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
