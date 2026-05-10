"""Design2Code-VLM hybrid that scores at the **slice** level.

Same component set as :class:`Design2CodeVLMGrader` (design2code v2 metrics
+ VLM judge) but the design2code components run **per viewport slice**
instead of on the full tall image. The VLM judge still runs once on the
tall image per page.

The slice geometry is identical to the ground-truth capture geometry —
both sides of every comparison go through
:func:`web_weaver.graders.capture.capture_page_full_and_slices`, so a
sliced grader is comparing apples-to-apples viewport renders rather than
arbitrary numpy crops.

Components:

- ``block_match``  Hungarian matched-area-ratio over detected blocks (per slice).
- ``text``         Sørensen-Dice on character bigrams of OCR text per pair (per slice).
- ``position``     ``1 - mean(normalized centroid distance)`` (per slice).
- ``color``        Per-pixel CIEDE2000 across cropped matched-region pairs (per slice).
- ``block_ssim``   SSIM on cropped matched-region pairs, area-weighted (per slice).
- ``edge_ssim``    SSIM on Canny edge maps of the slice pair (per slice).
- ``vlm_judge``    Top-line score from VLMJudgeGrader on the *full* tall image.

Per-slice component scores are averaged across all slices to produce the
per-page component score, then the 7 components are averaged
(equal-weighted) into the final per-page score.

If a page has no matching slice files (e.g. legacy captures with only
``*_full.png``), the grader falls back to running on the tall image as a
single "slice" and records ``degraded_to_tall=True`` in metadata.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image

from web_weaver.graders.base import (
    Grader,
    GraderResult,
    clamp01,
)
from web_weaver.graders.capture import find_slice_siblings
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


class Design2CodeVLMSlicedGrader(Grader):
    """Sliced design2code v2 components + VLM judge on the tall image."""

    name = "design2code_vlm_sliced"

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

        agent_slices = find_slice_siblings(agent_screenshot)
        truth_slices = find_slice_siblings(truth_screenshot)

        degraded_to_tall = False
        pair_count = min(len(agent_slices), len(truth_slices))
        if pair_count == 0:
            degraded_to_tall = True
            agent_slices = [agent_screenshot]
            truth_slices = [truth_screenshot]
            pair_count = 1
        elif pair_count != len(agent_slices) or pair_count != len(truth_slices):
            agent_slices = agent_slices[:pair_count]
            truth_slices = truth_slices[:pair_count]

        per_slice_components: list[dict[str, float]] = []
        for agent_slice_path, truth_slice_path in zip(agent_slices, truth_slices):
            per_slice_components.append(
                _grade_slice_pair(agent_slice_path, truth_slice_path)
            )

        component_keys = [
            "block_match",
            "text",
            "position",
            "color",
            "block_ssim",
            "edge_ssim",
        ]
        components: dict[str, float] = {}
        for key in component_keys:
            values = [slice_components[key] for slice_components in per_slice_components]
            components[key] = clamp01(float(np.mean(values))) if values else 0.0

        vlm_result = self._vlm_grader.grade(agent_screenshot, truth_screenshot)
        components["vlm_judge"] = clamp01(vlm_result.score)

        score = float(np.mean(list(components.values())))

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata={
                "grader": self.name,
                "elapsed_ms": elapsed_ms,
                "slice_pairs_scored": pair_count,
                "degraded_to_tall": degraded_to_tall,
                "vlm_rubric": vlm_result.components,
                "vlm_reasons": vlm_result.metadata.get("rubric_reasons", {}),
            },
        )


def _grade_slice_pair(agent_slice_path: Path, truth_slice_path: Path) -> dict[str, float]:
    truth_pil = Image.open(truth_slice_path).convert("RGB")
    agent_pil = Image.open(agent_slice_path).convert("RGB")
    if agent_pil.size != truth_pil.size:
        agent_pil = agent_pil.resize(truth_pil.size, Image.Resampling.LANCZOS)
    truth_arr = np.asarray(truth_pil)
    agent_arr = np.asarray(agent_pil)

    truth_blocks = _extract_blocks(truth_arr)
    agent_blocks = _extract_blocks(agent_arr)
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

    return {
        "block_match": clamp01(block_match),
        "text": clamp01(text_score),
        "position": clamp01(position_score),
        "color": clamp01(color_score),
        "block_ssim": clamp01(block_ssim_score),
        "edge_ssim": clamp01(edge_ssim_score),
    }
