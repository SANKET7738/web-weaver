"""Generate plot options for the per-grader summary section of docs/part1.md.

For each of 12 sites, compute the per-grader mean across pages.
Then render four plot options on the resulting (12 sites x 7 graders) matrix:
  1. bar + error bars (mean +/- std, with min/max whiskers)
  2. box plot
  3. violin plot
  4. strip plot (all individual site means)

All saved to docs/figures/grader-summary-{option}.png at 300 dpi.
"""
import json
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
GRADER_DIR = REPO / "Runs" / "Graders"
OUT_DIR = REPO / "docs" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GRADER_ORDER = [
    "design2code",
    "design2code_vlm",
    "design2code_vlm_sliced",
    "waffle",
    "perceptual",
    "clip_only",
    "vlm_judge",
]
LABELS = {
    "design2code": "design2code",
    "design2code_vlm": "d2c_vlm",
    "design2code_vlm_sliced": "d2c_vlm_sliced",
    "waffle": "waffle",
    "perceptual": "perceptual",
    "clip_only": "clip_only",
    "vlm_judge": "vlm_judge",
}

# Load every per-task JSON, collect per-site per-grader means.
records = []
files = sorted(GRADER_DIR.glob("ww-*-real-run.json"))
files = [f for f in files if "animation" not in f.name]
print(f"loaded {len(files)} grader files")
for f in files:
    site = f.name.replace("-real-run.json", "")
    data = json.loads(f.read_text())
    by_grader = defaultdict(list)
    for row in data["rows"]:
        by_grader[row["grader"]].append(row["score"])
    for g in GRADER_ORDER:
        if g in by_grader:
            records.append({"site": site, "grader": g, "mean": float(np.mean(by_grader[g]))})

df = pd.DataFrame(records)
pivot = df.pivot(index="site", columns="grader", values="mean")[GRADER_ORDER]
print(pivot.round(3))
print(f"\nshape: {pivot.shape}  (sites x graders)")

# Color per grader for visual consistency across plots.
COLORS = ["#3b82f6", "#0ea5e9", "#06b6d4", "#22c55e",
          "#f59e0b", "#94a3b8", "#a855f7"]


def style(ax, title):
    ax.set_ylim(0.50, 1.00)
    ax.set_ylabel("score (mean across 5 pages)")
    ax.set_xlabel("")
    ax.set_title(title, fontsize=12, pad=12)
    ax.yaxis.grid(True, linestyle=":", alpha=0.4)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_xticklabels([LABELS[g] for g in GRADER_ORDER], rotation=20, ha="right")


# ---- Option 1: bar + error bars (std as error bar, min/max as whiskers)
fig, ax = plt.subplots(figsize=(9, 4.5))
means = pivot.mean(axis=0).values
stds = pivot.std(axis=0).values
mins = pivot.min(axis=0).values
maxs = pivot.max(axis=0).values
x = np.arange(len(GRADER_ORDER))
ax.bar(x, means, yerr=stds, capsize=6, color=COLORS, alpha=0.85,
       edgecolor="#1e293b", linewidth=0.8,
       error_kw=dict(ecolor="#1e293b", lw=1.2))
ax.scatter(x, mins, marker="v", color="#1e293b", zorder=3, label="min")
ax.scatter(x, maxs, marker="^", color="#1e293b", zorder=3, label="max")
for xi, m in zip(x, means):
    ax.text(xi, m + 0.012, f"{m:.3f}", ha="center", fontsize=9)
ax.set_xticks(x)
style(ax, "Per-grader score across 12 sites — bar + std (whiskers = min/max)")
ax.legend(loc="lower left", frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "grader-summary-bar.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- Option 2: box plot
fig, ax = plt.subplots(figsize=(9, 4.5))
data = [pivot[g].values for g in GRADER_ORDER]
bp = ax.boxplot(
    data, positions=x, widths=0.55, patch_artist=True,
    medianprops=dict(color="#1e293b", lw=1.4),
    whiskerprops=dict(color="#1e293b"),
    capprops=dict(color="#1e293b"),
    flierprops=dict(marker="o", markerfacecolor="#1e293b",
                    markeredgecolor="#1e293b", markersize=4),
)
for patch, c in zip(bp["boxes"], COLORS):
    patch.set_facecolor(c)
    patch.set_alpha(0.75)
ax.set_xticks(x)
style(ax, "Per-grader score across 12 sites — box (median, IQR, range)")
plt.tight_layout()
plt.savefig(OUT_DIR / "grader-summary-box.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- Option 3: violin plot
fig, ax = plt.subplots(figsize=(9, 4.5))
parts = ax.violinplot(data, positions=x, widths=0.7, showmeans=False,
                      showmedians=True, showextrema=True)
for body, c in zip(parts["bodies"], COLORS):
    body.set_facecolor(c)
    body.set_edgecolor("#1e293b")
    body.set_alpha(0.7)
for k in ("cbars", "cmins", "cmaxes", "cmedians"):
    if k in parts:
        parts[k].set_color("#1e293b")
        parts[k].set_linewidth(1.0)
# Overlay site means as small dots for transparency
for xi, g in zip(x, GRADER_ORDER):
    ys = pivot[g].values
    xs = np.full_like(ys, xi, dtype=float) + np.random.uniform(-0.05, 0.05, len(ys))
    ax.scatter(xs, ys, color="#1e293b", s=12, alpha=0.6, zorder=3)
ax.set_xticks(x)
style(ax, "Per-grader score across 12 sites — violin (distribution + site dots)")
plt.tight_layout()
plt.savefig(OUT_DIR / "grader-summary-violin.png", dpi=300, bbox_inches="tight")
plt.close()

# ---- Option 4: strip plot with mean line
np.random.seed(0)
fig, ax = plt.subplots(figsize=(9, 4.5))
for xi, g, c in zip(x, GRADER_ORDER, COLORS):
    ys = pivot[g].values
    xs = np.full_like(ys, xi, dtype=float) + np.random.uniform(-0.12, 0.12, len(ys))
    ax.scatter(xs, ys, color=c, s=44, alpha=0.85, edgecolor="#1e293b", linewidth=0.4)
    m = float(np.mean(ys))
    ax.hlines(m, xi - 0.22, xi + 0.22, color="#1e293b", lw=2.0, zorder=4)
    ax.text(xi, m + 0.012, f"{m:.3f}", ha="center", fontsize=9, fontweight="bold")
ax.set_xticks(x)
style(ax, "Per-grader score across 12 sites — strip plot (one dot per site, bar = mean)")
plt.tight_layout()
plt.savefig(OUT_DIR / "grader-summary-strip.png", dpi=300, bbox_inches="tight")
plt.close()

print("\nwrote 4 plots to docs/figures/:")
for p in sorted(OUT_DIR.glob("grader-summary-*.png")):
    print(f"  {p.relative_to(REPO)}  {p.stat().st_size // 1024} KB")
