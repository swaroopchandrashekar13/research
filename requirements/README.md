# Dependency sets

| File | For | Notes |
|---|---|---|
| `core.txt` | analyses, retrieval runs, figures, tables | exact versions recorded in the run manifests |
| `test.txt` | the test suite | |
| `generation.txt` | Tier 2 generation (`ragmv.generate`) | `llama-cpp-python` is built from source |
| `dense.txt` | Study 1b dense retrieval / semantic chunkers | GPU in practice |

Supported interpreters: **Python 3.12 and 3.13** (`numpy==2.5.3` and `scipy==1.18.1` require ≥ 3.12, so the earlier
`requires-python >= 3.11` could not be satisfied). The historical results were produced with Python 3.13.16 (Study 1,
`env/environment.json`) and 3.13.15 (Study 1b, Kaggle manifests).

`../requirements.txt` and `../requirements-study1b.txt` are the original combined pin lists. They are kept unchanged
as historical environment records; new installs use the split files above.

A complete lock of the validation environment used for the 2026-10-24 repair (every transitive package) is in
`../env/validation/`.
