# About this package

This archive holds the code, written analysis plans, deviation logs, run manifests, per-query results, analyses,
tables, figures and manuscript sources of the study *Chunking Verdicts in Retrieval-Augmented Generation Depend on
the Evaluation Protocol: A Multiverse Analysis* (author: Swaroop Chand J C). Answer-generation records (Tier 2) are
given as per-row metric values in `experiments/E2_generation/runs/*/*/generations.metrics.jsonl`; each file
corresponds line for line to one generation log, and its fields are listed in `src/ragmv/metrics_form.py`.
Licences and third-party material: `LICENSE`, `LICENSE-DATA.md`. Every file's SHA-256 is in `SHA256SUMS`.

## Check the package

Python 3.12 or 3.13, from the package root:

```bash
sha256sum -c SHA256SUMS                     # or: shasum -a 256 -c SHA256SUMS
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/core.txt -r requirements/test.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/python -I tools/validate_artifacts.py
```

Recompute the stored analyses into new directories and compare every field (expect 0 differences); the files each
analysis read are checked against `SHA256SUMS`:

```bash
.venv/bin/python -I -m ragmv.analyze   --run experiments/E1_retrieval_multiverse/runs/confirmatory-20261018 --label CONFIRMATORY --out W/e1
.venv/bin/python -I -m ragmv.analyze1b --run experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu --label CONFIRMATORY --out W/e3
.venv/bin/python -I -m ragmv.analyze_generation --run experiments/E2_generation/runs/qwen3-4b-kaggle-gpu --out W/e2
.venv/bin/python -I tools/compare_results.py experiments/E2_generation/analysis/qwen3-4b-kaggle-gpu/results.json W/e2/results.json \
    --inputs-against SHA256SUMS --run-dir experiments/E2_generation/runs/qwen3-4b-kaggle-gpu
.venv/bin/python -I tools/independent_stats.py --out-json W/sv.json --out-md W/sv.md
```

The datasets are downloaded and checked by `.venv/bin/python -I -m ragmv.fetch`; the data-dependent tests and checks
then run with `RAGMV_DATA_ROOT=data/raw` and `tools/validate_artifacts.py --data-root data/raw`. Further steps
(post-hoc analyses, displays, manuscript build): `docs/remediation/REPRODUCIBILITY.md`.

## What this package cannot reproduce

| Check | Why |
|---|---|
| Re-scoring exact match and F1 of the Tier 2 answers, and the unanswerable rate, from the answer strings | Needs the gold answer and model response strings; the stored per-row values are given instead |
| Rebuilding Tier 2 prompts and retrieval from the data and comparing them with each stored row | Possible for retrieval values and context length (`--data-root`); the prompts are rebuilt but their stored digests were removed |
| Dense retrieval (bge-m3) and answer generation (Qwen3-4B) | Need a GPU; greedy outputs can differ across hardware. The stored per-query scores and metrics are validated instead |
| The chronology of the analysis plans | The original version history is not available |
| Re-auditing the stored responses of the Semantic Scholar API used for the bibliographic identity checks | Rerun `tools/verify_bib_identity.py` against the live services |
