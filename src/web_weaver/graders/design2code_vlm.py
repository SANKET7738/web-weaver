"""Design2Code-VLM hybrid grader.

Same component set as :class:`Design2CodeGrader` (v2) except the global
CLIP cosine signal is replaced with the top-line score from
:class:`VLMJudgeGrader`. The intuition: CLIP gives one cheap semantic
similarity number, but it has known dynamic-range collapse on screenshot
pairs (blank pages still score ~0.65). The VLM judge, asked to compare
the two images on a 10-criterion rubric and average the result, produces
a higher-quality "global semantic agreement" signal at the cost of an
API call.

Components:

- ``block_match``  Hungarian matched-area-ratio over detected blocks.
- ``text``         Sørensen-Dice on character bigrams of OCR text per pair.
- ``position``     ``1 - mean(normalized centroid distance)``.
- ``color``        Per-pixel CIEDE2000 across cropped matched-region pairs.
- ``block_ssim``   SSIM on cropped matched-region pairs (area-weighted).
- ``edge_ssim``    SSIM on Canny edge maps of the full images.
- ``vlm_judge``    Top-line score from VLMJudgeGrader (mean of 10 rubric
                   criteria / 5).

Aggregate score = mean of the 7 components.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from web_weaver.graders.base import (
    CANONICAL_WIDTH,
    Grader,
    GraderResult,
    clamp01,
    load_image_pair,
)
from web_weaver.graders.design2code import (
    _block_internal_ssim,
    _block_match,
    _color_similarity_perpixel,
    _edge_map_ssim,
    _extract_blocks,
    _position_similarity,
    _text_similarity,
)
from web_weaver.graders.vlm_judge import VLMJudgeGrader


class Design2CodeVLMGrader(Grader):
    """Design2Code v2 with the CLIP component replaced by VLM rubric mean."""

    name = "design2code_vlm"

    def __init__(
        self,
        *,
        vlm_grader: VLMJudgeGrader | None = None,
    ) -> None:
        self._vlm_grader = vlm_grader or VLMJudgeGrader()

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

        vlm_result = self._vlm_grader.grade(agent_screenshot, truth_screenshot)
        vlm_score = vlm_result.score

        components = {
            "block_match": clamp01(block_match),
            "text": clamp01(text_score),
            "position": clamp01(position_score),
            "color": clamp01(color_score),
            "block_ssim": clamp01(block_ssim_score),
            "edge_ssim": clamp01(edge_ssim_score),
            "vlm_judge": clamp01(vlm_score),
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
                "vlm_rubric": vlm_result.components,
                "vlm_reasons": vlm_result.metadata.get("rubric_reasons", {}),
            },
        )
