"""Harbor task templates baked into the site-generator image.

The site-gen container, after a successful run (sanity + playwright +
screenshot capture + screen recording capture), assembles a complete
Harbor task directory at ``/workspace/harbor/`` using:

- the rendered template files placed under ``/workspace/harbor_template/``
  (Dockerfile, instruction.md, task.toml, solve.sh, test.sh, grader/run.py)
- the assembly script at ``/workspace/assemble_harbor.py``

The volume mount on the host (``attempt.harbor_dir`` ↔
``/workspace/harbor``) means the assembled directory lands at
``Runs/SiteGeneration/<task_id>/attempt-NNN/harbor/`` after the container
exits, ready to be consumed by ``harbor run -p <path>``.

Each ``render_*`` function returns a string. The strings are written out
verbatim by ``build_env.prepare_env`` at site-gen image build time.

The harbor task ``instruction.md`` and ``task.toml`` are parameterized by
the ``framework`` of the design-to-code target — one of
``html_css`` (default), ``react_css``, ``react_tailwind``, or
``solid_tailwind``. The reference site itself is always generated as
plain HTML+CSS (so the screenshots and recordings are framework-agnostic
ground truth); the framework parameter only changes the instructions the
harbor agent under test reads.
"""
from typing import Literal


Framework = Literal["html_css", "react_css", "react_tailwind", "solid_tailwind"]
ALL_FRAMEWORKS: tuple[Framework, ...] = (
    "html_css",
    "react_css",
    "react_tailwind",
    "solid_tailwind",
)
DEFAULT_FRAMEWORK: Framework = "html_css"


HARBOR_BASE_IMAGE = "node:22-slim"
HARBOR_AGENT_TIMEOUT_SECONDS = 1800
HARBOR_VERIFIER_TIMEOUT_SECONDS = 600
HARBOR_BUILD_TIMEOUT_SECONDS = 1200
HARBOR_CPUS = 2
HARBOR_MEMORY_MB = 4096


_FRAMEWORK_TITLE = {
    "html_css": "Replicate the screenshots and recordings as an HTML+CSS+JS website",
    "react_css": "Replicate the screenshots and recordings as a React + plain CSS website",
    "react_tailwind": "Replicate the screenshots and recordings as a React + Tailwind CSS website",
    "solid_tailwind": "Replicate the screenshots and recordings as a Solid JS + Tailwind CSS website",
}

_FRAMEWORK_TOML_DESCRIPTION = {
    "html_css": "Replicate a {page_count}-page website (including its motion design) from screenshots and video recordings using HTML, CSS, and vanilla JavaScript.",
    "react_css": "Replicate a {page_count}-page website (including its motion design) from screenshots and video recordings using React (Vite multi-page mode) with plain CSS.",
    "react_tailwind": "Replicate a {page_count}-page website (including its motion design) from screenshots and video recordings using React (Vite multi-page mode) styled with Tailwind CSS.",
    "solid_tailwind": "Replicate a {page_count}-page website (including its motion design) from screenshots and video recordings using Solid JS (Vite multi-page mode) styled with Tailwind CSS.",
}

_FRAMEWORK_TOML_KEYWORDS = {
    "html_css": ["design-to-code", "web", "html", "css", "js", "animation", "multi-page"],
    "react_css": ["design-to-code", "web", "react", "vite", "css", "animation", "multi-page"],
    "react_tailwind": ["design-to-code", "web", "react", "vite", "tailwind", "animation", "multi-page"],
    "solid_tailwind": ["design-to-code", "web", "solid", "vite", "tailwind", "animation", "multi-page"],
}


def _framework_lede(framework: Framework) -> str:
    """Opening paragraph: what the agent is replicating in, and which language tier."""
    if framework == "html_css":
        return (
            "You are given full-page screenshots **and video recordings** of "
            "every page of a multi-page website. Your job is to replicate "
            "each page as faithfully as possible — both the steady-state "
            "visual design (from screenshots) and the motion design (from "
            "recordings) — using HTML, CSS, and vanilla JavaScript."
        )
    if framework == "react_css":
        return (
            "You are given full-page screenshots **and video recordings** of "
            "every page of a multi-page website. Your job is to replicate "
            "each page as faithfully as possible — both the steady-state "
            "visual design (from screenshots) and the motion design (from "
            "recordings) — using **React** (function components, JSX) styled "
            "with **plain CSS**, built into static HTML+CSS+JS with Vite in "
            "multi-page mode."
        )
    if framework == "react_tailwind":
        return (
            "You are given full-page screenshots **and video recordings** of "
            "every page of a multi-page website. Your job is to replicate "
            "each page as faithfully as possible — both the steady-state "
            "visual design (from screenshots) and the motion design (from "
            "recordings) — using **React** (function components, JSX) styled "
            "with **Tailwind CSS**, built into static HTML+CSS+JS with Vite "
            "in multi-page mode."
        )
    if framework == "solid_tailwind":
        return (
            "You are given full-page screenshots **and video recordings** of "
            "every page of a multi-page website. Your job is to replicate "
            "each page as faithfully as possible — both the steady-state "
            "visual design (from screenshots) and the motion design (from "
            "recordings) — using **Solid JS** (Solid components, signals) "
            "styled with **Tailwind CSS**, built into static HTML+CSS+JS "
            "with Vite in multi-page mode."
        )
    raise ValueError(f"Unknown framework: {framework!r}")


def _framework_what_to_produce(framework: Framework, page_count: int) -> str:
    if framework == "html_css":
        return f"""Write your output as HTML, CSS, and vanilla JavaScript files under
`/app/site/`.

The `/app/site/` directory must contain:

- `/app/site/index.html` for `page_01.png` / `page_01.mp4`
- `/app/site/page_02.html` for `page_02.png` / `page_02.mp4`
- `/app/site/page_03.html` for `page_03.png` / `page_03.mp4`
- ... and so on through `/app/site/page_{page_count:02d}.html` for
  `page_{page_count:02d}.png` / `page_{page_count:02d}.mp4`

You may add any supporting files you need (CSS, SVG, vanilla JS, fonts)
under `/app/site/` and reference them from your HTML."""

    framework_label = {
        "react_css": "React (plain CSS)",
        "react_tailwind": "React (Tailwind CSS)",
        "solid_tailwind": "Solid JS (Tailwind CSS)",
    }[framework]
    vite_plugin_hint = {
        "react_css": "`@vitejs/plugin-react`",
        "react_tailwind": "`@vitejs/plugin-react` plus the official Tailwind Vite plugin (`@tailwindcss/vite`) or PostCSS+Tailwind",
        "solid_tailwind": "`vite-plugin-solid` plus the official Tailwind Vite plugin (`@tailwindcss/vite`) or PostCSS+Tailwind",
    }[framework]
    return f"""Build the site with {framework_label} and emit a fully-built static
output at `/app/site/`. The verifier serves `/app/site/` as a static
directory — your source can live anywhere inside `/app/site/`
(`src/`, `pages/`, wherever you like) as long as the served root has
the final built HTML+CSS+JS at the expected filenames.

After your build runs (e.g. `npm install && npm run build`), the
`/app/site/` directory must contain:

- `/app/site/index.html` for `page_01.png` / `page_01.mp4` (the built
  static HTML produced from your `{framework_label}` source for page 1)
- `/app/site/page_02.html` for `page_02.png` / `page_02.mp4`
- `/app/site/page_03.html` for `page_03.png` / `page_03.mp4`
- ... and so on through `/app/site/page_{page_count:02d}.html` for
  `page_{page_count:02d}.png` / `page_{page_count:02d}.mp4`
- bundled CSS / JS / asset files referenced by those HTML files

Use Vite in multi-page mode so each route gets its own HTML entry point
(https://vite.dev/guide/build.html#multi-page-app). Configure it with
{vite_plugin_hint}. If Vite emits build output to `dist/`, copy or move
the contents into `/app/site/` so the served root has the final files
at the expected names.

`node` and `npm` are pre-installed in the verifier image; you can
install dependencies and run the build inside the container without
network restrictions."""


def _framework_constraints(framework: Framework) -> str:
    if framework == "html_css":
        return """- Use only HTML, CSS, and vanilla JavaScript. No build step.
- Use CSS `@keyframes` and `transition` for animations; use
  `IntersectionObserver` (vanilla JS) for scroll-triggered reveals;
  `requestAnimationFrame` for custom tweens. You may also pull in
  animation libraries (GSAP, Anime.js, Framer Motion, AOS, Lottie,
  ScrollMagic, motion-one, etc.) if they help replicate the reference.
- Do not use React, Vue, Svelte, Solid, Tailwind, Bootstrap, or any
  component library or CSS framework.
- Do not use external images, copied website assets, or remote media.
  All visuals must be inline SVG, local SVG files under `/app/site/`,
  or pure CSS.
- Free fonts only: Google Fonts or system web-safe stacks.
- Do not start any server. Just generate the files.
- Do not add backend functionality. Visual replication is what matters;
  functionality (forms, search, real navigation behavior) is out of scope."""

    if framework == "react_css":
        styling = (
            "- Style with **plain CSS** (CSS files imported by components, or\n"
            "  CSS modules). Do **not** use Tailwind, styled-components,\n"
            "  Emotion, vanilla-extract, or any CSS framework / CSS-in-JS\n"
            "  library."
        )
    elif framework == "react_tailwind":
        styling = (
            "- Style with **Tailwind CSS** utility classes. Bespoke CSS\n"
            "  files / modules are allowed only where Tailwind cannot\n"
            "  express the design (e.g. complex `@keyframes`). Do not use\n"
            "  styled-components, Emotion, or any other CSS-in-JS library.\n"
            "- Do not use Tailwind-based component libraries\n"
            "  (shadcn/ui, daisyUI, Headless UI, Flowbite, etc.) — use\n"
            "  Tailwind utilities directly."
        )
    else:  # solid_tailwind
        styling = (
            "- Style with **Tailwind CSS** utility classes. Bespoke CSS\n"
            "  files are allowed only where Tailwind cannot express the\n"
            "  design (e.g. complex `@keyframes`).\n"
            "- Do not use Tailwind-based component libraries (daisyUI,\n"
            "  Kobalte, etc.) — use Tailwind utilities directly."
        )

    if framework in ("react_css", "react_tailwind"):
        source_lang = (
            "- Source layer: **React** function components with JSX.\n"
            "  Use React hooks (`useState`, `useEffect`, `useRef`, etc.)\n"
            "  for state and lifecycle.\n"
            "- Do not use Vue, Svelte, Solid, Angular, or any other UI\n"
            "  framework alongside React.\n"
            "- Do not use React component libraries (MUI, Chakra, Ant\n"
            "  Design, Mantine, Radix UI primitives wrapped as components,\n"
            "  etc.). Build components yourself."
        )
        animation_libs = (
            "- Implement motion with whatever fits best: CSS `@keyframes` /\n"
            "  `transition` and vanilla `IntersectionObserver` (orchestrated\n"
            "  from React hooks) for scroll-triggered reveals, or third-party\n"
            "  animation libraries (Framer Motion, GSAP, react-spring,\n"
            "  react-transition-group, AOS, Lottie, ScrollMagic, etc.) where\n"
            "  they make replication cleaner. Your choice."
        )
    else:  # solid_tailwind
        source_lang = (
            "- Source layer: **Solid JS** components with JSX. Use Solid\n"
            "  signals (`createSignal`, `createMemo`, `createEffect`,\n"
            "  `onMount`) for state and lifecycle.\n"
            "- Do not use React, Vue, Svelte, Angular, or any other UI\n"
            "  framework alongside Solid.\n"
            "- Do not use Solid component libraries (Kobalte UI, Ark UI,\n"
            "  etc.). Build components yourself."
        )
        animation_libs = (
            "- Implement motion with whatever fits best: CSS `@keyframes` /\n"
            "  `transition` and vanilla `IntersectionObserver` (orchestrated\n"
            "  from Solid effects / `onMount`) for scroll-triggered reveals,\n"
            "  or third-party animation libraries (motion-one, GSAP,\n"
            "  Anime.js, AOS, Lottie, ScrollMagic, etc.) where they make\n"
            "  replication cleaner. Your choice."
        )

    return f"""{source_lang}
{styling}
- Build with **Vite in multi-page mode** so each page gets its own
  HTML entry point. Emit final HTML files into `/app/site/` at the
  filenames specified above (`index.html`, `page_NN.html`).
{animation_libs}
- Do not use external images, copied website assets, or remote media.
  All visuals must be inline SVG, local SVG files under your source
  tree, or pure CSS / Tailwind utilities.
- Free fonts only: Google Fonts or system web-safe stacks.
- The verifier serves `/app/site/` as a static directory. You must
  run your build before the verifier evaluates — the easiest pattern
  is to `npm install && npm run build` at the end of your work and
  ensure the built artifacts land at `/app/site/index.html`,
  `/app/site/page_NN.html`, plus their bundled CSS/JS/assets.
- Do not start any persistent server. Just produce the final built
  files at `/app/site/`.
- Do not add backend functionality. Visual replication is what matters;
  functionality (forms, search, real navigation behavior) is out of
  scope."""


def render_harbor_dockerfile(*, base_image: str = HARBOR_BASE_IMAGE) -> str:
    return f"""FROM {base_image}

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    curl \\
    ffmpeg \\
    git \\
    python3 \\
    python3-pip \\
    python3-venv \\
    && rm -rf /var/lib/apt/lists/*

ENV NODE_PATH=/usr/local/lib/node_modules
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN npm install -g playwright \\
    && mkdir -p /ms-playwright \\
    && playwright install --with-deps chromium \\
    && chmod -R a+rx /ms-playwright

RUN pip3 install --break-system-packages --no-cache-dir \\
    beautifulsoup4 \\
    playwright

RUN useradd -m -s /bin/bash agent

RUN mkdir -p /app/site /app/prompt /logs/agent /logs/verifier \\
    && chown -R agent:agent /app /logs/agent

COPY --chown=agent:agent prompt /app/prompt
RUN chmod -R a+rX /app/prompt

COPY solution_assets /opt/solution
RUN chown -R root:root /opt/solution \\
    && chmod -R go-rwx /opt/solution \\
    && chmod 700 /opt/solution

COPY grader /opt/grader
RUN chown -R root:root /opt/grader \\
    && chmod -R go-rwx /opt/grader \\
    && chmod 700 /opt/grader

USER agent
WORKDIR /app
"""


def render_harbor_instruction_md(
    *,
    page_count: int,
    framework: Framework = DEFAULT_FRAMEWORK,
) -> str:
    title = _FRAMEWORK_TITLE[framework]
    lede = _framework_lede(framework)
    what_to_produce = _framework_what_to_produce(framework, page_count)
    constraints = _framework_constraints(framework)
    return f"""# {title}

{lede}

## Inputs

### Screenshots — `/app/prompt/screenshots/`

Contains {page_count} full-page screenshots, one per page of the website,
plus viewport-sized slices for easier inspection of long pages:

- `page_01.png` ... `page_{page_count:02d}.png` — tall full-page captures
- `page_NN_full.png` — same tall image with the `_full` suffix
- `page_NN_001.png`, `page_NN_002.png`, ... — 1440x1000 viewport slices of
  the same page, useful if the tall PNG is hard to navigate

All captures are at a 1440 pixel viewport width. `page_01.png` is the home
page.

### Video recordings — `/app/prompt/screenrecordings/`

Contains {page_count} mp4 recordings, one per page, captured at 1440x1000
viewport at 25 fps:

- `page_01.mp4` ... `page_{page_count:02d}.mp4`

Each recording shows the page from top to bottom over roughly 10-20 seconds.
It demonstrates:

- **On-load animations** — visible during the initial hold at the top of the
  page (about 2.5 seconds before any scrolling begins).
- **Scroll-triggered reveal animations** — visible as sections enter the
  viewport during the eased scroll.
- **Looped / ambient motion** — visible throughout the recording
  (marquees, pulses, gradient sweeps, parallax drifts, etc.).
- *Note*: hover-triggered animations are not exercised in the recording. If
  the screenshots show hover-state alternates, use them as a hint.

You will not be given any other information about the website. There is no
design document, no blueprint, no copy file, no asset list. Everything you
need to reproduce the design and its motion is in the screenshots and
recordings.

## What to produce

{what_to_produce}

## Hard requirements

{constraints}

Aim to match layout, color, typography, spacing, and content positioning
as closely as the screenshots allow. Match the motion design (entrance
animations, scroll reveals, looped ambient motion, hover affordances) as
closely as the recordings and screenshots together allow. Where text is
unreadable in the screenshot, use plausible filler that matches the
visible style.

## Tools available

`ffmpeg` and `ffprobe` are installed and on `$PATH` if you find it useful
to extract individual frames from the recordings for closer inspection.
There is no requirement to use them.
"""


def render_harbor_task_toml(
    *,
    task_id: str,
    page_count: int,
    framework: Framework = DEFAULT_FRAMEWORK,
    agent_timeout_seconds: int = HARBOR_AGENT_TIMEOUT_SECONDS,
    verifier_timeout_seconds: int = HARBOR_VERIFIER_TIMEOUT_SECONDS,
    build_timeout_seconds: int = HARBOR_BUILD_TIMEOUT_SECONDS,
    cpus: int = HARBOR_CPUS,
    memory_mb: int = HARBOR_MEMORY_MB,
) -> str:
    description = _FRAMEWORK_TOML_DESCRIPTION[framework].format(page_count=page_count)
    keywords = _FRAMEWORK_TOML_KEYWORDS[framework]
    keywords_str = ", ".join(f'"{k}"' for k in keywords)
    return f"""schema_version = "1.1"

[task]
name = "web-weaver/{task_id}"
description = "{description}"
keywords = [{keywords_str}]

[metadata]
task_id = "{task_id}"
category = "design-to-code"
framework = "{framework}"
page_count = {page_count}
generator = "web-weaver"

[agent]
timeout_sec = {agent_timeout_seconds}.0
user = "agent"

[verifier]
timeout_sec = {verifier_timeout_seconds}.0
user = "root"

[environment]
build_timeout_sec = {build_timeout_seconds}.0
os = "linux"
cpus = {cpus}
memory_mb = {memory_mb}
allow_internet = true
"""


def render_harbor_oracle_script() -> str:
    return r"""#!/bin/bash
# Oracle solver: copies the pre-renamed reference site that lives alongside
# this script (in /solution/site/) into /app/site/.
#
# The oracle answer is shipped inside the Harbor task's solution/ directory
# and is only copied into /solution/ in the container during Oracle runs,
# never during regular agent runs. The oracle therefore reads only what
# Harbor mounts at /solution/, with no other shared state to worry about.

set -euo pipefail

ORACLE_SITE_DIR="/solution/site"
SITE_DIR="/app/site"

if [ ! -d "${ORACLE_SITE_DIR}" ]; then
  echo "Missing oracle site at ${ORACLE_SITE_DIR}" >&2
  exit 1
fi

mkdir -p "${SITE_DIR}"
rm -rf "${SITE_DIR:?}"/*
cp -R "${ORACLE_SITE_DIR}"/. "${SITE_DIR}"/

echo "Oracle copied $(find "${SITE_DIR}" -maxdepth 1 -name '*.html' | wc -l) HTML page(s) to ${SITE_DIR}"
"""


def render_harbor_test_script() -> str:
    return r"""#!/bin/bash
# Verifier entry point. Runs as root (per task.toml [verifier].user = "root").
# Invokes /opt/grader/run.py with the locked grader interface and writes
# Harbor's reward.txt from the resulting reward.json["score"].

set -euo pipefail

REWARD_JSON="/logs/verifier/reward.json"
REWARD_TXT="/logs/verifier/reward.txt"
CAPTURES_DIR="/logs/verifier/agent_screenshots"
RECORDINGS_DIR="/logs/verifier/agent_screenrecordings"

mkdir -p /logs/verifier "${CAPTURES_DIR}" "${RECORDINGS_DIR}"

python3 /opt/grader/run.py \
  --agent-site /app/site \
  --prompt /app/prompt \
  --solution /opt/solution \
  --captures-out "${CAPTURES_DIR}" \
  --recordings-out "${RECORDINGS_DIR}" \
  --reward-out "${REWARD_JSON}"

python3 - "${REWARD_JSON}" "${REWARD_TXT}" <<'PYEOF'
import json
import sys
from pathlib import Path

reward_json_path = Path(sys.argv[1])
reward_txt_path = Path(sys.argv[2])

reward = json.loads(reward_json_path.read_text(encoding="utf-8"))
score = reward.get("score")
if not isinstance(score, (int, float)):
    raise SystemExit(f"Grader did not produce a numeric score: {reward!r}")

reward_txt_path.write_text(f"{float(score):.6f}\n", encoding="utf-8")
PYEOF

echo "Verifier wrote ${REWARD_JSON} and ${REWARD_TXT}"
"""


def render_harbor_placeholder_grader_script() -> str:
    return r'''#!/usr/bin/env python3
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
'''


def render_assemble_harbor_script() -> str:
    return r'''#!/usr/bin/env python3
"""Assembles a complete Harbor task directory at /workspace/harbor/.

Run inside the site-gen container after sanity + playwright + screenshot
capture + screen recording capture all succeed. Reads:

- /workspace/input/blueprint.json       (slug order, used only to drive the
                                         indexed renaming; never appears in
                                         the assembled harbor task)
- /workspace/output/reference_site/     (the agent-generated site)
- /workspace/validation/screenshots/    (per-slug screenshots)
- /workspace/validation/screenrecordings/  (per-slug mp4 recordings)
- /workspace/harbor_template/           (pre-rendered Dockerfile, instruction.md,
                                         task.toml, solve.sh, test.sh, grader/run.py)

Writes:

    /workspace/harbor/
      instruction.md
      task.toml
      environment/
        Dockerfile
        prompt/
          screenshots/page_01.png .. page_NN.png   # agent-readable, neutral filenames
          screenrecordings/page_01.mp4 .. page_NN.mp4  # agent-readable, indexed
        solution_assets/                           # baked into image at /opt/solution, root-only
          screenshots/<slug>/<slug>_full.png + slices
          screenrecordings/<slug>.mp4
        grader/
          run.py
      solution/                                    # mounted only for Harbor Oracle runs
        solve.sh
        site/                     # reference_site with indexed renaming
      tests/
        test.sh
"""
import json
import shutil
from pathlib import Path


WORKSPACE = Path("/workspace")
INPUT_DIR = WORKSPACE / "input"
REFERENCE_SITE_DIR = WORKSPACE / "output" / "reference_site"
SCREENSHOTS_DIR = WORKSPACE / "validation" / "screenshots"
SCREENRECORDINGS_DIR = WORKSPACE / "validation" / "screenrecordings"
TEMPLATE_DIR = WORKSPACE / "harbor_template"
HARBOR_DIR = WORKSPACE / "harbor"


def clean_output_dir() -> None:
    if HARBOR_DIR.exists():
        for child in HARBOR_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    HARBOR_DIR.mkdir(parents=True, exist_ok=True)


def write_top_level_files() -> None:
    shutil.copy2(TEMPLATE_DIR / "instruction.md", HARBOR_DIR / "instruction.md")
    shutil.copy2(TEMPLATE_DIR / "task.toml", HARBOR_DIR / "task.toml")


def write_environment(slugs):
    environment_dir = HARBOR_DIR / "environment"
    environment_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(TEMPLATE_DIR / "Dockerfile", environment_dir / "Dockerfile")

    prompt_screenshots_dir = environment_dir / "prompt" / "screenshots"
    prompt_screenshots_dir.mkdir(parents=True, exist_ok=False)
    for index, slug in enumerate(slugs, start=1):
        slug_dir = SCREENSHOTS_DIR / slug
        full_source = slug_dir / f"{slug}_full.png"
        if not full_source.is_file():
            raise SystemExit(
                f"Missing full-page screenshot for slug {slug!r} at {full_source}"
            )
        full_destination = prompt_screenshots_dir / f"page_{index:02d}_full.png"
        shutil.copy2(full_source, full_destination)
        # Also copy the legacy tall name page_NN.png so existing graders that
        # expect a single tall PNG (no _full suffix) keep working.
        shutil.copy2(full_source, prompt_screenshots_dir / f"page_{index:02d}.png")

        slice_index = 0
        for slice_path in sorted(slug_dir.iterdir()):
            if not slice_path.is_file():
                continue
            stem = slice_path.stem
            if not stem.startswith(f"{slug}_"):
                continue
            suffix = stem[len(slug) + 1 :]
            if not suffix.isdigit():
                continue
            slice_index += 1
            shutil.copy2(
                slice_path,
                prompt_screenshots_dir / f"page_{index:02d}_{int(suffix):03d}.png",
            )

    if SCREENRECORDINGS_DIR.is_dir():
        prompt_screenrecordings_dir = environment_dir / "prompt" / "screenrecordings"
        prompt_screenrecordings_dir.mkdir(parents=True, exist_ok=False)
        for index, slug in enumerate(slugs, start=1):
            recording_source = SCREENRECORDINGS_DIR / f"{slug}.mp4"
            if recording_source.is_file():
                shutil.copy2(
                    recording_source,
                    prompt_screenrecordings_dir / f"page_{index:02d}.mp4",
                )

    solution_assets_dir = environment_dir / "solution_assets"
    solution_assets_dir.mkdir(parents=True, exist_ok=False)
    shutil.copytree(SCREENSHOTS_DIR, solution_assets_dir / "screenshots")
    if SCREENRECORDINGS_DIR.is_dir():
        shutil.copytree(SCREENRECORDINGS_DIR, solution_assets_dir / "screenrecordings")

    grader_dir = environment_dir / "grader"
    grader_dir.mkdir(parents=True, exist_ok=False)
    grader_path = grader_dir / "run.py"
    shutil.copy2(TEMPLATE_DIR / "grader" / "run.py", grader_path)
    grader_path.chmod(0o755)


def write_solution(slugs):
    solution_dir = HARBOR_DIR / "solution"
    solution_dir.mkdir(parents=True, exist_ok=False)

    solve_path = solution_dir / "solve.sh"
    shutil.copy2(TEMPLATE_DIR / "solve.sh", solve_path)
    solve_path.chmod(0o755)

    oracle_site_dir = solution_dir / "site"
    oracle_site_dir.mkdir(parents=True, exist_ok=False)

    for entry in REFERENCE_SITE_DIR.iterdir():
        if entry.is_dir():
            shutil.copytree(entry, oracle_site_dir / entry.name)
        elif entry.suffix.lower() != ".html":
            shutil.copy2(entry, oracle_site_dir / entry.name)

    for index, slug in enumerate(slugs, start=1):
        source_name = "index.html" if slug == "home" else f"{slug}.html"
        source = REFERENCE_SITE_DIR / source_name
        if not source.is_file():
            raise SystemExit(f"Reference site missing page: {source}")
        destination_name = "index.html" if index == 1 else f"page_{index:02d}.html"
        shutil.copy2(source, oracle_site_dir / destination_name)


def write_tests():
    tests_dir = HARBOR_DIR / "tests"
    tests_dir.mkdir(parents=True, exist_ok=False)
    test_path = tests_dir / "test.sh"
    shutil.copy2(TEMPLATE_DIR / "test.sh", test_path)
    test_path.chmod(0o755)


def main():
    blueprint_path = INPUT_DIR / "blueprint.json"
    if not blueprint_path.is_file():
        raise SystemExit(f"Missing {blueprint_path}")
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    pages = blueprint.get("pages") or []
    if not pages:
        raise SystemExit("Blueprint has no pages")
    slugs = [page["slug"] for page in pages]

    if not REFERENCE_SITE_DIR.is_dir():
        raise SystemExit(f"Missing reference site at {REFERENCE_SITE_DIR}")
    if not SCREENSHOTS_DIR.is_dir():
        raise SystemExit(f"Missing screenshots at {SCREENSHOTS_DIR}")
    if not TEMPLATE_DIR.is_dir():
        raise SystemExit(f"Missing harbor templates at {TEMPLATE_DIR}")

    clean_output_dir()
    write_top_level_files()
    write_environment(slugs)
    write_solution(slugs)
    write_tests()

    print(f"Assembled Harbor task at {HARBOR_DIR} for {len(slugs)} page(s).")


if __name__ == "__main__":
    main()
'''
