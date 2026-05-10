"""Shared interface and helpers for design-to-code graders.

Every grader takes two image paths (the agent's rendered page and the
ground-truth reference) and returns a :class:`GraderResult` whose
``score`` field is in ``[0, 1]``.

The graders live outside the Harbor task image: they operate on PNGs that
were captured during a Harbor run (or fabricated by the test set tool in
``testset.py``). This decoupling means we can iterate on graders, re-score
historical runs, and swap winners without touching the Harbor image.

See ``graders_plan.md`` at the repository root for the design rationale.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


CANONICAL_WIDTH = 1440


@dataclass
class GraderResult:
    """Output of a single :class:`Grader.grade` call."""

    score: float
    components: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.score, (int, float)):
            raise TypeError(f"score must be numeric, got {type(self.score).__name__}")
        self.score = float(self.score)
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "components": dict(self.components),
            "metadata": dict(self.metadata),
        }


class Grader(ABC):
    """Abstract base class for graders.

    Subclasses set ``name`` and implement :meth:`grade`. Renderability is
    enforced by :meth:`grade_safely`, which returns a zero-score result with
    an error in ``metadata`` whenever an input image cannot be loaded.
    """

    name: str

    @abstractmethod
    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        ...

    def grade_safely(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        """Run :meth:`grade` with a hard renderability gate.

        Returns a zero-score :class:`GraderResult` whose ``metadata.error``
        explains the failure if either image cannot be loaded, instead of
        raising.
        """
        for label, path in (("agent", agent_screenshot), ("truth", truth_screenshot)):
            if not path.is_file():
                return GraderResult(
                    score=0.0,
                    components={},
                    metadata={
                        "grader": self.name,
                        "error": f"missing {label} screenshot at {path}",
                    },
                )
            try:
                with Image.open(path) as image:
                    image.verify()
            except Exception as error:
                return GraderResult(
                    score=0.0,
                    components={},
                    metadata={
                        "grader": self.name,
                        "error": f"failed to load {label} screenshot at {path}: {error}",
                    },
                )

        return self.grade(agent_screenshot, truth_screenshot)


def load_image_pair(
    agent_screenshot: Path,
    truth_screenshot: Path,
    *,
    canonical_width: int = CANONICAL_WIDTH,
    grayscale: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Load both images and resize to a common ``(canonical_width, H_truth)``.

    The agent's image is resized to *exactly* the truth's dimensions after
    the truth has been canonicalized to ``canonical_width``. This collapses
    page-height mismatches into the score (taller agent → squish; shorter
    → stretch) which SSIM and LPIPS will naturally penalize.
    """

    truth_pil = _load_pil(truth_screenshot, grayscale=grayscale)
    truth_resized = _resize_to_width(truth_pil, canonical_width)
    target_size = truth_resized.size  # (W, H)

    agent_pil = _load_pil(agent_screenshot, grayscale=grayscale)
    agent_resized = agent_pil.resize(target_size, Image.Resampling.LANCZOS)

    return np.asarray(agent_resized), np.asarray(truth_resized)


def load_image_pair_pil(
    agent_screenshot: Path,
    truth_screenshot: Path,
    *,
    canonical_width: int = CANONICAL_WIDTH,
) -> tuple[Image.Image, Image.Image]:
    """Like :func:`load_image_pair` but returns PIL Images (RGB)."""

    truth_pil = _load_pil(truth_screenshot, grayscale=False)
    truth_resized = _resize_to_width(truth_pil, canonical_width)
    agent_pil = _load_pil(agent_screenshot, grayscale=False)
    agent_resized = agent_pil.resize(truth_resized.size, Image.Resampling.LANCZOS)
    return agent_resized, truth_resized


def _load_pil(path: Path, *, grayscale: bool) -> Image.Image:
    image = Image.open(path)
    image.load()
    if grayscale:
        return image.convert("L")
    return image.convert("RGB")


def _resize_to_width(image: Image.Image, target_width: int) -> Image.Image:
    width, height = image.size
    if width == target_width:
        return image
    target_height = max(1, round(height * target_width / width))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)
