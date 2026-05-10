#!/usr/bin/env bash
# Run N sequential harbor agent runs against one harbor task and track each
# in a manifest. Resume-friendly: re-running picks up after the last
# completed trial.
#
# Usage: scripts/run_variance_runs.sh [task_id] [attempt] [n]
# Defaults: ww-00022 attempt-002 10
#
# Outputs under Runs/Variance/<task_id>-<attempt>/:
#   manifest.tsv             trial bookkeeping
#   runs.log                 high-level driver log
#   run-NN.log               full harbor stdout per trial
#
# Companion: scripts/score_variance_runs.sh reads the manifest and runs
# the grader package per completed trial.

set -euo pipefail

TASK_ID="${1:-ww-00022}"
ATTEMPT="${2:-attempt-002}"
N_RUNS="${3:-10}"
MODEL="${MODEL:-claude-opus-4-7}"
AGENT="${AGENT:-claude-code}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

HARBOR_TASK_DIR="Runs/SiteGeneration/${TASK_ID}/${ATTEMPT}/harbor"
EXPERIMENT_DIR="Runs/Variance/${TASK_ID}-${ATTEMPT}"
MANIFEST="${EXPERIMENT_DIR}/manifest.tsv"
DRIVER_LOG="${EXPERIMENT_DIR}/runs.log"

if [ ! -d "${HARBOR_TASK_DIR}" ]; then
  echo "Harbor task directory not found: ${HARBOR_TASK_DIR}" >&2
  exit 2
fi

mkdir -p "${EXPERIMENT_DIR}"
if [ ! -f "${MANIFEST}" ]; then
  printf "trial\tstarted_at\tfinished_at\tjob_dir\ttrial_dir\treward\tstatus\n" > "${MANIFEST}"
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f .env ]; then
  set +u
  export ANTHROPIC_API_KEY="$(grep -E '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)"
  set -u
fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ANTHROPIC_API_KEY is required (export it or put it in .env)" >&2
  exit 2
fi

if [ ! -x .venv/bin/python3 ]; then
  echo "Expected .venv/bin/python3 to exist; run uv sync first" >&2
  exit 2
fi

trial_status() {
  # Read the recorded status of a trial number, or empty string if missing.
  local trial="$1"
  awk -F'\t' -v t="${trial}" 'NR>1 && $1==t {print $7}' "${MANIFEST}" | tail -1
}

echo "===== run_variance_runs.sh starting at $(date)" | tee -a "${DRIVER_LOG}"
echo "  task=${TASK_ID} attempt=${ATTEMPT} n=${N_RUNS} agent=${AGENT} model=${MODEL}" \
  | tee -a "${DRIVER_LOG}"
echo "  experiment dir: ${EXPERIMENT_DIR}" | tee -a "${DRIVER_LOG}"

for i in $(seq 1 "${N_RUNS}"); do
  trial_num="$(printf "%02d" "$i")"
  existing="$(trial_status "${trial_num}" || true)"
  if [ "${existing}" = "completed" ]; then
    echo "----- trial ${trial_num}: already completed, skipping" \
      | tee -a "${DRIVER_LOG}"
    continue
  fi

  started_at="$(date -u +%FT%TZ)"
  echo "----- trial ${trial_num} starting at ${started_at}" \
    | tee -a "${DRIVER_LOG}"

  run_log="${EXPERIMENT_DIR}/run-${trial_num}.log"
  set +e
  harbor run \
    -p "${HARBOR_TASK_DIR}" \
    -a "${AGENT}" \
    -m "${MODEL}" \
    > "${run_log}" 2>&1
  rc=$?
  set -e

  finished_at="$(date -u +%FT%TZ)"
  job_dir="$(grep -E "Results written to jobs/" "${run_log}" | sed -E 's|.*Results written to jobs/([^/]+)/.*|\1|' | head -1)"
  if [ -z "${job_dir}" ]; then
    job_dir="-"
    trial_dir="-"
    reward="-"
    status="failed_no_job_dir_rc=${rc}"
  else
    trial_dir="$(ls "jobs/${job_dir}" 2>/dev/null | grep -E '^harbor__' | head -1)"
    if [ -z "${trial_dir}" ]; then
      trial_dir="-"
      reward="-"
      status="failed_no_trial_dir_rc=${rc}"
    else
      reward_txt="jobs/${job_dir}/${trial_dir}/verifier/reward.txt"
      if [ -f "${reward_txt}" ]; then
        reward="$(tr -d '[:space:]' < "${reward_txt}")"
        status="completed"
      else
        reward="-"
        status="failed_no_reward_rc=${rc}"
      fi
    fi
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "${trial_num}" "${started_at}" "${finished_at}" "${job_dir}" \
    "${trial_dir}" "${reward}" "${status}" \
    >> "${MANIFEST}"

  echo "  trial ${trial_num} finished at ${finished_at}: status=${status} reward=${reward} job=${job_dir} trial=${trial_dir}" \
    | tee -a "${DRIVER_LOG}"
done

echo "===== run_variance_runs.sh complete at $(date)" | tee -a "${DRIVER_LOG}"
echo "Manifest: ${MANIFEST}" | tee -a "${DRIVER_LOG}"
echo "Next:    scripts/score_variance_runs.sh ${TASK_ID} ${ATTEMPT}" | tee -a "${DRIVER_LOG}"
