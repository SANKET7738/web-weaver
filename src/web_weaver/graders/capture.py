"""Shared screenshot capture for graders.

Single source of truth for the slice geometry and the Playwright capture
mechanics used everywhere a webpage screenshot is taken in the grading
pipeline:

- ground-truth capture during site generation (Node implementation in
  ``site_generator/screenshot_capture_template.py``);
- agent capture inside the harbor verifier (Python; emitted by
  ``site_generator/harbor_templates.render_harbor_placeholder_grader_script``);
- test set fabrication on the host (``graders/testset.py``).

The Python ``slice_positions`` function is a deterministic line-for-line
port of the JS ``slicePositions`` function, so all three paths produce
the **same number of slices at the same scroll positions** for the same
page height.

The Playwright calls (``waitForLoadState``, ``document.fonts.ready``,
``scroll-behavior: auto !important`` override, fixed/sticky element
neutralization, ``animations: "disabled"``) mirror the JS version
call-for-call.
"""
from __future__ import annotations

import http.server
import socket
import socketserver
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


VIEWPORT_WIDTH = 1440
VIEWPORT_HEIGHT = 1000
SLICE_STEP = 1000


@dataclass(frozen=True)
class SliceCapture:
    """Result of a single page capture."""

    full_path: Path
    slice_paths: list[Path]
    scroll_height: int
    slice_positions: list[int]


def slice_positions(
    scroll_height: int,
    *,
    viewport_height: int = VIEWPORT_HEIGHT,
    step: int = SLICE_STEP,
) -> list[int]:
    """Python port of the JS ``slicePositions`` from
    ``site_generator/screenshot_capture_template.py``.

    Returns the scroll-Y positions for each slice. The last position
    snaps to ``max_scroll_y = scroll_height - viewport_height`` if it
    isn't already covered by the regular ``step`` cadence.
    """
    max_scroll_y = max(0, int(scroll_height) - viewport_height)
    positions: list[int] = []
    if max_scroll_y == 0:
        return [0]
    y = 0
    while y <= max_scroll_y:
        positions.append(y)
        y += step
    if positions[-1] != max_scroll_y:
        positions.append(max_scroll_y)
    seen: set[int] = set()
    deduped: list[int] = []
    for value in positions:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def neutralize_pinned_elements_js() -> str:
    """JS source for the fixed/sticky element neutralization.

    Same logic as ``site_generator/screenshot_capture_template.py``'s
    ``neutralizeViewportPinnedElements``.
    """
    return r"""
() => {
  document.documentElement.style.setProperty("scroll-behavior", "auto", "important");
  if (document.body) {
    document.body.style.setProperty("scroll-behavior", "auto", "important");
  }
  const elements = document.body
    ? Array.from(document.body.querySelectorAll("*"))
    : [];
  for (const element of elements) {
    const style = window.getComputedStyle(element);
    if (style.position !== "fixed" && style.position !== "sticky") continue;
    const rect = element.getBoundingClientRect();
    element.setAttribute("data-web-weaver-capture-position", style.position);
    if (style.position === "fixed") {
      element.style.setProperty("position", "absolute", "important");
      element.style.setProperty("top", (rect.top + window.scrollY) + "px", "important");
      element.style.setProperty("left", (rect.left + window.scrollX) + "px", "important");
      element.style.setProperty("right", "auto", "important");
      element.style.setProperty("bottom", "auto", "important");
      element.style.setProperty("width", rect.width + "px", "important");
      element.style.setProperty("height", rect.height + "px", "important");
    } else {
      element.style.setProperty("position", "static", "important");
      element.style.setProperty("top", "auto", "important");
      element.style.setProperty("right", "auto", "important");
      element.style.setProperty("bottom", "auto", "important");
      element.style.setProperty("left", "auto", "important");
    }
  }
}
"""


def fonts_ready_js() -> str:
    return r"""
async () => {
  if (document.fonts && document.fonts.ready) {
    await document.fonts.ready;
  }
}
"""


def get_scroll_height_js() -> str:
    return r"""
() => {
  const body = document.body;
  const html = document.documentElement;
  return Math.max(
    (body && body.scrollHeight) || 0,
    (body && body.offsetHeight) || 0,
    (html && html.clientHeight) || 0,
    (html && html.scrollHeight) || 0,
    (html && html.offsetHeight) || 0
  );
}
"""


def capture_page_full_and_slices(
    *,
    browser,
    url: str,
    out_prefix: Path,
    viewport_width: int = VIEWPORT_WIDTH,
    viewport_height: int = VIEWPORT_HEIGHT,
) -> SliceCapture:
    """Capture one page as a tall full-page PNG plus viewport slices.

    Mirrors the algorithm in ``site_generator/screenshot_capture_template.py``:

    1. Open at ``viewport_width x viewport_height``.
    2. Wait for ``domcontentloaded`` and ``load`` (load is best-effort).
    3. Wait for ``document.fonts.ready``.
    4. Neutralize fixed/sticky elements so they don't get rendered into
       every slice.
    5. Disable scroll-behavior smooth (so programmatic scrolls land
       instantly at the requested y).
    6. Capture full-page screenshot to ``<out_prefix>_full.png``.
    7. For each ``y`` in :func:`slice_positions`, scroll to ``(0, y)``
       and capture a viewport screenshot to
       ``<out_prefix>_<index:03>.png`` (1-indexed).

    Output filenames mirror the ground-truth convention from
    ``screenshot_capture_template.py`` (``<slug>_full.png``,
    ``<slug>_001.png``, ``<slug>_002.png``, …) but using the supplied
    ``out_prefix`` as the stem.
    """
    out_prefix = Path(out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(
        viewport={"width": viewport_width, "height": viewport_height}
    )
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        try:
            page.wait_for_load_state("load", timeout=15000)
        except Exception:
            pass
        page.evaluate(fonts_ready_js())
        page.evaluate(neutralize_pinned_elements_js())
        page.wait_for_timeout(150)
        scroll_height = int(page.evaluate(get_scroll_height_js()))

        full_path = out_prefix.with_name(out_prefix.name + "_full.png")
        page.screenshot(path=str(full_path), full_page=True, animations="disabled")

        positions = slice_positions(
            scroll_height,
            viewport_height=viewport_height,
            step=SLICE_STEP,
        )
        slice_paths: list[Path] = []
        for index, scroll_y in enumerate(positions, start=1):
            page.evaluate(
                "(y) => { window.scrollTo({left: 0, top: y, behavior: 'instant'}); }",
                scroll_y,
            )
            page.wait_for_timeout(150)
            slice_path = out_prefix.with_name(
                f"{out_prefix.name}_{index:03d}.png"
            )
            page.screenshot(path=str(slice_path), full_page=False, animations="disabled")
            slice_paths.append(slice_path)
    finally:
        context.close()

    return SliceCapture(
        full_path=full_path,
        slice_paths=slice_paths,
        scroll_height=scroll_height,
        slice_positions=positions,
    )


@contextmanager
def serve_directory(directory: Path) -> Iterator[int]:
    """Spin up a quiet static HTTP server on a free port for ``directory``.

    Yields the port. The server is shut down on context exit. Used by
    consumers that need to render local HTML through Playwright.
    """
    port = _find_free_port()

    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    handler = lambda *args, **kwargs: _QuietHandler(
        *args, directory=str(directory), **kwargs
    )
    httpd = socketserver.TCPServer(
        ("127.0.0.1", port), handler, bind_and_activate=False
    )
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                break
        except OSError:
            time.sleep(0.1)
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def find_slice_siblings(full_path: Path) -> list[Path]:
    """Return the sorted slice files paired with a ``*_full.png``.

    Looks for siblings named ``<stem>_NNN.png`` next to ``full_path``.
    Empty list if none found.
    """
    full_path = Path(full_path)
    name = full_path.name
    if not name.endswith("_full.png"):
        return []
    stem = name[: -len("_full.png")]
    parent = full_path.parent
    candidates: list[tuple[int, Path]] = []
    prefix = f"{stem}_"
    for entry in parent.iterdir():
        if not entry.is_file() or not entry.name.startswith(prefix):
            continue
        suffix = entry.name[len(prefix) :]
        if not suffix.endswith(".png"):
            continue
        index_part = suffix[: -len(".png")]
        if not index_part.isdigit():
            continue
        candidates.append((int(index_part), entry))
    candidates.sort(key=lambda pair: pair[0])
    return [path for _, path in candidates]
