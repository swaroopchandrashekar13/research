# Experiments

| ID | Directory | Status |
|---|---|---|
| E1 retrieval multiverse | `E1_retrieval_multiverse/` | confirmatory run done (`RESULTS.md`) |
| E2 generation (Tier 2, exploratory) | `E2_generation/` | done (`RESULTS.md`); analysed run `runs/qwen3-4b-kaggle-gpu` |

Conventions: `runs/<run_id>/<dataset>/` holds `manifest.json` (git SHA and status, config hash, versions, timings,
peak memory, chunk statistics), `queries.json` (question IDs and document indices only, no text) and one `.npz` of
per-query metric values per chunking. `analysis/<run_id>/` holds `results.json`, `results.md` and figures generated
by `python -I -m ragmv.analyze` and `python -I -m ragmv.figures`. Every result file states EXPLORATORY or
CONFIRMATORY. Failed runs are kept and logged.
