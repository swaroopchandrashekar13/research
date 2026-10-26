# RAG Research

A reproducible research project studying how retrieval-selection protocols—fixed numbers of chunks versus fixed word
budgets—affect chunking comparisons in retrieval-augmented generation (RAG).

Canonical manuscript: `manuscript/main.tex` (title: *Chunking Verdicts in Retrieval-Augmented Generation Depend on
the Evaluation Protocol: A Multiverse Analysis*). The current verification status, the open limitations and the owner
decisions before a release are in [`docs/remediation/VERIFICATION.md`](docs/remediation/VERIFICATION.md).

## Repository layout

| Path | Contents |
|---|---|
| `data/MANIFEST.yaml` | Dataset sources, SHA-256 digests of the downloads and of the extracted files the loaders read, licence status |
| `docs/guides/` | Zenodo archiving and ORCID guide |
| `docs/remediation/` | Verification report, claim and citation matrices, statistical verification, hash policy, budget-underfill census, rights inventory, reproducibility guide, protected-file digests |
| `env/` | Historical environment record (`environment.json`) and the validation lock (`validation/`) |
| `experiments/` | Experiment runs, analysis outputs, figures, result summaries (historical evidence; never overwritten) |
| `literature/` | Literature protocol, search log, bibliography, evidence matrix, identity checks and the provisional protocol audit |
| `release/` | Licence notes and description that the metrics-only release package carries |
| `research/` | Problem statement, analysis plans and their errata |
| `requirements/` | Dependency sets (core, test, generation, dense) |
| `src/ragmv/` | Python package: data, chunking, retrieval, evaluation, analysis, generation |
| `tests/` | Automated tests |
| `tools/` | Artefact validation, result comparison, independent statistics, claim tracing, bibliography, release staging and metadata tools |

## Install and run the checks

Supported interpreters: Python 3.12 or 3.13. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/core.txt -r requirements/test.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/python -I tools/validate_artifacts.py
.venv/bin/python -I tools/check_bibliography.py
```

Tests that need the four datasets are skipped unless the data are present (see below), and the tests of the optional
Gemini and llama.cpp back ends are skipped unless `requirements/generation.txt` is installed; pytest lists every skip.
`tools/validate_artifacts.py` reports structure (PASS/FAIL) and provenance (complete/incomplete) separately; the
historical runs are structurally valid with incomplete provenance. To write a new environment record, pass a new
file: `.venv/bin/python tools/env_probe.py --out /tmp/environment.json` (`env/environment.json` is a historical record
and is not overwritten).

### Datasets

Datasets are not included. Download and verify them (archives and the extracted files the loaders read are checked
against `data/MANIFEST.yaml`; a mismatching file is never overwritten):

```bash
.venv/bin/python -I -m ragmv.fetch                 # into data/raw/
RAGMV_DATA_ROOT=data/raw .venv/bin/python -m pytest -q
.venv/bin/python -I tools/validate_artifacts.py --data-root data/raw
```

The full reproduction guide, including the analysis, figure, table and manuscript commands, is
[`docs/remediation/REPRODUCIBILITY.md`](docs/remediation/REPRODUCIBILITY.md).

## Research integrity

Do not fabricate results or citations. Preserve negative results and record deviations from the analysis plans.
Historical run outputs under `experiments/` are evidence: new analyses go to new directories. The bibliography
validator can enforce a minimum reference-verification level for specified citations:

```bash
.venv/bin/python -I tools/check_bibliography.py --cite KEY1 KEY2 --min-level L3
```

## License, citation and archiving

Code is licensed under MIT (see [LICENSE](LICENSE)). Results, documents and figures are described in
[LICENSE-DATA.md](LICENSE-DATA.md), which also lists the third-party material (gold answer strings and model answers
in the generation logs, dataset question identifiers, quotations) that is not covered by the project's licences.
Dataset source files are not redistributed; see [data/MANIFEST.yaml](data/MANIFEST.yaml).

Citation metadata: [CITATION.cff](CITATION.cff) and [.zenodo.json](.zenodo.json), checked by
`python -I tools/check_release_metadata.py` (which also records an ORCID iD with `--set-orcid`). The metrics-only
release package is built and verified with `tools/stage_release.py`; how to deposit it on Zenodo:
[docs/guides/ZENODO.md](docs/guides/ZENODO.md).
