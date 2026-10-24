# Search log

All searches on 2026-10-18 via the server-side web-search tool ("std" = standard mode, "ext" = extended mode).
Direct API/primary-page access was blocked (see PROTOCOL.md §2).

| # | Mode | Query | Purpose / direction | Key results recorded |
|---:|---|---|---|---|
| 1 | ext | LLM agent fault tolerance crash recovery checkpoint duplicate side effects tool calls arXiv | C1 | Atomix, Crab, Verified Tool Calls, Exactly-Once, Belayer, AgentChaos(title unconfirmed) |
| 2 | std | transactional tool use LLM agents rollback undo compensation GoEX SagaLLM Atomix | C1 | SagaLLM, Atomix, Cordon; GoEX not found |
| 3 | ext | LLM agents tool returns empty or erroneous output hallucinate answer benchmark tool failure robustness 2025 | C2 | MIRAGE-Bench, ToolFailBench, AgentNoiseBench, When Tools Fail, AgentProp-Bench, SHIELDA |
| 4 | std | RAG robustness corpus corruption ingestion errors duplicate stale documents benchmark retrieval-augmented generation | C3 | RobustRAG, ReliabilityRAG, RARE; no ingestion-fault benchmark found |
| 5 | std | OCR document parsing errors impact on RAG retrieval benchmark OHRBench | C3/C4 | OHRBench (ICCV 2025) |
| 6 | std | RAG index freshness stale documents deletion propagation unlearning retrieval-augmented generation evaluation | C3 | Practitioner blogs only |
| 7 | ext | chunking strategies evaluation retrieval-augmented generation tables structured heterogeneous documents 2026 arXiv | C4 | Academic-texts chunking study; journal/industry studies |
| 8 | ext | fault injection RAG pipeline ingestion data quality silent failures parsing truncation evaluation arXiv 2026 | C3 | Silent-failure RAG study (Elsevier 2026), CatchBench, datasheet instrumentation |
| 9 | std | LLM agent root cause analysis benchmark OpenRCA RCAEval missing incomplete telemetry robustness | C6 | OpenRCA, OpenRCA pitfalls, real-world telemetry RCA |
| 10 | std | statistical significance sample size power analysis RAG evaluation retrieval comparisons confidence intervals LLM evals | C5 | Error bars (Miller), VERA, case-aware judge, tool-failure power analysis |
| 11 | std | on-device small language model agents tool calling latency memory energy benchmark local LLM agent privacy data egress | C7 | TinyLLM, two NeurIPS 2026 listings |
| 12 | ext | "Silent-failure detection in RAG pipelines" controlled fault-injection study multi-layer quality gates Results in Engineering authors | C3 | Abstract-level detail; authors not visible |
| 13 | std | "Where Does Exactly-Once Live" duplicate side effects LLM agents authors abstract | C1 | Author, LIMBO details |
| 14 | std | "ToolFailBench" diagnosing tool-use failures LLM agents authors abstract | C2 | Author, ICML 2026 listing |
| 15 | std | "Tools Fail: Detecting Silent Errors in Faulty Tools" Sun EMNLP 2024 | C2 | Authors, ACL Anthology ID |
| 16 | std | "Is Semantic Chunking Worth the Computational Cost" Vectara NAACL Findings 2025 | C4/C5 | Authors, pages |
| 17 | ext | variance of RAG evaluation conclusions pipeline configuration chunking retriever LLM judge reproducibility study sensitivity rankings | C5 | No direct study found; RAGalyst, chunk coverage, chunking cost |
| 18 | std | end-to-end RAG benchmark raw documents parsing PDF parser choice impact retrieval answer quality comparative study | C3/C4 | PDF parsing + chunking financial QA (2026) |
| 19 | std | LLM-as-judge variance RAG evaluation run-to-run reproducibility judge disagreement faithfulness metrics reliability study | C5 | Judge reliability papers; STAC note (paywalled) |
| 20 | std | machine unlearning retrieval-augmented generation document deletion right to be forgotten RAG benchmark arXiv | C3 | RAG-based unlearning (2024); no deletion benchmark |
| 21 | std | root cause analysis LLM agents telemetry dropout missing logs metrics traces ablation robustness RCAEval AIOpsLab 2026 | C6 | No dropout-robustness study found |
| 22 | std | prompt injection system-level defense agents CaMeL Progent FIDES AgentDojo 2026 policy enforcement tool calls | C9 | CaMeL, 2026 adaptive evaluation of out-of-band defenses |
| 23 | std | "When Poison Fails After Retrieval" corpus poisoning chunking reranking pipelines arXiv 2606.11265 | C3/C5 | Authors, findings |
| 24 | std | MCP tool selection at scale large tool registry retrieval benchmark agents 2026 RAG-MCP ScaleMCP MCP-Zero | C10 | MCP-Zero, LiveMCPBench, HumanMCP, RAG-MCP (ID not seen) |
| 25 | std | user feedback memory poisoning RAG agents human approval gate knowledge base updates AgentPoison MINJA defense evaluation | C8 | AgentPoison, memory-poisoning defense, SMSR |
| 26 | std | "Seven Failure Points When Engineering a Retrieval Augmented Generation System" Barnett CAIN 2024 | C3 | Authors, venue |
| 27 | std | "RAG-TESTER" automated end-to-end testing retrieval-augmented large language models abstract 2608.00054 | C3 | Method-level only |
| 28 | std | multiverse analysis retrieval-augmented generation evaluation design choices robustness of conclusions | C5 | No RAG multiverse study found; RAG design-decisions paper |
| 29 | std | RAG corpus completeness source-to-index reconciliation ingestion validation detect missing documents knowledge base coverage research paper | C3 | Practitioner tools only |
| 30 | std | "Modeling the Machine Learning Multiverse" Bell Kampman Dodge Lawrence NeurIPS 2022 | C5 | Confirmed |
| 31 | std | "Adding Error Bars to Evals" Evan Miller arXiv 2411.00640; "Signal and Noise" ... Heineman 2025 | C5 | Both confirmed |
| 32 | std | "Understanding the Fundamental Design Decisions of Retrieval-Augmented Generation Systems" arXiv 2411.19463 authors | C5 | Authors, TOSEM journal ref |
| 33 | std | AgentDojo Debenedetti NeurIPS 2024 datasets benchmarks; "Defeating Prompt Injections by Design" CaMeL arXiv 2503.18813 authors | C9 | CaMeL authors |
| 34 | std | "AgentDojo" dynamic environment evaluate prompt injection attacks defenses LLM agents arXiv | C9 | AgentDojo confirmed (NeurIPS 2024 D&B) |
| 35 | std | statistical significance testing IR evaluation Type I Type II errors Urbano SIGIR 2019; Smucker Allan Carterette CIKM 2007 | C5 challenge | Both confirmed (Urbano venue unconfirmed) |
| 36 | std | BERGEN benchmarking library RAG reproducibility; RAG reproducibility study variance seeds configurations ECIR SIGIR reproducibility track | C5 challenge | BERGEN (Findings EMNLP 2024) |
