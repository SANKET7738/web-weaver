DEFAULT_PORT = 3000


def build_task_prompt(task_id: str) -> str:
    return f"""
You are a helpful coding assistant who needs to build beautiful websites.

The exact inputs are provided here:
- /workspace/input/concept.json
- /workspace/input/blueprint.json
- /workspace/input/design_plan.json

Build a static multi-page reference website using only:
- HTML
- CSS
- optional vanilla JavaScript for visual-only behavior
- inline SVG, local SVG files, or CSS-generated visuals for asset ideas

Hard requirements:
- Write all site files under /workspace/output/reference_site/.
- The home page must be /workspace/output/reference_site/index.html.
- Every non-home blueprint page must have a matching <slug>.html file.
- Add data-page-slug="<slug>" to each page's body element.
- Use every blueprint section id as the corresponding HTML section id.
- Add data-section-type="<section type>" to each section.
- Use blueprint.json for page structure and copy.
- Use design_plan.json as the source of truth for visual design.
- Implement asset ideas yourself as inline SVG, local SVG files, or CSS visuals.
- Use only freely accessible fonts, such as Google Fonts or system web-safe stacks.
- Do not use React, Vue, Svelte, Tailwind, Bootstrap, or component libraries.
- Do not use external images, crawled assets, copied website assets, or remote media.
- Do not add backend functionality.
- Navigation links may work between pages, but functionality beyond visual behavior is out of scope.
- Do not start a server or worry about ports. Only generate the site files.

A good final structure is:

/workspace/output/reference_site/
  index.html
  <page-slug>.html
  styles.css
  script.js
  assets/

If you create SVG assets, keep them local to /workspace/output/reference_site/assets/
or inline them in the HTML.
""".strip() + "\n"


def build_entrypoint_script() -> str:
    return f"""#!/bin/bash
set -euo pipefail

mkdir -p /workspace/output/reference_site /workspace/logs /workspace/validation/screenshots /workspace/validation/screenrecordings
cd /workspace

log() {{
  echo "[$(date -Iseconds)] $*" | tee -a /workspace/logs/entrypoint.log
}}

if [ -z "${{ANTHROPIC_API_KEY:-}}" ]; then
  echo "ANTHROPIC_API_KEY is required to run Claude Code." | tee /workspace/logs/agent_error.txt
  exit 1
fi

AGENT_TIMEOUT_SECONDS="${{SITEGEN_AGENT_TIMEOUT_SECONDS:-1800}}"

log "Starting Claude Code with timeout ${{AGENT_TIMEOUT_SECONDS}} seconds"
set +e
timeout "${{AGENT_TIMEOUT_SECONDS}}" claude --dangerously-skip-permissions \\
  -p "$(cat /workspace/task.md)" \\
  --output-format stream-json \\
  --verbose \\
  > /workspace/logs/claude_stream.jsonl 2>&1
AGENT_EXIT_CODE=$?
set -e

echo "${{AGENT_EXIT_CODE}}" > /workspace/logs/agent_exit_code.txt
if [ "${{AGENT_EXIT_CODE}}" -eq 124 ]; then
  log "Claude timed out after ${{AGENT_TIMEOUT_SECONDS}} seconds"
  echo "Claude timed out after ${{AGENT_TIMEOUT_SECONDS}} seconds" > /workspace/logs/agent_timeout.txt
else
  log "Claude exited with code ${{AGENT_EXIT_CODE}}"
fi

cd /workspace/output/reference_site
python3 -m http.server {DEFAULT_PORT} --bind 0.0.0.0 > /workspace/logs/server.log 2>&1 &
SERVER_PID=$!
echo "${{SERVER_PID}}" > /workspace/logs/server_pid.txt
log "Started static server on 0.0.0.0:{DEFAULT_PORT} with PID ${{SERVER_PID}}"

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:{DEFAULT_PORT} >/dev/null 2>&1; then
    SERVER_READY=1
    break
  fi
  sleep 1
done

if [ "${{SERVER_READY:-0}}" != "1" ]; then
  log "Static server did not become ready"
  echo "Static server did not become ready" > /workspace/logs/server_error.txt
else
  log "Running site generation sanity check"
  set +e
  python3 /workspace/sanity_check.py \\
    --blueprint /workspace/input/blueprint.json \\
    --design-plan /workspace/input/design_plan.json \\
    --site-dir /workspace/output/reference_site \\
    --base-url http://127.0.0.1:{DEFAULT_PORT} \\
    --out /workspace/validation/sanity_report.json
  SANITY_EXIT_CODE=$?
  set -e
  echo "${{SANITY_EXIT_CODE}}" > /workspace/logs/sanity_exit_code.txt
  log "Sanity check exited with code ${{SANITY_EXIT_CODE}}"

  log "Running Playwright browser sanity check"
  set +e
  node /workspace/playwright_check.js \\
    --blueprint /workspace/input/blueprint.json \\
    --base-url http://127.0.0.1:{DEFAULT_PORT} \\
    --out /workspace/validation/playwright_report.json
  PLAYWRIGHT_EXIT_CODE=$?
  set -e
  echo "${{PLAYWRIGHT_EXIT_CODE}}" > /workspace/logs/playwright_exit_code.txt
  log "Playwright sanity check exited with code ${{PLAYWRIGHT_EXIT_CODE}}"

  log "Capturing viewport screenshot slices"
  set +e
  node /workspace/capture_screenshots.js \\
    --blueprint /workspace/input/blueprint.json \\
    --base-url http://127.0.0.1:{DEFAULT_PORT} \\
    --out-dir /workspace/validation/screenshots \\
    --report /workspace/validation/screenshot_capture_report.json
  SCREENSHOT_CAPTURE_EXIT_CODE=$?
  set -e
  echo "${{SCREENSHOT_CAPTURE_EXIT_CODE}}" > /workspace/logs/screenshot_capture_exit_code.txt
  log "Screenshot capture exited with code ${{SCREENSHOT_CAPTURE_EXIT_CODE}}"

  log "Capturing screen recordings"
  set +e
  node /workspace/capture_screenrecordings.js \\
    --blueprint /workspace/input/blueprint.json \\
    --base-url http://127.0.0.1:{DEFAULT_PORT} \\
    --out-dir /workspace/validation/screenrecordings \\
    --report /workspace/validation/screenrecording_capture_report.json
  SCREENRECORDING_CAPTURE_EXIT_CODE=$?
  set -e
  echo "${{SCREENRECORDING_CAPTURE_EXIT_CODE}}" > /workspace/logs/screenrecording_capture_exit_code.txt
  log "Screen recording capture exited with code ${{SCREENRECORDING_CAPTURE_EXIT_CODE}}"

  if [ "${{SANITY_EXIT_CODE:-1}}" = "0" ] \\
     && [ "${{PLAYWRIGHT_EXIT_CODE:-1}}" = "0" ] \\
     && [ "${{SCREENSHOT_CAPTURE_EXIT_CODE:-1}}" = "0" ] \\
     && [ "${{SCREENRECORDING_CAPTURE_EXIT_CODE:-1}}" = "0" ]; then
    log "All validations passed; assembling Harbor task at /workspace/harbor"
    set +e
    python3 /workspace/assemble_harbor.py > /workspace/logs/harbor_assemble.log 2>&1
    HARBOR_ASSEMBLE_EXIT_CODE=$?
    set -e
    echo "${{HARBOR_ASSEMBLE_EXIT_CODE}}" > /workspace/logs/harbor_assemble_exit_code.txt
    log "Harbor assembly exited with code ${{HARBOR_ASSEMBLE_EXIT_CODE}}"
  else
    log "Skipping Harbor assembly because one or more validations failed"
    echo "skipped" > /workspace/logs/harbor_assemble_exit_code.txt
  fi
fi

if [ -n "${{SERVER_PID:-}}" ] && kill -0 "${{SERVER_PID}}" 2>/dev/null; then
  log "Stopping static server (PID ${{SERVER_PID}})"
  kill "${{SERVER_PID}}" 2>/dev/null || true
  wait "${{SERVER_PID}}" 2>/dev/null || true
fi

log "Site generation pipeline complete; exiting"
"""
