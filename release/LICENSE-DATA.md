# Licences and third-party material in this package

Copyright (c) 2026 Swaroop Chand J C

- **Code** (`src/`, `tools/`, `tests/`, `manuscript/*.py`, `experiments/**/*.py`, `experiments/**/*.sh`,
  `.github/workflows/`): MIT, see [`LICENSE`](LICENSE).
- **Material produced in this project**: analysis plans, deviation logs, reports, literature coding (except the
  quotations listed below), run manifests, per-query and per-row metric values, analyses, tables, figures and
  manuscript sources. Licensed under the **Creative Commons Attribution 4.0 International licence (CC BY 4.0)**
  (<https://creativecommons.org/licenses/by/4.0/legalcode>), **except** the third-party material listed below.

## Third-party material (not covered by the licences above)

| Material | Where | Source and terms (as read on 2026-10-25) |
|---|---|---|
| Dataset question identifiers | `queries.json`, `jobs_meta.json`, `*.metrics.jsonl` (`qid`, `job_id`), analysis outputs that name queries | The datasets' own IDs. SQuAD 2.0 (Rajpurkar et al., 2018): CC BY-SA 4.0 per the authors' Hugging Face dataset card. COVID-QA (Möller et al., 2020): Apache-2.0 per the repository's LICENSE file. CUAD (Hendrycks et al., 2021): CC BY 4.0 per the publisher's dataset card; CUAD's IDs contain the contract's EDGAR file name, title and clause category, and the card states that the creators make no representations about the licence status of the underlying contracts. Qasper (Dasigi et al., 2021): CC BY 4.0 per the publisher's dataset card. |
| Values computed from the datasets | per-query arrays, chunk boundaries (word offsets), gold-span offsets and counts, metric values | Computed by this project from the datasets above; they contain no dataset text. The datasets themselves are not included: `ragmv.fetch` downloads them from their publishers and checks the digests in `data/MANIFEST.yaml`. |
| Bibliographic records | `literature/identity_checks/raw/*.bib` | BibTeX records from the ACL Anthology, whose copyright page states that materials published in or after 2016 are licensed under CC BY 4.0 (<https://aclanthology.org/faq/copyright/>). |
| Short quotations from cited works | `headline_claim` in `literature/protocol_audit/coding.csv`; quotations in `literature/` and the manuscript | Quoted with source and page for criticism and review; they remain under their authors' or publishers' terms. |
| Models | named in run manifests and job metadata; no weights included | Qwen3-4B (`Qwen/Qwen3-4B-GGUF`): Apache-2.0 per its model card and LICENSE file. BAAI/bge-m3: MIT per its model card. Gemini (two aborted runs, metric values only): Google's API terms, which could not be read from the checking environment. |

Answer-generation records in this package are per-row metric values (exact match, F1, retrieval hit and coverage,
token counts, timing, whether the answer was "unanswerable") without the answer or response text.

## Attribution

When you reuse material derived from a dataset, cite that dataset (see `manuscript/refs.bib`) and give its licence.
Changes made here: queries were sampled and split, documents were chunked, and retrieval and answer-quality metrics
were computed; no dataset text is reproduced.

These notes describe the files. They are not a legal clearance.
