# Literature review protocol

Status: **Phase 0 scoping search** (2026-10-18). This is a scoping protocol, not yet a systematic review.
It becomes systematic once a direction is approved (see "Phase 1 upgrade" below).

## 1. Purpose
Map candidate research directions, find the closest prior work for each, and estimate whether a defensible gap exists.

## 2. Sources actually used
| Source | Used? | Notes |
|---|---|---|
| Web search engine (server-side `WebSearch` tool) | Yes | US-indexed web search; returns titles, URLs and snippets |
| arXiv API / abs pages | **Blocked** | Container network policy returns 403; `WebFetch` cannot resolve arxiv.org |
| Semantic Scholar API | **Blocked** | 403 |
| Crossref API | **Blocked** | 403 |
| OpenReview API | **Blocked** | 403 |
| ACL Anthology, IEEE Xplore, ACM DL, ScienceDirect | **Blocked** | 403 / DNS failure |
| Google Scholar | Not used | No API; scraping would violate ToS |

Consequence: every reference is at most **L1** (existence confirmed in a search index; content known from snippets only).

## 3. Verification levels
| Level | Meaning | May be cited in a manuscript? |
|---|---|---|
| L0 | Not checked (from memory) | Never — not stored |
| L1 | Title + ID/URL seen in a search index; content from snippets | No — only in internal planning |
| L2 | Abstract read on the primary page | Only for background statements matching the abstract |
| L3 | Full text read; extracted fields checked | Yes |

`tools/check_bibliography.py --cite KEY... --min-level L3` enforces this gate for manuscripts.

## 4. Search strings
All 36 queries, in order, are listed in `search_log.md`. They covered: agent fault tolerance and exactly-once
side effects; tool-failure robustness; RAG corpus corruption and ingestion faults; OCR/parsing effects; deletion/unlearning
in RAG; chunking evaluations; RAG evaluation statistics and judge reliability; multiverse analysis; RCA agents;
on-device agents; prompt-injection system defenses; MCP tool discovery; memory poisoning.

## 5. Inclusion / exclusion (scoping)
- Include: peer-reviewed papers or arXiv preprints, 2019-2026, that directly address a candidate direction's research question, or that are the field's standard benchmark or method.
- Include practitioner sources only as evidence that a problem exists in practice, never as evidence of a scientific finding.
- Exclude: vendor marketing, aggregator pages as primary sources (used only to locate a paper), anything without a stable identifier.

## 6. Known limitations of this search
1. Snippet-level evidence only (no abstracts or full text read).
2. One search engine, US-indexed; non-English work under-represented.
3. No forward/backward citation chaining yet.
4. Strong recency effect: 2026 arXiv activity is dense, and anything after ~early Oct 2026 may be missing from the index.
5. "No result found" means "not found by these queries", **not** "does not exist".

## 7. Phase 1 upgrade (after a direction is approved)
1. Unblock arxiv.org, export.arxiv.org, api.semanticscholar.org, api.crossref.org, openreview.net, aclanthology.org (environment network settings).
2. Write the structured search script (arXiv + Semantic Scholar) with saved raw responses for reproducibility.
3. Title/abstract screening with logged include/exclude decisions; two-pass screening of borderline papers by the researcher.
4. Backward and forward citation chaining from the 5 closest papers.
5. Raise the closest papers to L3 and fill every column of the evidence matrix from full text.
