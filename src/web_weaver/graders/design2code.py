"""Design2Code grader.

Implements the 5-component visual similarity metric from
"Design2Code: Benchmarking Multimodal Code Generation for Automated
Front-End Engineering" (Si et al., NAACL 2025; arXiv:2403.03163).

Components:

1. **Block-Match**: detect visual blocks in both screenshots (text via OCR,
   non-text via edge detection + connected components), solve the optimal
   assignment with the Hungarian algorithm via
   ``scipy.optimize.linear_sum_assignment``, score by matched-area /
   total-truth-area.
2. **Text similarity**: Sørensen-Dice coefficient on character bigrams of
   the OCR text inside each matched pair.
3. **Position similarity**: ``1 - mean(normalized centroid distance)``
   over matched pairs.
4. **Color similarity**: CIEDE2000 distance on the mean LAB color of each
   matched pair, mapped to ``[0, 1]``.
5. **CLIP similarity**: cosine similarity between CLIP image embeddings
   from a frozen ViT-B/32 (LAION-2B-s34B-b79K weights), rescaled to
   ``[0, 1]``.

Aggregate score = mean of the 5 components.

Reference implementation:
    https://github.com/NoviScl/Design2Code/blob/main/metrics.py
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
import pytesseract
import torch
from PIL import Image
from scipy.optimize import linear_sum_assignment
from skimage.color import deltaE_ciede2000, rgb2lab

from web_weaver.graders.base import (
    CANONICAL_WIDTH,
    Grader,
    GraderResult,
    clamp01,
    load_image_pair,
    load_image_pair_pil,
)


MIN_BLOCK_AREA = 400
MAX_BLOCK_AREA_FRACTION = 0.6
TEXT_OCR_MIN_CONF = 30
EDGE_DILATE_KERNEL = (15, 15)
COST_THRESHOLD_NORMALIZED = 0.35
CIEDE2000_MAX = 30.0
CLIP_MODEL_NAME = "ViT-B-32"
CLIP_MODEL_PRETRAINED = "laion2b_s34b_b79k"


@dataclass
class Block:
    bbox: tuple[int, int, int, int]  # (x, y, w, h)
    text: str
    mean_color_rgb: tuple[float, float, float]

    @property
    def area(self) -> int:
        return self.bbox[2] * self.bbox[3]

    @property
    def centroid(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


_clip_lock = Lock()
_clip_state: dict | None = None


def _get_clip():
    global _clip_state
    with _clip_lock:
        if _clip_state is None:
            import open_clip

            model, _, preprocess = open_clip.create_model_and_transforms(
                CLIP_MODEL_NAME, pretrained=CLIP_MODEL_PRETRAINED
            )
            model.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            _clip_state = {
                "model": model,
                "preprocess": preprocess,
                "device": device,
            }
    return _clip_state


class Design2CodeGrader(Grader):
    """Eight-component Design2Code visual similarity grader (v2).

    Components vs the original Design2Code paper:

    - ``block_match`` (paper) — Hungarian matched-area-ratio over detected blocks.
    - ``text`` (paper) — Sørensen-Dice on character bigrams of OCR text per pair.
    - ``position`` (paper) — ``1 - mean(normalized centroid distance)``.
    - ``color`` (paper, **strengthened**) — was mean RGB → CIEDE2000 per block;
      now per-pixel CIEDE2000 across the cropped matched region pair.
    - ``clip`` (paper) — global CLIP image-image cosine, rescaled.
    - ``block_ssim`` (**new in v2**) — SSIM between cropped matched-region pairs,
      area-weighted. Catches within-block detail (icons, illustrations, text
      shape) that mean-color and block-match are blind to.
    - ``edge_ssim`` (**new in v2**) — SSIM on Canny edge maps of the full
      images. Catches typography weight/family + component shape diffs.
    - (cw_ssim is in :class:`waffle.WaffleGrader` only.)

    Score = mean of the components above.
    """

    name = "design2code"

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        started_at = time.perf_counter()

        agent_arr, truth_arr = load_image_pair(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )

        agent_blocks = _extract_blocks(agent_arr)
        truth_blocks = _extract_blocks(truth_arr)

        height, width = truth_arr.shape[:2]
        diagonal = float(np.hypot(width, height))
        block_match, matches = _block_match(
            agent_blocks=agent_blocks,
            truth_blocks=truth_blocks,
            image_diagonal=diagonal,
        )
        text_score = _text_similarity(matches)
        position_score = _position_similarity(matches, image_diagonal=diagonal)
        color_score = _color_similarity_perpixel(matches, agent_arr, truth_arr)
        block_ssim_score = _block_internal_ssim(matches, agent_arr, truth_arr)
        edge_ssim_score = _edge_map_ssim(agent_arr, truth_arr)

        agent_pil, truth_pil = load_image_pair_pil(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )
        clip_score = _clip_similarity(agent_pil, truth_pil)

        components = {
            "block_match": clamp01(block_match),
            "text": clamp01(text_score),
            "position": clamp01(position_score),
            "color": clamp01(color_score),
            "block_ssim": clamp01(block_ssim_score),
            "edge_ssim": clamp01(edge_ssim_score),
            "clip": clamp01(clip_score),
        }
        score = float(np.mean(list(components.values())))

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata={
                "grader": self.name,
                "elapsed_ms": elapsed_ms,
                "agent_block_count": len(agent_blocks),
                "truth_block_count": len(truth_blocks),
                "matched_pairs": len(matches),
            },
        )


def _extract_blocks(image: np.ndarray) -> list[Block]:
    """Detect visual blocks in an RGB ``HxWx3`` numpy image."""

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Block extraction expects an RGB image")

    height, width = image.shape[:2]
    max_block_area = int(MAX_BLOCK_AREA_FRACTION * height * width)

    text_blocks = _extract_text_blocks(image, max_block_area)
    visual_blocks = _extract_visual_blocks(image, max_block_area)

    blocks = text_blocks + visual_blocks
    return _suppress_overlapping_blocks(blocks, image_area=height * width)


def _extract_text_blocks(image: np.ndarray, max_block_area: int) -> list[Block]:
    pil_image = Image.fromarray(image)
    try:
        data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        return []

    blocks: list[Block] = []
    n = len(data["level"])
    for i in range(n):
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            continue
        if conf < TEXT_OCR_MIN_CONF:
            continue
        text = (data["text"][i] or "").strip()
        if not text:
            continue
        x = int(data["left"][i])
        y = int(data["top"][i])
        w = int(data["width"][i])
        h = int(data["height"][i])
        if w * h < MIN_BLOCK_AREA or w * h > max_block_area:
            continue
        blocks.append(
            Block(
                bbox=(x, y, w, h),
                text=text,
                mean_color_rgb=_block_mean_color(image, (x, y, w, h)),
            )
        )
    return blocks


def _extract_visual_blocks(image: np.ndarray, max_block_area: int) -> list[Block]:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, EDGE_DILATE_KERNEL)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    blocks: list[Block] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < MIN_BLOCK_AREA or area > max_block_area:
            continue
        blocks.append(
            Block(
                bbox=(x, y, w, h),
                text="",
                mean_color_rgb=_block_mean_color(image, (x, y, w, h)),
            )
        )
    return blocks


def _block_mean_color(
    image: np.ndarray, bbox: tuple[int, int, int, int]
) -> tuple[float, float, float]:
    x, y, w, h = bbox
    height, width = image.shape[:2]
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(width, x + w)
    y1 = min(height, y + h)
    if x1 <= x0 or y1 <= y0:
        return (0.0, 0.0, 0.0)
    region = image[y0:y1, x0:x1].reshape(-1, 3)
    mean = region.mean(axis=0)
    return (float(mean[0]), float(mean[1]), float(mean[2]))


def _suppress_overlapping_blocks(blocks: list[Block], image_area: int) -> list[Block]:
    if not blocks:
        return blocks
    sorted_blocks = sorted(blocks, key=lambda b: b.area, reverse=True)
    kept: list[Block] = []
    for block in sorted_blocks:
        if all(_iou(block.bbox, other.bbox) < 0.6 for other in kept):
            kept.append(block)
    return kept


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    ax1, ay1 = ax0 + aw, ay0 + ah
    bx1, by1 = bx0 + bw, by0 + bh
    x0 = max(ax0, bx0)
    y0 = max(ay0, by0)
    x1 = min(ax1, bx1)
    y1 = min(ay1, by1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    union = aw * ah + bw * bh - inter
    if union <= 0:
        return 0.0
    return inter / union


def _block_match(
    *,
    agent_blocks: list[Block],
    truth_blocks: list[Block],
    image_diagonal: float,
) -> tuple[float, list[tuple[Block, Block]]]:
    if not truth_blocks:
        return (1.0 if not agent_blocks else 0.0), []
    if not agent_blocks:
        return 0.0, []

    n_truth = len(truth_blocks)
    n_agent = len(agent_blocks)
    cost = np.zeros((n_truth, n_agent), dtype=np.float64)
    for i, truth_block in enumerate(truth_blocks):
        for j, agent_block in enumerate(agent_blocks):
            cost[i, j] = _pairwise_cost(
                truth_block, agent_block, image_diagonal=image_diagonal
            )

    row_ind, col_ind = linear_sum_assignment(cost)

    matches: list[tuple[Block, Block]] = []
    matched_truth_area = 0
    for r, c in zip(row_ind, col_ind):
        if cost[r, c] > COST_THRESHOLD_NORMALIZED:
            continue
        truth_block = truth_blocks[r]
        agent_block = agent_blocks[c]
        matches.append((truth_block, agent_block))
        matched_truth_area += truth_block.area

    total_truth_area = sum(block.area for block in truth_blocks)
    if total_truth_area == 0:
        return 1.0, matches
    return matched_truth_area / total_truth_area, matches


def _pairwise_cost(
    truth_block: Block,
    agent_block: Block,
    *,
    image_diagonal: float,
) -> float:
    cx_t, cy_t = truth_block.centroid
    cx_a, cy_a = agent_block.centroid
    if image_diagonal <= 0:
        position_cost = 1.0
    else:
        position_cost = float(np.hypot(cx_t - cx_a, cy_t - cy_a) / image_diagonal)
    if truth_block.area == 0:
        size_cost = 1.0
    else:
        size_cost = abs(truth_block.area - agent_block.area) / max(
            truth_block.area, agent_block.area, 1
        )
    color_cost = float(_pair_color_distance(truth_block, agent_block) / CIEDE2000_MAX)
    return clamp01(0.5 * position_cost + 0.3 * size_cost + 0.2 * color_cost)


def _pair_color_distance(truth_block: Block, agent_block: Block) -> float:
    truth_rgb = np.array([[list(truth_block.mean_color_rgb)]], dtype=np.float64) / 255.0
    agent_rgb = np.array([[list(agent_block.mean_color_rgb)]], dtype=np.float64) / 255.0
    truth_lab = rgb2lab(truth_rgb)
    agent_lab = rgb2lab(agent_rgb)
    return float(deltaE_ciede2000(truth_lab, agent_lab)[0, 0])


def _text_similarity(matches: list[tuple[Block, Block]]) -> float:
    if not matches:
        return 0.0
    scores: list[float] = []
    for truth_block, agent_block in matches:
        if not truth_block.text and not agent_block.text:
            scores.append(1.0)
            continue
        scores.append(_sorensen_dice_bigrams(truth_block.text, agent_block.text))
    return float(np.mean(scores))


def _sorensen_dice_bigrams(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    a_norm = a.lower()
    b_norm = b.lower()
    bigrams_a = {a_norm[i : i + 2] for i in range(len(a_norm) - 1)} or {a_norm}
    bigrams_b = {b_norm[i : i + 2] for i in range(len(b_norm) - 1)} or {b_norm}
    intersection = bigrams_a & bigrams_b
    return 2 * len(intersection) / (len(bigrams_a) + len(bigrams_b))


def _position_similarity(
    matches: list[tuple[Block, Block]], *, image_diagonal: float
) -> float:
    if not matches:
        return 0.0
    if image_diagonal <= 0:
        return 0.0
    distances: list[float] = []
    for truth_block, agent_block in matches:
        cx_t, cy_t = truth_block.centroid
        cx_a, cy_a = agent_block.centroid
        distances.append(float(np.hypot(cx_t - cx_a, cy_t - cy_a) / image_diagonal))
    return clamp01(1.0 - float(np.mean(distances)))


def _color_similarity(matches: list[tuple[Block, Block]]) -> float:
    """Block-mean CIEDE2000 (legacy v1; kept for reference and unit tests)."""
    if not matches:
        return 0.0
    distances = [
        _pair_color_distance(truth_block, agent_block)
        for truth_block, agent_block in matches
    ]
    return clamp01(1.0 - float(np.mean(distances)) / CIEDE2000_MAX)


def _color_similarity_perpixel(
    matches: list[tuple[Block, Block]],
    agent_image: np.ndarray,
    truth_image: np.ndarray,
) -> float:
    """Per-pixel CIEDE2000 over the matched region pair (v2).

    Crops each matched bbox out of both images, resizes the agent crop to the
    truth crop's shape, converts both to LAB, and computes CIEDE2000 per pixel.
    Aggregate score = ``1 - mean(per_pixel_dE) / CIEDE2000_MAX`` averaged over
    matched pairs (area-weighted by the truth bbox area).
    """
    if not matches:
        return 0.0
    weighted_sum = 0.0
    weight_total = 0
    for truth_block, agent_block in matches:
        truth_crop = _crop(truth_image, truth_block.bbox)
        agent_crop = _crop(agent_image, agent_block.bbox)
        if truth_crop.size == 0 or agent_crop.size == 0:
            continue
        target_h, target_w = truth_crop.shape[:2]
        if target_h < 2 or target_w < 2:
            continue
        agent_resized = cv2.resize(
            agent_crop, (target_w, target_h), interpolation=cv2.INTER_AREA
        )
        truth_lab = rgb2lab(truth_crop.astype(np.float64) / 255.0)
        agent_lab = rgb2lab(agent_resized.astype(np.float64) / 255.0)
        dE = deltaE_ciede2000(truth_lab, agent_lab)
        per_pair_score = clamp01(1.0 - float(np.mean(dE)) / CIEDE2000_MAX)
        weight = truth_block.area
        weighted_sum += per_pair_score * weight
        weight_total += weight
    if weight_total <= 0:
        return 0.0
    return weighted_sum / weight_total


def _block_internal_ssim(
    matches: list[tuple[Block, Block]],
    agent_image: np.ndarray,
    truth_image: np.ndarray,
) -> float:
    """Area-weighted SSIM over cropped matched-region pairs (v2)."""
    if not matches:
        return 0.0
    from skimage.metrics import structural_similarity

    weighted_sum = 0.0
    weight_total = 0
    for truth_block, agent_block in matches:
        truth_crop = _crop(truth_image, truth_block.bbox)
        agent_crop = _crop(agent_image, agent_block.bbox)
        if truth_crop.size == 0 or agent_crop.size == 0:
            continue
        target_h, target_w = truth_crop.shape[:2]
        if target_h < 11 or target_w < 11:
            continue
        agent_resized = cv2.resize(
            agent_crop, (target_w, target_h), interpolation=cv2.INTER_AREA
        )
        try:
            ssim = structural_similarity(
                truth_crop, agent_resized, channel_axis=2, data_range=255
            )
        except ValueError:
            continue
        per_pair_score = clamp01(float(ssim))
        weight = truth_block.area
        weighted_sum += per_pair_score * weight
        weight_total += weight
    if weight_total <= 0:
        return 0.0
    return weighted_sum / weight_total


def _edge_map_ssim(agent_image: np.ndarray, truth_image: np.ndarray) -> float:
    """SSIM on Canny edge maps of the full images (v2).

    Edge maps emphasize typography (glyph outlines) and component shape; they
    are robust to large flat regions (which dominate full-page SSIM) and so
    catch font-weight or component-shape differences that get washed out by
    page-level pixel SSIM.
    """
    from skimage.metrics import structural_similarity

    truth_gray = cv2.cvtColor(truth_image, cv2.COLOR_RGB2GRAY)
    agent_gray = cv2.cvtColor(agent_image, cv2.COLOR_RGB2GRAY)
    truth_edges = cv2.Canny(truth_gray, 50, 150)
    agent_edges = cv2.Canny(agent_gray, 50, 150)
    if (
        truth_edges.shape[0] < 11
        or truth_edges.shape[1] < 11
        or agent_edges.shape[0] < 11
        or agent_edges.shape[1] < 11
    ):
        return 0.0
    try:
        ssim = structural_similarity(truth_edges, agent_edges, data_range=255)
    except ValueError:
        return 0.0
    return clamp01(float(ssim))


def _crop(image: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = bbox
    height, width = image.shape[:2]
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(width, int(x + w))
    y1 = min(height, int(y + h))
    if x1 <= x0 or y1 <= y0:
        return np.zeros((0, 0, image.shape[2]), dtype=image.dtype)
    return image[y0:y1, x0:x1]


def _clip_similarity(agent_pil: Image.Image, truth_pil: Image.Image) -> float:
    state = _get_clip()
    model = state["model"]
    preprocess = state["preprocess"]
    device = state["device"]
    with torch.no_grad():
        agent_tensor = preprocess(agent_pil).unsqueeze(0).to(device)
        truth_tensor = preprocess(truth_pil).unsqueeze(0).to(device)
        agent_features = model.encode_image(agent_tensor)
        truth_features = model.encode_image(truth_tensor)
        agent_features = agent_features / agent_features.norm(dim=-1, keepdim=True)
        truth_features = truth_features / truth_features.norm(dim=-1, keepdim=True)
        cos = float((agent_features @ truth_features.T).item())
    return (cos + 1.0) / 2.0
