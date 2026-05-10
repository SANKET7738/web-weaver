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
"""


HARBOR_BASE_IMAGE = "node:22-slim"
HARBOR_AGENT_TIMEOUT_SECONDS = 1800
HARBOR_VERIFIER_TIMEOUT_SECONDS = 600
HARBOR_BUILD_TIMEOUT_SECONDS = 1200
HARBOR_CPUS = 2
HARBOR_MEMORY_MB = 4096


def render_harbor_dockerfile(*, base_image: str = HARBOR_BASE_IMAGE) -> str:
    return f"""FROM {base_image}

RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates \\
    curl \\
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


def render_harbor_instruction_md(*, page_count: int) -> str:
    return f"""# Replicate the screenshots as a static HTML+CSS website

You are given full-page screenshots of every page of a multi-page website.
Your job is to replicate each page as faithfully as possible using only
static HTML and CSS.

## Inputs

You can read screenshots in `/app/prompt/screenshots/`. The directory
contains exactly {page_count} full-page screenshots, one per page of the
website, named in order:

- `page_01.png`
- `page_02.png`
- ...
- `page_{page_count:02d}.png`

Each PNG is a tall image showing the entire page from top to bottom at a
1440 pixel viewport width. The first screenshot (`page_01.png`) is the
home page.

You will not be given any other information about the website. There is
no design document, no blueprint, no copy file, no asset list. Everything
you need to reproduce the design is in the screenshots.

## What to produce

Write your output as static HTML and CSS files under `/app/site/`.

The `/app/site/` directory must contain:

- `/app/site/index.html` for `page_01.png`
- `/app/site/page_02.html` for `page_02.png`
- `/app/site/page_03.html` for `page_03.png`
- ... and so on through `/app/site/page_{page_count:02d}.html` for
  `page_{page_count:02d}.png`

You may add any supporting files you need (CSS, SVG, vanilla JS, fonts)
under `/app/site/` and reference them from your HTML.

## Hard requirements

- Use only HTML, CSS, and (optionally) vanilla JavaScript for visual-only
  behavior such as a mobile menu toggle. No build step.
- Do not use React, Vue, Svelte, Tailwind, Bootstrap, or any component
  library or CSS framework.
- Do not use external images, copied website assets, or remote media.
  All visuals must be inline SVG, local SVG files under `/app/site/`,
  or pure CSS.
- Free fonts only: Google Fonts or system web-safe stacks.
- Do not start any server. Just generate the files.
- Do not add backend functionality. Visual replication is what matters;
  functionality (forms, search, real navigation behavior) is out of scope.

Aim to match layout, color, typography, spacing, and content positioning
as closely as the screenshots allow. Where text is unreadable in the
screenshot, use plausible filler that matches the visible style.
"""


def render_harbor_task_toml(
    *,
    task_id: str,
    page_count: int,
    docker_image: str,
    agent_timeout_seconds: int = HARBOR_AGENT_TIMEOUT_SECONDS,
    verifier_timeout_seconds: int = HARBOR_VERIFIER_TIMEOUT_SECONDS,
    build_timeout_seconds: int = HARBOR_BUILD_TIMEOUT_SECONDS,
    cpus: int = HARBOR_CPUS,
    memory_mb: int = HARBOR_MEMORY_MB,
) -> str:
    return f"""schema_version = "1.1"

[task]
name = "web-weaver/{task_id}"
description = "Replicate a {page_count}-page website from full-page screenshots using static HTML and CSS."
keywords = ["design-to-code", "web", "html", "css", "multi-page"]

[metadata]
task_id = "{task_id}"
category = "design-to-code"
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
docker_image = "{docker_image}"
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

mkdir -p /logs/verifier "${CAPTURES_DIR}"

python3 /opt/grader/run.py \
  --agent-site /app/site \
  --prompt /app/prompt \
  --solution /opt/solution \
  --captures-out "${CAPTURES_DIR}" \
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
        source = SCREENSHOTS_DIR / slug / f"{slug}_full.png"
        if not source.is_file():
            raise SystemExit(
                f"Missing full-page screenshot for slug {slug!r} at {source}"
            )
        destination = prompt_screenshots_dir / f"page_{index:02d}.png"
        shutil.copy2(source, destination)

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


def harbor_image_tag(task_id: str) -> str:
    return f"web-weaver-harbor-{task_id.lower()}:latest"
