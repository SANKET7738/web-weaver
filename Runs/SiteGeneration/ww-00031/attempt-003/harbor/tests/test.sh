#!/bin/bash
# Verifier entry point. Runs as root (per task.toml [verifier].user = "root").
# Invokes /opt/grader/run.py with the locked grader interface and writes
# Harbor's reward.txt from the resulting reward.json["score"].

set -euo pipefail

REWARD_JSON="/logs/verifier/reward.json"
REWARD_TXT="/logs/verifier/reward.txt"
CAPTURES_DIR="/logs/verifier/agent_screenshots"
RECORDINGS_DIR="/logs/verifier/agent_screenrecordings"

mkdir -p /logs/verifier "${CAPTURES_DIR}" "${RECORDINGS_DIR}"

python3 /opt/grader/run.py \
  --agent-site /app/site \
  --prompt /app/prompt \
  --solution /opt/solution \
  --captures-out "${CAPTURES_DIR}" \
  --recordings-out "${RECORDINGS_DIR}" \
  --reward-out "${REWARD_JSON}"

python3 - "${REWARD_JSON}" "${REWARD_TXT}" <<'PYEOF'
import json
import sys
from pathlib import Path

reward_json_path = Path(sys.argv[1])
reward_txt_path = Path(sys.argv[2])

reward = json.loads(reward_json_path.read_text(encoding="utf-8"))
score = reward.get("score")
if not isinstance(score, (int, float)):
    raise SystemExit(f"Grader did not produce a numeric score: {reward!r}")

reward_txt_path.write_text(f"{float(score):.6f}\n", encoding="utf-8")
PYEOF

echo "Verifier wrote ${REWARD_JSON} and ${REWARD_TXT}"
