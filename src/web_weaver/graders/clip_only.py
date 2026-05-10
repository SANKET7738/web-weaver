"""CLIP-only grader.

Single-signal baseline: cosine similarity between CLIP image embeddings,
rescaled to ``[0, 1]`` via ``(cos + 1) / 2``.

Reuses the CLIP model loader from :mod:`web_weaver.graders.design2code`
to avoid loading the model twice when both graders run in the same
process.

Reference: Radford et al., "Learning Transferable Visual Models From
Natural Language Supervision", ICML 2021, https://arxiv.org/abs/2103.00020
"""
from __future__ import annotations

import time
from pathlib import Path

from web_weaver.graders.base import (
    CANONICAL_WIDTH,
    Grader,
    GraderResult,
    clamp01,
    load_image_pair_pil,
)
from web_weaver.graders.design2code import _clip_similarity


class CLIPOnlyGrader(Grader):
    """Single-signal CLIP cosine baseline."""

    name = "clip_only"

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        started_at = time.perf_counter()
        agent_pil, truth_pil = load_image_pair_pil(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )
        score = clamp01(_clip_similarity(agent_pil, truth_pil))
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        return GraderResult(
            score=score,
            components={"clip": score},
            metadata={"grader": self.name, "elapsed_ms": elapsed_ms},
        )
