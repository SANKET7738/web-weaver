# Graders

Five visual-similarity graders for the design-to-code pipeline, plus a
test-set fabricator and comparison driver. Operates outside the Harbor
image — graders read screenshots from disk (e.g. those captured by a
Harbor run) and produce continuous scores in `[0, 1]`.

See `graders_plan.md` at the repository root for the design rationale,
paper references, and library choices.

## Layout

```
src/web_weaver/graders/
  base.py              # Grader ABC, GraderResult, image loaders, clamp01
  design2code.py       # Block-Match + Text + Position + Color + CLIP
  waffle.py            # Design2Code + CW-SSIM (haarpsi via piq)
  perceptual.py        # SSIM + LPIPS
  clip_only.py         # CLIP cosine (single signal)
  vlm_judge.py         # Anthropic Claude vision API + 10-criterion rubric
  testset.py           # Tier 1-5 + 3 adversarial fabricator (Playwright capture)
  compare.py           # CLI that runs all graders × all test cases
```

## Quickstart

### 1. Fabricate a test set from a harbor task

```
python3 -m web_weaver.graders.compare \
  --harbor-task-dir Runs/SiteGeneration/<id>/attempt-NNN/harbor \
  --output-root     Runs/Graders/<run-name>
```

The fabricator builds these synthetic outputs from the harbor task's
reference site, captures each at the same 1440x1000 viewport used to
prompt the agent, and writes the manifest:

| Tier                     | What                                       |
| ------------------------ | ------------------------------------------ |
| tier_01_verbatim         | exact copy of reference site               |
| tier_02_minor            | hue +10°, font-size +5%                    |
| tier_03_section_removed  | drop last `<section>` per page             |
| tier_04_shuffle_repaint  | shuffle sections + grayscale filter        |
| tier_05_blank            | empty `<body>`                             |
| adv_01_brand_color_blank | blank with reference dominant bg color     |
| adv_02_color_block       | single full-viewport `#f0f0f0` block       |
| adv_03_text_dump         | raw text in `<p>` tags, no styling         |

For an N-page task, this produces 8 × N test cases.

### 2. Re-run the comparison without re-fabricating

```
python3 -m web_weaver.graders.compare --output-root Runs/Graders/<run-name>
```

### 3. Skip the Anthropic API grader (offline / cost control)

```
python3 -m web_weaver.graders.compare --output-root Runs/Graders/<run-name> \
  --exclude-vlm-judge
```

### 4. Use a single grader programmatically

```python
from pathlib import Path
from web_weaver.graders.design2code import Design2CodeGrader

grader = Design2CodeGrader()
result = grader.grade_safely(
    Path("/path/to/agent_screenshot.png"),
    Path("/path/to/truth_screenshot.png"),
)
print(result.score)            # float in [0, 1]
print(result.components)       # per-component sub-scores
print(result.metadata)         # timing, error info, etc.
```

## Output

Every comparison run writes:

- `<output-root>/scores.csv` — one row per (grader, test_case) with
  the aggregate score, per-component sub-scores, and timing.
- `<output-root>/report.md` — human-readable summary with tier means,
  inversion rate, tier separation, adversarial catch rate, and median
  runtime per pair.

## Headline metrics

- **inversion_rate** — fraction of `(higher_quality, lower_quality)`
  pairs that the grader ranked in the wrong order. Lower is better;
  `0` means the grader's ordering matches the gold tier ordering.
- **tier_separation** — `mean(tier_01) - mean(tier_05)`. Larger means
  the grader uses more of the score range. Compressed top end (CLIP
  is a known offender) yields small separation.
- **adversarial_catch_rate** — fraction of adversarial cases scored
  at or below the highest tier-5 score. Higher is better.
- **median_ms_per_pair** — robust runtime central tendency.

## Initial findings (smoke test on `ww-00008/attempt-005`)

From the first comparison run on a 5-page harbor task:

| Grader      | Inversion | Separation | Adv catch | Median ms |
|-------------|-----------|------------|-----------|-----------|
| design2code | **0.032** | 0.738      | 0.333     | 1684      |
| waffle      | **0.032** | 0.637      | 0.333     | 1967      |
| perceptual  | 0.116     | 0.410      | 0.600     | 12963     |
| clip_only   | 0.076     | 0.308      | 0.333     | 183       |
| vlm_judge   | 0.036     | **0.740**  | **0.467** | 8041      |

Takeaways:

- **`design2code` and `vlm_judge` are co-leaders**: nearly identical
  inversion and separation. They agree on ordering but vlm_judge
  catches more adversarials (Claude correctly recognized "this is
  a colored block, not a webpage" where block-match alone did not).
- **`waffle`'s extra CW-SSIM did not help** on this test set: lower
  separation than `design2code` with the same inversion. Drop the
  CW-SSIM component for production.
- **`clip_only` has dynamic-range collapse**: usable range only
  ~0.31, blank pages score 0.637. Confirmed the literature warning
  about CLIP-only RL rewards.
- **`perceptual` is the worst**: highest inversion, and it scores
  adversarials *at* the level of mid-tier quality. Cannot
  distinguish "page with right average color" from "page with right
  average color and actual content".

For a single live reward in the harbor verifier:

- **`design2code`** is the recommended default. 95% of `vlm_judge`'s
  separation at ~5x the speed and zero per-call API cost.
- **`vlm_judge`** is the recommended grader for the offline benchmark
  reports (the "10 tasks × 10 attempts" deliverable in `task.md`),
  where total cost is bounded (~$30) and you want the cleanest
  quality signal.

## Implementation notes

- All graders share `web_weaver.graders.base.load_image_pair`, which
  resizes both images to a common 1024px-wide canvas at the truth's
  aspect ratio. Page-height mismatches show up as squish/stretch and
  are penalized by SSIM/LPIPS naturally.
- CLIP and LPIPS models are lazy-loaded at module level and shared
  across grade calls in the same process. First call pulls a ~600 MB
  CLIP checkpoint and a ~528 MB VGG checkpoint from the network; both
  are cached locally afterward.
- `pytesseract` requires the `tesseract` system binary
  (`brew install tesseract` on macOS).
- The fabricator drives Playwright via the Python `playwright` package;
  install Chromium with `python3 -m playwright install chromium`.
