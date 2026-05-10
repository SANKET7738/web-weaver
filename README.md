# web-weaver

A recipe for generating Harbor RL tasks that grade an agent's ability
to replicate a multi-page website design from screenshots (and
optional screen recordings) using HTML + CSS + vanilla JS.

📄 **Detailed docs:**
- [`docs/overview.md`](docs/overview.md) — pipeline architecture
- [`docs/part1.md`](docs/part1.md) — still-image graders + empirical evaluation
- [`docs/part2.md`](docs/part2.md) — animation graders + ww-00031 results
- [`docs/valid_tasks.md`](docs/valid_tasks.md) — list of runnable tasks

## Setup

Requires Python 3.12+ and [`uv`](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/SANKET7738/web-weaver.git
cd web-weaver
uv sync
source .venv/bin/activate
playwright install chromium
```

Put your Anthropic API key in a `.env` at the repo root:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

[Harbor](https://harborframework.com/) and [`harbor` CLI](https://github.com/harborframework/harbor) are required to actually run the tasks against an agent.

## Run a task with Claude Code

Pick a task ID from [`docs/valid_tasks.md`](docs/valid_tasks.md), then:

```bash
export ANTHROPIC_API_KEY=$(grep -E '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)
harbor run \
  -p Runs/SiteGeneration/ww-00031/attempt-003/harbor \
  -a claude-code \
  -m claude-opus-4-7
```

Agent output lands under `jobs/<job_id>/harbor__<trial>/verifier/`.

## Score a Harbor run

After the agent has produced screenshots (and recordings if animation
is in scope):

```bash
python -m web_weaver.graders.score_harbor_run \
  --job-dir jobs/<job_id>/harbor__<trial> \
  --harbor-task-dir Runs/SiteGeneration/<task_id>/<attempt>/harbor \
  --out-json Runs/Graders/<task_id>-real-run.json
```

This runs all 7 still-image graders (`design2code`, `design2code_vlm`,
`design2code_vlm_sliced`, `waffle`, `perceptual`, `clip_only`,
`vlm_judge`). Animation graders (`animation_temporal`,
`animation_vlm`) run separately on the mp4 pairs.

## Generate a new task

End-to-end pipeline (concept → blueprint → design plan → site →
Harbor task):

```bash
# 1. Sample a new concept (or several)
web-weaver sample --count 1

# 2. Generate the blueprint
web-weaver blueprint --concept-id ww-00099

# 3. Generate the design plan
web-weaver design --blueprint-id ww-00099

# 4. Build the sitegen container image (once per repo)
web-weaver sitegen-build-image

# 5. Create a fresh attempt directory + run the sitegen container
web-weaver sitegen-create-attempt --task-id ww-00099
web-weaver sitegen-attempt-run --task-id ww-00099 --attempt attempt-001
```

The final attempt produces a runnable Harbor task at
`Runs/SiteGeneration/ww-00099/attempt-001/harbor/`.

## Variance experiment

To re-run the same task N times and score every trial:

```bash
scripts/run_variance_runs.sh ww-00022 attempt-002 5
scripts/score_variance_runs.sh ww-00022 attempt-002
```

Outputs land under `Runs/Variance/<task>-<attempt>/`.

## Regenerate plots

```bash
python scripts/plot_grader_summary.py
python scripts/plot_per_site.py
python scripts/plot_corr.py
```

Outputs land under `docs/figures/`.
