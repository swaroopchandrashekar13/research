# Validation environment (2026-10-24 repair)

**This is not the historical environment.** It is a separately created environment used to validate the repaired
project. The historical environment cannot be recreated exactly: only the direct pins and the versions printed into
the run manifests were recorded, not a full lock.

| | Historical (Study 1, `env/environment.json` and manifests) | Historical (Study 1b, Kaggle manifests) | Validation |
|---|---|---|---|
| Python | 3.13.16 | 3.13.15 | 3.13.17 and 3.12.3 |
| Platform | Linux 6.18.44 (fc-v139), glibc 2.39, 4 vCPU | Kaggle, Tesla T4 | Linux 6.18.44 (fc-v153), glibc 2.39, 4 vCPU, no GPU |
| numpy / bm25s / PyStemmer / scipy / statsmodels | 2.5.3 / 0.2.13 / 2.2.0.3 / 1.18.1 / 0.15.0 | numpy 2.5.3, bm25s 0.2.13, PyStemmer 2.2.0.3 | identical pins |
| Transitive packages | not recorded | not recorded | `lock-py3.13.txt`, `lock-py3.12.txt` (`pip freeze`) |
| torch / transformers / sentence-transformers | — | 2.14.1 / 5.20.1 / 6.1.0 | not installed (no GPU; dense retrieval not rerun) |

The two validation locks differ only in `wrapt` (2.5.2rc1 on 3.13, 2.5.1 on 3.12; a dependency of `formulaic`, which
`statsmodels` uses for formulas). **Measured effect of the environment difference on outputs:** every stored E1, E3
and E2 analysis was recomputed in this environment and matched the stored `results.json` field by field with zero
differences; BM25 retrieval re-executed here reproduced the stored Study 1 scores and word counts exactly (see
`docs/repair/VERIFICATION.md`). Dense retrieval and model generation were not re-executed, so for them the
environment difference is unquantified.

Recreate: `python3.13 -m venv .venv && .venv/bin/python -m pip install -r env/validation/lock-py3.13.txt &&
.venv/bin/python -m pip install --no-deps -e .`
