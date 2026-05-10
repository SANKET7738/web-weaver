# Grader comparison report

Test set: 5 quality tiers + 3 adversarial cases × N pages, fabricated
by `src/web_weaver/graders/testset.py`. Each grader scored every test
case via `Grader.grade_safely`.


## Tier means

| tier | design2code | waffle | perceptual | clip_only | vlm_judge |
| --- | --- | --- | --- | --- | --- |
| tier_01_verbatim | 0.820 | 0.741 | 0.791 | 0.944 | 0.964 |
| tier_02_minor | 0.806 | 0.727 | 0.777 | 0.945 | 0.964 |
| tier_03_section_removed | 0.738 | 0.658 | 0.522 | 0.913 | 0.884 |
| tier_04_shuffle_repaint | 0.651 | 0.582 | 0.359 | 0.824 | 0.600 |
| tier_05_blank | 0.209 | 0.195 | 0.397 | 0.637 | 0.200 |
| tier_06_within_block_drift | 0.683 | 0.612 | 0.421 | 0.856 | 0.748 |
| adv_01_brand_color_blank | 0.217 | 0.200 | 0.501 | 0.688 | 0.208 |
| adv_02_color_block | 0.201 | 0.188 | 0.408 | 0.581 | 0.200 |
| adv_03_text_dump | 0.442 | 0.398 | 0.371 | 0.695 | 0.304 |

## Headline metrics

| grader | inversion_rate | tier_separation | adversarial_catch_rate | median_ms_per_pair |
| --- | --- | --- | --- | --- |
| design2code | 0.060 | 0.611 | 0.400 | 5459 |
| waffle | 0.056 | 0.546 | 0.467 | 5997 |
| perceptual | 0.116 | 0.394 | 0.533 | 29367 |
| clip_only | 0.076 | 0.307 | 0.333 | 140 |
| vlm_judge | 0.032 | 0.764 | 0.533 | 11610 |

## Notes

- **inversion_rate** counts how often the grader scored a lower
  quality tier above a higher one across all quality-tier pairs.
  Lower is better. 0 means the grader exactly matches the gold tier
  ordering.
- **tier_separation** is `mean(tier_01) - mean(tier_05)`. Larger
  means the grader uses more of the score range.
- **adversarial_catch_rate** is the fraction of adversarial cases
  scored at or below the highest tier-05 score; higher is better.
