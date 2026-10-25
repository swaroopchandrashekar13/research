# Rights and attribution inventory (2026-10-25)

What the repository distributes, who holds the rights, which terms were read and where, and what remains for the
owner to decide. This is a description of the files, not legal advice or a legal clearance. Terms were read on
2026-10-25 from the sources named; "not verified" means the source could not be reached from the checking
environment.

## 1. Terms read

| Work | Terms | Read from |
|---|---|---|
| SQuAD 2.0 dev set (Rajpurkar et al., 2018) | CC BY-SA 4.0 | Hugging Face dataset card `rajpurkar/squad_v2` (front matter `license: cc-by-sa-4.0`; text "The dataset is distributed under the CC BY-SA 4.0 license"). The SQuAD-explorer README states no licence; the SQuAD website was not reachable. |
| COVID-QA (Möller et al., 2020) | Apache-2.0 | `LICENSE` file of the deepset-ai/COVID-QA repository; the `deepset/covid_qa_deepset` card agrees |
| CUAD v1 (Hendrycks et al., 2021) | CC BY 4.0 | Hugging Face dataset card `theatticusproject/cuad-qa`, which adds: "The creators make no representations or warranties regarding the license status of the underlying contracts, which are publicly available and downloadable from EDGAR." The repository README and LICENSE could not be fetched (404). |
| Qasper v0.3 (Dasigi et al., 2021) | CC BY 4.0 | Hugging Face dataset card `allenai/qasper`; not stated in the archive README |
| Qwen3-4B, GGUF (`Qwen/Qwen3-4B-GGUF`) | Apache-2.0 | model card front matter and the repository's `LICENSE` file |
| BAAI/bge-m3 | MIT | model card front matter |
| Gemini API outputs (two aborted runs) | Google's Gemini API terms | **not verified** (ai.google.dev not reachable) |
| ACL Anthology records | CC BY 4.0 for materials published in or after 2016 (CC BY-NC-SA 3.0 before) | <https://aclanthology.org/faq/copyright/> |
| arXiv metadata | CC0 1.0 for descriptive metadata (title, abstract, authors, identifiers) | arXiv API Terms of Use, <https://info.arxiv.org/help/api/tou.html> (no arXiv response is stored) |
| Semantic Scholar API responses | Semantic Scholar API licence | **not verified** (semanticscholar.org not reachable) |

## 2. Inventory by file and field

| Files | Field or content | Origin | In the repository | In the metrics-only package |
|---|---|---|---|---|
| `experiments/E2_generation/runs/**/generations*.jsonl` (1,819 rows: 1,600 analysed, 198 + 21 from aborted runs) | `answers` (3,499 gold answer strings) | copied from the datasets | yes | removed |
| same | `response` (1,819 model answers) | Qwen3-4B / Gemini output; often reproduces passage wording | yes | removed; `response_unanswerable` (true/false) derived instead |
| same | `qid`, `job_id` | dataset question IDs (+ chunking and operating point) | yes | yes |
| same | `em`, `f1`, `retrieval`, `context_words`, `usage`, `latency_s`, `status`, `finish_reason`, `model`, `model_version`, `hardware`, `called_utc`, `prompt_sha256` | project (metrics, run records; prompt digests are removed-value markers) | yes | yes |
| `experiments/**/queries.json`, `experiments/E2_generation/runs/**/jobs_meta.json` | question IDs; CUAD IDs (1,244 distinct) contain the contract's EDGAR file name, title and clause category | datasets | yes | yes |
| same | `doc_idx`, `n_gold_spans`, `gold_words`; job settings and the system prompt | project | yes | yes |
| `experiments/**/*.npz`, `chunks_*.json.gz`, manifests, analysis outputs, figures | numbers, word offsets, settings, verdicts | project, computed from the datasets (no dataset text) | yes | yes |
| `experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/build_gpu.log.gz` | pip build output | tool output (one container cache path) | yes | yes |
| `literature/protocol_audit/coding.csv` (19 rows) | `headline_claim`: one quoted sentence per paper, with page | cited works | yes | yes |
| `literature/*.md`, `manuscript/` | short quotations with citations | cited works | yes | yes |
| `literature/bibliography.yaml`, `manuscript/refs.bib` | bibliographic facts | project, from public records | yes | yes |
| `literature/identity_checks/raw/*.bib` (9) | ACL Anthology BibTeX records | ACL Anthology (CC BY 4.0) | yes | yes |
| `literature/identity_checks/raw/*.json` (25; 10 hold a record, the rest an error text) | Semantic Scholar API responses | Semantic Scholar (terms not verified) | yes | not included |
| `src/`, `tools/`, `tests/`, scripts, workflow | code; synthetic test fixtures (one test-only token, synthetic) | project (MIT) | yes | yes |
| everything else (plans, deviation logs, reports, manuscript sources) | text | project (CC BY 4.0) | yes | yes |

Scans of all tracked files on 2026-10-25 found no credentials (one synthetic test token), no private absolute paths
(only `/kaggle/working` in notebooks and `/root/.cache/pip` in the build log, both container paths), no file over
1 MB, and, outside the generation logs, no run of 8 words copied from a dataset document or question once question
IDs are set aside (the MIT licence text also occurs in some CUAD contracts). Only `allow_pickle=False` NumPy loads
and `yaml.safe_load` are used.

## 3. Attribution and notices required by the terms read

- **CC BY 4.0 / CC BY-SA 4.0** (CUAD, Qasper, SQuAD; ACL records): credit the creators, link the licence, indicate
  changes. `LICENSE-DATA.md` (repository) and `release/LICENSE-DATA.md` (package) name each dataset, its licence and
  the changes made; the manuscript and `manuscript/refs.bib` cite all four datasets. ShareAlike (SQuAD) applies to
  adaptations of SQuAD text, i.e. to the `answers` and possibly `response` strings of the SQuAD rows.
- **Apache-2.0** (COVID-QA; Qwen3 weights, not distributed): redistributing COVID-QA material requires the licence
  text and notices to accompany it; the repository names the licence and source, but does not include the Apache
  licence text. (Owner decision 3.)
- **MIT** (bge-m3, not distributed): nothing is redistributed.

## 4. Unresolved questions (owner decisions)

1. **Gold answer and response strings.** Whether to distribute them at all, and if so under the datasets' terms
   (attribution, ShareAlike for SQuAD, Apache notices for COVID-QA). CUAD's answers are clause text from contracts whose
   own licence status CUAD's creators do not warrant. Until this is decided, deposit the metrics-only package
   (`docs/guides/ZENODO.md`, route A).
2. **Gemini outputs** (21 rows in an aborted run): Google's terms were not read; the package keeps only their metrics.
3. **Apache-2.0 notice for COVID-QA-derived material**: whether to add the Apache licence text to the repository and
   the package (the identifiers and, in the logs, the answer strings derive from COVID-QA).
4. **Semantic Scholar responses**: whether their terms allow redistribution; they are left out of the package.
5. **Quotations** in the audit coding and literature notes: whether the short quotations fit the quotation exception
   where the archive will be hosted.
6. **History and earlier distribution.** The strings are in the history of the current repository, which was public
   when audited, and possibly in clones, forks and caches. A metrics-only package does not remove them from that
   history or from copies already distributed, and no action in the repository can recall earlier distribution.
   Removing them from history needs a history rewrite, which was not authorised. Creating the new repository from a
   tree without the logs (for example the extracted package) gives a repository whose history never contained them;
   the old repository, its forks and caches are unaffected.

None of these decisions can be made automatically: each depends on the owner's intended use and jurisdiction.
