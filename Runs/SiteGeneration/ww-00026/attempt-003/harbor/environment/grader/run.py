#!/usr/bin/env python3
"""Placeholder grader: completeness-only, with agent screenshot + recording capture.

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
    --recordings-out DIR    directory the grader writes captured agent
                            screen recordings into (mp4 per page). Persisted
                            by Harbor under
                            <job>/<trial>/verifier/agent_screenrecordings/.
    --reward-out PATH       where to write reward.json

The placeholder still scores on completeness only (present + non-empty body),
but it boots a static server on the agent's site, drives Playwright at the
same 1440x1000 viewport used to capture the prompt assets, and saves:

- a tall full-page PNG plus per-viewport slices per page
- an mp4 screen recording per page (top hold + eased scroll + bottom hold,
  matching the protocol used to capture the reference recordings)

so a human can eyeball the agent's output afterwards and the offline
visual / animation graders have the assets they need. Capture failures
do not affect the score.
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
RECORDING_TOP_HOLD_MS = 2500
RECORDING_BOTTOM_HOLD_MS = 2000
RECORDING_MIN_SCROLL_MS = 7000
RECORDING_MAX_SCROLL_MS = 15000


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
    parser.add_argument("--recordings-out", required=True, type=Path)
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

    recording_result = capture_agent_screenrecordings(
        agent_site=args.agent_site,
        recordings_out=args.recordings_out,
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
        "recordings": recording_result,
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


def capture_agent_screenrecordings(*, agent_site, recordings_out, expected_filenames):
    """Capture an mp4 per page using the same protocol as the reference
    recordings (top hold + eased scroll + bottom hold)."""
    recordings_out.mkdir(parents=True, exist_ok=True)

    pages_to_record = [
        (filename, idx + 1)
        for idx, filename in enumerate(expected_filenames)
        if (agent_site / filename).is_file()
    ]
    if not pages_to_record:
        return {"recorded": 0, "skipped": len(expected_filenames), "errors": []}

    port = _find_free_port()
    httpd = None
    errors = []
    recorded = 0
    bytes_by_page = {}
    try:
        httpd = _start_static_server(agent_site, port)
        for _ in range(20):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    break
            except OSError:
                time.sleep(0.1)

        for filename, index in pages_to_record:
            url = f"http://127.0.0.1:{port}/{filename}"
            out_path = recordings_out / f"page_{index:02d}.mp4"
            try:
                _record_page(url=url, out_path=out_path)
                size = out_path.stat().st_size if out_path.is_file() else 0
                if size <= 0:
                    raise RuntimeError(f"recording for {filename} is empty")
                recorded += 1
                bytes_by_page[f"page_{index:02d}"] = size
            except Exception as error:
                errors.append({"page": filename, "error": str(error)})
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()

    return {
        "recorded": recorded,
        "skipped": len(expected_filenames) - len(pages_to_record),
        "errors": errors,
        "bytes_by_page": bytes_by_page,
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


def _record_page(*, url, out_path):
    """Record one page as an mp4 using top-hold + eased-scroll + bottom-hold.

    Mirrors the algorithm in
    ``site_generator/screenrecording_capture_template.py``. Animations are
    NOT disabled during capture (unlike screenshots) because the whole
    point of the recording is to surface motion design.
    """
    import os
    import shutil
    import tempfile

    tmp_dir = Path(tempfile.mkdtemp(prefix="agent-rec-"))
    try:
        script = f"""
const fs = require("fs");
const path = require("path");
const {{ chromium }} = require("playwright");

const VIEWPORT = {{ width: {VIEWPORT_WIDTH}, height: {VIEWPORT_HEIGHT} }};
const TOP_HOLD_MS = {RECORDING_TOP_HOLD_MS};
const BOTTOM_HOLD_MS = {RECORDING_BOTTOM_HOLD_MS};
const MIN_SCROLL_MS = {RECORDING_MIN_SCROLL_MS};
const MAX_SCROLL_MS = {RECORDING_MAX_SCROLL_MS};

async function waitForVisualStability(page) {{
  await page.waitForLoadState("domcontentloaded", {{ timeout: 10000 }});
  await page.waitForLoadState("load", {{ timeout: 10000 }}).catch(() => {{}});
  await page.evaluate(async () => {{
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  }}).catch(() => {{}});
  await page.waitForTimeout(500);
}}

async function scrollThroughPage(page, maxScrollY, durationMs) {{
  await page.evaluate(async ({{ maxScrollY, durationMs }}) => {{
    const html = document.documentElement;
    const body = document.body;
    const overrideStyle = document.createElement("style");
    overrideStyle.textContent = "html, body, * {{ scroll-behavior: auto !important; }}";
    document.head.appendChild(overrideStyle);
    try {{
      window.scrollTo({{ left: 0, top: 0, behavior: "instant" }});
      if (maxScrollY <= 0) return;
      await new Promise(resolve => {{
        const startedAt = performance.now();
        function tick(now) {{
          const progress = Math.min(1, (now - startedAt) / durationMs);
          const eased = progress < 0.5
            ? 2 * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 2) / 2;
          window.scrollTo({{ left: 0, top: Math.round(maxScrollY * eased), behavior: "instant" }});
          if (progress < 1) requestAnimationFrame(tick);
          else resolve();
        }}
        requestAnimationFrame(tick);
      }});
    }} finally {{
      overrideStyle.remove();
    }}
  }}, {{ maxScrollY, durationMs }});
}}

(async () => {{
  const browser = await chromium.launch({{ headless: true }});
  const context = await browser.newContext({{
    viewport: VIEWPORT,
    recordVideo: {{ dir: {json.dumps(str(tmp_dir))}, size: VIEWPORT }},
  }});
  const page = await context.newPage();
  const video = page.video();

  const response = await page.goto({json.dumps(url)}, {{ waitUntil: "domcontentloaded", timeout: 15000 }});
  const status = response ? response.status() : null;
  if (status === null || status < 200 || status >= 300) {{
    await context.close();
    await browser.close();
    process.stderr.write("non-2xx response: " + status);
    process.exit(2);
  }}

  await waitForVisualStability(page);
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
  const maxScrollY = Math.max(0, scrollHeight - VIEWPORT.height);
  const scrollDurationMs = Math.round(Math.min(MAX_SCROLL_MS, Math.max(MIN_SCROLL_MS, maxScrollY * 2)));

  await page.evaluate(() => window.scrollTo({{ left: 0, top: 0, behavior: "instant" }}));
  await page.waitForTimeout(TOP_HOLD_MS);
  await scrollThroughPage(page, maxScrollY, scrollDurationMs);
  await page.waitForTimeout(BOTTOM_HOLD_MS);
  await page.waitForTimeout(500);

  await page.close();
  await context.close();
  await browser.close();

  const tempPath = await video.path();
  process.stdout.write(JSON.stringify({{ tempPath }}));
}})().catch(error => {{
  process.stderr.write(error.stack || error.message);
  process.exit(2);
}});
"""
        proc = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"playwright recording failed for {url}: "
                f"{proc.stderr.strip() or proc.stdout.strip()}"
            )
        try:
            info = json.loads(proc.stdout.strip())
            temp_path = info["tempPath"]
        except Exception as error:
            raise RuntimeError(
                f"could not parse recording report for {url}: {error}; "
                f"stdout={proc.stdout!r}"
            )
        if not os.path.isfile(temp_path):
            raise RuntimeError(f"recording temp file missing: {temp_path}")

        ffmpeg_proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", temp_path,
                "-an",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-r", "25",
                "-fps_mode", "cfr",
                "-movflags", "+faststart",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if ffmpeg_proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg conversion failed for {url}: "
                f"{ffmpeg_proc.stderr.strip() or ffmpeg_proc.stdout.strip()}"
            )
        try:
            os.unlink(temp_path)
        except OSError:
            pass
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
