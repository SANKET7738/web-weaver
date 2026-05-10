"""Temporal motion histogram grader for animation evaluation.

Compares two screen recordings (agent vs reference) by computing a
per-frame motion magnitude signal for each, binning into fixed temporal
bins, and scoring via cosine similarity of the binned signals plus
per-window magnitude ratios.

Score components (equal-weighted mean):

- ``temporal_corr``      — cosine similarity of binned per-frame motion
  signals over the full recording. Robust to length differences because
  bins are by fraction of total runtime.
- ``onload_match``       — magnitude ratio of motion in the top-hold
  window (first 2.5s, no scrolling — pure on-load animation territory).
- ``bottom_hold_match``  — magnitude ratio of motion in the bottom-hold
  window (last 2.0s, no scrolling — pure ambient looped motion +
  any post-reveal completion).

This grader operates on mp4 recordings rather than PNG screenshots.
Inputs are passed through the ``(agent_screenshot, truth_screenshot)``
parameter names of the :class:`Grader` ABC, but the values are mp4
paths. ``grade_safely`` is overridden to validate mp4 readability via
OpenCV instead of PIL.

See ``graders_plan.md`` (Animation grading section) for design notes.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from web_weaver.graders.base import Grader, GraderResult, clamp01


CANONICAL_FRAME_WIDTH = 360
CANONICAL_FRAME_HEIGHT = 250
NUM_BINS = 16
TOP_HOLD_SECONDS = 2.5
BOTTOM_HOLD_SECONDS = 2.0


class AnimationTemporalGrader(Grader):
    """Compares motion timelines of two recordings via histogram similarity."""

    name = "animation_temporal"

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        started_at = time.perf_counter()

        agent_signal, agent_meta = _motion_signal(Path(agent_screenshot))
        truth_signal, truth_meta = _motion_signal(Path(truth_screenshot))

        agent_binned = _bin_signal(agent_signal, NUM_BINS)
        truth_binned = _bin_signal(truth_signal, NUM_BINS)

        temporal_corr = _cosine_similarity(agent_binned, truth_binned)

        onload_match = _window_magnitude_match(
            agent_signal=agent_signal,
            agent_fps=agent_meta["fps"],
            truth_signal=truth_signal,
            truth_fps=truth_meta["fps"],
            agent_window=(0.0, TOP_HOLD_SECONDS),
            truth_window=(0.0, TOP_HOLD_SECONDS),
        )

        bottom_hold_match = _window_magnitude_match(
            agent_signal=agent_signal,
            agent_fps=agent_meta["fps"],
            truth_signal=truth_signal,
            truth_fps=truth_meta["fps"],
            agent_window=(
                max(0.0, agent_meta["duration"] - BOTTOM_HOLD_SECONDS),
                agent_meta["duration"],
            ),
            truth_window=(
                max(0.0, truth_meta["duration"] - BOTTOM_HOLD_SECONDS),
                truth_meta["duration"],
            ),
        )

        components = {
            "temporal_corr": clamp01(temporal_corr),
            "onload_match": clamp01(onload_match),
            "bottom_hold_match": clamp01(bottom_hold_match),
        }
        score = sum(components.values()) / len(components)

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata={
                "grader": self.name,
                "elapsed_ms": elapsed_ms,
                "num_bins": NUM_BINS,
                "agent_video": agent_meta,
                "truth_video": truth_meta,
            },
        )

    def grade_safely(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        """Override base PIL-based gate to validate mp4 readability."""
        for label, path in (
            ("agent", Path(agent_screenshot)),
            ("truth", Path(truth_screenshot)),
        ):
            if not path.is_file():
                return GraderResult(
                    score=0.0,
                    components={},
                    metadata={
                        "grader": self.name,
                        "error": f"missing {label} recording at {path}",
                    },
                )
            cap = cv2.VideoCapture(str(path))
            opened = cap.isOpened()
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            cap.release()
            if not opened or frame_count < 2:
                return GraderResult(
                    score=0.0,
                    components={},
                    metadata={
                        "grader": self.name,
                        "error": (
                            f"could not open {label} recording at {path} "
                            f"(opened={opened}, frame_count={frame_count})"
                        ),
                    },
                )
        return self.grade(agent_screenshot, truth_screenshot)


def _motion_signal(path: Path) -> tuple[np.ndarray, dict]:
    """Compute per-frame motion magnitude (mean abs grayscale diff) over time."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    declared_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    diffs: list[float] = []
    prev_gray: np.ndarray | None = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        small = cv2.resize(
            frame,
            (CANONICAL_FRAME_WIDTH, CANONICAL_FRAME_HEIGHT),
            interpolation=cv2.INTER_AREA,
        )
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            diff = (
                np.mean(
                    np.abs(gray.astype(np.int16) - prev_gray.astype(np.int16))
                )
                / 255.0
            )
            diffs.append(float(diff))
        prev_gray = gray
    cap.release()

    signal = np.array(diffs, dtype=np.float64)
    actual_frame_count = len(signal) + 1 if signal.size else 0
    duration = actual_frame_count / fps if fps > 0 else 0.0
    return signal, {
        "fps": fps,
        "frame_count_declared": declared_frame_count,
        "frame_count_actual": actual_frame_count,
        "duration": duration,
    }


def _bin_signal(signal: np.ndarray, num_bins: int) -> np.ndarray:
    if signal.size == 0:
        return np.zeros(num_bins, dtype=np.float64)
    indices = np.linspace(0, signal.size, num_bins + 1).astype(int)
    bins = np.zeros(num_bins, dtype=np.float64)
    for i in range(num_bins):
        start, end = indices[i], indices[i + 1]
        if end > start:
            bins[i] = signal[start:end].mean()
    return bins


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    # Both signals essentially zero → both pages are static, perfect match
    if a_norm < 1e-9 and b_norm < 1e-9:
        return 1.0
    # One has motion, the other doesn't → no match
    if a_norm < 1e-9 or b_norm < 1e-9:
        return 0.0
    cos = float(np.dot(a, b) / (a_norm * b_norm))
    # Cosine of two non-negative vectors is in [0, 1]; clamp defensively
    return clamp01(cos)


def _window_magnitude_match(
    *,
    agent_signal: np.ndarray,
    agent_fps: float,
    truth_signal: np.ndarray,
    truth_fps: float,
    agent_window: tuple[float, float],
    truth_window: tuple[float, float],
) -> float:
    """Compare summed motion magnitude in two corresponding time windows."""
    agent_motion = _window_sum(agent_signal, agent_fps, *agent_window)
    truth_motion = _window_sum(truth_signal, truth_fps, *truth_window)
    if truth_motion < 1e-6 and agent_motion < 1e-6:
        return 1.0  # both windows are still → match
    if truth_motion < 1e-6:
        # truth has no motion in this window but agent does — mild penalty
        # (could legitimately be a richer agent design, but rare in practice).
        return 0.5
    if agent_motion < 1e-6:
        # truth has motion but agent doesn't — clear miss.
        return 0.0
    return float(min(agent_motion, truth_motion) / max(agent_motion, truth_motion))


def _window_sum(
    signal: np.ndarray,
    fps: float,
    start_sec: float,
    end_sec: float,
) -> float:
    if fps <= 0 or signal.size == 0:
        return 0.0
    start_idx = max(0, int(start_sec * fps))
    end_idx = min(signal.size, int(end_sec * fps))
    if end_idx <= start_idx:
        return 0.0
    return float(signal[start_idx:end_idx].sum())
