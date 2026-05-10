# Replicate the screenshots and recordings as an HTML+CSS+JS website

You are given full-page screenshots **and video recordings** of every page of
a multi-page website. Your job is to replicate each page as faithfully as
possible — both the steady-state visual design (from screenshots) and the
motion design (from recordings) — using HTML, CSS, and vanilla JavaScript.

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

Write your output as HTML, CSS, and vanilla JavaScript files under
`/app/site/`.

The `/app/site/` directory must contain:

- `/app/site/index.html` for `page_01.png` / `page_01.mp4`
- `/app/site/page_02.html` for `page_02.png` / `page_02.mp4`
- `/app/site/page_03.html` for `page_03.png` / `page_03.mp4`
- ... and so on through `/app/site/page_05.html` for
  `page_05.png` / `page_05.mp4`

You may add any supporting files you need (CSS, SVG, vanilla JS, fonts)
under `/app/site/` and reference them from your HTML.

## Hard requirements

- Use only HTML, CSS, and vanilla JavaScript. No build step.
- Use CSS `@keyframes` and `transition` for animations; use
  `IntersectionObserver` (vanilla JS) for scroll-triggered reveals;
  `requestAnimationFrame` for custom tweens.
- Do not use animation libraries (GSAP, Anime.js, Framer Motion, AOS,
  Lottie, ScrollMagic, etc.).
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
as closely as the screenshots allow. Match the motion design (entrance
animations, scroll reveals, looped ambient motion, hover affordances) as
closely as the recordings and screenshots together allow. Where text is
unreadable in the screenshot, use plausible filler that matches the
visible style.

## Tools available

`ffmpeg` and `ffprobe` are installed and on `$PATH` if you find it useful
to extract individual frames from the recordings for closer inspection.
There is no requirement to use them.
