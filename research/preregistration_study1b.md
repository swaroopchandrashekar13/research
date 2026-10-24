# Pre-registration — Study 1b: semantic chunking and dense retrieval under count- vs budget-matched protocols

| Field | Value |
|---|---|
| Version | **1.0 (frozen)** — frozen 2026-10-19 after the exploratory pilot, approved by the researcher. v0.1 (hypotheses, before any code or data) → v0.2 (§3.5 implementation details, before any pilot output) → v1.0 (H5b added as a disclosed post-pilot amendment, §9). The freeze reference is the commit that introduces this line |
| Pilot disclosure | Exploratory pilot run on the 20% exploratory split only (`experiments/E3_semantic_dense/PILOT_MEMO.md`). The confirmatory split had not been touched when this version was frozen |
| Date | drafted 2026-10-19, before any Study 1b code or data exists |
| Relation to Study 1 | Extension. Study 1 (E1, pre-registration v1.0, frozen at `eb1de3c`) is complete and unchanged. Same datasets, splits, metrics, statistics and thresholds wherever possible, so results are comparable |
| Motivation | (1) The protocol audit (provisional) found the most-cited semantic-vs-fixed comparison (Qu et al., NAACL Findings 2025) and 8 other papers compare arms of different chunk length at a fixed number of chunks. (2) Study 1 used lexical retrieval only; semantic chunkers are used with dense retrievers in practice. (3) Tier 2 found the retrieval reversal did **not** carry over to answer F1 for one 4B reader, so Study 1b is framed as a study of *retrieval-evaluation* protocols |
| Authors | Researcher (PI); AI research assistant (drafting) |

## 1. Research questions
- **RQ6.** Do conclusions about *semantic* chunking (breakpoint- and clustering-based) versus fixed-size chunking change
  between count-matched and budget-matched protocols?
- **RQ7.** Does Study 1's primary reversal (fixed-128 vs fixed-512) hold with a *dense* retriever?

## 2. Data and splits
Identical to Study 1 (§2 of v1.0): SQuAD 2.0 dev, COVID-QA, CUAD v1 test, Qasper v0.3 dev+test; document-level split,
seed `20261018`, exploratory 20% / confirmatory 80%; same gold spans. The exploratory split is used for the pilot only.

## 3. Design
### 3.1 Chunkings
| Name | Rule |
|---|---|
| fixed-W, W ∈ {128, 256, 512} | as Study 1 (no overlap) |
| **semantic-bp** (breakpoint) | sentences (Study 1 splitter) embedded with the encoder in §3.2; a boundary is placed where the cosine *distance* between consecutive sentences exceeds the **95th percentile** of that document's distances (LangChain/LlamaIndex default, used by Qu et al.); a chunk longer than 512 words is split with the Study 1 sentence-packing rule (cap 512) |
| **semantic-cl** (clustering) | Qu et al.'s single-linkage clustering of sentences with distance d = λ·d_pos + (1−λ)·d_cos, **λ = 0.5**, merge threshold 0.5, cluster cap 512 words. Chunks may be **non-contiguous**; a chunk is the set of its sentences' character intervals, text is passed in document order, and relevance uses the same interval-based metrics as Study 1 |

Mean chunk length (words) of each semantic chunker is measured per dataset on the exploratory split and reported; it
is a property of the chunker, not an outcome.

### 3.2 Retrievers (2)
| Retriever | Specification |
|---|---|
| BM25 | Study 1 default: Lucene, k1 = 1.5, b = 0.75, English stop words + Snowball stemming (`bm25s` 0.2.13) |
| **Dense** | `BAAI/bge-m3` (MIT, no remote code; pinned Hugging Face commit `5617a9f61b`, file hashes recorded), dense embeddings, cosine similarity, max sequence length 8,192 tokens so that no chunk is truncated; fp16 on GPU (Kaggle), the same model embeds sentences for both semantic chunkers |

### 3.3 Selection protocols, metrics, universes
As Study 1: count-matched k ∈ {1, 3, 5, 10}; budget-matched B ∈ {128, 256, 512, 1024, 2048}; metrics hit_strict,
hit_lenient, coverage. **Admissible budgets:** B ≥ the larger *cap* of the two arms (so B ∈ {512, 1024, 2048} for any
claim involving a semantic chunker or fixed-512); all budgets in sensitivity analysis (e).

### 3.4 Claims (Δ = metric(A) − metric(B))
| ID | Role | A | B |
|---|---|---|---|
| S5-W | primary family | semantic-bp | fixed-W, W ∈ {128, 256, 512} |
| S6-W | secondary | semantic-cl | fixed-W, W ∈ {128, 256, 512} |
| P1-dense | secondary | fixed-128 | fixed-512 (dense retriever only) |

### 3.5 Implementation details (written 2026-10-19 during implementation, before any pilot output)
1. **Sentences** are Study 1's rule-based sentences over the whole document; a sentence longer than 512 words is split
   into 512-word windows first, so every unit fits in a chunk (both semantic chunkers).
2. **Breakpoint chunker:** each sentence is embedded on its own (no neighbour buffer); cosine distance between
   consecutive sentences; boundaries where distance > the document's 95th percentile (`numpy.percentile`, linear);
   a document with one sentence is one chunk; a group > 512 words is re-packed with Study 1's sentence-packing rule.
3. **Clustering chunker:** all pairs with d ≤ 0.5 are visited in increasing d (ties: lower first index, then lower
   second index); two clusters merge if their combined length ≤ 512 words; d_cos = 1 − max(cos, 0); d_pos = |i−j|/n.
   A chunk's text is its sentences in document order joined by a newline; adjacent sentences form one interval.
4. **Selection with non-contiguous chunks:** count-matched takes whole chunks; budget-matched truncates the last chunk
   in document order of its intervals. For one-interval chunks this is exactly Study 1 (unit-tested; BM25 fixed-chunk
   results reproduce Study 1's stored confirmatory scores exactly).
5. **"Shorter arm"** = the arm with the smaller mean chunk length (words) over the **full retrieval corpus** of that
   dataset (the corpus is always the full dataset, as in Study 1), read from the run manifest's chunk statistics,
   which are computed before any retrieval metric.
6. **Dense retrieval:** `bge-m3` (commit `5617a9f61b028005a4858fdac845db406aefb181`) via sentence-transformers 6.1.0 /
   transformers 5.20.1 / torch 2.14.1, normalised dense embeddings, fp16 on GPU; embeddings cached as fp16; ranking
   by descending cosine, ties to the lower chunk index. The same encoder embeds sentences for both semantic chunkers.
7. **Admissible budgets:** B ∈ {512, 1024, 2048} for every Study 1b claim (all involve an arm capped at 512 words).

## 4. Hypotheses (fixed before any Study 1b data, pilot included)
Verdicts per universe and the joint-bootstrap uncertainty exactly as Study 1 §4 (paired bootstrap 2,000 resamples, seed
7; 1,000 joint replicates).

Because the *direction* of a protocol effect depends on which arm has shorter chunks, the hypotheses are stated for
**"the shorter arm"**: for each (dataset, claim instance) the arm whose mean chunk length is smaller, determined from
chunk statistics on the confirmatory corpus before any metric is computed.

| ID | Statement | Supported if | Falsified if |
|---|---|---|---|
| **H4** (primary) | For S5 (all W, both retrievers), the share of universes supporting the *shorter arm* is **≥ 20 pp higher** under budget-matched than under count-matched selection | point estimate ≥ 20 pp and 95% CI excludes 0 | CI upper bound < 20 pp |
| H4b | Same for S6 (clustering) | ≥ 10 pp and CI excludes 0 | CI upper bound < 10 pp |
| H5 | For P1-dense, the share supporting fixed-512 is **≥ 20 pp lower** under budget- than count-matched (Study 1's H1 with a dense retriever) | ≥ 20 pp and CI excludes 0 | CI upper bound < 20 pp |
| H5b *(post-pilot amendment, §9)* | For P1-dense, the share of universes supporting the **shorter arm** (fixed-128) is **≥ 20 pp higher** under budget- than count-matched selection (H4's form, applied to P1 with the dense retriever) | ≥ 20 pp and CI excludes 0 | CI upper bound < 20 pp |

Multiplicity: H4 is the single primary test of Study 1b. H4b, H5 and H5b are secondary. Everything else is exploratory.

## 5. Analysis plan
Study 1 §5 applies unchanged (verdict shares, specification curves, sensitivity analyses (a)–(e), document-cluster
bootstrap). Added: (f) H4 separately per retriever; (g) shares for *semantic* (rather than "shorter arm") wins under
each protocol — the quantity Qu et al. report — as a descriptive replication.

Exploratory (pre-specified, not hypotheses): a Tier 2 answer-quality check for S5-256 with the Tier 2 reader and
design (50 confirmatory queries per dataset, top-5 vs 1,024 words), if time allows.

## 6. Pilot and freezing
1. Implement chunkers, dense retrieval and tests; pilot on the **exploratory split only** (runtime, chunk-length
   statistics, implementation checks). No hypothesis or threshold changes after the pilot; implementation fixes are
   logged in §8.
2. Researcher approves → this document is frozen as v1.0 (gate G3) → confirmatory run on Kaggle GPU.

## 7. Known threats
- One dense encoder; one breakpoint percentile and one clustering setting (Qu et al. tuned per dataset; we fix
  defaults in advance to avoid tuning on outcomes).
- Clustering chunks are non-contiguous; text passed in document order may read unnaturally (retrieval metrics are
  unaffected; matters only for the optional Tier 2 check).
- GPU fp16 embeddings are not bit-identical to CPU; the run records hardware, and all universes use one run.

## 8. Deviations log
| Date | Deviation | Reason | Affects confirmatory results? |
|---|---|---|---|
| 2026-10-19 | **Post-pilot amendment: H5b added** (H5 kept unchanged) | Pilot (exploratory split): with the dense retriever fixed-512 wins only 8% of universes even under count-matched selection, so H5's drop in *its* share has a floor below the 20 pp threshold; the protocol effect appears on the shorter arm's share. H5b states it in H4's form. Seen on the exploratory split only; H5 is still tested and reported as pre-registered | Adds one secondary hypothesis; no other hypothesis, threshold or analysis changed |
| 2026-10-19 | Clustering defaults (λ = 0.5, threshold 0.5) kept although the pilot shows clusters fill the 512-word cap with bge-m3 | Changing them after the pilot would be tuning; reported as a limitation | No |
