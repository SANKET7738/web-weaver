# Replicate the screenshots and recordings as a Solid JS + Tailwind CSS website

You are given full-page screenshots **and video recordings** of every page of a multi-page website. Your job is to replicate each page as faithfully as possible — both the steady-state visual design (from screenshots) and the motion design (from recordings) — using **Solid JS** (Solid components, signals) styled with **Tailwind CSS**, built into static HTML+CSS+JS with Vite in multi-page mode.

## Inputs

### Screenshots — `/app/prompt/screenshots/`

Contains 5 full-page screenshots, one per page of the website,
plus viewport-sized slices for easier inspection of long pages:

- `page_01.png` ... `page_05.png` — tall full-page captures
- `page_NN_full.png` — same tall image with the `_full` suffix
- `page_NN_001.png`, `page_NN_002.png`, ... — 1440x1000 viewport slices of
  the same page, useful if the tall PNG is hard to navigate

All captures are at a 1440 pixel viewport width. `page_01.png` is the home
page.

### Video recordings — `/app/prompt/screenrecordings/`

Contains 5 mp4 recordings, one per page, captured at 1440x1000
viewport at 25 fps:

- `page_01.mp4` ... `page_05.mp4`

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

Build the site with Solid JS (Tailwind CSS) and emit a fully-built static
output at `/app/site/`. The verifier serves `/app/site/` as a static
directory — your source can live anywhere inside `/app/site/`
(`src/`, `pages/`, wherever you like) as long as the served root has
the final built HTML+CSS+JS at the expected filenames.

After your build runs (e.g. `npm install && npm run build`), the
`/app/site/` directory must contain:

- `/app/site/index.html` for `page_01.png` / `page_01.mp4` (the built
  static HTML produced from your `Solid JS (Tailwind CSS)` source for page 1)
- `/app/site/page_02.html` for `page_02.png` / `page_02.mp4`
- `/app/site/page_03.html` for `page_03.png` / `page_03.mp4`
- ... and so on through `/app/site/page_05.html` for
  `page_05.png` / `page_05.mp4`
- bundled CSS / JS / asset files referenced by those HTML files

Use Vite in multi-page mode so each route gets its own HTML entry point
(https://vite.dev/guide/build.html#multi-page-app). Configure it with
`vite-plugin-solid` plus the official Tailwind Vite plugin (`@tailwindcss/vite`) or PostCSS+Tailwind. If Vite emits build output to `dist/`, copy or move
the contents into `/app/site/` so the served root has the final files
at the expected names.

`node` and `npm` are pre-installed in the verifier image; you can
install dependencies and run the build inside the container without
network restrictions.

## Hard requirements

- Source layer: **Solid JS** components with JSX. Use Solid
  signals (`createSignal`, `createMemo`, `createEffect`,
  `onMount`) for state and lifecycle.
- Do not use React, Vue, Svelte, Angular, or any other UI
  framework alongside Solid.
- Do not use Solid component libraries (Kobalte UI, Ark UI,
  etc.). Build components yourself.
- Style with **Tailwind CSS** utility classes. Bespoke CSS
  files are allowed only where Tailwind cannot express the
  design (e.g. complex `@keyframes`).
- Do not use Tailwind-based component libraries (daisyUI,
  Kobalte, etc.) — use Tailwind utilities directly.
- Build with **Vite in multi-page mode** so each page gets its own
  HTML entry point. Emit final HTML files into `/app/site/` at the
  filenames specified above (`index.html`, `page_NN.html`).
- Implement motion with whatever fits best: CSS `@keyframes` /
  `transition` and vanilla `IntersectionObserver` (orchestrated
  from Solid effects / `onMount`) for scroll-triggered reveals,
  or third-party animation libraries (motion-one, GSAP,
  Anime.js, AOS, Lottie, ScrollMagic, etc.) where they make
  replication cleaner. Your choice.
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
  scope.

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
