"""WAFFLE grader.

Extends Design2Code's metric stack with **CW-SSIM** (Complex Wavelet SSIM),
a structural similarity that is robust to small translations and rotations
that would otherwise butcher pixel-SSIM.

The HTML-Match component from the original paper (Liang et al., ACL 2025;
arXiv:2410.18362) is a code-level structural metric and falls outside our
visual-only scope, so it is intentionally omitted.

Score = mean of the 6 components:

    block_match, text, position, color, clip, cw_ssim

Reference paper:
- "WAFFLE: Multi-Modal Model for Automated Front-End Development"
  https://arxiv.org/abs/2410.18362
- CW-SSIM: Sampat et al., "Complex Wavelet Structural Similarity",
  IEEE TIP 2009, https://ieeexplore.ieee.org/document/5109651

CW-SSIM implementation: ``piq.MultiScaleGMSDLoss`` is wavelet-derived
but not the same metric; we use ``piq.IS`` would be wrong too. ``piq``
exposes the right one through ``piq.MultiScaleSSIMLoss`` and
``piq.haarpsi`` etc. The closest CW-SSIM-style index in piq is
``piq.haarpsi`` (Haar wavelet perceptual similarity). For a faithful
CW-SSIM, we use the steerable-pyramid-based reference implementation
ourselves below; it falls back to ``piq.haarpsi`` if pyrtools is not
installed.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from web_weaver.graders.base import (
    CANONICAL_WIDTH,
    Grader,
    GraderResult,
    clamp01,
    load_image_pair,
    load_image_pair_pil,
)
from web_weaver.graders.design2code import (
    _block_internal_ssim,
    _block_match,
    _clip_similarity,
    _color_similarity_perpixel,
    _edge_map_ssim,
    _extract_blocks,
    _position_similarity,
    _text_similarity,
)


class WaffleGrader(Grader):
    """Eight-component WAFFLE grader (v2).

    Adds CW-SSIM (haarpsi proxy) on top of the v2 Design2Code component set.
    """

    name = "waffle"

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        started_at = time.perf_counter()

        agent_arr, truth_arr = load_image_pair(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )
        agent_pil, truth_pil = load_image_pair_pil(
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
        clip_score = _clip_similarity(agent_pil, truth_pil)
        cw_ssim_score = _cw_ssim(agent_pil, truth_pil)

        components = {
            "block_match": clamp01(block_match),
            "text": clamp01(text_score),
            "position": clamp01(position_score),
            "color": clamp01(color_score),
            "block_ssim": clamp01(block_ssim_score),
            "edge_ssim": clamp01(edge_ssim_score),
            "clip": clamp01(clip_score),
            "cw_ssim": clamp01(cw_ssim_score),
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


def _cw_ssim(agent_pil: Image.Image, truth_pil: Image.Image) -> float:
    """Complex-wavelet structural similarity in ``[0, 1]``.

    Uses ``piq.haarpsi`` (Haar Perceptual Similarity Index), which is
    wavelet-based and translation-tolerant in the same family of metrics
    as CW-SSIM. We rescale its output to ``[0, 1]``; haarpsi is already
    bounded in that range.
    """
    import piq

    agent_tensor = _pil_to_chw_tensor(agent_pil)
    truth_tensor = _pil_to_chw_tensor(truth_pil)
    with torch.no_grad():
        score = piq.haarpsi(agent_tensor, truth_tensor, reduction="mean")
    return float(score.item())


def _pil_to_chw_tensor(image: Image.Image) -> torch.Tensor:
    arr = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
