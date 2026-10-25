# Problem statement — Study 1 

**Working title:** *Are Chunking Conclusions Artefacts of the Evaluation Protocol? A Multiverse Analysis of
Chunking Comparisons in Retrieval-Augmented Generation*

---

## Part A — In plain language

**The situation.** Every RAG system splits documents into chunks before indexing them. Teams and papers then ask
questions like "are 128-word chunks better than 512-word chunks?" or "is splitting on paragraph boundaries better
than fixed windows?", and answer them with a benchmark number.

**The suspicion.** The answer may depend less on the chunking than on *how the comparison was measured*. A concrete
example: most comparisons retrieve the same number of chunks (say top-5) for each strategy. But five 512-word chunks
are four times more text than five 128-word chunks, so the "bigger chunks win" result may only mean "more text wins".
If you instead give both strategies the same amount of text (a token budget), the conclusion might flip. The same
worry applies to how "relevant" is defined, which metric is reported, which dataset is used, and which retriever
settings are chosen.

**What we will do.** Take four public datasets with long documents and exact answer locations (Wikipedia, biomedical
papers, legal contracts, NLP papers). Run every reasonable combination of these evaluation choices (the
"multiverse") for a fixed set of chunking comparisons. Then count how often each conclusion holds, flips, or becomes
uncertain, and measure which choices cause the flips.

**Why it matters.** If conclusions flip with the protocol, then (a) published chunking advice needs a stated protocol
before it means anything, and (b) teams choosing chunk sizes from benchmarks may be optimising an artefact. If
conclusions do *not* flip, that is useful too: it tells practitioners which conclusions are safe.

**What would prove us wrong.** If count-matched and budget-matched comparisons agree in more than 80% of settings,
the protocol is not a major source of artefacts, and we report exactly that.

---

## Part B — Academic formulation

### B.1 Background and motivation
Chunking is a required design decision in RAG pipelines and is the subject of a growing number of empirical
comparisons: semantic vs fixed-size chunking (Qu et al., Findings of NAACL 2025), chunk size across datasets and
embedders (Bhat et al., arXiv 2505.21700), sensitivity of RAG to chunk size and top-k on one dataset (Muthyam,
arXiv 2606.28337), and chunk granularity on textbooks (Garrido-Lestache Belinchon & Garrido-Lestache Belinchon,
arXiv 2607.24767). Standardised RAG benchmarking libraries fix chunking as preprocessing (BERGEN; Rau et al.,
Findings of EMNLP 2024). The general methodology of evaluation uncertainty (Miller 2024; Heineman et al. 2025),
significance testing in IR (Smucker et al. 2007; Urbano et al. 2019) and multiverse analysis in ML (Bell et al.,
NeurIPS 2022) has not, as far as our searches found, been applied to chunking comparisons.
*(All citations currently at verification level L1–L2; they must reach L3 before the manuscript.)*

### B.2 Problem definition
Let $\mathcal{D}$ be a document collection with query set $Q$, where each query $q$ has gold evidence spans
$G_q$ (character intervals in documents). A **chunking** $c$ maps each document to a set of contiguous character
intervals. A **retriever** $r$ ranks chunks for $q$. A **selection protocol** $\pi$ turns a ranking into retrieved
text $R_{c,r,\pi}(q)$: either *count-matched* (top-$k$ chunks) or *budget-matched* (highest-ranked chunks until a
budget of $B$ words is filled, the last chunk truncated). A **metric** $m(R, G_q) \in [0,1]$ scores the retrieved
text against the gold spans.

A **chunking claim** is an ordered pair $(c_A, c_B)$. In a **universe** $u = (\mathcal{D}, r, \pi, m)$ its effect is
$$\Delta_u = \frac{1}{|Q|}\sum_{q \in Q} \big[m(R_{c_A,r,\pi}(q), G_q) - m(R_{c_B,r,\pi}(q), G_q)\big],$$
with a paired-bootstrap confidence interval. Each universe *supports A*, *supports B*, or is *inconclusive*.

**We study the distribution of these verdicts over a planned multiverse $\mathcal{U}$ of defensible evaluation
choices, for a fixed set of claims.**

### B.3 Research questions
- **RQ1 (protocol artefacts):** How often does the verdict on a chunking claim change between count-matched and
  budget-matched protocols, holding everything else fixed?
- **RQ2 (stability):** Across $\mathcal{U}$, what share of universes support, contradict, or fail to resolve each claim?
- **RQ3 (attribution):** How much of the variation in $\Delta_u$ is explained by the dataset, retriever
  configuration, protocol and operating point, and metric?
- **RQ4 (power):** How many paired queries are needed to resolve a 2-point difference, and are typical study sizes
  (≤ 500 queries) sufficient?
- **RQ5 (end-to-end, conditional on budget approval):** Do retrieval-level verdicts carry over to answer quality
  with LLM generators?

### B.4 Hypotheses
Exact operationalisations and thresholds are fixed in.

### B.5 Scope and assumptions
- **In scope:** lexical retrieval (BM25 family) on four public long-document QA datasets with span-level gold
  evidence; four chunking families; count- and budget-matched protocols.
- **Out of scope (stated as limitations):** dense or learned retrievers (unavailable in this environment; a
  conditional extension), rerankers, multimodal documents, document parsing from PDF, non-English text.
- **Assumption:** gold spans are a valid proxy for "the evidence needed". Partly tested by RQ5.

### B.6 Expected contributions
1. A quantitative estimate of how often chunking conclusions are protocol artefacts.
2. A variance decomposition of chunking effects across evaluation choices.
3. Power and sample-size guidance for chunking comparisons.
4. An open, tested multiverse harness (`src/ragmv`) and per-query results for reuse.

### B.7 Criteria for success and failure
The study **succeeds** if it delivers a planned, reproducible estimate for H1–H4 with uncertainty, whatever the
direction. It **fails** if the pipeline cannot be shown to compute metrics correctly (unit tests), or if deviations
from the analysis plan are undocumented.
