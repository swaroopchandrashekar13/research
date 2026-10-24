# Licence for results, documents and figures

Copyright (c) 2026 Swaroop Chand J C

- **Code** (`src/`, `tools/`, `tests/`, `manuscript/*.py`, `experiments/**/*.py`, `experiments/**/*.sh`): MIT, see
  [`LICENSE`](LICENSE).
- **Material written or produced in this project** — analysis plans (pre-registration documents), deviation logs,
  reports, literature coding, run manifests, per-query metric values, analyses, tables, figures and manuscript
  sources — is licensed under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**:
  <https://creativecommons.org/licenses/by/4.0/legalcode>, **except** the third-party material listed below. You may
  share and adapt it for any purpose, provided you give appropriate credit (cite the record in
  [`CITATION.cff`](CITATION.cff)).

## Third-party material (not covered by the licences above)
- **Datasets.** The four source datasets are *not* redistributed; `ragmv.fetch` downloads them from their publishers
  and checks the SHA-256 digests in [`data/MANIFEST.yaml`](data/MANIFEST.yaml), which also records each licence and
  how it was checked. Most result files refer to documents and spans only by identifiers and offsets.
- **Text copied from the datasets and model outputs that reproduce it.** Each row of
  `experiments/E2_generation/runs/**/generations.jsonl` (200 sampled questions in the analysed run, plus the aborted
  runs) stores the question's **gold answer strings**, copied from the dataset, and the **model's answer**, which often
  reproduces wording of the retrieved passages. These strings remain under the source datasets' terms: SQuAD 2.0
  (Rajpurkar et al., 2018) CC BY-SA 4.0; COVID-QA (Möller et al., 2020) Apache-2.0; CUAD (Hendrycks et al., 2021) and
  Qasper (Dasigi et al., 2021) CC BY 4.0 (sources and how each was checked: `data/MANIFEST.yaml`). They are **not**
  relicensed under CC BY 4.0. In particular, ShareAlike applies to adaptations of SQuAD text.
- **Models.** Model outputs were produced with Qwen3-4B (GGUF, Apache-2.0 per its Hugging Face model card) and
  BAAI/bge-m3 (MIT per its model card); the weights are not included and remain under their own licences.
- **Literature.** Bibliographic records and short quotations in `literature/` are used for scholarly citation; the
  cited works remain under their publishers' terms. Paper PDFs are never committed.

## Release status
These notes describe the files; they are **not** legal clearance. Before a public release or archive deposit, the
owner must decide how the third-party strings in `generations.jsonl` are distributed (for example: release them under
the source licences with the required attribution and ShareAlike terms, or keep those files private and publish only
the per-query metric values). Until then this is an open release blocker (see `docs/repair/REPAIR_REPORT.md`).
