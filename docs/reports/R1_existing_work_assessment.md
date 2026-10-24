# Report 1 — Existing Research and Technical Work Assessment

*Phase 0 · 2026-10-18 · prepared by the AI research mentor for the human researcher (PI of this project)*

> **Confidentiality note.** This repository is **public**. Employer names, internal metrics, customer details and
> internal architecture are deliberately left out of this file. The specifics were reviewed in the private session
> and summarised to you in chat. Do not add employer names, internal metrics, customer details or internal architecture to this public repository.

## 1. What I could and could not inspect

| Source | Access | What it contained | Used as evidence? |
|---|---|---|---|
| This repository | Yes | Empty (no commits) | — |
| GitHub account linked to this session | Yes | Created today; only this repository | — |
| Your public GitHub profile linked from your portfolio | Yes (public page) | 8 public repos, mostly early coursework-style ML notebooks and web projects; **no repository for the on-device multi-agent assistant** was visible | Yes (low weight) |
| Three portfolio/positioning artifacts in your Claude account | Yes | A portfolio site with 11 case studies, a research-interests page, and a critical positioning-strategy document | **Yes — primary evidence** |
| The "documented work record"/"sourcebook" and résumé PDFs that those artifacts were built from | **No** | Referenced by the artifacts but not attached to any connected source | Gap |
| Google Drive | **Not connected** | — | Gap |
| Gmail (connected) | Narrow search only (résumé/CV with attachments) | Results belonged to a different person's job search plus unrelated personal threads; **I did not open them** and they are not used | No |
| Indeed profile | Yes | Empty | — |
| Develop21 / résumé connector | Failed to connect | — | — |

**Identity and attribution.** The Claude account's email is in a different person's name, but your docs profile, the
portfolio artifacts and this GitHub account all point to one researcher, the subject of this report. I have
assumed that researcher is you. **Please confirm** (Decision D1 in Report 4).

**Evidence quality.** Every claim below comes from *self-authored portfolio material*. That material is unusually careful:
each case study separates delivered, prototype and designed-only work and lists "what this does not claim". But it is
still self-report. I could not see code, design documents, commit history or a third-party record. Confidence ratings
reflect this.

## 2. Evidence table — capabilities and attribution

Attribution codes: **P** personally designed/implemented · **C** collaborated (team platform; your slice stated) ·
**D** designed but not yet implemented/validated · **I** independent project · **O** open-source capability used, not built.

| # | Work | What you did (per source) | Attr. | Source | Confidence |
|---|---|---|---|---|---|
| 1 | Source-aware ingestion and retrieval for a team's self-service RAG platform | Format-specific chunking (header-aware tables, recursive JSON, heading-aware Markdown, YAML), multilingual processing, moving embeddings into workflow stages, bounded parallel processing, retrieval controls (per-source top-k, metadata filters) | **C** (your components; platform is a team product) | Portfolio case study "Enterprise knowledge & RAG platform"; positioning doc | Medium |
| 2 | Customer-owned object-store connector | Connection test, listing, credential isolation, fetch-time secret resolution, byte-preserving key parsing (root-caused a key-truncation bug), validation at large object counts | **P** (your connector inside a team platform) | Case study "Customer-owned S3 ingestion" | Medium |
| 3 | Agent discovery / registry and endpoint-backed execution | Registry lifecycle, endpoint routing, standalone ReAct research agent with a multi-backend search fallback (diagnosed egress blocking) | **C/P** (explicitly "not sole platform ownership") | Case study "Agent discovery & governed execution"; engineering note "A registry is not a runtime" | Medium |
| 4 | Human-reviewed feedback-to-FAQ loop | Feedback queue, owner approval, re-embedding, idempotent queueing, cross-service non-prod hardening | **P/C** | Case study "Human-reviewed FAQ lifecycle" | Medium |
| 5 | Multimodal knowledge processing | Transcription + sampled-frame analysis + OCR with source/timing metadata | **P/C** | Case study "Multimodal knowledge processing" | Medium |
| 6 | Multi-agent observability / RCA prototype | Parallel investigators, partial-evidence merging, conflict detection, ranked hypotheses | **P** (prototype; no accuracy evidence) | Case study "Multi-agent observability & RCA" | Medium-low |
| 7 | Durable agent harness (planning, sub-agents, checkpoints, approvals) | Integration architecture, runtime contract, event model, first-slice plan | **D** (no validated end-to-end run) | Case study "Durable agent harness design" | Medium (as design) |
| 8 | On-device multi-agent assistant | Nine specialised agents, LangGraph orchestration, Apple MLX local inference, MCP tools | **I** | Case study "On-device multi-agent assistant" (states no public repo, config or benchmark) | Low-medium (not publicly verifiable) |
| 9 | CV model-serving decomposition | Split UI and inference services; durable input staging; identity/storage troubleshooting | **P/C** | Case study "Reliable computer-vision deployment" | Medium |
| 10 | Platform API consolidation and hardening | ~a dozen onboarding capabilities moved to a unified backend; auth alignment; release validation | **C** | Case study "Platform APIs & operational hardening" | Medium |
| 11 | Applied ML on physical systems (previous employer) | RNN/CNN/XGBoost/RF/AutoML for building-energy forecasting; thermodynamic modelling; EV battery models | **P** | Case study "Energy forecasting & applied ML" (states metric definitions are unavailable) | Medium-low |
| 12 | Education | M.Eng. in AI & ML (2026, CGPA 9.08); B.E. Computer Science (2023) | — | Portfolio "About" | Medium (transcripts not seen) |
| 13 | Research outputs | **None.** No papers, preprints, technical reports or reproducible benchmarks; the portfolio says so explicitly | — | Portfolio research page; positioning doc | High |

## 3. Demonstrated technical strengths (evidence-backed)

1. **End-to-end systems reasoning across boundaries.** Several root causes sat outside the layer where symptoms appeared
   (URL-parsing truncation, datacenter egress blocking, identity/storage mismatches). That habit of localising a failure
   to the right layer is the same skill experimental design needs: isolating variables.
2. **Retrieval and ingestion engineering on heterogeneous content** (tables, JSON/YAML, Markdown, media). Most
   applicants have only used RAG frameworks; you have worked on the parts those frameworks hide.
3. **Reliability engineering vocabulary:** idempotency, partial failure, graceful degradation, fallback chains,
   deterministic identifiers, explicit failure surfacing.
4. **Agent-platform architecture:** separating discovery from execution, authorization outside the model,
   human-approval gates.
5. **Claim calibration.** Your materials distinguish delivered, prototype and proposed work and state limitations.
   This is rare, it is what reviewers look for, and it will matter more than any single skill below.

## 4. Research-relevant experience: an honest classification

| Activity | Research-relevant? | Why |
|---|---|---|
| Measuring elapsed time before/after a pipeline change | Partly | A real measurement, but n=2 workloads, single runs, no variance; engineering evidence, not a study |
| Golden-record evaluation, recall@K, groundedness, citation accuracy (listed in toolkit) | Partly | Right metrics; no evidence yet of controlled comparisons with uncertainty estimates |
| Comparing chunking strategies / OCR tools at work | Engineering evaluation | Your own positioning doc says this too; no pre-registered hypothesis, baseline protocol or public data |
| Root-cause debugging | Transferable skill | Hypothesis → test → revise, but not knowledge that generalises beyond one system |
| Proposed experiments on your research page (restart vs checkpoint; prose vs structure-aware chunking; on-device evaluation) | **Yes — your best research seeds** | Each names an independent variable, a comparison and measurable outcomes. Report 3 tests whether they are still open (two are now crowded) |
| M.Eng. coursework / thesis | Unknown | No thesis topic, advisor or report visible — **please tell me** (Report 4, Q3) |

## 5. Potential research contributions your background makes credible
- **Measurement and evaluation of retrieval pipelines**, where realistic pipeline details (ingestion, chunking,
  parsing) change conclusions. You have seen those details break in production; most academic benchmarks hide them.
- **Reliability of agentic systems**: failure semantics, recovery, side-effect safety. Credible, but the field
  moved fast in 2026 (Report 3).
- **Human-in-the-loop knowledge governance**: approval-gated memory/knowledge updates. Credible, but hard to evaluate
  without human-subject studies.

## 6. Missing theoretical and methodological skills (prioritised)

| Priority | Skill | Why it matters for the likely directions | How to build it (concrete) |
|---|---|---|---|
| 1 | **Experimental design and statistics for ML evaluation:** paired tests, bootstrap/permutation, multiple comparisons, power analysis, mixed-effects models | Every candidate direction lives or dies on whether a difference is real | Work through Miller (2024) and Urbano et al. (2019) with code; replicate one significance analysis on a public run file |
| 2 | **IR evaluation methodology** (test collections, pooling, nDCG/recall, query-set size) | RAG evaluation inherits IR's problems; reviewers from IR will check this | Read the evaluation chapters of a standard IR textbook; reproduce BM25 numbers on one BEIR-style dataset |
| 3 | **Reading and positioning papers:** related-work synthesis, finding the *exact* delta from prior work | Your largest gap: zero papers written | One structured critique per week (template in Report 4) |
| 4 | **Scientific writing:** claim → evidence → limitation, in 8 pages | Needed for the first preprint | Write the problem statement for the approved topic yourself; I critique, not ghost-write |
| 5 | Mathematical maturity for the chosen sub-field (probability; for agent theory, some formal methods / distributed-systems semantics) | Needed for PhD-level depth and interviews | Targeted, after topic selection |
| 6 | Reproducible research engineering (seeded runs, config tracking, artifact release) | You already have the engineering habits; formalise them | Built into this repository's workflow |

## 7. Readiness for independent research

**Current level: strong research engineer, beginning researcher.** On a 0-4 scale per dimension:

| Dimension | Score | Basis |
|---|---:|---|
| Building research infrastructure | 3.5 | Extensive production systems work |
| Problem finding (spotting important questions) | 2.5 | Your research page asks good questions; two of three are now crowded (see Report 3), which a literature check would have caught |
| Literature positioning | 1 | No evidence yet |
| Experimental design and statistics | 1.5 | Right metrics named; no controlled studies with uncertainty |
| Writing for peer review | 1 | No evidence yet |
| Intellectual honesty and claim calibration | 3.5 | Clearly demonstrated |

These are my judgements from limited evidence; they are meant to steer effort, not to grade you.

## 8. Where you could develop genuine expertise
1. **Evaluation science for retrieval-augmented and agentic systems.** Your production exposure plus a statistics
   upgrade is a distinctive combination.
2. **Data-centric reliability of RAG:** ingestion, corpus integrity, freshness and deletion semantics.
3. **Agent reliability semantics:** failure signalling, recovery, side effects. A longer-term interest, best entered
   once you have a first paper and a sharper niche.

## 9. Relationship to PhD fields
| Field / community | Fit | Comment |
|---|---|---|
| Information retrieval (SIGIR, ECIR, CIKM) | **High** | RAG evaluation, corpus quality, test-collection methodology |
| NLP evaluation (ACL/EMNLP and Findings, evaluation workshops) | High | LLM-judge reliability, RAG benchmarks |
| ML systems / AI engineering (MLSys workshops, CAIN, data-management-for-ML workshops) | High | Ingestion faults, reliability, operations |
| Agentic AI / LLM agents | Medium-high | Strong interest; crowded; enter through evaluation/reliability |
| AI security | Medium | Strong groups dominate; better as a secondary interest |
| Applied ML for physical systems | Low (for stated goal) | Real experience, but off your target |

## 10. Information I still need from you
1. Confirmation of identity and that portfolio claims are accurate (D1).
2. Your M.Eng. thesis/project topic and supervisor, and whether that supervisor could write a research letter.
3. Whether any employer agreement restricts publishing independent research or using work-derived ideas (IP clauses).
