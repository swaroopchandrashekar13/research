# Study 1b pilot memo (EXPLORATORY split only)

*2026-10-19 · run `runs/exploratory-kaggle-gpu` (Kaggle, Tesla T4, clean tree; bge-m3 revision `5617a9f6` fp16;
torch 2.14.1 / transformers 5.20.1 / sentence-transformers 6.1.0) · analysis `analysis/exploratory-kaggle-gpu` ·
analysis plan v0.2. The confirmatory split has not been touched.*

> **Provenance.** The original version history is not available, so this run cannot be tied to a commit (see
> `docs/remediation/HASH_POLICY.md`). The bge-m3 revision above is the one pinned in the dense-retrieval code; the
> run's own record of it is not part of the materials.

## Purpose
Runtime, chunk statistics and implementation checks before freezing (analysis plan §6). Hypothesis estimates below
are on the exploratory split and are **not evidence**; they are reported because they expose a design issue (H5).

## Runtime
~30 min GPU in total (embeddings for the full retrieval corpus of all four datasets, both retrievers, 5 chunkings);
Qasper is the largest (~5 min per chunking). The confirmatory run needs the same embedding work.

## Implementation checks (all pass)
- Semantic chunks partition every document exactly (each word once) and never exceed 512 words.
- BM25 scores for every chunking recompute exactly here from the stored chunk boundaries.
- Fixed-chunk BM25 scores equal Study 1's own exploratory pilot run exactly (all datasets, 128/256/512).
- Query lists equal the exploratory split; all manifests `ok`.

## Chunk statistics (mean words; full retrieval corpus)
| Dataset | fixed-128 | fixed-256 | fixed-512 | semantic-bp | semantic-cl |
|---|---:|---:|---:|---:|---:|
| SQuAD 2.0 | 126 | 249 | 485 | 293 | 456 |
| COVID-QA | 126 | 247 | 483 | 287 | 455 |
| CUAD | 127 | 252 | 495 | 320 | 458 |
| Qasper | 126 | 247 | 477 | 278 | 452 |

- Breakpoint chunks average 280–320 words, between fixed-256 and fixed-512.
- **Clustering chunks fill up to the 512-word cap** (median ~495–500) and 92–95% are non-contiguous: with bge-m3,
  almost all sentence pairs fall under the planned distance threshold (0.5), so the cap, not the threshold,
  ends merging. This is a property of the planned defaults with this encoder; not changed (changing it now
  would be tuning). Reported as a limitation.
- The "shorter arm" is the same in all datasets: fixed-W for W = 128, 256; the semantic arm for W = 512.

## Exploratory estimates (not evidence)
| | Estimate | 95% CI | Threshold |
|---|---:|---|---:|
| H4 (breakpoint, shorter arm, budget − count) | 42.7 pp | [33.0, 49.2] | 20 pp |
| H4b (clustering) | 45.1 pp | [35.1, 51.6] | 10 pp |
| H5 (dense, fixed-512 share, count − budget) | 8.3 pp | [6.2, 22.9] | 20 pp |

Descriptive (Qu et al.'s quantity): semantic-bp vs fixed-128 — at top-k semantic wins 42% of universes and fixed 6%;
at equal budget semantic wins 8% and fixed 67%. The common "semantic beats small fixed chunks" verdict reverses.

## Design issue found: H5 has a floor
With the dense retriever, fixed-512 rarely wins even under count-matched selection (8% of universes; BM25 in Study 1:
79%), so a drop in *its* share cannot reach 20 pp. The protocol effect is large on the other side: the share favouring
fixed-128 rises from 31% (count) to 92% (budget). As worded, H5 tests the wrong side of the contrast for this retriever.
Options for the researcher before freezing were recorded in a project state file that is not in this repository. Whatever is chosen is logged as a
**post-pilot amendment** in the analysis plan's deviation log.
