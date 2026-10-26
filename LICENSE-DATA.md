# Licence for results, documents and figures

Copyright (c) 2026 Swaroop Chand J C

- **Code** (`src/`, `tools/`, `tests/`, `manuscript/*.py`, `experiments/**/*.py`, `experiments/**/*.sh`,
  `.github/workflows/`): MIT, see [`LICENSE`](LICENSE).
- **Material written or produced in this project**: analysis plans, deviation logs, reports, literature coding
  (except the quotations listed below), run manifests, per-query metric values, analyses, tables, figures and
  manuscript sources. Licensed under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**
  (<https://creativecommons.org/licenses/by/4.0/legalcode>), **except** the third-party material listed below. You may
  share and adapt it for any purpose, provided you give appropriate credit (cite the record in
  [`CITATION.cff`](CITATION.cff)).

## Third-party material (not covered by the licences above)

- **Text copied from the datasets, and model outputs that reproduce it.** Each row of
  `experiments/E2_generation/runs/**/generations.jsonl` stores the question's **gold answer strings** (`answers`,
  copied from the dataset) and the **model's answer** (`response`), which often reproduces wording of the retrieved
  passages. These strings remain under the source datasets' terms: SQuAD 2.0 (Rajpurkar et al., 2018) CC BY-SA 4.0;
  COVID-QA (Möller et al., 2020) Apache-2.0; CUAD (Hendrycks et al., 2021) and Qasper (Dasigi et al., 2021) CC BY 4.0.
  They are **not** relicensed under CC BY 4.0, and ShareAlike applies to adaptations of SQuAD text.
- **Dataset question identifiers** in query lists, job metadata, generation logs and analysis outputs are the
  datasets' own IDs, under the same terms. CUAD's contain the contract's EDGAR file name, title and clause category.
- **Datasets.** The four source datasets are not redistributed; `ragmv.fetch` downloads them from their publishers
  and checks the SHA-256 digests in [`data/MANIFEST.yaml`](data/MANIFEST.yaml), which also records each licence and
  where it was read.
- **Models.** Model outputs were produced with Qwen3-4B (`Qwen/Qwen3-4B-GGUF`, Apache-2.0 per its model card and
  LICENSE file) and, in two aborted runs, Gemini (Google's API terms); dense retrieval used BAAI/bge-m3 (MIT per its
  model card). No weights are included.
- **Literature.** Bibliographic records (ACL Anthology records: CC BY 4.0 for materials from 2016 onwards; Semantic
  Scholar API responses: terms not verified) and short quotations in `literature/` are used for scholarly citation;
  the cited works remain under their authors' or publishers' terms. Paper PDFs are never committed.

The file- and field-level inventory, the sources each licence was read from, and the open owner decisions are in
[`docs/remediation/RIGHTS_AND_ATTRIBUTION.md`](docs/remediation/RIGHTS_AND_ATTRIBUTION.md). The metrics-only release
package (`tools/stage_release.py`) carries its own licence notes. These notes describe the files; they are not a
legal clearance.
