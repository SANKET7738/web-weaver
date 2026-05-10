#!/usr/bin/env python3
"""Placeholder grader: completeness-only, with agent screenshot capture.

Conforms to the locked harbor grader interface:
    --agent-site DIR        path to /app/site
    --prompt DIR            path to /app/prompt (agent-readable; the screenshot
                            count drives the expected page count)
    --solution DIR          path to /opt/solution (root-only; rich ground-truth
                            assets: screenshots/ and screenrecordings/ for
                            future visual / motion graders. Placeholder ignores)
    --captures-out DIR      directory the grader writes captured agent
                            screenshots into. Persisted by Harbor under
                            <job>/<trial>/verifier/agent_screenshots/.
    --reward-out PATH       where to write reward.json

The placeholder still scores on completeness only (present + non-empty body),
but it boots a static server on the agent's site, drives Playwright at the
same 1440x1000 viewport used to capture the prompt screenshots, and saves a
full-page PNG per page so a human can eyeball the agent's output afterwards.
Capture failures do not affect the score.
"""
import argparse
import http.server
import json
import re
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

from bs4 import BeautifulSoup


PROMPT_FILENAME_RE = re.compile(r"^page_(\d+)\.png$")
VIEWPORT_WIDTH = 1440
VIEWPORT_HEIGHT = 1000


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

    capture_result = capture_agent_screenshots(
        agent_site=args.agent_site,
        captures_out=args.captures_out,
        expected_filenames=expected_filenames,
    )

    reward = {
        "score": score,
        "expected_pages": page_count,
        "present_pages": present_pages,
        "non_empty_pages": non_empty_pages,
        "missing": missing,
        "empty_body": empty_body,
        "parse_failures": parse_failures,
        "captures": capture_result,
        "grader": "placeholder-completeness-v1",
    }

    args.reward_out.parent.mkdir(parents=True, exist_ok=True)
    args.reward_out.write_text(json.dumps(reward, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reward, indent=2))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_static_server(directory, port):
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(directory), **kw
    )
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def capture_agent_screenshots(*, agent_site, captures_out, expected_filenames):
    captures_out.mkdir(parents=True, exist_ok=True)

    pages_to_capture = [
        (filename, idx + 1)
        for idx, filename in enumerate(expected_filenames)
        if (agent_site / filename).is_file()
    ]
    if not pages_to_capture:
        return {"captured": 0, "skipped": len(expected_filenames), "errors": []}

    port = _find_free_port()
    httpd = None
    errors = []
    captured = 0
    try:
        httpd = _start_static_server(agent_site, port)
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    break
            except OSError:
                time.sleep(0.1)

        for filename, index in pages_to_capture:
            url = f"http://127.0.0.1:{port}/{filename}"
            output_path = captures_out / f"page_{index:02d}.png"
            try:
                _capture_full_page(url=url, output_path=output_path)
                captured += 1
            except Exception as error:
                errors.append({"page": filename, "error": str(error)})
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()

    return {
        "captured": captured,
        "skipped": len(expected_filenames) - len(pages_to_capture),
        "errors": errors,
    }


def _capture_full_page(*, url, output_path):
    script = f"""
const {{ chromium }} = require("playwright");
(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const context = await browser.newContext({{
    viewport: {{ width: {VIEWPORT_WIDTH}, height: {VIEWPORT_HEIGHT} }},
  }});
  const page = await context.newPage();
  await page.goto({json.dumps(url)}, {{ waitUntil: "domcontentloaded", timeout: 15000 }});
  await page.waitForLoadState("load", {{ timeout: 15000 }}).catch(() => {{}});
  await page.evaluate(async () => {{
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  }}).catch(() => {{}});
  await page.evaluate(() => {{
    const html = document.documentElement;
    const body = document.body;
    if (html) html.style.scrollBehavior = "auto";
    if (body) body.style.scrollBehavior = "auto";
    window.scrollTo({{ left: 0, top: 0, behavior: "instant" }});
  }});
  await page.waitForTimeout(500);
  await page.screenshot({{ path: {json.dumps(str(output_path))}, fullPage: true, animations: "disabled" }});
  await browser.close();
}})();
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"playwright capture failed for {url}: {proc.stderr.strip() or proc.stdout.strip()}"
        )


if __name__ == "__main__":
    main()
