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

mkdir -p /workspace/output/reference_site /workspace/logs
cd /workspace

if [ -z "${{ANTHROPIC_API_KEY:-}}" ]; then
  echo "ANTHROPIC_API_KEY is required to run Claude Code." | tee /workspace/logs/agent_error.txt
  exit 1
fi

AGENT_TIMEOUT_SECONDS="${{SITEGEN_AGENT_TIMEOUT_SECONDS:-1800}}"

set +e
timeout "${{AGENT_TIMEOUT_SECONDS}}" claude --dangerously-skip-permissions \\
  -p "$(cat /workspace/task.md)" \\
  --output-format stream-json \\
  --verbose \\
  > /workspace/logs/run.jsonl 2>&1
AGENT_EXIT_CODE=$?
set -e

echo "${{AGENT_EXIT_CODE}}" > /workspace/logs/agent_exit_code.txt
if [ "${{AGENT_EXIT_CODE}}" -eq 124 ]; then
  echo "Claude timed out after ${{AGENT_TIMEOUT_SECONDS}} seconds" > /workspace/logs/agent_timeout.txt
fi

cd /workspace/output/reference_site
exec python3 -m http.server {DEFAULT_PORT} --bind 0.0.0.0
"""
