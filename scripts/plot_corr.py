"""Plot options for the Spearman rank-correlation matrix between graders.

Re-derives the matrix from Runs/Graders/ww-*-real-run.json (per-site means
across the 12 sites, then scipy.stats.spearmanr).

Options:
  A. Full symmetric heatmap with cell values
  B. Lower triangle only (drop redundant upper triangle + diagonal)
  C. Lower triangle, clustered ordering (rows/cols reordered so similar
     graders sit next to each other)
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

REPO = Path(__file__).resolve().parents[1]
GRADER_DIR = REPO / "Runs" / "Graders"
OUT_DIR = REPO / "docs" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GRADERS = [
    "design2code",
    "design2code_vlm",
    "design2code_vlm_sliced",
    "waffle",
    "perceptual",
    "vlm_judge",
    "clip_only",
]
LABELS = {
    "design2code": "design2code",
    "design2code_vlm": "d2c_vlm",
    "design2code_vlm_sliced": "sliced",
    "waffle": "waffle",
    "perceptual": "perceptual",
    "vlm_judge": "vlm_judge",
    "clip_only": "clip_only",
}

records = []
for f in sorted(GRADER_DIR.glob("ww-*-real-run.json")):
    if "animation" in f.name:
        continue
    site = f.name.replace("-real-run.json", "")
    data = json.loads(f.read_text())
    by_grader = defaultdict(list)
    for row in data["rows"]:
        by_grader[row["grader"]].append(row["score"])
    for g in GRADERS:
        if g in by_grader:
            records.append({"site": site, "grader": g, "mean": float(np.mean(by_grader[g]))})

df = pd.DataFrame(records)
pivot = df.pivot(index="site", columns="grader", values="mean")[GRADERS]
corr = pivot.corr(method="spearman")[GRADERS].loc[GRADERS]
print("Spearman rank correlation (12 sites):")
print(corr.round(2))

# Diverging colormap centered at 0.
cmap = LinearSegmentedColormap.from_list(
    "div", ["#1e3a8a", "#3b82f6", "#f8fafc", "#f97316", "#7f1d1d"], N=256
)


def annotate(ax, mat, mask=None):
    n = mat.shape[0]
    for i in range(n):
        for j in range(n):
            if mask is not None and mask[i, j]:
                continue
            v = mat[i, j]
            text_color = "#0f172a" if -0.4 < v < 0.7 else "#ffffff"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color=text_color, fontsize=10)


def style_ticks(ax, labels):
    n = len(labels)
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_yticks(np.arange(n))
    ax.set_yticklabels(labels)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---- A. Full symmetric heatmap ----
fig, ax = plt.subplots(figsize=(8, 6.5))
im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect="equal")
annotate(ax, corr.values)
style_ticks(ax, [LABELS[g] for g in GRADERS])
ax.set_title("Spearman rank correlation (full)", fontsize=12, pad=12)
cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
cbar.set_label("Spearman rho", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "corr-A-full.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- B. Lower-triangle only ----
mat = corr.values.copy()
mask = np.triu(np.ones_like(mat, dtype=bool), k=0)  # mask upper + diagonal
mat_masked = np.ma.array(mat, mask=mask)
fig, ax = plt.subplots(figsize=(8, 6.5))
cmap_b = cmap.copy()
cmap_b.set_bad("white")
im = ax.imshow(mat_masked, cmap=cmap_b, vmin=-1, vmax=1, aspect="equal")
annotate(ax, mat, mask=mask)
style_ticks(ax, [LABELS[g] for g in GRADERS])
ax.set_title("Spearman rank correlation (lower triangle)", fontsize=12, pad=12)
cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
cbar.set_label("Spearman rho", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "corr-B-lower.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- C. Lower-triangle, clustered ordering ----
# Hierarchical clustering with 1-|corr| as distance.
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform

dist = 1.0 - corr.values
np.fill_diagonal(dist, 0.0)
dist = (dist + dist.T) / 2.0           # symmetrize against fp noise
condensed = squareform(dist, checks=False)
linkage = hierarchy.linkage(condensed, method="average")
order = hierarchy.leaves_list(linkage)
clustered_labels = [GRADERS[i] for i in order]
clustered = corr.loc[clustered_labels, clustered_labels].values

mask_c = np.triu(np.ones_like(clustered, dtype=bool), k=0)
clustered_masked = np.ma.array(clustered, mask=mask_c)
fig, ax = plt.subplots(figsize=(8, 6.5))
im = ax.imshow(clustered_masked, cmap=cmap_b, vmin=-1, vmax=1, aspect="equal")
annotate(ax, clustered, mask=mask_c)
style_ticks(ax, [LABELS[g] for g in clustered_labels])
ax.set_title("Spearman rank correlation (lower, clustered ordering)",
             fontsize=12, pad=12)
cbar = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
cbar.set_label("Spearman rho", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "corr-C-clustered.png", dpi=300, bbox_inches="tight")
plt.close()

print("\nwrote 3 correlation plots:")
for p in sorted(OUT_DIR.glob("corr-*.png")):
    print(f"  {p.relative_to(REPO)}  {p.stat().st_size // 1024} KB")
print("\nClustered ordering:", [LABELS[l] for l in clustered_labels])
