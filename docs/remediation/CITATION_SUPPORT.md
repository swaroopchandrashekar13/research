# Citation-support matrix (2026-10-25)

Every citation in `manuscript/main.tex` and `manuscript/tables/audit.tex`: what the manuscript attributes to the work,
what was read, and whether that reading supports the attribution. Identity (title, authors, year, venue) was checked
against primary records with `tools/verify_bib_identity.py` (`literature/identity_checks/2026-10-25.md`): 36 of the
39 cited works were confirmed; for the other 3 no primary record was reachable (DOI resolvers, publishers, Crossref
and Semantic Scholar were blocked or rate-limited from the checking environment). Verification levels are those of
`literature/bibliography.yaml` (L1 identity from a secondary record; L2 abstract or the relevant sections read; L3 read
in full for the claim). Entries below L3 carry a visible "[Verification Lx: not yet read in full]" note in the
reference list.

Status: **PASS** the attribution is supported by what was read; **PARTIAL** consistent with the abstract or the
sections read, full text not read; **UNVERIFIED** not read beyond the bibliographic record.

## 1. Citations in the text (29 uses of 27 works)

| # | Location | Attributed to the work | Key | Level | Identity | What was read | Status |
|---|---|---|---|---|---|---|---|
| C1 | §1 Introduction | RAG combines a language model with retrieved material | `lewis2020rag` | L2 | ok (arXiv) | abstract | PARTIAL |
| C2 | §1 | (same, survey) | `gao2023ragsurvey` | L2 | ok (arXiv) | abstract | PARTIAL |
| C3 | §1 | multiverse analysis evaluates a declared grid of settings | `steegen2016multiverse` | L1 | ok (Semantic Scholar) | record only | UNVERIFIED |
| C4 | §2 Related work | fixed-size chunks in long-document retrieval | `bhat2025chunksize` | L2 | ok (arXiv) | abstract, experimental setup | PARTIAL |
| C5 | §2 | financial-report chunking as an alternative to uniform segmentation | `jimenoyepes2024financial` | L2 | ok (arXiv) | abstract, experimental setup | PARTIAL |
| C6 | §2 | LumberChunker, same | `duarte2024lumberchunker` | L2 | ok (arXiv) | abstract, experimental setup | PARTIAL |
| C7 | §2 | late chunking changes when chunk representations are formed | `gunther2024latechunking` | L2 | ok (arXiv) | abstract, experimental setup | PARTIAL |
| C8 | §2 | close reference for the semantic-chunking extension (fixed chunks of consecutive sentences, breakpoint thresholds, clustering) | `qu2025semanticchunking` | L3 | ok (ACL Anthology) | full text, appendices A–E | PASS |
| C9 | §2 | MoC holds average chunk length consistent across methods | `moc2025` | L3 | ok (arXiv) | full main text, App. A.1–A.2 (quoted: "consistent average chunk length of 178") | PASS |
| C10 | §2 | HiChunk limits retrieved context by a token budget, not a chunk count | `hichunk2025` | L3 | ok (arXiv) | full main text (§5.3: 4,096-token limit "for a fair comparison"; §5.6: 2k–4k budgets) | PASS |
| C11 | §2 | BERGEN organizes RAG evaluation around retrieval, generation and scoring choices | `rau2024bergen` | L2 | ok (ACL Anthology) | abstract, the authors' slide deck | PARTIAL |
| C12 | §2 | a single answer metric can be an incomplete measure of correctness | `kamalloo2023evaluating` | L2 | ok (ACL Anthology) | abstract | PARTIAL |
| C13 | §2 | multiverse analysis exposes dependence on analytical choices | `steegen2016multiverse` | L1 | ok | record only | UNVERIFIED |
| C14 | §2 | specification-curve analysis, same | `simonsohn2020speccurve` | L1 | no primary record reachable | record only | UNVERIFIED |
| C15 | §2 | the dependence is studied in machine learning | `bell2022multiverse` | L2 | ok (arXiv) | abstract | PARTIAL |
| C16 | §2 | reporting expected performance as a function of the computation budget changes what a comparison can establish | `dodge2019showyourwork` | L2 | ok (ACL Anthology) | abstract | PARTIAL |
| C17 | §2 | significance testing in IR motivates the paired design | `smucker2007sigtests` | L1 | no primary record reachable | record only | UNVERIFIED |
| C18 | §2 | same | `urbano2019sigtesting` | L2 | ok (arXiv; ACM reference and DOI from the authors' version) | abstract, first page | PARTIAL |
| C19 | §2 | uncertainty in language-model evaluation, power planning | `miller2024errorbars` | L2 | ok (arXiv) | abstract | PARTIAL |
| C20 | §3 Data | SQuAD 2.0 | `rajpurkar2018squad2` | L2 | ok (ACL Anthology) | abstract; dataset properties checked on the data | PASS (attribution) |
| C21 | §3 | COVID-QA | `moller2020covidqa` | L2 | ok (ACL Anthology) | abstract; dataset properties checked on the data | PASS (attribution) |
| C22 | §3 | CUAD | `hendrycks2021cuad` | L2 | ok (arXiv) | abstract; dataset properties checked on the data | PASS (attribution) |
| C23 | §3 | Qasper | `dasigi2021qasper` | L2 | ok (ACL Anthology) | abstract; dataset properties checked on the data | PASS (attribution) |
| C24 | §3 Retrieval | BM25 | `robertson2009bm25` | L1 | no primary record reachable | record only | UNVERIFIED |
| C25 | §3 | `bm25s` 0.2.13 is the BM25 library used | `lu2024bm25s` | L2 | ok (arXiv) | abstract; version from the pinned requirements | PASS (attribution) |
| C26 | §4 Analysis | Benjamini–Hochberg adjustment | `benjamini1995fdr` | L1 | ok (Semantic Scholar) | record only | UNVERIFIED |
| C27 | §5 Study 1b | the positional–semantic distance of Qu et al. | `qu2025semanticchunking` | L3 | ok | full text (Eqs. 1–3; stop at 0.5; cap by a sentence count from the target number of chunks) | PASS |
| C28 | §5 | BGE-M3 dense retrieval | `chen2024bgem3` | L2 | ok (ACL Anthology) | abstract; model pinned in code | PASS (attribution) |
| C29 | §6 Tier 2 | Qwen3-4B reader | `qwen2025qwen3` | L2 | ok (arXiv) | abstract; model pinned in code | PASS (attribution) |

C16 was checked against the abstract ("expected validation performance of the best-found model as a function of
computation budget"; comparisons "would have reached a different conclusion if they had used more (or less)
computation"). C8/C27: the manuscript calls its clustering arm an adaptation, because it caps clusters by words where
Qu et al. cap them by a number of sentences.

## 2. Protocol-audit records (19 papers, `tables/audit.tex`)

All 19 records were coded by a single coder (an AI research assistant) from the full text, reading the abstract and
the experimental-setup sections; no independent second coding and no reliability statistic exist, so every audit
share is **provisional** (as the manuscript states).

| Key | Level | Coded protocol | Coded uncertainty | Re-checked in full | Status |
|---|---|---|---|---|---|
| `qu2025semanticchunking` | L3 | fixed_k | none | yes: consistent | PASS (single coder) |
| `moc2025` | L3 | fixed_k | CI | yes: protocol consistent; the "CI" code (its Table 8) could not be confirmed | PARTIAL |
| `hichunk2025` | L3 | fixed_budget | none | yes: consistent | PASS (single coder) |
| `bhat2025chunksize` | L2 | fixed_k | none | no | PARTIAL |
| `muthyam2026ragstability` | L2 | fixed_k | seeds_only | no | PARTIAL |
| `beyondchunkthenembed2026` | L2 | fixed_k | significance_test | no | PARTIAL |
| `chunkembedsensitivity2026` | L2 | fixed_k | CI | no | PARTIAL |
| `garrido2026chunksize` | L2 | other (reciprocal rank over chunks) | none | no | PARTIAL |
| `chunkingcost2026` | L2 | fixed_k | none | no | PARTIAL |
| `pdfparsingfin2026` | L2 | other (page ranking) | none | no | PARTIAL |
| `chunkingacademic2026` | L2 | unclear | none | no | PARTIAL |
| `reconstructingcontext2025` | L2 | other (document ranking) | none | no | PARTIAL |
| `metachunking2024` | L2 | fixed_k | none | no | PARTIAL |
| `freechunker2025` | L2 | fixed_k | seeds_only | no | PARTIAL |
| `queryadaptivechunking2026` | L2 | fixed_k | seeds_only | no | PARTIAL |
| `arabicrag2025` | L2 | unclear | none | no | PARTIAL |
| `jimenoyepes2024financial` | L2 | fixed_k | none | no | PARTIAL |
| `duarte2024lumberchunker` | L2 | fixed_k | none | no | PARTIAL |
| `gunther2024latechunking` | L2 | other (document ranking) | none | no | PARTIAL |

The re-check of the three L3 records was a second reading by the same kind of coder, not an independent coding.

## 3. Open items

- Read in full (L3) the works cited for specific claims at L1/L2, in particular C3/C13, C14, C17, C24 and C26
  (classical method references whose primary records were unreachable here) and C16.
- Independent blind second coding of the 19 audit records and a reliability statistic (Cohen's κ); no codes or κ
  values have been invented.
