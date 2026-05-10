# Grader comparison report

Test set: 5 quality tiers + 3 adversarial cases × N pages, fabricated
by `src/web_weaver/graders/testset.py`. Each grader scored every test
case via `Grader.grade_safely`.


## Tier means

| tier | design2code | waffle | perceptual | clip_only | vlm_judge |
| --- | --- | --- | --- | --- | --- |
| tier_01_verbatim | 0.865 | 0.758 | 0.782 | 0.945 | 0.940 |
| tier_02_minor | 0.858 | 0.749 | 0.768 | 0.945 | 0.940 |
| tier_03_section_removed | 0.783 | 0.670 | 0.496 | 0.913 | 0.856 |
| tier_04_shuffle_repaint | 0.670 | 0.575 | 0.342 | 0.824 | 0.572 |
| tier_05_blank | 0.127 | 0.120 | 0.372 | 0.637 | 0.200 |
| adv_01_brand_color_blank | 0.138 | 0.127 | 0.477 | 0.688 | 0.212 |
| adv_02_color_block | 0.116 | 0.111 | 0.381 | 0.581 | 0.200 |
| adv_03_text_dump | 0.401 | 0.348 | 0.346 | 0.696 | 0.284 |

## Headline metrics

| grader | inversion_rate | tier_separation | adversarial_catch_rate | median_ms_per_pair |
| --- | --- | --- | --- | --- |
| design2code | 0.032 | 0.738 | 0.333 | 1684 |
| waffle | 0.032 | 0.637 | 0.333 | 1967 |
| perceptual | 0.116 | 0.410 | 0.600 | 12963 |
| clip_only | 0.076 | 0.308 | 0.333 | 183 |
| vlm_judge | 0.036 | 0.740 | 0.467 | 8041 |

## Notes

- **inversion_rate** counts how often the grader scored a lower
  quality tier above a higher one across all quality-tier pairs.
  Lower is better. 0 means the grader exactly matches the gold tier
  ordering.
- **tier_separation** is `mean(tier_01) - mean(tier_05)`. Larger
  means the grader uses more of the score range.
- **adversarial_catch_rate** is the fraction of adversarial cases
  scored at or below the highest tier-05 score; higher is better.
