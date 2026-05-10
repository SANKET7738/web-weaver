# Replicate the screenshots as a static HTML+CSS website

You are given full-page screenshots of every page of a multi-page website.
Your job is to replicate each page as faithfully as possible using only
static HTML and CSS.

## Inputs

You can read screenshots in `/app/prompt/screenshots/`. The directory
contains exactly 5 full-page screenshots, one per page of the
website, named in order:

- `page_01.png`
- `page_02.png`
- ...
- `page_05.png`

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
- ... and so on through `/app/site/page_05.html` for
  `page_05.png`

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
