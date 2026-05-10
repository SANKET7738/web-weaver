#!/usr/bin/env bash
# Score each completed trial from a variance-run manifest using the grader
# package. Skips trials already scored. Safe to run while the runs script
# is still going - it scores trials as they complete.
#
# Usage: scripts/score_variance_runs.sh [task_id] [attempt]
# Defaults: ww-00022 attempt-002
#
# Reads:
#   Runs/Variance/<task_id>-<attempt>/manifest.tsv
# Writes:
#   Runs/Variance/<task_id>-<attempt>/trial-NN.json    (per-trial scores)
#   Runs/Variance/<task_id>-<attempt>/scoring.log
#
# Companion: scripts/run_variance_runs.sh produces the manifest.

set -euo pipefail

TASK_ID="${1:-ww-00022}"
ATTEMPT="${2:-attempt-002}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

HARBOR_TASK_DIR="Runs/SiteGeneration/${TASK_ID}/${ATTEMPT}/harbor"
EXPERIMENT_DIR="Runs/Variance/${TASK_ID}-${ATTEMPT}"
MANIFEST="${EXPERIMENT_DIR}/manifest.tsv"
DRIVER_LOG="${EXPERIMENT_DIR}/scoring.log"

if [ ! -f "${MANIFEST}" ]; then
  echo "Manifest not found: ${MANIFEST}" >&2
  echo "Run scripts/run_variance_runs.sh ${TASK_ID} ${ATTEMPT} first" >&2
  exit 2
fi

if [ ! -d "${HARBOR_TASK_DIR}" ]; then
  echo "Harbor task directory not found: ${HARBOR_TASK_DIR}" >&2
  exit 2
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f .env ]; then
  set +u
  export ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)"
  set -u
fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY is required for the VLM grader (export it or put it in .env)" >&2
  exit 2
fi

if [ ! -x .venv/bin/python3 ]; then
  echo "Expected .venv/bin/python3 to exist; run uv sync first" >&2
  exit 2
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "===== score_variance_runs.sh starting at $(date)" | tee -a "${DRIVER_LOG}"
echo "  task=${TASK_ID} attempt=${ATTEMPT}" | tee -a "${DRIVER_LOG}"
echo "  experiment dir: ${EXPERIMENT_DIR}" | tee -a "${DRIVER_LOG}"

# Read manifest line-by-line, skipping header, scoring completed trials.
tail -n +2 "${MANIFEST}" | while IFS=$'\t' read -r trial_num started_at finished_at job_dir trial_dir reward status; do
  if [ "${status}" != "completed" ]; then
    echo "----- trial ${trial_num}: status=${status}, skipping" \
      | tee -a "${DRIVER_LOG}"
    continue
  fi

  out_json="${EXPERIMENT_DIR}/trial-${trial_num}.json"
  if [ -f "${out_json}" ]; then
    echo "----- trial ${trial_num}: already scored at ${out_json}, skipping" \
      | tee -a "${DRIVER_LOG}"
    continue
  fi

  echo "----- trial ${trial_num} -> ${out_json} ($(date))" \
    | tee -a "${DRIVER_LOG}"

  set +e
  python3 -m web_weaver.graders.score_harbor_run \
    --job-dir "jobs/${job_dir}/${trial_dir}" \
    --harbor-task-dir "${HARBOR_TASK_DIR}" \
    --out-json "${out_json}" \
    >> "${DRIVER_LOG}" 2>&1
  rc=$?
  set -e

  if [ "${rc}" -ne 0 ]; then
    echo "  trial ${trial_num} scoring failed (rc=${rc}); see ${DRIVER_LOG}" \
      | tee -a "${DRIVER_LOG}"
  else
    echo "  trial ${trial_num} scored at $(date)" | tee -a "${DRIVER_LOG}"
  fi
done

echo "===== score_variance_runs.sh complete at $(date)" | tee -a "${DRIVER_LOG}"
echo "Trial outputs: ${EXPERIMENT_DIR}/trial-*.json" | tee -a "${DRIVER_LOG}"
