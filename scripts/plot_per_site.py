"""Generate plot options for the 'Per-site scores' table in docs/part1.md.

Source: docs/part1.md's per-site table, but re-derived from
Runs/Graders/ww-*-real-run.json so the numbers stay in sync.

Renders four options at 300 dpi:
  A. heatmap (sites x graders, color = score)
  B. small-multiples sorted bar (one panel per grader, sites sorted by that grader's score)
  C. parallel coordinates (one line per site across graders)
  D. grouped bar chart (sites on x-axis, 5 grouped bars per site)

All saved as docs/figures/per-site-{A,B,C,D}.png.
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

# Same graders as the per-site table in part1.md.
GRADERS = [
    "design2code",
    "design2code_vlm",
    "design2code_vlm_sliced",
    "vlm_judge",
    "clip_only",
]
LABELS = {
    "design2code": "design2code",
    "design2code_vlm": "d2c_vlm",
    "design2code_vlm_sliced": "sliced",
    "vlm_judge": "vlm_judge",
    "clip_only": "clip_only",
}
COLORS = {
    "design2code": "#3b82f6",
    "design2code_vlm": "#0ea5e9",
    "design2code_vlm_sliced": "#06b6d4",
    "vlm_judge": "#a855f7",
    "clip_only": "#94a3b8",
}

records = []
for f in sorted(GRADER_DIR.glob("ww-*-real-run.json")):
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
print(pivot.round(3))


def base_style(ax):
    ax.yaxis.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---- A. heatmap ----
fig, ax = plt.subplots(figsize=(8, 6))
cmap = LinearSegmentedColormap.from_list(
    "wb", ["#dc2626", "#fef3c7", "#16a34a"], N=256
)
mat = pivot.values  # sites x graders
im = ax.imshow(mat, cmap=cmap, vmin=0.55, vmax=1.00, aspect="auto")
ax.set_xticks(np.arange(len(GRADERS)))
ax.set_xticklabels([LABELS[g] for g in GRADERS], rotation=20, ha="right")
ax.set_yticks(np.arange(len(pivot.index)))
ax.set_yticklabels(pivot.index)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat[i, j]
        # Pick a text color that stays readable on every shade.
        text_color = "#0f172a" if 0.65 <= v <= 0.92 else "#ffffff"
        ax.text(j, i, f"{v:.3f}", ha="center", va="center",
                color=text_color, fontsize=9)
ax.set_title("Per-site scores — heatmap (red = low, green = high)",
             fontsize=12, pad=12)
cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
cbar.set_label("score (mean over 5 pages)", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "per-site-A-heatmap.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- B. small multiples (one panel per grader, sorted bar) ----
fig, axes = plt.subplots(1, len(GRADERS), figsize=(15, 5), sharey=True)
for ax, g in zip(axes, GRADERS):
    series = pivot[g].sort_values()
    ax.barh(np.arange(len(series)), series.values,
            color=COLORS[g], alpha=0.85, edgecolor="#1e293b", lw=0.4)
    ax.set_yticks(np.arange(len(series)))
    ax.set_yticklabels(series.index, fontsize=9)
    ax.set_xlim(0.55, 1.00)
    for i, v in enumerate(series.values):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=8)
    ax.set_title(LABELS[g], fontsize=11)
    ax.set_xlabel("score")
    base_style(ax)
fig.suptitle("Per-site scores — small multiples (one panel per grader, sites sorted ascending)",
             fontsize=12, y=1.02)
plt.tight_layout()
plt.savefig(OUT_DIR / "per-site-B-smallmult.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- C. parallel coordinates (one line per site) ----
fig, ax = plt.subplots(figsize=(11, 5.5))
x = np.arange(len(GRADERS))
# Use a perceptually ordered palette so we can read site ordering.
site_order = pivot["design2code"].sort_values().index.tolist()
palette = plt.cm.viridis(np.linspace(0.05, 0.95, len(site_order)))
for site, color in zip(site_order, palette):
    ys = pivot.loc[site, GRADERS].values
    ax.plot(x, ys, marker="o", color=color, lw=1.5, alpha=0.9, label=site)
ax.set_xticks(x)
ax.set_xticklabels([LABELS[g] for g in GRADERS])
ax.set_ylim(0.55, 1.00)
ax.set_ylabel("score (mean over 5 pages)")
ax.set_title("Per-site scores — parallel coordinates (one line per site, color = design2code rank)",
             fontsize=12, pad=12)
base_style(ax)
ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8,
          frameon=False, ncol=1)
plt.tight_layout()
plt.savefig(OUT_DIR / "per-site-C-parallel.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- D. grouped bar chart ----
fig, ax = plt.subplots(figsize=(12, 5))
sites = pivot.index.tolist()
x = np.arange(len(sites))
width = 0.16
for i, g in enumerate(GRADERS):
    offset = (i - (len(GRADERS) - 1) / 2) * width
    ax.bar(x + offset, pivot[g].values, width=width,
           color=COLORS[g], alpha=0.9, edgecolor="#1e293b", lw=0.3,
           label=LABELS[g])
ax.set_xticks(x)
ax.set_xticklabels(sites, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("score")
ax.set_ylim(0.55, 1.00)
ax.set_title("Per-site scores — grouped bars (5 graders per site)",
             fontsize=12, pad=12)
ax.legend(loc="lower right", fontsize=9, frameon=False, ncol=5)
base_style(ax)
plt.tight_layout()
plt.savefig(OUT_DIR / "per-site-D-grouped.png", dpi=300, bbox_inches="tight")
plt.close()

print("\nwrote 4 per-site plots:")
for p in sorted(OUT_DIR.glob("per-site-*.png")):
    print(f"  {p.relative_to(REPO)}  {p.stat().st_size // 1024} KB")
