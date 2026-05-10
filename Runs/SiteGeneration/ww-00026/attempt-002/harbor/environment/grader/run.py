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
    slice_counts = {}
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
            out_prefix = captures_out / f"page_{index:02d}"
            try:
                slices = _capture_full_and_slices(url=url, out_prefix=out_prefix)
                captured += 1
                slice_counts[f"page_{index:02d}"] = slices
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
        "slice_counts": slice_counts,
    }


def _capture_full_and_slices(*, url, out_prefix):
    """Capture one page as a tall full-page PNG plus viewport slices.

    Mirrors the algorithm in
    ``site_generator/screenshot_capture_template.py`` (Node Playwright).
    Outputs:

        <out_prefix>_full.png    # tall full page
        <out_prefix>_001.png     # first viewport slice (scrollY = 0)
        <out_prefix>_002.png     # ...
        <out_prefix>_NNN.png     # last slice, snapped to scrollHeight - viewport.height

    Returns the number of slice files written.
    """
    full_path = f"{out_prefix}_full.png"
    slice_prefix = str(out_prefix)
    script = f"""
const {{ chromium }} = require("playwright");
const VIEWPORT = {{ width: {VIEWPORT_WIDTH}, height: {VIEWPORT_HEIGHT} }};
const SLICE_STEP = 1000;

function slicePositions(scrollHeight) {{
  const maxScrollY = Math.max(0, scrollHeight - VIEWPORT.height);
  const positions = [];
  for (let y = 0; y <= maxScrollY; y += SLICE_STEP) {{
    positions.push(y);
  }}
  if (!positions.length || positions[positions.length - 1] !== maxScrollY) {{
    positions.push(maxScrollY);
  }}
  return [...new Set(positions)];
}}

(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const context = await browser.newContext({{ viewport: VIEWPORT }});
  const page = await context.newPage();
  await page.goto({json.dumps(url)}, {{ waitUntil: "domcontentloaded", timeout: 15000 }});
  await page.waitForLoadState("load", {{ timeout: 15000 }}).catch(() => {{}});
  await page.evaluate(async () => {{
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  }}).catch(() => {{}});
  await page.evaluate(() => {{
    document.documentElement.style.setProperty("scroll-behavior", "auto", "important");
    if (document.body) {{
      document.body.style.setProperty("scroll-behavior", "auto", "important");
    }}
    const elements = document.body
      ? Array.from(document.body.querySelectorAll("*"))
      : [];
    for (const element of elements) {{
      const style = window.getComputedStyle(element);
      if (style.position !== "fixed" && style.position !== "sticky") continue;
      const rect = element.getBoundingClientRect();
      element.setAttribute("data-web-weaver-capture-position", style.position);
      if (style.position === "fixed") {{
        element.style.setProperty("position", "absolute", "important");
        element.style.setProperty("top", (rect.top + window.scrollY) + "px", "important");
        element.style.setProperty("left", (rect.left + window.scrollX) + "px", "important");
        element.style.setProperty("right", "auto", "important");
        element.style.setProperty("bottom", "auto", "important");
        element.style.setProperty("width", rect.width + "px", "important");
        element.style.setProperty("height", rect.height + "px", "important");
      }} else {{
        element.style.setProperty("position", "static", "important");
        element.style.setProperty("top", "auto", "important");
        element.style.setProperty("right", "auto", "important");
        element.style.setProperty("bottom", "auto", "important");
        element.style.setProperty("left", "auto", "important");
      }}
    }}
  }});
  await page.waitForTimeout(150);
  const scrollHeight = await page.evaluate(() => {{
    const body = document.body;
    const html = document.documentElement;
    return Math.max(
      (body && body.scrollHeight) || 0,
      (body && body.offsetHeight) || 0,
      (html && html.clientHeight) || 0,
      (html && html.scrollHeight) || 0,
      (html && html.offsetHeight) || 0
    );
  }});
  await page.evaluate(() => window.scrollTo({{ left: 0, top: 0, behavior: "instant" }}));
  await page.waitForTimeout(100);
  await page.screenshot({{ path: {json.dumps(full_path)}, fullPage: true, animations: "disabled" }});
  const positions = slicePositions(scrollHeight);
  for (let i = 0; i < positions.length; i++) {{
    const y = positions[i];
    await page.evaluate(scrollY => window.scrollTo({{ left: 0, top: scrollY, behavior: "instant" }}), y);
    await page.waitForTimeout(150);
    const sliceIndex = String(i + 1).padStart(3, "0");
    const slicePath = {json.dumps(slice_prefix)} + "_" + sliceIndex + ".png";
    await page.screenshot({{ path: slicePath, fullPage: false, animations: "disabled" }});
  }}
  await browser.close();
  process.stdout.write(JSON.stringify({{ slices: positions.length, scrollHeight }}));
}})();
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"playwright capture failed for {url}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        info = json.loads(proc.stdout.strip())
        return int(info.get("slices", 0))
    except Exception:
        return 0


if __name__ == "__main__":
    main()
