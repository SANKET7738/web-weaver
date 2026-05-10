from web_weaver.site_generator.harbor_templates import (
    ALL_FRAMEWORKS,
    DEFAULT_FRAMEWORK,
    Framework,
)


DEFAULT_PORT = 3000


_MOTION_GUIDANCE = """Animations and visual flair — you have real creative latitude here:
- Add motion where it genuinely enhances the design. The page should feel
  alive when it loads and as the visitor scrolls, not like a static brochure.
- Motion patterns to draw from, picking what fits the brand voice and aesthetic:
  - On-load entrance animations on the hero (fade, slide-up, gentle scale,
    staggered word reveals) so the page feels like it is arriving.
  - Scroll-triggered reveal animations as each section enters the viewport.
    Use `IntersectionObserver` in vanilla JS, or your framework's idiomatic
    equivalent. Stagger child elements inside a section for richer reveals
    when it suits the layout.
  - Hover effects on cards, buttons, CTAs, nav items, and interactive media
    (translateY lift, color shift, shadow grow, scale, underline grow, icon
    swap) so affordances feel responsive.
  - Looped ambient motion where it fits the aesthetic — marquees of logos
    or stats, gentle pulses on primary CTAs, parallax drift on hero
    illustrations, slow conic / linear gradient sweeps, blinking cursors
    on terminal-flavored designs.
  - Micro-interactions on form fields, focus rings, accordion expand /
    collapse, modal slide-ins, tab switches — wherever the page has
    interactive surfaces.
- Calibrate intensity to the brand:
  - A playful consumer / friendly_consumer_app aesthetic can lean into 6 to
    10 distinct motion moments per page.
  - A heritage / editorial / luxury aesthetic should be far more restrained
    — 2 or 3 subtle, refined moments.
  - A maximalist / cyberpunk / vaporwave aesthetic should embrace bold,
    layered, saturated motion.
  - A swiss / minimalist aesthetic should use motion sparingly and only on
    structural / typographic moves.
- Do not animate everything. Choose deliberately — every animation should
  reinforce hierarchy, draw attention to a signature moment, or add delight.
- Respect prefers-reduced-motion if you want to, but it is optional for this
  reference site."""


def build_task_prompt(
    task_id: str,
    framework: Framework = DEFAULT_FRAMEWORK,
) -> str:
    if framework == "html_css":
        return _build_html_css_prompt(task_id)
    if framework == "react_css":
        return _build_react_css_prompt(task_id)
    if framework == "react_tailwind":
        return _build_react_tailwind_prompt(task_id)
    if framework == "solid_tailwind":
        return _build_solid_tailwind_prompt(task_id)
    raise ValueError(
        f"Unknown framework {framework!r}; expected one of {ALL_FRAMEWORKS}"
    )


def _build_html_css_prompt(task_id: str) -> str:
    return f"""
You are a helpful coding assistant who needs to build beautiful websites.

The exact inputs are provided here:
- /workspace/input/concept.json
- /workspace/input/blueprint.json
- /workspace/input/design_plan.json

Build a multi-page reference website with thoughtful motion design using only:
- HTML
- CSS (including @keyframes, transitions, and transforms for animations)
- vanilla JavaScript for visual-only behavior and animation orchestration
  (IntersectionObserver for scroll-triggered reveals, requestAnimationFrame
  for custom tweens, etc.)
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
- Animation libraries (GSAP, Anime.js, Framer Motion, AOS, Lottie, ScrollMagic,
  motion-one, etc.) are allowed if they help. Or use vanilla CSS keyframes /
  transitions and vanilla JavaScript — implementer's choice.
- Do not use external images, crawled assets, copied website assets, or remote media.
- Do not add backend functionality.
- Navigation links may work between pages, but functionality beyond visual behavior is out of scope.
- Do not start a server or worry about ports. Only generate the site files.

{_MOTION_GUIDANCE}

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


_FINAL_OUTPUT_CONTRACT = """Final output contract — same for every page, framework-agnostic:
- The home page must be /workspace/output/reference_site/index.html.
- Every non-home blueprint page must have a matching /workspace/output/reference_site/<slug>.html file
  where <slug> is exactly the blueprint page's slug.
- Each page's rendered DOM (what a headless browser sees after hydration / JS bootstrap)
  must carry:
  - `<body data-page-slug="<slug>">` on the body element.
  - Each section in the blueprint must be rendered as `<section id="<section_id>" data-section-type="<section_type>">`
    where the id and section_type come straight from blueprint.json.
- Use blueprint.json for page structure and copy.
- Use design_plan.json as the source of truth for visual design (palette, typography, layout, motion).
- Implement asset ideas yourself as inline SVG, local SVG files, or CSS visuals — no remote media.
- Use only freely accessible fonts: Google Fonts or system web-safe stacks. No proprietary fonts.
- Animation libraries (GSAP, Anime.js, Framer Motion, AOS, Lottie, ScrollMagic, motion-one,
  framework-idiomatic motion primitives, etc.) are allowed if they help. Use them or skip them at your discretion.
- Do not use external images, crawled assets, copied website assets, or remote media.
- Do not add backend functionality.
- Navigation links may work between pages, but functionality beyond visual behavior is out of scope.
- Do not start a server or worry about ports. Only produce the built static files.

The sitegen harness runs your build inside this container (which has Node 22, npm, Python, git,
ffmpeg, and Chromium pre-installed) and then serves /workspace/output/reference_site/ as a static
directory at http://127.0.0.1:3000/ for screenshot / recording capture. You have full internet
access for `npm install`."""


def _build_react_css_prompt(task_id: str) -> str:
    return f"""
You are a helpful coding assistant who needs to build beautiful websites.

The exact inputs are provided here:
- /workspace/input/concept.json
- /workspace/input/blueprint.json
- /workspace/input/design_plan.json

Build a multi-page reference website with thoughtful motion design using:
- **React** (function components with JSX, React hooks for state and lifecycle)
- **Plain CSS** (CSS files imported by components, or CSS Modules)
- **Vite in multi-page mode** to bundle and emit static HTML+CSS+JS
- inline SVG, local SVG files, or CSS-generated visuals for asset ideas

Tech stack hard requirements:
- Source code: React function components in `.jsx` or `.tsx` files. No class components needed.
- Styling: plain `.css` files (or CSS Modules `.module.css`). Do NOT use Tailwind,
  styled-components, Emotion, vanilla-extract, or any CSS framework / CSS-in-JS library.
- Build tool: Vite in multi-page mode
  (https://vite.dev/guide/build.html#multi-page-app) with `@vitejs/plugin-react`.
- Configure Vite with `rollupOptions.input` pointing at one HTML entry per blueprint page,
  so each page gets its own static HTML output.
- Do not use React component libraries (MUI, Chakra, Ant Design, Mantine, Radix, etc.).
  Build your own components — that is the entire point of this exercise.

Suggested working directory layout (you can deviate if you keep the final output contract):

/workspace/build/                   # your source tree + node_modules; not served
  package.json
  vite.config.js                    # MPA config: rollupOptions.input lists every page's HTML
  index.html                        # home page entry; references src/pages/home.jsx
  <page-slug>.html                  # one entry per non-home page
  src/
    pages/home.jsx
    pages/<page-slug>.jsx
    components/...                  # your shared components
    styles/...                      # plain CSS files imported by components
    assets/...                      # SVGs / icons you author

After your build:
- Run `npm install` and `npm run build` in /workspace/build/.
- Configure Vite so `build.outDir = '/workspace/output/reference_site'` and
  `build.emptyOutDir = true`. The built static HTML+CSS+JS will land directly in the
  served root.

{_FINAL_OUTPUT_CONTRACT}

{_MOTION_GUIDANCE}

Motion can be implemented with CSS `@keyframes` + `transition`, the Web Animations API,
`IntersectionObserver` orchestrated from React hooks, `requestAnimationFrame`, or any
animation library (Framer Motion, GSAP, react-spring, react-transition-group, AOS,
Lottie, ScrollMagic, etc.). Pick what fits the brand and aesthetic.
""".strip() + "\n"


def _build_react_tailwind_prompt(task_id: str) -> str:
    return f"""
You are a helpful coding assistant who needs to build beautiful websites.

The exact inputs are provided here:
- /workspace/input/concept.json
- /workspace/input/blueprint.json
- /workspace/input/design_plan.json

Build a multi-page reference website with thoughtful motion design using:
- **React** (function components with JSX, React hooks for state and lifecycle)
- **Tailwind CSS** (utility-first styling)
- **Vite in multi-page mode** to bundle and emit static HTML+CSS+JS
- inline SVG, local SVG files, or CSS-generated visuals for asset ideas

Tech stack hard requirements:
- Source code: React function components in `.jsx` or `.tsx` files.
- Styling: **Tailwind CSS utility classes**. Bespoke `.css` files are allowed only
  where Tailwind cannot express the design (e.g. complex `@keyframes`). Do NOT use
  styled-components, Emotion, or any CSS-in-JS library.
- Tailwind v4 with the official Vite plugin is the easiest setup
  (https://tailwindcss.com/docs/installation/using-vite):
  `npm install -D tailwindcss @tailwindcss/vite`, add `@tailwindcss/vite` to
  vite.config.js plugins, and put `@import "tailwindcss";` in your main CSS file.
- Build tool: Vite in multi-page mode
  (https://vite.dev/guide/build.html#multi-page-app) with `@vitejs/plugin-react`.
  Configure `rollupOptions.input` so each blueprint page has its own HTML entry.
- Express the design plan's palette and fonts via Tailwind's `@theme` block (v4) or
  via tailwind.config.js `theme.extend` (v3) — do NOT just inline raw hex values in
  arbitrary-value classes; the palette must be a first-class part of the theme so the
  whole site stays consistent.
- Do not use Tailwind-based component libraries (shadcn/ui, daisyUI, Headless UI,
  Flowbite, etc.). Use Tailwind utilities directly.
- Do not use React component libraries (MUI, Chakra, Ant Design, Mantine, Radix, etc.).

Suggested working directory layout (you can deviate if you keep the final output contract):

/workspace/build/                   # your source tree + node_modules; not served
  package.json
  vite.config.js                    # MPA + @vitejs/plugin-react + @tailwindcss/vite
  tailwind.config.js (optional in v4 if all theme lives in @theme)
  index.html                        # home page entry
  <page-slug>.html                  # one entry per non-home page
  src/
    pages/home.jsx
    pages/<page-slug>.jsx
    components/...
    styles/tailwind.css             # contains @import "tailwindcss"; + @theme {{...}}
    assets/...

After your build:
- Run `npm install` and `npm run build` in /workspace/build/.
- Set `build.outDir = '/workspace/output/reference_site'` and
  `build.emptyOutDir = true` in vite.config.js. The built static HTML+CSS+JS lands
  directly in the served root.

{_FINAL_OUTPUT_CONTRACT}

{_MOTION_GUIDANCE}

Motion: Tailwind has reasonable built-in `transition-*`, `animate-*` utilities for
simple cases, but for anything richer use CSS `@keyframes` (define in your CSS file
and reference via an arbitrary class), the Web Animations API, `IntersectionObserver`
orchestrated from React hooks, or animation libraries (Framer Motion, GSAP,
react-spring, react-transition-group, AOS, Lottie, etc.).
""".strip() + "\n"


def _build_solid_tailwind_prompt(task_id: str) -> str:
    return f"""
You are a helpful coding assistant who needs to build beautiful websites.

The exact inputs are provided here:
- /workspace/input/concept.json
- /workspace/input/blueprint.json
- /workspace/input/design_plan.json

Build a multi-page reference website with thoughtful motion design using:
- **Solid JS** (Solid components with JSX, Solid signals for state and lifecycle)
- **Tailwind CSS** (utility-first styling)
- **Vite in multi-page mode** to bundle and emit static HTML+CSS+JS
- inline SVG, local SVG files, or CSS-generated visuals for asset ideas

Tech stack hard requirements:
- Source code: Solid JS components in `.jsx` or `.tsx` files. Use Solid's signals
  (`createSignal`, `createMemo`, `createEffect`, `onMount`, `onCleanup`) for state
  and lifecycle. Do NOT use React, Vue, Svelte, or any other UI framework alongside
  Solid.
- Styling: **Tailwind CSS utility classes**. Bespoke `.css` files are allowed only
  where Tailwind cannot express the design (e.g. complex `@keyframes`).
- Tailwind v4 with the official Vite plugin is the easiest setup
  (https://tailwindcss.com/docs/installation/using-vite):
  `npm install -D tailwindcss @tailwindcss/vite`, add `@tailwindcss/vite` to
  vite.config.js plugins, and put `@import "tailwindcss";` in your main CSS file.
- Build tool: Vite in multi-page mode
  (https://vite.dev/guide/build.html#multi-page-app) with `vite-plugin-solid`.
  Configure `rollupOptions.input` so each blueprint page has its own HTML entry.
- Express the design plan's palette and fonts via Tailwind's `@theme` block (v4) or
  via tailwind.config.js `theme.extend` (v3) — do NOT just inline raw hex values in
  arbitrary-value classes.
- Do not use Tailwind-based component libraries (daisyUI, etc.) or Solid component
  libraries (Kobalte UI, Ark UI, etc.). Build your own components.

Suggested working directory layout (you can deviate if you keep the final output contract):

/workspace/build/                   # your source tree + node_modules; not served
  package.json
  vite.config.js                    # MPA + vite-plugin-solid + @tailwindcss/vite
  tailwind.config.js (optional in v4 if all theme lives in @theme)
  index.html                        # home page entry
  <page-slug>.html                  # one entry per non-home page
  src/
    pages/home.jsx
    pages/<page-slug>.jsx
    components/...
    styles/tailwind.css             # contains @import "tailwindcss"; + @theme {{...}}
    assets/...

After your build:
- Run `npm install` and `npm run build` in /workspace/build/.
- Set `build.outDir = '/workspace/output/reference_site'` and
  `build.emptyOutDir = true` in vite.config.js. The built static HTML+CSS+JS lands
  directly in the served root.

{_FINAL_OUTPUT_CONTRACT}

{_MOTION_GUIDANCE}

Motion: use Tailwind's `transition-*` / `animate-*` utilities for simple cases,
CSS `@keyframes` for richer keyframe motion, the Web Animations API,
`IntersectionObserver` orchestrated from Solid `createEffect` / `onMount` for
scroll-triggered reveals, or animation libraries (motion-one, GSAP, Anime.js, AOS,
Lottie, etc.) — implementer's choice.
""".strip() + "\n"


def build_entrypoint_script(framework: Framework = DEFAULT_FRAMEWORK) -> str:
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

log "Starting Claude Code with framework={framework} and timeout ${{AGENT_TIMEOUT_SECONDS}} seconds"
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
    --framework {framework} \\
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
