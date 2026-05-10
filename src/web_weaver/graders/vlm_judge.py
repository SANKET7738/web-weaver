"""VLM-as-judge grader.

Asks a multimodal Claude model to score the agent's screenshot against the
ground-truth screenshot on a fixed 10-criterion rubric, then aggregates
into ``[0, 1]``.

The rubric is the one specified in ``graders_plan.md``:

    1. Layout fidelity
    2. Color accuracy
    3. Typography hierarchy
    4. Spacing and rhythm
    5. Component structure
    6. Image/asset placement
    7. Text content fidelity
    8. Visual polish
    9. Semantic correctness
    10. Overall similarity

Each criterion is scored on a ``1-5`` Likert scale; aggregate score is
``mean(scores) / 5``. ``temperature=0`` for determinism.

This grader makes a real Anthropic API call per pair. Cost is roughly
$0.05-0.30 per evaluation depending on model and image size.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

from web_weaver.graders.base import (
    Grader,
    GraderResult,
    clamp01,
)


DEFAULT_MODEL = "claude-opus-4-7"
RUBRIC_CRITERIA = [
    "layout_fidelity",
    "color_accuracy",
    "typography_hierarchy",
    "spacing_and_rhythm",
    "component_structure",
    "asset_placement",
    "text_content_fidelity",
    "visual_polish",
    "semantic_correctness",
    "overall_similarity",
]
SCORE_RANGE = 5.0
MAX_TOKENS = 1024
PROMPT_TEMPLATE = """You are evaluating how well a generated webpage replicates a reference design.

The first image is the **reference design** (ground truth).
The second image is the **agent-generated webpage**.

Score the generated page on each criterion below on a 1-5 Likert scale.
Reserve 5 for near-pixel-perfect matches and 1 for unrecognizable. Do NOT
default to the middle. Anchor your judgments on the **reference**, not on
"this looks like a reasonable webpage in general".

CALIBRATION ANCHORS

- Score 5: virtually indistinguishable from the reference; differences
  imperceptible without side-by-side comparison.
- Score 4: clear match in this dimension; only minor refinements would be
  needed to call it identical.
- Score 3: roughly comparable; the dimension is recognizably present but
  has substantial differences from the reference (e.g. a card grid is
  there, but card colors / icons / text sizes are noticeably different
  from the reference).
- Score 2: dimension is partially present but with large, immediate
  differences (e.g. wrong palette, wrong typography family, wrong
  illustration style).
- Score 1: dimension is essentially absent or wrong (blank, dummy
  content, totally different page).

For each criterion, write a brief one-sentence reason **before** picking
the score. Compare what you see against the reference per-criterion; do
not let a strong score on one criterion lift the others.

CRITERIA

1. layout_fidelity      — Are the same sections, in the same vertical order, with the same column structure?
2. color_accuracy       — Are the accent colors, gradients, and section backgrounds matched? (Per-pixel, not just average.)
3. typography_hierarchy — Are font family, weight, and size relationships matched? Headings vs subtitles vs body.
4. spacing_and_rhythm   — Is whitespace, padding, and density matched section-by-section?
5. component_structure  — Are cards / lists / tables / buttons present with the same internal structure?
6. asset_placement      — Are illustrations, icons, and images in the right places AND of the right kind/style?
7. text_content_fidelity— Is the text matched (allowing for plausible filler where the reference is unreadable)?
8. visual_polish        — Does the generated page have the same level of finish as the reference, or does it look rougher / placeholder-ish?
9. semantic_correctness — Is this clearly the same kind of page (pricing vs about vs contact etc.)?
10. overall_similarity  — Aggregate human-perceptual judgment.

Respond with strict JSON in this exact shape, no prose, no markdown fence:

{
  "layout_fidelity":       {"reason": "<one sentence>", "score": <1-5>},
  "color_accuracy":        {"reason": "<one sentence>", "score": <1-5>},
  "typography_hierarchy":  {"reason": "<one sentence>", "score": <1-5>},
  "spacing_and_rhythm":    {"reason": "<one sentence>", "score": <1-5>},
  "component_structure":   {"reason": "<one sentence>", "score": <1-5>},
  "asset_placement":       {"reason": "<one sentence>", "score": <1-5>},
  "text_content_fidelity": {"reason": "<one sentence>", "score": <1-5>},
  "visual_polish":         {"reason": "<one sentence>", "score": <1-5>},
  "semantic_correctness":  {"reason": "<one sentence>", "score": <1-5>},
  "overall_similarity":    {"reason": "<one sentence>", "score": <1-5>}
}
"""


class VLMJudgeGrader(Grader):
    """Claude-as-judge grader with the 10-criterion rubric."""

    name = "vlm_judge"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL_VLM_JUDGE", DEFAULT_MODEL)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "VLMJudgeGrader requires ANTHROPIC_API_KEY in the environment."
            )

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        from anthropic import Anthropic

        started_at = time.perf_counter()
        client = Anthropic(api_key=self.api_key)

        truth_b64 = _encode_png(truth_screenshot)
        agent_b64 = _encode_png(agent_screenshot)

        message = client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Reference design (ground truth):"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": truth_b64,
                            },
                        },
                        {"type": "text", "text": "Agent-generated webpage:"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": agent_b64,
                            },
                        },
                        {"type": "text", "text": PROMPT_TEMPLATE},
                    ],
                }
            ],
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
            "input_tokens": getattr(message.usage, "input_tokens", None),
            "output_tokens": getattr(message.usage, "output_tokens", None),
            "rubric_reasons": {k: v.get("reason", v.get("note", "")) for k, v in rubric.items()},
        }
        if parse_warning:
            metadata["parse_warning"] = parse_warning

        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata=metadata,
        )


def _encode_png(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("ascii")


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
