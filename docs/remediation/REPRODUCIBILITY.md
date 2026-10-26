# Reproducibility guide

Every command runs from the repository root (or the root of the release package). Each step writes to a **new**
directory; historical runs and analyses under `experiments/` are evidence and are never overwritten (the tools refuse
non-empty output directories). `W` below is any new scratch directory. The outcome of the latest run of every step is
in `VERIFICATION.md`.

## 0. Environment

Python 3.12 or 3.13 on Linux or macOS (`requirements/README.md`; `env/validation/README.md` describes the validation
environment, which is not the historical one).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/core.txt -r requirements/test.txt   # or: -r env/validation/lock-py3.13.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q -rs                      # data-dependent and optional-SDK tests are listed as skipped
.venv/bin/python -I tools/validate_artifacts.py        # structure PASS/FAIL; provenance COMPLETE/INCOMPLETE
.venv/bin/python -I tools/check_hash_policy.py
.venv/bin/python -I tools/check_bibliography.py
.venv/bin/python -I tools/check_release_metadata.py
```

## 1. Data (public sources, digest-checked)

```bash
.venv/bin/python -I -m ragmv.fetch                     # archives and extracted members checked; mismatches never overwritten
.venv/bin/python -I -m ragmv.fetch --verify-only       # re-check later without writing
RAGMV_DATA_ROOT=data/raw .venv/bin/python -m pytest -q -rs     # includes BM25 retrieval reproduction of the stored Study 1 run
.venv/bin/python -I tools/validate_artifacts.py --data-root data/raw   # splits, query lists, gold spans, chunk partitions, Tier 2 inputs
```

## 2. Recompute the stored analyses (same code, new directories)

```bash
.venv/bin/python -I -m ragmv.analyze   --run experiments/E1_retrieval_multiverse/runs/confirmatory-20261018 --label CONFIRMATORY --out W/e1
.venv/bin/python -I -m ragmv.analyze1b --run experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu --label CONFIRMATORY --out W/e3
.venv/bin/python -I -m ragmv.analyze_generation --run experiments/E2_generation/runs/qwen3-4b-kaggle-gpu --out W/e2
.venv/bin/python -I tools/compare_results.py experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json W/e1/results.json \
    --inputs-against docs/remediation/PROTECTED_SHA256.txt --run-dir experiments/E1_retrieval_multiverse/runs/confirmatory-20261018
# likewise for e3 and e2: expect 0 differences, 0 missing fields, 0 consumed-input mismatches
.venv/bin/python -I tools/independent_stats.py --out-json W/sv.json --out-md W/sv.md       # does not import the package
.venv/bin/python -I tools/budget_underfill_census.py --out-json W/census.json --out-md W/census.md
.venv/bin/python -I tools/underfill_bound.py --census W/census.json --work W/bound --out-json W/bound.json
```

`compare_results.py` fails on any changed, missing, non-finite or type-changed scientific value; only the metadata
fields it names (code and input identities, validation notes) may differ. Its float tolerance cannot be raised above
1e-9.

## 3. Post-hoc character-metric sensitivity (re-executes BM25; needs the data; ~6 min on 4 CPUs)

```bash
.venv/bin/python -I -m ragmv.posthoc study1  --stored experiments/E1_retrieval_multiverse/runs/confirmatory-20261018 --data-root data/raw --out W/posthoc/e1_confirmatory
.venv/bin/python -I -m ragmv.posthoc study1b --stored experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu --data-root data/raw --out W/posthoc/e3_confirmatory_bm25
for v in word64 char char_nows; do
  .venv/bin/python -I -m ragmv.analyze --run W/posthoc/e1_confirmatory/$v --label POSTHOC --out W/posthoc/e1_analysis_$v
done
.venv/bin/python -I tools/posthoc_summary_e1.py W W/posthoc_summary_e1.json
.venv/bin/python -I tools/posthoc_summary_e3_bm25.py W
```

Both `ragmv.posthoc` commands exit 0 only if every stored score and word count is reproduced.

## 4. Displays and manuscript

```bash
.venv/bin/python -I manuscript/build_displays.py --out W/displays --compare manuscript    # exit 0 = identical to the committed displays
.venv/bin/python -I manuscript/build_pdf.py --workdir W/build --render-pages --report W/build.json   # TeX Live, latexmk, poppler
.venv/bin/python -I tools/trace_claims.py --out W/claims.md                                # every result macro recomputed
```

`build_displays.py` sets `SOURCE_DATE_EPOCH` and uses `manuscript/matplotlibrc` (DejaVu Sans, bundled with matplotlib;
fonts embedded as TrueType); with the pinned matplotlib the figure PDFs are byte-identical. `build_pdf.py` builds the named and the anonymous variant and fails
on undefined references or on identifying text, metadata or links in the anonymous PDF. Promote regenerated displays
only deliberately (`--promote`), after reviewing the comparison.

## 5. Release package

```bash
.venv/bin/python -I tools/stage_release.py build --out W/ragmv-release.zip          # needs a clean, committed tree
.venv/bin/python -I tools/stage_release.py verify W/ragmv-release.zip --source . --data-root data/raw --recompute
```

## 6. What cannot be reproduced here

| Step | Why | What exists instead |
|---|---|---|
| Dense retrieval (bge-m3) for Study 1b | GPU embeddings of all corpora | stored per-query scores, validated; BM25 arm re-executed |
| Tier 2 generation (Qwen3-4B on a T4 GPU) | GPU; greedy outputs can differ across hardware | stored rows; retrieval and context length rebuilt from the data; EM/F1 re-scored from the stored responses |
| Configuration, prompt, model-revision and upload digests of the stored runs | removed by the owner (`HASH_POLICY.md`) | the code's pins; prompts are rebuilt from the data |
| Chronology of the analysis plans | original version history unavailable | plans and deviation logs as text, with SHA-256 digests |

New runs: `python -I -m ragmv.run ...`, `python -I -m ragmv.run1b ...` and `python -I -m ragmv.generate ...` record a
run identity, the code content digest and the digests of their inputs, fill budget-matched selections to the budget
(recording depth, expansions and corpus exhaustion), and exit 2 instead of writing into a directory that already
holds results (`run`, `run1b`) or extending an incompatible or historical generation run (`generate`). Notebook runs need `RAGMV_REPO_URL` and `RAGMV_CODE_REF` (a tag or full commit id) and push results only
with `RAGMV_PUSH_RESULTS=1`.
