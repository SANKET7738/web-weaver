# Part 2: animation graders

When a task includes screen recordings of motion design (not just
still screenshots), we add two more graders that operate on mp4s
instead of PNGs.

## What each grader tests

| Grader | What it tests | API cost |
|---|---|---|
| `animation_temporal` | Did the *amount and timing* of motion match? Per-frame motion magnitude over time, binned into 16 fractional buckets. | none |
| `animation_vlm` | Did the *kind* of motion match? 16 sampled frames per video → labeled time-stamped sequence → Claude scores on 5 criteria. | 1 Claude vision call per page |

## Pseudo-code

```
# animation_temporal
agent_signal = per_frame_mean_abs_grayscale_diff(agent.mp4)   # 360x250 downsampled
truth_signal = per_frame_mean_abs_grayscale_diff(truth.mp4)

temporal_corr     = cosine_similarity(bin(agent_signal, 16), bin(truth_signal, 16))
onload_match      = min/max ratio of motion in first 2.5s     (top-hold window)
bottom_hold_match = min/max ratio of motion in last 2.0s      (bottom-hold window)

score = mean(temporal_corr, onload_match, bottom_hold_match)
```

```
# animation_vlm
truth_frames = sample 16 evenly-spaced 480x333 frames from truth.mp4
agent_frames = sample 16 evenly-spaced 480x333 frames from agent.mp4
prompt = "Reference frame N of 16 at t=X.YYs: <img>"  x16  +  same for agent  +  rubric

5 criteria (1-5 Likert each):
  entrance_match        # first 2.5s, on-load animation
  scroll_reveal_match   # middle frames, scroll-triggered reveals
  ambient_motion_match  # final 2.0s, looped motion at rest
  intensity_calibration # overall motion energy
  steady_state_match    # final frame correctness

score = mean(scores) / 5
```

The capture protocol is identical for reference and agent: 1440×1000
viewport, hold at top ~2.5s, eased scroll to bottom, hold at bottom
~2.0s. That fixed protocol is what lets us read "motion in the first
2.5s" as "on-load animation" and "motion in the last 2.0s" as
"ambient/looped motion at rest".

## Results on a real Claude-Code run (ww-00031)

We re-ran Harbor on `ww-00031/attempt-003` (jazz festival site) with
the recording-aware verifier and scored all 5 page pairs.

Summary table (per-page mean + the two most-telling components from
each grader):

| page | temporal | vlm | t.onload | t.bottom_hold | v.entrance | v.steady_state |
|---|---|---|---|---|---|---|
| page_01 (home) | 0.677 | **0.760** | 0.896 | 0.159 | 0.60 | 1.00 |
| page_02 (lineup) | **0.547** | 0.720 | 0.618 | 0.058 | **0.40** | 1.00 |
| page_03 (tickets) | 0.768 | 0.720 | 0.471 | 0.940 | 0.60 | 1.00 |
| page_04 (map) | 0.784 | **0.680** | 0.898 | 0.457 | **0.40** | 1.00 |
| page_05 (experience) | 0.602 | 0.760 | 0.653 | 0.191 | 0.60 | 0.80 |
| **mean** | **0.676** | **0.728** | 0.707 | 0.361 | 0.52 | 0.96 |

### Per-page video pairs and full component breakdown

Each row plays the reference recording (left) and Claude Code's
recording (right) side by side. Below each pair is the full
component breakdown from both graders.

#### page_01 — home

<table>
<tr><th>Truth</th><th>Agent (Claude Code)</th></tr>
<tr>
<td><video src="videos/ww-00031/truth-page_01.mp4" controls width="420" muted></video></td>
<td><video src="videos/ww-00031/agent-page_01.mp4" controls width="420" muted></video></td>
</tr>
</table>

| grader | score | components |
|---|---|---|
| `animation_temporal` | **0.677** | temporal_corr **0.977** · onload_match **0.896** · bottom_hold_match **0.159** |
| `animation_vlm` | **0.760** | entrance **0.60** · scroll_reveal **0.80** · ambient **0.80** · intensity **0.60** · steady_state **1.00** |

#### page_02 — lineup

<table>
<tr><th>Truth</th><th>Agent (Claude Code)</th></tr>
<tr>
<td><video src="videos/ww-00031/truth-page_02.mp4" controls width="420" muted></video></td>
<td><video src="videos/ww-00031/agent-page_02.mp4" controls width="420" muted></video></td>
</tr>
</table>

| grader | score | components |
|---|---|---|
| `animation_temporal` | **0.547** | temporal_corr **0.967** · onload_match **0.618** · bottom_hold_match **0.058** |
| `animation_vlm` | **0.720** | entrance **0.40** · scroll_reveal **0.80** · ambient **0.80** · intensity **0.60** · steady_state **1.00** |

#### page_03 — tickets

<table>
<tr><th>Truth</th><th>Agent (Claude Code)</th></tr>
<tr>
<td><video src="videos/ww-00031/truth-page_03.mp4" controls width="420" muted></video></td>
<td><video src="videos/ww-00031/agent-page_03.mp4" controls width="420" muted></video></td>
</tr>
</table>

| grader | score | components |
|---|---|---|
| `animation_temporal` | **0.768** | temporal_corr **0.891** · onload_match **0.471** · bottom_hold_match **0.940** |
| `animation_vlm` | **0.720** | entrance **0.60** · scroll_reveal **0.60** · ambient **0.80** · intensity **0.60** · steady_state **1.00** |

#### page_04 — map

<table>
<tr><th>Truth</th><th>Agent (Claude Code)</th></tr>
<tr>
<td><video src="videos/ww-00031/truth-page_04.mp4" controls width="420" muted></video></td>
<td><video src="videos/ww-00031/agent-page_04.mp4" controls width="420" muted></video></td>
</tr>
</table>

| grader | score | components |
|---|---|---|
| `animation_temporal` | **0.784** | temporal_corr **0.997** · onload_match **0.898** · bottom_hold_match **0.457** |
| `animation_vlm` | **0.680** | entrance **0.40** · scroll_reveal **0.80** · ambient **0.60** · intensity **0.60** · steady_state **1.00** |

#### page_05 — experience

<table>
<tr><th>Truth</th><th>Agent (Claude Code)</th></tr>
<tr>
<td><video src="videos/ww-00031/truth-page_05.mp4" controls width="420" muted></video></td>
<td><video src="videos/ww-00031/agent-page_05.mp4" controls width="420" muted></video></td>
</tr>
</table>

| grader | score | components |
|---|---|---|
| `animation_temporal` | **0.602** | temporal_corr **0.962** · onload_match **0.653** · bottom_hold_match **0.191** |
| `animation_vlm` | **0.760** | entrance **0.60** · scroll_reveal **0.80** · ambient **0.80** · intensity **0.80** · steady_state **0.80** |

### What the data tells us

**Claude gets the final layout right but skips the entrance
animations.** Across all 5 pages:

- `steady_state_match` averages **0.96/1.0** — final rendered page
  is essentially correct.
- `entrance_match` averages **0.52/1.0** — the staged text reveals,
  underline sweeps, and word-by-word fade-ins from the reference are
  almost always skipped; Claude renders the headline as already-built
  at t=0.
- `intensity_calibration` averages **0.64/1.0** — overall motion
  energy is lower than reference (compounding the missed entrances).

`animation_temporal`'s `bottom_hold_match` is the most telling
component — it swings from 0.058 (no ambient motion at all) to 0.940
(matches well), depending on whether the reference has ambient
looped motion that Claude skipped. Page 04's reference has a compass
spin on the map illustration; Claude's map is static, so the VLM
penalizes ambient motion and the temporal grader catches the missing
motion energy in the bottom-hold window.

One asymmetric case: **page 05** has the *reverse* problem — Claude
*added* an entrance fade that the reference doesn't have. Both
graders penalize over-animation roughly as much as under-animation,
which is the symmetric behaviour you want from a motion-fidelity
metric.

## Failure modes Claude shows on motion design

From the VLM's per-criterion reasons across the 5 pages:

1. **Skipped staged text entrances** (5/5 pages): "Reference reveals
   'Three days drawn from the best of jazz culture.' progressively
   word-by-word with a staggered fade-in; agent jumps to a
   fully-formed headline."
2. **Missing underline / accent reveals** (3/5 pages): "Reference has
   the underline highlight sweeping in under the title; agent has
   the underline statically present."
3. **Skipped ambient looped motion** (1/5 pages clearly, more subtly
   in others): "Reference shows an ambient compass/arrow rotation on
   the map illustration which the agent's map appears to lack."
4. **Occasional over-animation** (1/5 pages): "Agent shows a clear
   text fade-in entrance the reference doesn't have."

The aggregate signal: **Claude treats motion design as decoration it
can drop** to focus on the static layout. The graders detect this
cleanly — the gap between `steady_state_match` (0.96) and
`entrance_match` (0.52) is the per-criterion fingerprint of "right
page, wrong motion".

## Glossary (animation-specific)

See `part1.md` glossary for SSIM/LPIPS/CLIP/etc. Terms that only
appear here:

- **mp4 / screen recording**: a short video of the page captured at
  1440×1000 viewport. Reference and agent recordings follow the same
  protocol: hold at top for 2.5s, easing scroll to bottom over ~8s,
  hold at bottom for 2s. ~12-15s total per page.
- **Per-frame motion magnitude**: for each frame after the first,
  the mean absolute difference (in grayscale) between this frame
  and the previous frame, normalised to `[0, 1]`. Big number =
  lots changed visually; near zero = nothing moved.
- **Top-hold window**: the first 2.5 seconds of the recording. The
  page is held at scroll position 0, so any motion in this window
  is *on-load animation* — entrance fades, staged reveals, etc.
- **Bottom-hold window**: the last 2.0 seconds of the recording.
  The page is held at the bottom, so any motion in this window is
  *ambient looped motion* — compass spins, marquees, breathing
  icons, pulses.
- **Likert scale (1-5)**: a discrete rating scale. The VLM picks
  an integer 1-5 per criterion; we rescale to `[0, 1]` by dividing
  by 5.
