"""Perceptual-only grader.

Combines two classical perceptual metrics:

- **SSIM** (Structural Similarity Index): pixel-window structural
  correlation, ``skimage.metrics.structural_similarity``.
- **LPIPS** (Learned Perceptual Image Patch Similarity): VGG-backbone
  CNN features compared with weighted L2.

Score = ``0.5 * ssim + 0.5 * lpips_similarity`` where
``lpips_similarity = 1 - lpips_distance``.

Reference papers:
- Wang et al., "Image Quality Assessment: From Error Visibility to
  Structural Similarity", IEEE TIP 2004.
- Zhang et al., "The Unreasonable Effectiveness of Deep Features as a
  Perceptual Metric", CVPR 2018, https://arxiv.org/abs/1801.03924
"""
from __future__ import annotations

import time
from pathlib import Path
from threading import Lock

import numpy as np
import torch
from PIL import Image
from skimage.metrics import structural_similarity

from web_weaver.graders.base import (
    CANONICAL_WIDTH,
    Grader,
    GraderResult,
    clamp01,
    load_image_pair,
    load_image_pair_pil,
)


_lpips_lock = Lock()
_lpips_state: dict | None = None


def _get_lpips():
    global _lpips_state
    with _lpips_lock:
        if _lpips_state is None:
            import lpips

            net = lpips.LPIPS(net="vgg")
            net.eval()
            device = "cuda" if torch.cuda.is_available() else "cpu"
            net.to(device)
            _lpips_state = {"net": net, "device": device}
    return _lpips_state


class PerceptualGrader(Grader):
    """SSIM + LPIPS perceptual baseline."""

    name = "perceptual"

    def grade(
        self,
        agent_screenshot: Path,
        truth_screenshot: Path,
    ) -> GraderResult:
        started_at = time.perf_counter()

        agent_arr, truth_arr = load_image_pair(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )
        ssim_score = _ssim(agent_arr, truth_arr)

        agent_pil, truth_pil = load_image_pair_pil(
            agent_screenshot, truth_screenshot, canonical_width=CANONICAL_WIDTH
        )
        lpips_similarity = _lpips_similarity(agent_pil, truth_pil)

        components = {
            "ssim": clamp01(ssim_score),
            "lpips": clamp01(lpips_similarity),
        }
        score = float(np.mean(list(components.values())))

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        return GraderResult(
            score=clamp01(score),
            components=components,
            metadata={"grader": self.name, "elapsed_ms": elapsed_ms},
        )


def _ssim(agent_arr: np.ndarray, truth_arr: np.ndarray) -> float:
    if agent_arr.ndim == 3:
        score = structural_similarity(
            agent_arr,
            truth_arr,
            channel_axis=2,
            data_range=255,
        )
    else:
        score = structural_similarity(agent_arr, truth_arr, data_range=255)
    return clamp01(float(score))


def _lpips_similarity(agent_pil: Image.Image, truth_pil: Image.Image) -> float:
    state = _get_lpips()
    net = state["net"]
    device = state["device"]
    with torch.no_grad():
        agent_tensor = _pil_to_lpips_tensor(agent_pil).to(device)
        truth_tensor = _pil_to_lpips_tensor(truth_pil).to(device)
        distance = net(agent_tensor, truth_tensor).item()
    return clamp01(1.0 - float(distance))


def _pil_to_lpips_tensor(image: Image.Image) -> torch.Tensor:
    arr = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor * 2.0 - 1.0
