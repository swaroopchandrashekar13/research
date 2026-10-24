# Licence for results, documents and figures

Copyright (c) 2026 Swaroop Chand J C

- **Code** (`src/`, `tools/`, `tests/`, `manuscript/*.py`, `experiments/**/*.py`, `experiments/**/*.sh`): MIT, see
  [`LICENSE`](LICENSE).
- **Everything else written or produced in this project** — pre-registrations, decision and integrity logs,
  reports, literature coding, run manifests, per-query results, analyses, tables, figures and manuscript sources — is
  licensed under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**:
  <https://creativecommons.org/licenses/by/4.0/legalcode>. You may share and adapt it for any purpose, provided you
  give appropriate credit (cite the record in [`CITATION.cff`](CITATION.cff)).

## Third-party material (not covered by the licences above)
- **Datasets.** The four source datasets are *not* redistributed; `ragmv.fetch` downloads them from their publishers
  and checks the SHA-256 hashes in [`data/MANIFEST.yaml`](data/MANIFEST.yaml), which also records each licence and its
  verification status. Result files refer to documents and spans by identifiers and character offsets. The gold
  answer strings stored in `experiments/E2_generation/runs/**/generations.jsonl` (200 sampled questions) come from
  SQuAD 2.0 (Rajpurkar et al., 2018), COVID-QA (Möller et al., 2020), CUAD (Hendrycks et al., 2021) and Qasper
  (Dasigi et al., 2021) and remain under those datasets' licences.
- **Models.** Model outputs were produced with Qwen3-4B (GGUF) and BAAI/bge-m3; the model weights are not included
  and remain under their own licences.
- **Literature.** Bibliographic records and short quotations in `literature/` are used for scholarly citation; the
  cited works remain under their publishers' terms. Paper PDFs are never committed.
