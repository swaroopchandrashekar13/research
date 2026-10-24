# Report 2 — Your Potential Research Identity and PhD Direction

*Phase 0 · 2026-10-18*

## 1. The one-sentence identity I recommend testing

> **"I study whether we can trust the measurements we use to build retrieval-augmented and agentic AI systems, and
> what in real pipelines makes those measurements wrong."**

In plain language: teams decide how to build RAG and agent systems from benchmark numbers. You have seen in production
that the parts benchmarks hide (ingestion, parsing, chunking, failure handling) are where systems actually break. A
research identity built on *evaluation validity* turns that experience into science. It also gives you a methodological
core (statistics, experimental design) that transfers across sub-fields, which PhD supervisors value because the field
changes quickly.

## 2. Three candidate identities, compared

| Identity | Core question | Fit with your evidence | Crowding (Oct 2026, L1 evidence) | Long-term PhD potential |
|---|---|---|---|---|
| **A. Evaluation validity for RAG/agent systems** (recommended) | When do our measurements of RAG/agent design choices hold, and what hidden pipeline factors break them? | High: production RAG, golden-set evaluation, ingestion faults | Moderate: eval statistics is mature in general and in IR; little found that is specific to RAG design conclusions or ingestion | High: extends naturally to agents, LLM judges and benchmark design |
| B. Reliability semantics for agents | How should agents recover from failures without duplicate side effects or fabrication? | High: harness design, fallback chains | **High**: at least 6 relevant 2026 preprints (Atomix, Crab, Exactly-Once/LIMBO, Verified Tool Calls, Cordon, When Tools Fail) | High, but competing with strong systems groups |
| C. Governed agent knowledge and security | How do we keep agent memory and knowledge trustworthy under feedback and attack? | Medium-high: feedback-approval loop, authorization outside the model | High in security (CaMeL, FIDES, Progent, AgentDojo); moderate for feedback governance | High, but needs security depth or human-subject studies |

Identity A does **not** close the door on B or C. A good first paper in A gives you the methodology and credibility to
make your second project an agent-reliability study.

## 3. Communities and venues where identity A lives
- **Information retrieval:** SIGIR, ECIR, CIKM. Reproducibility tracks exist at some of these; check each year's call.
- **NLP:** ACL/EMNLP/NAACL main and Findings; evaluation-focused workshops.
- **AI engineering / ML systems:** CAIN (where the "Seven Failure Points" RAG paper appeared), MLSys workshops, and
  data-management-for-ML workshops.
- **Benchmarks:** NeurIPS Datasets & Benchmarks track (where AgentDojo appeared).

Venue calls, deadlines and AI-use policies change every year. I will verify them for the chosen venue before we plan
a submission. None are asserted here.

## 4. Who works on this: an illustrative, not-yet-verified list

These groups come from **author lists of papers in our bibliography** (L1). Affiliations are as shown in search
snippets at publication time. I have **not** verified current positions, student intake or funding. Treat this as a
starting point for Phase 13, not as recommendations.

| Paper (our key) | Group / affiliation shown | Why relevant |
|---|---|---|
| Urbano, Lima, Hanjalic (urbano2019sigtesting) | TU Delft (institutional-repository listing) | Statistical validity of IR evaluation |
| Bell, Kampman, Dodge, Lawrence (bell2022multiverse) | University of Cambridge; Allen Institute for AI | Multiverse analysis for ML conclusions |
| Heineman et al. (heineman2025signalnoise) | Allen Institute for AI; University of Washington | Signal/noise of LM evaluation |
| Barnett, Abdelrazek et al. (barnett2024sevenfailure) | Deakin University | RAG engineering failure points |
| Zhao, …, Lei Ma (zhao2026ragdesign) | University of Alberta; East China Normal University; University of Tokyo | RAG design decisions, SE for AI |
| Sun, Min, Chang, Bisk (sun2024toolsfail) | Carnegie Mellon University (plus industry) | Silent tool errors (agent reliability) |
| Debenedetti, …, Tramèr (agentdojo, camel) | ETH Zurich (plus industry labs) | Agent security and evaluation |
| Mohammadi et al. (atomix) | MPI-SWS | Transactional agent tool use |
| BERGEN authors (rau2024bergen) | NAVER LABS Europe (industrial lab) | RAG benchmarking; possible internship route |

How to use this list (exercise E5 in Report 4): read one recent paper per group and write two sentences on what
*your* study would add to theirs. Supervisors respond to that specificity, not to prestige.

## 5. Funded-PhD landscape: structural facts to verify per program

| Region | Typical funding structure | Implication for you |
|---|---|---|
| USA | Admission to strong CS PhDs usually comes with RA/TA funding; applications typically close around December for the next autumn | A December 2026 deadline is roughly 6-8 weeks away; a peer-reviewed paper is not achievable by then, a preprint might be |
| Continental Europe (e.g., Netherlands, Switzerland, Germany, Nordics) | Often **advertised funded positions** on a specific project, frequently salaried; applications all year | Fit with the advertised project matters most; a focused preprint plus code is strong evidence |
| Pan-European programmes (e.g., the ELLIS PhD programme) | Annual centralized call; co-supervision across countries | Check the current call's dates and eligibility |
| UK | Studentships and doctoral-training centres; international-fee coverage varies | Verify that a studentship covers international fees before applying |
| Canada | Funded MSc/PhD through supervisor grants; often supervisor-first | Supervisor contact matters |

**Admission vs funding (from your positioning doc, and I agree):** an unfunded or self-funded PhD abroad is a trap.
Plan for funded routes only.

## 6. Prerequisites: where you stand
| Requirement | Status | Note |
|---|---|---|
| Relevant master's degree with strong grades | Met (M.Eng. AI&ML, CGPA 9.08 — transcript not seen) | Strong formal credential |
| Research evidence (paper, preprint, technical report with code) | **Missing** | The main gap; this project addresses it |
| Research-calibre recommendation letters | **Unclear / likely missing** | Industry-manager letters carry little weight for research ability. Plan one letter from someone who supervises your research |
| English-language test | Unknown | Many programmes require IELTS/TOEFL; some waive it for English-medium degrees. Check per programme |
| GRE | Often optional in CS now | Verify per programme |
| Statement of purpose with a specific research agenda | Not started | This project's problem statement becomes its core |

## 7. How you will demonstrate independent research ability
1. **A public, reproducible study** with a pre-registered plan, a negative-result-tolerant design, released code and
   data, and an honest limitations section.
2. **A preprint** (arXiv) that you can defend line by line, followed by a workshop or Findings-level submission.
3. **One research letter**, ideally from your M.Eng. supervisor or a researcher you collaborate with on this study.
4. **A specific statement of purpose** naming the evaluation-validity problem, your result, and the next question.
5. **Targeted supervisor contact** after the preprint exists, citing their work and your result.

## 8. What I recommend you decide (details in Report 4)
- Whether identity A ("evaluation validity") is the identity you want to grow into. Disagreeing is fine, but give me
  your reason, since it will change Report 3's weights.
- Which application cycle you are targeting, because it changes how small the first study must be.
