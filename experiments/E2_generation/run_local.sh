#!/usr/bin/env bash
# Tier 2 local run (decision 025). Resumable: rerunning skips finished jobs.
# Usage: bash experiments/E2_generation/run_local.sh [model-dir]
set -euo pipefail
RUN=experiments/E2_generation/runs/qwen3-4b-20261019
for ds in squad2 covidqa cuad qasper; do
  .venv/bin/python -I -m ragmv.generate --backend llama --model qwen3-4b-q4_k_m --model-dir "${1:-$HOME/.cache/ragmv-models}" \
    --dataset "$ds" --out "$RUN" >> "$RUN/$ds.log" 2>&1
done
