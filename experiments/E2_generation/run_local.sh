#!/usr/bin/env bash
# Tier 2 local CPU run. Resumable: rerunning skips finished jobs of the SAME run identity.
# Usage: bash experiments/E2_generation/run_local.sh <new-run-name> [model-dir]
# The historical CPU run runs/qwen3-4b-20261019 has no run identity record and is kept as it is: the generator refuses
# to extend it, so always pass a new run name.
set -euo pipefail
RUN="experiments/E2_generation/runs/${1:?usage: run_local.sh <new-run-name> [model-dir]}"
mkdir -p "$RUN"
for ds in squad2 covidqa cuad qasper; do
  rc=0
  .venv/bin/python -I -m ragmv.generate --backend llama --model qwen3-4b-q4_k_m --model-dir "${2:-$HOME/.cache/ragmv-models}" \
    --dataset "$ds" --out "$RUN" >> "$RUN/$ds.log" 2>&1 || rc=$?
  [ "$rc" -ne 2 ] || { echo "$ds: generator could not start (exit 2); see $RUN/$ds.log"; exit 2; }
done
