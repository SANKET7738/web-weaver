"""VLM-as-judge grader for animation evaluation.

Extracts ``NUM_FRAMES`` evenly-spaced frames from each recording and sends
them to a multimodal Claude model as a **labeled image sequence** — each
frame is a separate image content block prefixed with a text label of the
form ``"Reference frame N of M at t=X.YYs:"``. The model is asked to
score the agent's motion-design replication on a 5-criterion rubric:

    1. entrance_match
    2. scroll_reveal_match
    3. ambient_motion_match
    4. intensity_calibration
    5. steady_state_match

Each criterion is scored on a 1-5 Likert scale; aggregate score is
``mean(scores) / 5``. Mirrors :mod:`web_weaver.graders.vlm_judge` but on
sampled video frames rather than a single still PNG.

Why a frame sequence rather than a 4x2 grid:
- Anthropic's Messages API does not accept native video uploads (as of
  mid-2025), so frames must be sampled regardless.
- A labeled sequence lets the model reason about timestamps explicitly
  rather than inferring time-order from spatial position in a grid.
- 16 frames over ~12-15s of recording samples at ~1s intervals — fine
  enough to catch short on-load animations and scroll-reveal cadences.

This grader makes a real Anthropic API call per pair. ``temperature``
defaults to 0 for determinism. Inputs are mp4 paths passed through the
``(agent_screenshot, truth_screenshot)`` parameter names of the
:class:`Grader` ABC. ``grade_safely`` is overridden to validate mp4
readability via OpenCV instead of PIL.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from web_weaver.graders.base import Grader, GraderResult, clamp01


DEFAULT_MODEL = "claude-opus-4-7"
NUM_FRAMES = 16
FRAME_WIDTH = 480
FRAME_HEIGHT = 333  # ~1440x1000 aspect at 480 wide

RUBRIC_CRITERIA = [
    "entrance_match",
    "scroll_reveal_match",
    "ambient_motion_match",
    "intensity_calibration",
    "steady_state_match",
]
SCORE_RANGE = 5.0
MAX_TOKENS = 1024

PROMPT_TEMPLATE = """You are evaluating how well a generated webpage replicates the *motion design* of a reference webpage.

You have been shown two sequences of frames, each sampled at evenly-spaced timestamps (labeled with t=X.YYs):

- The **reference** sequence: 16 frames from the reference recording, in time order from start to end.
- The **agent** sequence: 16 frames from the agent's recording, sampled at corresponding timestamps in its own runtime.

Both recordings were captured under identical conditions: 1440x1000 viewport, page held at top for ~2.5s (so frames in the early window with t<2.5s show only on-load animation, no scrolling), then eased scroll to bottom (frames in the middle show scroll progression and any scroll-triggered reveals), then held at the bottom for ~2.0s (frames in the late window with t > duration-2.0s show only ambient looped motion at rest).

Score the agent's motion design on each criterion below on a 1-5 Likert scale. Reserve 5 for near-perfect motion match and 1 for completely missing motion design. Do NOT default to the middle. Anchor your judgments on the reference, not on "this looks like a reasonable webpage in general".

CALIBRATION ANCHORS

- Score 5: motion design matches the reference closely - same entrance behavior, same scroll-reveal cadence, same ambient motion, same intensity calibration.
- Score 4: motion design is clearly comparable, with only minor differences (e.g. agent fades where reference slides, but both have a comparable entrance moment at roughly the same timestamps).
- Score 3: motion design is recognizably present but has substantial differences (e.g. agent has scroll reveals but no entrance animation; agent has motion but at noticeably different intensity).
- Score 2: motion design is partially present but with large differences (e.g. only one or two motion moments where the reference has many; or motion is happening at very different timestamps).
- Score 1: motion design is essentially absent (agent's frames look static across the entire timeline) or completely wrong.

CRITERIA

1. entrance_match        - Does the agent show an entrance / on-load animation comparable to the reference's? Compare the early frames (t < 2.5s, top-hold window) of each sequence — if the reference shows visible change between t=0 and t=2.5s but the agent is static, that's a clear miss.
2. scroll_reveal_match   - As the page scrolls (middle frames of each sequence), do sections appear / fade / slide in similarly between agent and reference? Compare frames at matching timestamps.
3. ambient_motion_match  - Is there comparable looped / ambient motion (marquees, pulses, gradient sweeps, breathing icons) where the reference has it? Look across the full sequences, especially the final 2-3 frames (bottom-hold window) where any motion is purely ambient.
4. intensity_calibration - Does the overall amount and energy of motion roughly match across the whole sequence? A playful brand should not be reduced to a static page; a restrained brand should not be over-animated.
5. steady_state_match    - Does the final state (last frame) of the agent's page look correct after motion completes, matching the reference's final state?

For each criterion, write a brief one-sentence reason BEFORE picking the score. Compare what you see against the reference per-criterion; do not let a strong score on one criterion lift the others.

Respond with strict JSON in this exact shape, no prose, no markdown fence:

{
  "entrance_match":         {"reason": "<one sentence>", "score": <1-5>},
  "scroll_reveal_match":    {"reason": "<one sentence>", "score": <1-5>},
  "ambient_motion_match":   {"reason": "<one sentence>", "score": <1-5>},
  "intensity_calibration":  {"reason": "<one sentence>", "score": <1-5>},
  "steady_state_match":     {"reason": "<one sentence>", "score": <1-5>}
}
"""


class AnimationVLMGrader(Grader):
    """Claude-as-judge grader for motion design replication."""

    name = "animation_vlm"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL_ANIMATION_VLM", DEFAULT_MODEL)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "AnimationVLMGrader requires ANTHROPIC_API_KEY in the environment."
            )

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        from anthropic import Anthropic

        started_at = time.perf_counter()
        client = Anthropic(api_key=self.api_key)

        truth_frames = _extract_frame_sequence(Path(truth_screenshot))
        agent_frames = _extract_frame_sequence(Path(agent_screenshot))

        content: list[dict] = [
            {
                "type": "text",
                "text": (
                    f"Reference recording: {len(truth_frames)} frames sampled "
                    "in time order from start to end."
                ),
            }
        ]
        for i, (b64, timestamp) in enumerate(truth_frames):
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"Reference frame {i + 1} of {len(truth_frames)} at "
                        f"t={timestamp:.2f}s:"
                    ),
                }
            )
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                }
            )

        content.append(
            {
                "type": "text",
                "text": (
                    f"Agent recording: {len(agent_frames)} frames sampled "
                    "in time order from start to end, at corresponding timestamps "
                    "in the agent's own runtime."
                ),
            }
        )
        for i, (b64, timestamp) in enumerate(agent_frames):
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"Agent frame {i + 1} of {len(agent_frames)} at "
                        f"t={timestamp:.2f}s:"
                    ),
                }
            )
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                }
            )

        content.append({"type": "text", "text": PROMPT_TEMPLATE})

        message = client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": content}],
        )

        raw_text = "".join(
            block.text for block in message.content if block.type == "text"
        )
        rubric, parse_warning = _parse_rubric(raw_text)

        scores = []
        components = {}
        for criterion in RUBRIC_CRITERIA:
            entry = rubric.get(criterion, {})
            value = float(entry.get("score", 0))
            value = max(1.0, min(SCORE_RANGE, value))
            components[criterion] = value / SCORE_RANGE
            scores.append(value)

        score = float(sum(scores)) / (SCORE_RANGE * len(scores))

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        metadata = {
            "grader": self.name,
            "model": self.model,
            "elapsed_ms": elapsed_ms,
            "num_frames_per_video": NUM_FRAMES,
            "agent_timestamps": [round(t, 3) for _, t in agent_frames],
            "truth_timestamps": [round(t, 3) for _, t in truth_frames],
            "input_tokens": getattr(message.usage, "input_tokens", None),
            "output_tokens": getattr(message.usage, "output_tokens", None),
            "rubric_reasons": {
                k: v.get("reason", "") for k, v in rubric.items()
            },
        }
        if parse_warning:
            metadata["parse_warning"] = parse_warning

        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata=metadata,
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
            if not opened or frame_count < 1:
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


def _extract_frame_sequence(video_path: Path) -> list[tuple[str, float]]:
    """Sample NUM_FRAMES evenly-spaced frames; return [(b64_png, t_seconds), ...]."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames < 1:
        cap.release()
        raise RuntimeError(f"Video has no frames: {video_path}")

    sample_indices = np.linspace(
        0, max(0, total_frames - 1), NUM_FRAMES
    ).astype(int)

    out: list[tuple[str, float]] = []
    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb).resize(
            (FRAME_WIDTH, FRAME_HEIGHT),
            Image.Resampling.LANCZOS,
        )
        buffer = io.BytesIO()
        pil.save(buffer, format="PNG")
        b64 = base64.standard_b64encode(buffer.getvalue()).decode("ascii")
        timestamp = float(idx) / fps if fps > 0 else 0.0
        out.append((b64, timestamp))
    cap.release()

    if not out:
        raise RuntimeError(f"Could not read any frames from: {video_path}")
    return out


def _parse_rubric(text: str) -> tuple[dict, str | None]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}, "no JSON object found in response"
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            return {}, f"JSON parse failed: {error}"
    if not isinstance(data, dict):
        return {}, f"expected JSON object, got {type(data).__name__}"
    return data, None
