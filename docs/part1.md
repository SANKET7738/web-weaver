# Part 1: graders we tried

Seven graders. Each one looks at two images — what the agent built and
the original — and outputs a single number from 0 to 1. Higher = closer
to the original.

## What each grader tests

| Grader | What it looks at | API cost |
|---|---|---|
| `design2code` | Are the same boxes (cards, sections, illustrations) in the same places, with the same colors and contents? | none |
| `design2code_vlm` | Same as above, but instead of using CLIP to ask "is this the same kind of page?", we ask Claude to score it on 10 things (layout, color, typography, etc.). | 1 Claude vision call per page |
| `design2code_vlm_sliced` | Same as `design2code_vlm`, but we cut both pages into screen-sized slices and check each slice separately, then average. Helps catch "this part is fine, that part is broken". | 1 Claude vision call per page |
| `waffle` | `design2code` plus one extra check (CW-SSIM) that's tolerant of small shifts. | none |
| `perceptual` | Pure pixel-similarity. Just SSIM + LPIPS, nothing structural. | none |
| `clip_only` | One number from CLIP. Asks "are these images about the same thing?" but doesn't care where anything is. | none |
| `vlm_judge` | Hand the two images to Claude with a 10-criterion rubric and ask for a 1-5 score on each. Mean is the final score. | 1 Claude vision call per page |

## Pseudo-code per grader

Each grader returns a value in `[0, 1]`. Components are also each in
`[0, 1]`. `mean(...)` is plain arithmetic mean.

### `design2code`

```
boxes_truth = find_blocks(truth_image)            # OCR + edge detection
boxes_agent = find_blocks(agent_image)
pairs       = hungarian_match(boxes_truth, boxes_agent)   # best 1-to-1 pairing

block_match = sum(area_of_matched_truth_boxes) / sum(area_of_all_truth_boxes)
text        = mean over pairs of: dice_coefficient(ocr_text(t), ocr_text(a))
position    = 1 - mean over pairs of: distance_between_centers / image_diagonal
color       = 1 - mean over pairs of: per_pixel_color_distance / 30
block_ssim  = area_weighted mean over pairs of: SSIM(crop(t), resized_crop(a))
edge_ssim   = SSIM(canny_edges(truth), canny_edges(agent))
clip        = (cosine_similarity(CLIP_embed(truth), CLIP_embed(agent)) + 1) / 2

score = mean(block_match, text, position, color, block_ssim, edge_ssim, clip)
```

### `design2code_vlm`

```
# same first six components as design2code
block_match, text, position, color, block_ssim, edge_ssim = design2code(...)

# replace the CLIP component with the VLM judge's overall score
vlm = vlm_judge(truth_image, agent_image).score    # see vlm_judge below

score = mean(block_match, text, position, color, block_ssim, edge_ssim, vlm)
```

### `design2code_vlm_sliced`

```
truth_slices = slice_into_viewports(truth_image)   # 1440x1000 each
agent_slices = slice_into_viewports(agent_image)

# per-slice scoring of the design2code components
for each (t_slice, a_slice) in pairs of slices:
    bm, tx, po, co, bs, es = design2code_components(t_slice, a_slice)

block_match = mean of bm across slices
text        = mean of tx across slices
position    = mean of po across slices
color       = mean of co across slices
block_ssim  = mean of bs across slices
edge_ssim   = mean of es across slices

# VLM still runs once on the full tall image (page-level question)
vlm = vlm_judge(truth_image, agent_image).score

score = mean(block_match, text, position, color, block_ssim, edge_ssim, vlm)
```

### `waffle`

```
# all seven design2code components
b, t, p, c, bs, es, cl = design2code_components(...)

# add CW-SSIM (translation-tolerant structural similarity, via piq.haarpsi)
cw_ssim = haarpsi(truth_image, agent_image)

score = mean(b, t, p, c, bs, es, cl, cw_ssim)
```

### `perceptual`

```
ssim_score  = SSIM(truth, agent)                   # in [0, 1] for natural images
lpips_dist  = LPIPS(truth, agent)                  # 0 = identical, ~1 = unrelated
lpips_score = 1 - lpips_dist

score = mean(ssim_score, lpips_score)
```

### `clip_only`

```
cos = cosine_similarity(CLIP_embed(truth), CLIP_embed(agent))   # in [-1, 1]
score = (cos + 1) / 2                                            # rescale to [0, 1]
```

### `vlm_judge`

```
prompt = "Compare these two screenshots on 10 criteria.
          Score each from 1 (very different) to 5 (essentially identical).
          Criteria: layout fidelity, color accuracy, typography hierarchy,
          spacing and rhythm, component structure, asset placement,
          text content fidelity, visual polish, semantic correctness,
          overall similarity."

response = claude.vision(truth_image, agent_image, prompt)   # JSON
                                                              # with 10 numbers + reasons

score = mean(response.scores) / 5                # rescale 1..5 -> 0..1
```

## Glossary

Just the technical terms that appear above, in plain words.

- **SSIM** (Structural Similarity Index): a number that says how
  similar two images look at the pixel level. It compares small
  windows of pixels and asks "is the brightness, contrast, and texture
  similar in this patch?" Then averages across all patches. 1 means
  identical, 0 means unrelated.
- **LPIPS** (Learned Perceptual Image Patch Similarity): a neural net
  trained on what humans say "looks alike". Outputs a *distance*: 0 if
  the images look the same to a person, larger if they look different.
  We flip it to a similarity by `1 - distance`.
- **CLIP**: a model that encodes any image into a vector capturing its
  *meaning* ("a contact page", "a pricing page"). Two images with
  similar meaning have similar vectors. We compare those vectors with
  cosine similarity.
- **CIEDE2000**: a color-distance formula that matches how humans
  perceive color differences. Two reds that look the same to a person
  give a small CIEDE2000; red vs green gives a big one.
- **Hungarian matching**: an algorithm that finds the best 1-to-1
  pairing between two sets of items (here: blocks in the truth image
  and blocks in the agent image), minimizing total "cost" of the
  matches.
- **OCR** (Optical Character Recognition): software that reads text
  out of an image. We use it to compare the text inside matched blocks.
- **Canny edges**: a classical algorithm that turns an image into a
  black-and-white outline showing where the edges are. Useful because
  edge maps are dominated by typography and component shapes, not
  large flat backgrounds.
- **Sørensen-Dice coefficient on bigrams**: a way to measure how
  similar two strings are. Break each string into pairs of letters
  ("hello" → {he, el, ll, lo}), then `2 × |overlap| / (|set A| + |set
  B|)`. 1 means identical, 0 means no shared letter pairs.
- **CW-SSIM** (Complex-Wavelet SSIM, here approximated by `piq.haarpsi`):
  like SSIM but tolerant of small translations. A page shifted 5 pixels
  to the right gets a much higher CW-SSIM than plain SSIM.
- **Cosine similarity**: how similar two vectors point in the same
  direction. 1 = same direction, 0 = perpendicular, -1 = opposite.
  We rescale to `[0, 1]` with `(cos + 1) / 2`.
