#!/usr/bin/env bash
# Tier 2 (E2) on an Apple-silicon Mac (Metal GPU). One command, resumable, free.
#
#   git clone -b claude/phd-research-mentor-vtven3 https://github.com/swaroopchandrashekar13/reasearch.git
#   cd reasearch
#   bash experiments/E2_generation/run_mac.sh
#
# If it stops (lid closed, Ctrl-C, crash), run the same command again: finished jobs are skipped.
# When it prints "ALL 1600 JOBS DONE", commit and push the two folders it names.
set -euo pipefail
cd "$(dirname "$0")/../.."
RUN=experiments/E2_generation/runs/qwen3-4b-mac
ANALYSIS=experiments/E2_generation/analysis/qwen3-4b-mac
MODELS="$HOME/.cache/ragmv-models"

[ "$(uname -s)-$(uname -m)" = "Darwin-arm64" ] || { echo "This script is for Apple-silicon Macs."; exit 1; }
xcode-select -p >/dev/null 2>&1 || { echo "Run: xcode-select --install   (then re-run this script)"; exit 1; }

# uv: a single-binary Python/venv manager, installed into your home folder (no admin rights needed)
command -v uv >/dev/null 2>&1 || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH"; }
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
# llama-cpp-python builds from source with Metal on macOS (first time ~5-10 min); the rest are wheels
CMAKE_ARGS="-DGGML_METAL=on" uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python --no-deps -e .

.venv/bin/python -I -m ragmv.fetch   # datasets, SHA-256 checked

mkdir -p "$RUN"
for ds in squad2 covidqa cuad qasper; do
  echo "== $ds (started $(date))"
  # caffeinate keeps the Mac awake while a dataset runs; the model is downloaded once and hash-checked
  caffeinate -i .venv/bin/python -I -m ragmv.generate --backend llama --model qwen3-4b-q4_k_m --model-dir "$MODELS" \
    --n-gpu-layers -1 --threads 8 --dataset "$ds" --out "$RUN" 2>&1 | tee -a "$RUN/$ds.log"
done

done_count=$(.venv/bin/python -I -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
from ragmv.generate import done_ids
print(sum(len(done_ids(Path('$RUN') / d / 'generations.jsonl')) for d in ('squad2', 'covidqa', 'cuad', 'qasper')))")
echo "completed jobs: $done_count / 1600"
if [ "$done_count" -ge 1600 ]; then
  .venv/bin/python -I -m ragmv.analyze_generation --run "$RUN" --out "$ANALYSIS"
  echo "ALL 1600 JOBS DONE. Now run:"
  echo "  git add $RUN $ANALYSIS && git commit -m 'E2: Tier 2 run on Mac (Metal)' && git push"
else
  echo "NOT FINISHED -> run this script again; finished jobs are skipped"
fi
