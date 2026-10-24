# Reproducibility guide

Every command runs from the repository root. Each step writes to a **new** directory; historical runs and analyses
under `experiments/` are evidence and are never overwritten (the tools refuse non-empty output directories).

## 0. Environment
Python 3.12 or 3.13, on Linux or macOS. See `requirements/README.md` and `env/validation/README.md` (the validation
environment is not the historical one; differences are listed there).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/core.txt -r requirements/test.txt   # or: -r env/validation/lock-py3.13.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q          # 128 passed, 11 skipped without data (2026-10-24)
```

## 1. Data (public sources, digest-checked)
```bash
.venv/bin/python -I -m ragmv.fetch                     # archives and extracted members checked; mismatches never overwritten
.venv/bin/python -I -m ragmv.fetch --verify-only       # re-check later without writing
RAGMV_DATA_ROOT=data/raw .venv/bin/python -m pytest -q # 136 passed, 3 skipped (optional SDKs) on 2026-10-24
.venv/bin/python -I tools/validate_artifacts.py --data-root data/raw   # 89 passed, 0 failed on 2026-10-24
```

## 2. Recompute the stored analyses (same code, new directories)
```bash
.venv/bin/python -I -m ragmv.analyze   --run experiments/E1_retrieval_multiverse/runs/confirmatory-20261018 --label CONFIRMATORY --out /tmp/e1
.venv/bin/python -I -m ragmv.analyze1b --run experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu      --label CONFIRMATORY --out /tmp/e3
.venv/bin/python -I -m ragmv.analyze_generation --run experiments/E2_generation/runs/qwen3-4b-kaggle-gpu   --out /tmp/e2
.venv/bin/python -I tools/compare_results.py experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json /tmp/e1/results.json
# (likewise for e3 and e2): expect 0 differences; only redacted `git` fields and new metadata are listed as added/removed
.venv/bin/python -I tools/independent_stats.py --out-json /tmp/sv.json --out-md /tmp/sv.md   # 13/13 PASS, ~4 min
```

## 3. Post-hoc character-metric sensitivity (re-executes BM25; ~6 min on 4 CPUs)
```bash
.venv/bin/python -I -m ragmv.posthoc study1  --stored experiments/E1_retrieval_multiverse/runs/confirmatory-20261018 --data-root data/raw --out W/posthoc/e1_confirmatory
.venv/bin/python -I -m ragmv.posthoc study1b --stored experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu      --data-root data/raw --out W/posthoc/e3_confirmatory_bm25
for v in word64 char char_nows; do
  .venv/bin/python -I -m ragmv.analyze --run W/posthoc/e1_confirmatory/$v --label POSTHOC --out W/posthoc/e1_analysis_$v
done
.venv/bin/python -I tools/posthoc_summary_e1.py W W/logs/posthoc_summary_e1.json
.venv/bin/python -I tools/posthoc_summary_e3_bm25.py W
```
Both `ragmv.posthoc` commands exit 0 only if every stored score and word count is reproduced (selection equivalence).

## 4. Displays and manuscript
```bash
.venv/bin/python -I manuscript/build_displays.py --out /tmp/displays --compare manuscript   # exit 0 = identical to committed
.venv/bin/python -I manuscript/build_pdf.py --workdir /tmp/build --render-pages            # needs TeX Live + latexmk + poppler
.venv/bin/python -I tools/trace_claims.py --out /tmp/trace.md                               # 115/115 macros recomputed
```
`build_displays.py` sets `SOURCE_DATE_EPOCH`, so regenerated PDFs are byte-identical across runs with the same
library versions. Promote regenerated displays only deliberately (`--promote`).

## 5. What cannot be reproduced here
| Step | Why | What exists instead |
|---|---|---|
| Dense retrieval (bge-m3) for Study 1b | GPU embeddings of all corpora | stored per-query scores, validated; BM25 arm re-executed |
| Tier 2 generation (Qwen3-4B on a T4 GPU) | GPU; greedy outputs can differ across hardware | stored responses; prompts, retrieval and EM/F1 rebuilt exactly |
| Freeze chronology of the plans | original version history unavailable | plans and deviation logs as text, with SHA-256 digests |
| Upload archives named in `UPLOAD_SHA256` | archives not in the repository | their digests only |

New generation or dense runs: `python -I -m ragmv.generate ...` / `python -I -m ragmv.run1b ...` record a run identity
and a code content digest and refuse to extend an incompatible or historical run directory (exit 2). Notebook runs
require `RAGMV_CODE_REF` (a tag or full commit id) and push results only with `RAGMV_PUSH_RESULTS=1`.
