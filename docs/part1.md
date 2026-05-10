# Part 1: graders we tried

Seven graders, each scoring `(agent screenshot, ground-truth screenshot)
→ float in [0, 1]`. All conform to a shared `Grader` ABC; aggregate
score is the mean of per-component scores (equal weighting).

| Grader | What it tests | API cost |
|---|---|---|
| `design2code` (v2) | Block-level structural fidelity: do the same blocks exist, in the same positions, with the same colors and within-block detail? Components: block_match, text, position, color, block_ssim, edge_ssim, clip. | none |
| `design2code_vlm` | Same as design2code v2 but CLIP cosine is replaced with the VLM rubric mean — keeps the structural strictness, swaps in semantic + adversarial sensitivity from Claude. | 1 Anthropic vision call per page |
| `design2code_vlm_sliced` | Same components as `design2code_vlm`, but the design2code components run **per viewport slice** (1440×1000) and are averaged across slices. VLM judge still runs once on the tall image per page. Catches "this slice is right, that slice is wrong" patterns the page-level mean blurs. | 1 vision call per page |
| `waffle` | design2code v2 + CW-SSIM (haarpsi proxy via `piq`). Adds translation-tolerant structural similarity on top of the design2code stack. | none |
| `perceptual` | Pure pixel-similarity baseline: SSIM (`scikit-image`) + LPIPS (VGG backbone). Tests "do these images look alike pixel-for-pixel after canonical resize". | none |
| `clip_only` | Single-signal semantic baseline: CLIP image cosine similarity, rescaled to `[0, 1]`. Tests "are these images depicting the same kind of page". | none |
| `vlm_judge` | Claude vision rubric, 10 criteria (layout fidelity, color accuracy, typography hierarchy, spacing and rhythm, component structure, asset placement, text content fidelity, visual polish, semantic correctness, overall similarity), 1-5 Likert each, mean rescaled to `[0, 1]`. Each criterion includes a written reason for diagnostic use. | 1 vision call per page |

## Component breakdown for the structural graders

The seven `design2code` v2 components (also used by the two hybrids):

| Component | What it measures |
|---|---|
| `block_match` | Hungarian-assignment matched-area / total truth-area, after detecting visual blocks via OCR + edge-detected connected components. |
| `text` | Sørensen-Dice coefficient on character bigrams of OCR text inside each matched block pair. |
| `position` | `1 − mean(normalized centroid distance)` over matched block pairs. |
| `color` | Per-pixel CIEDE2000 distance over the cropped matched-region pair (replaces the original mean-RGB version which was blind to accent colors). |
| `block_ssim` | Area-weighted SSIM over cropped matched-region pairs. Catches within-block detail (icons, illustrations, glyph shape). |
| `edge_ssim` | SSIM on Canny edge maps of the full image. Catches typography weight and component shape; insensitive to large flat regions. |
| `clip` | Cosine similarity between CLIP image embeddings (ViT-B/32, LAION-2B), rescaled `(cos+1)/2`. |
