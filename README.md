# RAG Research

A reproducible research project studying how retrieval-selection protocols—fixed numbers of chunks versus fixed word
budgets—affect chunking comparisons in retrieval-augmented generation (RAG).

Canonical manuscript: `manuscript/main.tex` (title: *Chunking Verdicts in Retrieval-Augmented Generation Depend on
the Evaluation Protocol: A Multiverse Analysis*). The repair carried out on 2026-10-24, its evidence and its open
release blockers are documented in [`docs/repair/REPAIR_REPORT.md`](docs/repair/REPAIR_REPORT.md).

## Repository layout

| Path | Contents |
|---|---|
| `data/MANIFEST.yaml` | Dataset sources, SHA-256 digests of the downloads and of the extracted files the loaders read, licence status |
| `docs/guides/` | Setup/access guide and Zenodo archiving guide |
| `docs/repair/` | Repair report and register, verification matrices, redaction ledger, reproducibility guide |
| `docs/reports/` | Research assessment, research direction, opportunity landscape, and roadmap reports (historical) |
| `env/` | Historical environment record (`environment.json`) and the 2026-10-24 validation lock (`validation/`) |
| `experiments/` | Experiment runs, analysis outputs, figures, result summaries (historical evidence; never overwritten) |
| `literature/` | Literature protocol, search log, bibliography, evidence matrix, and provisional protocol-audit materials |
| `research/` | Problem statement, pre-registrations and their errata |
| `requirements/` | Dependency sets (core, test, generation, dense) |
| `src/ragmv/` | Python package: data, chunking, retrieval, evaluation, analysis, generation |
| `tests/` | Automated tests |
| `tools/` | Artefact validation, result comparison, bibliography, environment probe and hash-scan tools |

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
To write a new environment record, pass a new file: `.venv/bin/python tools/env_probe.py --out /tmp/environment.json`
(`env/environment.json` is a historical record and is not overwritten).

### Datasets

Datasets are not included. Download and verify them (archives and the extracted files the loaders read are checked
against `data/MANIFEST.yaml`; a mismatching file is never overwritten):

```bash
.venv/bin/python -I -m ragmv.fetch                 # into data/raw/
RAGMV_DATA_ROOT=data/raw .venv/bin/python -m pytest -q
.venv/bin/python -I tools/validate_artifacts.py --data-root data/raw
```

The full reproduction guide, including the analysis, figure, table and manuscript commands, is
[`docs/repair/REPRODUCIBILITY.md`](docs/repair/REPRODUCIBILITY.md).

## Research integrity

Do not fabricate results or citations. Preserve negative results and record deviations from the pre-registered
methodology. Historical run outputs under `experiments/` are evidence: new analyses go to new directories. The
bibliography validator can enforce a minimum reference-verification level for specified citations:

```bash
.venv/bin/python -I tools/check_bibliography.py --cite KEY1 KEY2 --min-level L3
```

## License and citation

Code is licensed under MIT (see [LICENSE](LICENSE)). Results, documents and figures are described in
[LICENSE-DATA.md](LICENSE-DATA.md), which also lists the third-party material whose redistribution status is
unresolved. Dataset source files are not redistributed; see [data/MANIFEST.yaml](data/MANIFEST.yaml).

For citation metadata, see [CITATION.cff](CITATION.cff). For Zenodo archiving guidance, see
[docs/guides/ZENODO.md](docs/guides/ZENODO.md).
