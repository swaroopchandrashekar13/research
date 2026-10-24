# RAG Research

A reproducible research project studying how retrieval-selection protocols—fixed numbers of chunks versus fixed word budgets—affect chunking comparisons in retrieval-augmented generation (RAG).

## Repository layout

| Path | Contents |
|---|---|
| `data/MANIFEST.yaml` | Dataset sources, expected hashes, and download instructions |
| `docs/guides/` | Setup/access guide and Zenodo archiving guide |
| `docs/reports/` | Research assessment, research direction, opportunity landscape, and roadmap reports |
| `env/environment.json` | Recorded environment information |
| `experiments/` | Existing experiment runs, analysis outputs, figures, and result summaries |
| `literature/` | Literature protocol, search log, bibliography, evidence matrix, and protocol-audit materials |
| `research/` | Research problem statement and preregistration documents |
| `src/ragmv/` | Python implementation for data processing, chunking, retrieval, evaluation, analysis, and generation |
| `tests/` | Automated tests for the core implementation and research tools |
| `tools/` | Environment probe and bibliography validator |

## Reproduce the available checks

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Run the automated tests and repository checks:

```bash
python -m pytest -q tests
python tools/check_bibliography.py
python tools/env_probe.py
```

Dataset files are downloaded separately according to `data/MANIFEST.yaml`; they are not included in the repository.

## Research integrity

Do not fabricate results or citations. Preserve negative results and record deviations from the preregistered methodology. The bibliography validator can enforce a minimum reference-verification level for specified citations; use the manuscript's required threshold explicitly, for example:

```bash
python tools/check_bibliography.py --cite KEY1 KEY2 --min-level L3
```

## License and citation

Code is licensed under MIT (see [LICENSE](LICENSE)). Results, documents, and figures are described in [LICENSE-DATA.md](LICENSE-DATA.md). Dataset source files are not redistributed; see [data/MANIFEST.yaml](data/MANIFEST.yaml).

For citation metadata, see [CITATION.cff](CITATION.cff). For Zenodo archiving guidance, see [docs/guides/ZENODO.md](docs/guides/ZENODO.md).
