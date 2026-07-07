# GroundedDocs — Stage 5 Round 2 Benchmark: 2026 RAG Senior-Architect Mature Choices

> Independent market-intelligence input. Produced 2026-06-29 as Phase A of Stage 5 Round 2.
> Consumed by: per-topic re-review memos in `92-stage5-review-memos.md` Round 2 section, and Phase D MUST-ALIGN decisions.
> Planning envelope context: 2-3 team / 180 days (DEC-073). Solo currently. Hardware floor: 16 GB VRAM single host. English-only MVP.

All sources accessed 2026-06-29 unless otherwise stated. Confidence tags: `high` = ≥2 independent production sources, `medium` = one strong source + alignment with general principles, `low` = single source or speculative.

---

## Summary table — alignment posture for the 9 topics

| Topic | 2026 mature default | Reasonable variation under MVP constraints | Confidence |
|---|---|---|---|
| 1. Pipeline orchestration | Event-driven graph / state machine (LangGraph 0.2.x or LlamaIndex Workflows 1.0); cyclic with reflection nodes | Hand-rolled finite-state controller acceptable for solo team if checkpoint + replay are explicit; pure-linear pipeline considered legacy by senior architects | high |
| 2. Concurrency / cache / queue | Hybrid: Postgres SKIP LOCKED for jobs + Redis/Valkey for hot cache OR proxy-layer cache (Helicone/Langfuse). Postgres-only is a credible minority position for small concurrency | Postgres-only fully credible at ≤2 concurrent users; Redis adds operational cost not justified at that scale. LISTEN/NOTIFY is a known scaling trap above ~hundreds of writers/s | high |
| 3. Retrieval architecture | BM25 + dense + RRF + cross-encoder rerank (bge-reranker-v2-m3 dominant open default). Query rewriting / HyDE selectively. Recursive structure-aware chunking baseline; semantic chunking only where measured wins justify cost | Skip HyDE/multi-query at MVP; single-stage rerank is fine. ColBERT/PLAID is real but rarely justified at <50M vectors | high |
| 4. Vector store + ACL | Qdrant default for new self-hosted; pgvector if Postgres already required (which it is for most stacks). Multi-tenancy via payload partitioning + payload index | pgvector is a legitimate primary choice at single-host MVP scale. Two-layer authorization (filter at retrieval + PDP re-check at generation) is the enterprise standard | high |
| 5. Evaluation | RAGAS (metrics) + DeepEval (CI runner) + Phoenix/Langfuse (traces). Golden set 100-300 prompts. 5-10% production sampling, weekly human review on 50-100 traces | A subset (RAGAS + golden set in CI) is the realistic solo-team floor. LLM-as-judge with a distinct judge model is non-negotiable | high |
| 6. Observability | OpenTelemetry GenAI semantic conventions + Langfuse (or LangSmith / Phoenix). Span structure: retrieve → rerank → generate → verify | Single dedicated tool (Langfuse self-hosted) sufficient at MVP; note Langfuse roadmap risk post-ClickHouse acquisition | high |
| 7. LLM serving | vLLM 0.5.x+ with prefix caching + chunked prefill + AWQ/FP8 quantization. SGLang where structured output / agentic prefix reuse dominates | TGI archived March 2026 (do not use new). llama.cpp acceptable only if no GPU. vLLM is the dominant choice on a single 16GB host with a 7-8B AWQ/FP8 model | high |
| 8. Two-layer authorization | Source-system ACL crawled at ingest + query-time enforcement against current ACL store. PDP re-check at answer assembly. Glean/AWS Q Business document patterns at user-store level | ACL pre-filter at vector store + ECM PDP post-check is industry-aligned. Stale-ACL detection (TTL + force-refresh) is mandatory in regulated deployments | high |
| 9. Refusal / grounding / safety | Layered: input rail (Llama Prompt Guard 2) → retrieval rail → output rail (Llama Guard 3, NeMo Guardrails) + NLI-based faithfulness check. Audit log captures model_version, prompt_version, retrieval_index_version | Solo teams can ship with output rail + NLI verifier as the core; full multi-layer rail stack is achievable inside 180-day envelope but consumes meaningful headcount | high |

---

## Two priority gaps — direct answers

### Gap 1: Concurrency / cache / queue layer — Redis or not in 2026?

**Direct answer: it depends on workload shape, and senior architects genuinely disagree.** The 2026 default for *teams with multi-tenant traffic above hundreds of req/min* is hybrid — Postgres as source-of-truth + Redis (or Valkey) for the hot-path cache, with cache invalidation via Postgres triggers or application code. But for low-concurrency self-hosted RAG, Postgres-only is no longer fringe — it is an actively endorsed pattern, especially for small teams who want one backup story and zero extra RAM overhead. (`high` confidence on both points; pattern coexistence is the actual 2026 state.)

The Postgres-only camp's evidence:
- Postgres SKIP LOCKED is "the pattern explicitly called out in the Postgres docs for multiple consumers accessing a queue-like table" and is what `pg-boss` and `pgmq` build on ([pg-boss GitHub, 2026-06-29](https://github.com/timgit/pg-boss); [pgmq GitHub, 2026-06-29](https://github.com/pgmq/pgmq)). Both are production-grade in 2026.
- A well-tuned Postgres + PgBouncer can serve read latencies under 5ms — sufficient for any RAG workload that is gated by LLM generation (seconds), not by cache (ms) ([Nordync, Redis vs PostgreSQL Caching 2026](https://www.nordync.com/blog/redis-vs-postgresql-caching-2026); `medium` — vendor blog, but consistent with the architecture principle).
- The "Making Redis Optional" / "Postgres-First" movement is visible on dev.to and Hacker News in 2026 ([dev.to, polliog, 2026](https://dev.to/polliog/making-redis-optional-why-im-pivoting-to-a-postgres-first-architecture-and-why-chose-valkey-as-4m0i); `medium`).

The "Redis still wins" camp:
- Benchmarks at 10K users / 100 RPS show Redis-only P50 read latency 1.2ms vs Postgres 8.5ms; hybrid 2.1ms with consistency ([Nordync, 2026](https://www.nordync.com/blog/redis-vs-postgresql-caching-2026); `medium`).
- Most production agent architectures still use Redis for short-term memory + Postgres for episodic/procedural state ([PingCAP, Best Database for AI Agents 2026](https://www.pingcap.com/compare/best-database-for-ai-agents/); `medium` — vendor analysis).

**Hard limit to know about: LISTEN/NOTIFY is a scaling trap.** Any commit containing a NOTIFY takes a global AccessExclusiveLock on the Postgres instance ([PgDog, Scaling Postgres LISTEN/NOTIFY](https://pgdog.dev/blog/scaling-postgres-listen-notify); [Recall.ai post-mortem March 2025](https://www.recall.ai/blog/postgres-listen-notify-does-not-scale); `high` — independent technical post-mortems). The PostgreSQL 19 fix (commit 282b1cde, ~Sept 2026 GA) is not yet in any production release. The pattern that *does* scale: SKIP LOCKED jobs table with bounded polling, and use NOTIFY only as an optional wake-up signal.

**Synthesis for self-hosted RAG at ≤2 concurrent queries / single host:** Postgres-only is a defensible 2026 senior choice. The decision is not "Redis is mature, Postgres is naive" — it's "Redis is mature, Postgres is *also* mature for low-concurrency single-tenant deployments, and adds no second daemon to monitor." Where senior architects would *push back* on a Postgres-only design is if (a) the cache is on the synchronous request path with hundreds of concurrent users, or (b) LISTEN/NOTIFY is being used for high-throughput fanout. Neither applies under the ≤2 concurrency cap.

### Gap 2: Mid-flight rewriting / per-claim verification — graph orchestration or stream interception?

**Direct answer: graph orchestration is the dominant 2026 pattern; streaming/token interception is an emerging research direction but not yet a mature production default.** Senior architects who want mid-flight critique-rewrite loops use LangGraph, LlamaIndex Workflows 1.0, or Burr — not custom streaming token-interceptors. (`high` confidence on graph adoption, `medium` on the relative immaturity of streaming interception in production.)

**Graph orchestration as the 2026 default.** Multiple independent sources put graph/state-machine orchestration well above linear chains in 2026 production usage:
- LangGraph: 32k+ GitHub stars (May 2026), 34.5M monthly downloads, named adopters Klarna, Uber, LinkedIn, AppFolio. Klarna runs an 85M-user customer-support assistant on it ([LangGraph repo, 2026-06-29](https://github.com/langchain-ai/langgraph); [LangChain customer stories](https://www.langchain.com/resources/ai-agent-frameworks); `high`).
- Industry trend cited: "Over 70% of production Agents adopted some form of graph structure (DAG or state machine), not simple linear Chain" ([Reactify, LangGraph in 2026](https://www.reactify-solutions.com/articles/langgraph-production-agents-2026); `medium` — single source for the exact %, but consistent with multi-source observed adoption).
- LlamaIndex shipped Workflows 1.0 as the recommended composition primitive in 2026, replacing the older monolithic query-engine pattern. It's event-driven with typed state and async step methods ([LlamaIndex Workflows 1.0 announcement](https://www.llamaindex.ai/blog/announcing-workflows-1-0-a-lightweight-framework-for-agentic-systems); `high`).
- DAGster's Burr remains a viable alternative emphasizing observability + state machine semantics; smaller adoption than LangGraph but cited in framework comparisons.

**Concrete pattern for per-claim verification in graph orchestration.** A 2026 reference pattern: research node gathers passages → writer node drafts → fact-checker node verifies claims against retrieved evidence → if any claim is unsupported, edge routes back to the writer node with the offending claim list ([Reactify, 2026](https://www.reactify-solutions.com/articles/langgraph-production-agents-2026); [Medium, "Next-Generation Agentic RAG with LangGraph 2026"](https://medium.com/@vinodkrane/next-generation-agentic-rag-with-langgraph-2026-edition-d1c4c068d2b8); `medium` — multiple Medium/blog sources, no formal case study yet).

This is structurally what Self-RAG and Corrective RAG (CRAG) describe academically; LangGraph / Workflows are the implementation vehicles in 2026 ([Asai et al., Self-RAG ICLR 2024](https://arxiv.org/abs/2310.11511); [CRAG ICLR 2024 paper](https://arxiv.org/pdf/2401.15884); `high`).

**Per-claim verification mechanics.** The mature 2026 pattern decomposes the generated answer into atomic claims, then runs an NLI classifier (DeBERTa-class) over (claim, retrieved-passage) pairs, classifying each as entailed / neutral / contradicted ([Deepchecks, RAG Evaluation Metrics](https://deepchecks.com/rag-evaluation-metrics-answer-relevancy-faithfulness-accuracy/); [FutureAGI, NLI-Based Evaluation 2026](https://futureagi.com/glossary/nli-evaluation/); [Auto-GDA arXiv 2410.03461](https://arxiv.org/pdf/2410.03461); `high`). Production systems run lightweight NLI online + heavier LLM-as-judge offline.

**Streaming / token-level interception.** This exists but is a research frontier, not a production default in 2026:
- Streaming-token safety probes (Kelp's Streaming Latent Dynamics Head, <0.5ms/token) target *safety/harmfulness*, not citation grounding ([Zylos research, 2026-03](https://zylos.ai/research/2026-03-28-llm-output-streaming-token-delivery-architectures/); `medium`).
- NExT-Guard does training-free streaming safeguards but again on safety, not factual entailment ([arXiv 2603.02219](https://arxiv.org/pdf/2603.02219); `low` — single paper, no production case).
- No production case studies of *per-claim verification at the streaming layer* surfaced in 2026 literature. The reason: claim-level entailment requires a completed claim, not a partial token stream — atomic claims are the natural unit, not tokens.

**Constrained-decoding integration.** Outlines (Apache 2) and SGLang's XGrammar/Outlines backend are 2026's mature options for structurally constrained JSON/grammar output during generation ([SGLang structured output guides 2026](https://medium.com/@rahularyan786/sglang-structured-generation-language-revolutionizing-efficient-and-controllable-llm-programming-f3438202c673); [vLLM structured output docs](https://docs.vllm.ai/en/latest/features/quantization/); `high`). They guarantee structural validity (the answer parses as a citation-tagged JSON), not factual grounding. Citation grounding still needs a post-step NLI verifier.

**Synthesis.** A 2026 senior architect implementing per-claim grounding does (a) structure the pipeline as a graph with an explicit verify node and a feedback edge to writer/retriever, (b) use constrained decoding to ensure the answer emits per-claim citation tags, and (c) run NLI entailment against retrieved passages at the verify node. Streaming-token interception is real but is the wrong abstraction for claim-level grounding; it solves harmfulness, not faithfulness. The "frameworks resist mid-flight rewriting" framing is partly outdated — LangGraph and Workflows 1.0 are explicitly designed for mid-flight rewriting loops.

---

## Topic 1 — Pipeline orchestration shape

### State of practice (2026)
- Graph / state-machine orchestration is the dominant 2026 pattern for non-trivial RAG. Cited adoption: "over 70% of production Agents adopted some form of graph structure" ([Reactify, 2026](https://www.reactify-solutions.com/articles/langgraph-production-agents-2026); `medium`).
- Reference architectures explicitly model the "writer → fact-checker → writer (on flag)" cycle in LangGraph ([Medium, Vinod Rane, 2026](https://medium.com/@vinodkrane/next-generation-agentic-rag-with-langgraph-2026-edition-d1c4c068d2b8); `medium`).
- LlamaIndex Workflows 1.0 became the recommended composition primitive in 2026, replacing the older query-engine pattern. Event-driven, typed state, async step methods ([LlamaIndex announcement](https://www.llamaindex.ai/blog/announcing-workflows-1-0-a-lightweight-framework-for-agentic-systems); `high`).
- Self-RAG (Asai et al., ICLR 2024) and CRAG (ICLR 2024) provide the academic backbone for adaptive retrieval + critique; 2026 production deployments cite them as foundational ([Self-RAG arXiv 2310.11511](https://arxiv.org/abs/2310.11511); [CRAG arXiv 2401.15884](https://arxiv.org/pdf/2401.15884); `high`).
- Constrained decoding via Outlines / SGLang's XGrammar is the 2026 mature mechanism for enforcing per-claim citation tags ([SGLang docs](https://medium.com/@rahularyan786/sglang-structured-generation-language-revolutionizing-efficient-and-controllable-llm-programming-f3438202c673); `high`).

### Mature frameworks / libraries
- **LangGraph 0.2.x+** — finite-state-machine framework, native checkpointing, time-travel, human-in-loop pause points
- **LlamaIndex Workflows 1.0** — event-driven, typed events, async step methods
- **Burr** (DAGster) — state-machine emphasis, strong observability
- **Inngest** — durable execution, step-based, no-determinism constraint, good fit for non-deterministic LLM calls ([Spheron, AI Agent Workflow Orchestration 2026](https://www.spheron.network/blog/ai-agent-workflow-orchestration-temporal-inngest-restate-gpu-cloud/); `medium`)
- **Temporal** — durable execution at scale but requires deterministic workflow code, which forces every LLM call into an Activity ([Inngest vs Temporal](https://www.inngest.com/compare-to-temporal); `medium`)
- **Outlines / SGLang XGrammar / vLLM guided decoding** — constrained output, FSM-based, 3x+ JSON decode speedup ([SqueezeBits, Guided Decoding Performance](https://blog.squeezebits.com/guided-decoding-performance-vllm-sglang); `medium`)

### Adoption signals
- LangGraph: 32k+ stars (May 2026), 34.5M monthly downloads; Klarna (85M users), Uber (~21k dev-hours saved), LinkedIn (recruiting + SQL bot), AppFolio ([LangGraph repo](https://github.com/langchain-ai/langgraph); LangChain case studies; `high`)
- LlamaIndex Workflows: official recommended pattern in LlamaIndex 2026 release ([LlamaIndex blog](https://www.llamaindex.ai/blog/announcing-workflows-1-0-a-lightweight-framework-for-agentic-systems); `high`)
- Temporal Nexus reached GA early 2026; Inngest favored for AI/LLM event-driven patterns ([Spheron 2026](https://www.spheron.network/blog/ai-agent-workflow-orchestration-temporal-inngest-restate-gpu-cloud/); `medium`)

### How mature 2026 systems implement per-claim grounding verification
The 2026 mature pattern:
1. Generate the answer in a structured format with per-claim citation tags (constrained decoding via Outlines / SGLang XGrammar guarantees parseability) ([SGLang 2026](https://medium.com/@rahularyan786/sglang-structured-generation-language-revolutionizing-efficient-and-controllable-llm-programming-f3438202c673); `medium`).
2. Decompose into atomic claims; for each claim, run an NLI classifier (DeBERTa-class fine-tuned on entailment) against retrieved passages ([Deepchecks](https://deepchecks.com/rag-evaluation-metrics-answer-relevancy-faithfulness-accuracy/); [Auto-GDA arXiv 2410.03461](https://arxiv.org/pdf/2410.03461); `high`).
3. If a claim is not entailed (or contradicted), route back through a writer node with the offending claim list, OR refuse the answer if no fix is possible ([Reactify](https://www.reactify-solutions.com/articles/langgraph-production-agents-2026); `medium`).
4. Audit-log per-claim NLI scores alongside model_version, prompt_version, retrieval_index_version ([Medium, Kuldeep Paul](https://medium.com/@kuldeep.paul08/the-ai-audit-trail-how-to-ensure-compliance-and-transparency-with-llm-observability-74fd5f1968ef); `medium`).

### Open debates
- LangGraph (Python-native, LangChain ecosystem) vs LlamaIndex Workflows (event-driven, decoupled from chains) — both have mature 2026 cohorts; choice is taste plus existing-stack alignment.
- Durable execution (Temporal/Inngest) wrapping LangGraph vs LangGraph's native checkpointing — Temporal/Inngest add a heavy second engine; LangGraph checkpointing is "good enough" for many. ([AppScale, Durable Execution 2026](https://appscale.blog/en/blog/durable-execution-llm-agents-temporal-langgraph-checkpointing-2026); `medium`).
- "Frameworks vs build from scratch" — some senior teams (Anthropic's Cognition, some agent-platform vendors) argue framework abstractions add brittle indirection. The counter is that 2026 graph frameworks are thin enough that the build-from-scratch argument has weakened ([MindStudio](https://www.mindstudio.ai/blog/llm-frameworks-replaced-by-agent-sdks); `low` — single Medium opinion).

**Confidence: high** on graph dominance; **medium** on the specific 70%+ adoption number.

---

## Topic 2 — Concurrency, queue, cache infrastructure

### State of practice (2026)
- Hybrid Postgres + Redis remains the mainstream production default for multi-tenant LLM/agent systems ([PingCAP, Best DB for AI Agents 2026](https://www.pingcap.com/compare/best-database-for-ai-agents/); `medium`).
- Postgres-only is rising and credible for low-concurrency deployments. The "Postgres-First" movement explicitly argues that Redis adds an extra service to monitor/secure/RAM for marginal gain ([dev.to, polliog, 2026](https://dev.to/polliog/making-redis-optional-why-im-pivoting-to-a-postgres-first-architecture-and-why-chose-valkey-as-4m0i); [HN thread 45380699 "Redis is fast – I'll cache in Postgres"](https://news.ycombinator.com/item?id=45380699); `medium`).
- pg-boss (Node-focused) and pgmq (Postgres extension) are the 2026 mature SKIP-LOCKED job queue libraries ([pg-boss GitHub](https://github.com/timgit/pg-boss); [pgmq GitHub](https://github.com/pgmq/pgmq); `high`).
- LLM-layer caching is increasingly done at the proxy/gateway: Helicone (acquired by Mintlify March 2026, now maintenance-mode), Langfuse, LiteLLM, Portkey ([ChatForest review of Helicone](https://chatforest.com/reviews/helicone-llm-observability-gateway/); [Klymentiev, LLM Gateway 2026](https://klymentiev.com/blog/llm-gateway-guide); `medium`).
- vLLM 0.5.x+ provides KV-cache and automatic prefix caching at the inference layer — orthogonal to application-level cache ([vLLM Automatic Prefix Caching docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/); `high`).

### Mature frameworks / libraries / patterns
- **Postgres + SKIP LOCKED jobs table** + optional NOTIFY wake-up (not for high fanout)
- **pgmq** — Postgres extension, queue = table, MIT-licensed
- **pg-boss** — Node.js job queue on Postgres, exactly-once semantics
- **Redis / Valkey** — Valkey (open-source Redis fork) is the 2026 Redis successor for license-conscious teams
- **Helicone / Langfuse / LiteLLM / Portkey** — proxy-layer caches, semantic caching emerging
- **vLLM automatic prefix caching + chunked prefill** — KV-cache reuse across requests with shared prefixes ([vLLM docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/); `high`)

### Adoption signals
- pgmq, pg-boss both have active 2026 commit history and are used in self-hosted stacks ([pgmq repo](https://github.com/pgmq/pgmq); `high`).
- vLLM prefix caching: documented production tuning advice "enable continuous batching first, then chunked prefill if TTFT p95 is the constraint" ([SitePoint, vLLM Production Deployment 2026](https://www.sitepoint.com/vllm-production-deployment-guide-2026/); `medium`).
- Helicone proxy-cache pattern saw 20-40% cost reduction for repeated queries before maintenance mode ([ChatForest review](https://chatforest.com/reviews/helicone-llm-observability-gateway/); `medium`).

### When Postgres-only breaks down (hard numbers)
- LISTEN/NOTIFY: any commit containing NOTIFY takes a global AccessExclusiveLock on the Postgres instance; serializes those commits. Recall.ai traced March 2025 outages to this lock under "tens of thousands of simultaneous producers" ([Recall.ai post-mortem](https://www.recall.ai/blog/postgres-listen-notify-does-not-scale); `high`).
- NOTIFY payload size cap: 8000 bytes ([PgDog](https://pgdog.dev/blog/scaling-postgres-listen-notify); `high`).
- Notification queue ceiling: ~8GB undelivered buffer in default config (configurable via `max_notify_queue_pages` since PG17) ([PgDog](https://pgdog.dev/blog/scaling-postgres-listen-notify); `high`).
- PG19 has a core fix (commit 282b1cde) eliminating the bottleneck — Beta 1 was June 4, 2026; GA ~September 2026 ([PgDog](https://pgdog.dev/blog/scaling-postgres-listen-notify); `high`).
- Latency comparison: well-tuned Postgres + PgBouncer ~<5ms reads; Redis ~1.2ms. Difference is irrelevant when LLM generation dominates request time (seconds) ([Nordync 2026](https://www.nordync.com/blog/redis-vs-postgresql-caching-2026); `medium`).

### Multi-tier caching layers in 2026 RAG
1. **KV cache inside vLLM** — automatic prefix caching, free with --enable-prefix-caching, big win when system prompt + retrieved chunks have high reuse ([vLLM docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/); `high`).
2. **Prompt-template cache** — application-level cache of (template, parameters) → rendered prompt; trivial Postgres or in-memory.
3. **Answer cache** — semantic or exact-match cache of (normalized query, ACL fingerprint) → answer + citations. Helicone-class proxies do exact-match; semantic caching is research-grade in 2026 ([arXiv 2602.13165 Asynchronous Verified Semantic Caching](https://arxiv.org/pdf/2602.13165); `low`).
4. **Embedding cache** — straightforward; embeddings are deterministic. Often co-located in vector store.

### Open debates
- "Postgres-only at MVP" vs "introduce Redis from day one" — genuine senior-architect split. The Postgres-first camp wins on operational simplicity for solo/small teams; the Redis camp wins as soon as you have multi-tenant high-concurrency traffic.
- Semantic caching: research-grade, not yet a production default. Hash-based exact-match cache is the safe 2026 choice.

**Confidence: high** on the patterns and limits; **medium** on the relative size of each camp.

---

## Topic 3 — Retrieval architecture

### State of practice (2026)
- "BM25 + dense + RRF + cross-encoder rerank" is described as the gold-standard hybrid retrieval in multiple 2026 production guides ([LocalAIMaster, Reranking Guide 2026](https://localaimaster.com/blog/reranking-cross-encoders-guide); [Denser.ai, Hybrid Search for RAG 2026](https://denser.ai/blog/hybrid-search-for-rag/); `high`).
- Recursive structure-aware chunking (split on headings, paragraph boundaries, with 10-20% overlap) is the 2026 default. Semantic chunking adds 2-3% recall at substantial embedding cost ([Chroma research cited in Firecrawl 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag); `medium`).
- Query rewriting / HyDE / multi-query is a high-leverage move applied selectively when recall is the bottleneck ([Medium, Mudassar Hakim, Retrieval is the Bottleneck](https://medium.com/@mudassar.hakim/retrieval-is-the-bottleneck-hyde-query-expansion-and-multi-query-rag-explained-for-production-c1842bed7f8a); `medium`).
- ColBERT v2 + PLAID is real and production-deployable but is rarely the right answer below ~50M passages ([CIKM 2022 PLAID paper](https://dl.acm.org/doi/10.1145/3511808.3557325); [Medium, "Fidelity Crisis in RAG"](https://blog.gopenai.com/the-fidelity-crisis-in-rag-why-late-interaction-colbert-is-the-4k-image-of-search-vs-e978d96b25b8); `medium`).

### Mature models / libraries
- **Embeddings**: BGE-M3 (568M params, 100+ langs, MIT, dense+sparse+multi-vector in one model) is the 2026 self-hosted default ([BentoML, Open-Source Embedding Models 2026](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models); `high`). Nomic-embed-text dominant on Ollama (73.8M pulls). Stella variants competitive on April 2026 MTEB.
- **Rerankers**: bge-reranker-v2-m3 (<600M params, runs on consumer GPU) is the dominant open default. Jina Reranker v3 listwise (5.43% over bge-reranker-v2-m3 at same scale, 131k-token context). Cohere Rerank 3/4 hosted alternative ([Agentset comparison](https://agentset.ai/rerankers/compare/cohere-rerank-4-fast-vs-baaibge-reranker-v2-m3); [LocalAIMaster 2026](https://localaimaster.com/blog/reranking-cross-encoders-guide); `high`).
- **Late-interaction**: ColBERT v2 + PLAID — 2.5-7× GPU / 9-45× CPU speedup over vanilla ColBERTv2; tens of ms on GPU at 140M passages ([CIKM 2022 PLAID paper](https://dl.acm.org/doi/10.1145/3511808.3557325); `high`). Active Late Interaction Workshop at ECIR 2026 confirms continued community investment ([lateinteraction.com](https://www.lateinteraction.com/); `medium`).
- **Hybrid fusion**: Reciprocal Rank Fusion (RRF) is the default; Vespa multi-stage ranking allows BM25 first-pass + dense second-pass ([Vespa hybrid docs](https://docs.vespa.ai/en/learn/tutorials/hybrid-search.html); `medium`).
- **Query strategies**: HyDE (hypothetical document embedding), multi-query / query decomposition, DMQR-RAG ([arXiv 2411.13154](https://arxiv.org/html/2411.13154v1); `medium`), LevelRAG for multi-hop ([arXiv 2502.18139](https://arxiv.org/html/2502.18139v1); `low`).

### Adoption signals
- bge-reranker-v2-m3 cited as the default in multiple 2026 production guides ([Milvus docs](https://milvus.io/docs/rerankers-bge.md); [MachineLearningMastery, Top 5 Rerankers](https://machinelearningmastery.com/top-5-reranking-models-to-improve-rag-results/); `high`).
- BGE-M3 + BGE-reranker-v2 is "most production RAG stacks in 2026" per multiple sources ([Innovative AIs, Best Embedding Models for RAG 2026](https://innovativeais.com/blog/best-embedding-models-for-rag-in-2026); [BentoML 2026](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models); `high`).
- Semantic chunking: Chroma's measurement — recursive 85-90% recall at 400 tokens vs semantic 91-92%; 2-3% gain at the cost of embedding every sentence ([Firecrawl 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag); `medium`).

### Chunking guidance (2026)
- 400-tokens with 10-20% overlap is the most-cited starting point ([Firecrawl 2026](https://www.firecrawl.dev/blog/best-chunking-strategies-rag); [Databricks community blog](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089); `medium`).
- Structure-aware (split on headings, code function boundaries) first, semantic chunking only where measured recall gap justifies the embedding cost.
- Hierarchical chunking (summary + detail layers) is recommended for long-form documents.

### Open debates
- Single dense + rerank vs hybrid BM25+dense+rerank — hybrid usually wins, but exact-match-heavy corpora (legal, technical, with part numbers) push hybrid even harder ([Digital Applied, Hybrid Search 2026](https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026); `medium`).
- HyDE pays off vs. doesn't — depends on whether query/document vocabulary mismatch is the bottleneck. No universal answer in 2026 literature.
- ColBERT for "everyone" vs ColBERT "only at large scale" — genuine split. The ColBERT/PLAID camp argues the "fidelity crisis" is real; the dense+rerank camp argues a good cross-encoder rerank closes the gap at far lower index cost.

**Confidence: high.**

---

## Topic 4 — Vector store + ACL filter combos

### State of practice (2026)
- Five vector databases dominate 2026 production: pgvector, Qdrant, Weaviate, Milvus, LanceDB ([CallSphere, Vector Database Benchmarks 2026](https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb); `high`).
- 2026 default recommendation: pgvector if you're already on Postgres, Qdrant if not ([Kalvium Labs, pgvector vs Pinecone vs Qdrant vs Weaviate 2026](https://www.kalviumlabs.ai/blog/vector-databases-compared-pgvector-pinecone-qdrant-weaviate/); `medium`).
- pgvector 0.9 (early 2026) added IVFFlat improvements, sparse vector support, substantial speed boosts ([CallSphere 2026](https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb); `medium`).
- Qdrant leads open-source speed (10-25% faster than Weaviate/Milvus on common workloads) and has the simplest operational story for self-hosted ([CallSphere 2026](https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb); `medium`).
- Enterprise RAG platforms (Glean, AWS Q Business, Vectara, Azure AI Search) enforce ACL at query time, not at ingestion time ([Glean perspectives](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search); [AWS Q Business ACL docs](https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/); `high`).

### Mature stores + ACL patterns
- **pgvector**: Postgres extension. ACL filter is just a SQL WHERE clause joining the embedding row to ACL tables. Simple to reason about, simple to audit. Latency penalty for large filtered scans is real but tolerable at single-host scale.
- **Qdrant**: payload filtering with payload indexes. Tenant index variant via `is_tenant: true` payload key. Multi-tenancy patterns: payload partitioning (cheap), or tiered multitenancy with named shards for large tenants (Qdrant 1.16+) ([Qdrant multitenancy docs](https://qdrant.tech/documentation/manage-data/multitenancy/); [Qdrant 1.16 release](https://qdrant.tech/blog/qdrant-1.16.x/); `high`).
- **Weaviate**: native hybrid search; multi-tenancy first-class.
- **Milvus**: billion-scale, K8s-native; overkill at MVP single-host but the right answer above ~100M vectors.
- **Vespa**: multi-stage ranking, BM25 + dense fusion, mature but heavier ops ([Vespa hybrid tutorial](https://docs.vespa.ai/en/learn/tutorials/hybrid-search.html); `medium`).

### Qdrant pre-filter performance — important nuance
"Pre-filtering should not be used over large datasets as it breaks too many links in the HNSW graph, causing lower accuracy" ([Qdrant Vector Search Filtering Guide](https://qdrant.tech/articles/vector-search-filtering/); `high`). Qdrant's query planner picks between (a) full pre-filter then ANN, (b) HNSW search with filter skipping non-matching nodes, (c) full scan — based on filter cardinality and the `full_scan_threshold`. **Payload indexes must be created before ingest for best performance.** This is the trap most "ACL pre-filter" naive designs fall into.

### Two-layer authorization pattern (2026 enterprise default)
The mature pattern across Glean, AWS Q Business, Microsoft Graph Connectors, Vectara:

1. **Ingest-time ACL crawl**: connector walks source system, collects ACL per document, stores in a user/group store ([AWS Q Business connector docs across data sources](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/box-user-management.html); `high`).
2. **Query-time ACL filter at retrieval**: candidate chunks filtered by current user's group membership ([Glean: "a document the querying user is not authorized to see does not appear in retrieval results, regardless of semantic similarity"](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search); `high`).
3. **PDP re-check at answer assembly**: just before generation (and ideally before final delivery), re-query the source system's authoritative PDP to confirm the user still has access. Catches stale-ACL race conditions.

ACL inheritance and union/replace semantics vary per source system: SharePoint/OneDrive union parent + child; Slack DMs *replace* workspace ACLs ([AWS Q Business OneDrive ACL docs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/onedrive-legacy-acl-crawling.html); [Slack ACL docs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-user-management.html); `high`). A generic ACL model must accommodate both.

### Failure modes (2026)
- **Stale ACL**: cached ACLs that lag behind source-system revocation. Mitigation: TTL + on-access PDP re-check ([AWS Q Business connector docs across data sources](https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/); `medium`).
- **PDP timeout**: source-system PDP slow → either fail-closed (refuse) or serve cached ACL (risk). Senior architects default to fail-closed in regulated deployments.
- **Pre-filter on huge filter sets breaks HNSW graph traversal accuracy** ([Qdrant docs](https://qdrant.tech/articles/vector-search-filtering/); `high`).

### Open debates
- pgvector "good enough" vs "dedicated vector DB always" — the dedicated-DB camp wins above ~5-10M vectors or when filtered queries dominate; pgvector wins on operational simplicity below.
- Single collection with payload-partitioned tenants vs collection-per-tenant — Qdrant's official guidance is "single collection in most cases" ([Qdrant multitenancy](https://qdrant.tech/documentation/manage-data/multitenancy/); `high`), but collection-per-tenant is still used by some teams for hard isolation.

**Confidence: high.**

---

## Topic 5 — Evaluation framework + LLM-as-judge

### State of practice (2026)
- The mature 2026 stack: **RAGAS for metrics + DeepEval for the CI runner + TruLens or Phoenix for traces** ([Atlan, LLM Evaluation Frameworks 2026](https://atlan.com/know/llm-evaluation-frameworks-compared/); [BestAIWeb, RAG Eval Harness 2026](https://www.bestaiweb.ai/how-to-build-a-rag-evaluation-harness-with-ragas-deepeval-and-trulens-in-2026/); `high`).
- Golden set 100-300 prompts is the typical size; 50-200 to start ([Premai, RAG Evaluation 2026](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/); [CalibreOS, Production RAG Evaluation](https://www.calibreos.com/learn/genai-rag-evaluation); `medium`).
- 5-10% production traffic sampling for continuous monitoring; full golden-set in CI; 50-100 random production traces / week for human review ([Premai 2026](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/); `medium`).
- LLM-as-judge with a *distinct* judge model (different family / size from the generator) is the discipline that distinguishes mature teams.

### Mature frameworks
- **RAGAS** — academically validated RAG metrics (faithfulness, answer relevance, context precision/recall) without requiring ground truth labels.
- **DeepEval** — pytest-style test runner, CI/CD-native, hard-fail on metric regression.
- **TruLens** — RAG metrics + OpenTelemetry-based tracing; diagnose pipeline failures at the span level.
- **Phoenix Arize** — observability + RAG eval; embedding-projection visualization makes retrieval drift visible.
- **Promptfoo** — declarative test harness, often used alongside the above.
- **Langfuse** — evals + observability + dataset management in one tool ([Langfuse repo](https://github.com/langfuse/langfuse); `high`).

### Metrics that matter in 2026
- **Faithfulness / groundedness** — proportion of claims supported by retrieved context. Operationalized via NLI decomposition + DeBERTa-class entailment classifier ([Deepchecks](https://deepchecks.com/rag-evaluation-metrics-answer-relevancy-faithfulness-accuracy/); `high`).
- **Citation correctness / source attribution** — claim cites the *specific* retrieved passage that supports it. Failure mode: "citation hallucination — correct facts with wrong attributions" ([FutureAGI, NLI Eval 2026](https://futureagi.com/glossary/nli-evaluation/); `medium`).
- **Refusal rate / refusal appropriateness** — track both false-refusal (refused when grounded answer was possible) and false-accept (answered when should have refused).
- **Context precision / recall** — retrieval quality measures.
- **Answer relevance** — answer addresses the question (orthogonal to faithfulness).

### Eval-in-CI vs continuous eval
- CI: hard quality gates on golden set; block PR if a metric drops below baseline + epsilon ([TestQuality, LLM Regression Testing Pipeline 2026](https://testquality.com/llm-regression-testing-pipeline/); `medium`).
- Continuous: sample 5-10% of production traffic; weekly human review on 50-100 random traces to calibrate the LLM-as-judge ([Premai 2026](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/); `medium`).

### Open debates
- LLM-as-judge calibration — judge models drift; correlation with humans varies by domain. Senior teams routinely retrain or re-prompt the judge.
- Synthetic golden-set generation vs human-curated — RAGAS supports synthetic generation; many teams insist on human-curated for regulated domains.

**Confidence: high.**

---

## Topic 6 — Observability stack for production LLM

### State of practice (2026)
- The industry is converging on **OpenTelemetry GenAI semantic conventions** as the standard wire format ([Langfuse OTEL docs](https://langfuse.com/integrations/native/opentelemetry); `high`).
- Langfuse SDK v4 is OTEL-native, automatically converting emitted spans into Langfuse observations with first-class helpers for token usage, cost, prompt linking, scoring ([Langfuse OTEL integration](https://langfuse.com/integrations/native/opentelemetry); `high`).
- Pydantic AI, smolagents, Strands Agents all emit OTEL traces; Langfuse, LangSmith, Phoenix, Arize all ingest OTEL ([n1n.ai, LLM Observability 2026](https://explore.n1n.ai/blog/llm-observability-langfuse-langsmith-opentelemetry-2026-05-17); `medium`).
- Langfuse was acquired by ClickHouse in January 2026 — adds DB heritage but introduces roadmap uncertainty ([Langfuse repo](https://github.com/langfuse/langfuse); `medium`).

### Mature tools
- **Langfuse** — open-source, MIT, Kubernetes/Helm deployment for production, processes billions of events/month, 50M+ monthly SDK installs; self-hostable ([Langfuse repo](https://github.com/langfuse/langfuse); `high`).
- **LangSmith** — LangChain's hosted observability; tight LangGraph integration; not open-source.
- **Phoenix Arize** — open-source, embedding-projection visualization, strong on retrieval drift diagnostics.
- **Helicone** — proxy-first observability; *maintenance mode* since March 2026 acquisition by Mintlify ([ChatForest review](https://chatforest.com/reviews/helicone-llm-observability-gateway/); `medium`).
- **OpenLLMetry** — OTEL-native instrumentation library, integrates with Langfuse ([Langfuse OpenLLMetry guide](https://langfuse.com/guides/cookbook/otel_integration_openllmetry); `medium`).

### Span structure for retrieve → generate → verify
Canonical 2026 structure ([Langfuse blog, AI Agent Observability](https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse); `medium`):
- Root: `rag.query` with attributes for user_id, session_id, tenant_id, ACL fingerprint
  - `rag.embed` — embedding latency, model_version
  - `rag.retrieve` — vector store latency, candidates count, filter applied
  - `rag.rerank` — rerank latency, top-K, model
  - `llm.generate` — token counts, model_version, prompt_version, latency (TTFT, ITL, total)
  - `rag.verify` — NLI scores per claim, overall faithfulness, refusal decision

### Metrics for SLO definition in 2026
- **p95 latency** (with TTFT/ITL breakdown for streaming) ([Spheron, LLM Inference SLO Engineering 2026](https://www.spheron.network/blog/llm-inference-slo-ttft-itl-latency-budget-guide-2026/); `medium`).
- **Refusal rate** — flagged as a quality leading indicator in 2026 dashboards.
- **Citation correctness / hit rate**.
- **Cache hit rate** ([Medium, Autoscaling Hid Our LLM Cost Regression](https://medium.com/@nroan/autoscaling-hid-our-llm-cost-regression-85-4-cache-hit-rate-b4beab5df240); `medium`).
- **Cost per turn** (token cost × model).

Example SLO from a customer-support assistant: p95 < 2.5s, refusal threshold tracked, cost budget per session ([OptyxStack, LLM Latency Hub](https://optyxstack.com/latency-serving); `medium`).

### Open debates
- Single tool (Langfuse all-in-one) vs decomposed (OTEL + Grafana/Loki + DeepEval) — the all-in-one camp is winning on operational ergonomics; the decomposed camp wins on regulated-industry "no SaaS observability" constraints.
- ClickHouse-acquired Langfuse roadmap risk — open question in 2026.

**Confidence: high** on OTEL convergence, **medium** on specific tool dominance.

---

## Topic 7 — Self-hosted LLM serving (2026 state)

### State of practice (2026)
- **vLLM is the dominant general-purpose serving engine for self-hosted LLM in 2026** — multi-hardware (NVIDIA, AMD, Intel, TPU, AWS Trainium, IBM Spyre, Huawei Ascend), memory-efficient, broad community ([DeployBase, Best LLM Inference Engines 2026](https://deploybase.ai/articles/best-llm-inference-engine); [PyTorch vLLM project](https://pytorch.org/projects/vllm/); `high`).
- **TGI is archived as of March 2026** — repository in maintenance mode, HuggingFace explicitly recommends vLLM, SGLang, llama.cpp instead ([DeployBase 2026](https://deploybase.ai/articles/best-llm-inference-engine); `high`).
- **SGLang** is the right choice when structured output / constrained decoding / agentic prefix reuse dominate; ~29% throughput advantage on 7-8B models on H100 via Radix Attention prefix-reuse; advantage narrows to 3-5% at 70B+ ([VRLA Tech, vLLM vs SGLang 2026](https://vrlatech.com/llm-inference-engine-comparison-2026/); [TECHSY, vLLM vs SGLang 2026](https://techsy.io/en/blog/vllm-vs-sglang); `medium`).
- **llama.cpp** for CPU-only, Apple Silicon, or commodity hardware — the only engine that runs on "nearly anything" ([TensorFoundry, LLM Inference Servers Compared](https://tensorfoundry.io/blog/llm-inference-servers-compared); `medium`).

### vLLM features that matter in 2026
- **Automatic prefix caching** — KV-cache reuse across requests with shared prefixes; reduces prefill time only (not decode) ([vLLM Automatic Prefix Caching docs](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/); `high`).
- **Chunked prefill** — large prefills split into chunks batched with decode requests; trades slight p50 TTFT cost for big p95 win ([vLLM forum discussion](https://discuss.vllm.ai/t/should-vllm-consider-prefix-caching-when-chunked-prefill-is-enabled/903); `medium`).
- **Speculative decoding** — EAGLE 3.1 is the 2026 advanced default; 1.3-2x speedup at ≥0.7 draft acceptance rate ([vLLM EAGLE 3.1 blog 2026-05-26](https://vllm.ai/blog/2026-05-26-eagle-3-1); `high`).
- **Continuous batching, PagedAttention** — on by default.

### Quantization for 16 GB VRAM hardware floor
- **AWQ (INT4)** — "current best-practice INT4 format for vLLM deployment"; Marlin-AWQ kernel combines AWQ quality with highest throughput ([VRLA Tech, LLM Quantization Explained 2026](https://vrlatech.com/llm-quantization-explained-int4-int8-fp8-awq-and-gptq-in-2026/); `medium`).
- **GPTQ (INT4)** — slightly lower quality than AWQ in most benchmarks; still widely used.
- **FP8** — "nearly indistinguishable from BF16 for most tasks", 2x memory reduction, 1.6x throughput; supported on Hopper/Blackwell GPUs in vLLM and TensorRT-LLM ([VRLA Tech 2026](https://vrlatech.com/llm-quantization-explained-int4-int8-fp8-awq-and-gptq-in-2026/); `medium`).
- **Memory fit at 16GB**: 7-8B models comfortably fit at AWQ/FP8 quantization, leaving room for KV cache ([Local AI Master, Quantization Calculator 2026](https://localaimaster.com/tools/quantization-calculator); `medium`).

### Throughput vs latency trade-offs
- **Continuous batching** raises throughput, modestly raises p50 latency.
- **Chunked prefill** raises p50 TTFT slightly, dramatically improves p95 ([vLLM forum](https://discuss.vllm.ai/t/should-vllm-consider-prefix-caching-when-chunked-prefill-is-enabled/903); `medium`).
- **Speculative decoding** wins on decode-bound low-concurrency workloads.

### Open debates
- vLLM "general default" vs SGLang "agentic / structured-output specialist" — both camps are active in 2026; choice driven by workload shape.
- TensorRT-LLM for deliberate NVIDIA-platform commitments only; broader portability lives in vLLM.
- Decision-tree summary: vLLM as shared-endpoint default; SGLang when prefix-reuse / structured-output dominates; TensorRT-LLM when locked into NVIDIA; llama.cpp when no GPU.

**Confidence: high.**

---

## Topic 8 — Two-layer authorization in enterprise RAG

### State of practice (2026)
The "permission-aware retrieval enforced at query time" pattern is the enterprise RAG standard. Multiple platforms document this explicitly:
- **Glean**: "a document the querying user is not authorized to see does not appear in retrieval results, regardless of semantic similarity. That enforcement happens at query time, not at ingestion time." ([Glean perspectives, Best RAG Features](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search); `high`).
- **AWS Q Business**: connector crawls source ACL at ingest; user store optimized for "quick matching during query execution"; ACL + content stored together in the Q Business index ([AWS Q Business connector ACL docs across S3, Box, OneDrive, Slack, GitHub, Zendesk, Jira](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/box-user-management.html); `high`).
- **Microsoft Graph Connectors** / **Azure AI Search**: query-time ACL/RBAC enforcement, document-level access — "canonical patterns" per Microsoft documentation ([Glean 2026 perspectives citing Microsoft docs](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search); `medium`).
- **Vectara**: RAG-as-a-service with permission-aware retrieval; cleanest example of the API-first pattern ([Glean perspectives](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search); `medium`).

### Two-layer authorization architectural pattern
The mature 2026 pattern decomposes authorization into two distinct enforcement points:

**Layer 1 — Pre-filter at retrieval.** The vector store (or hybrid retriever) is given the user's identity / group set as a filter; only chunks the user can access become candidates. This is implemented at:
- pgvector via SQL WHERE clauses joining ACL tables.
- Qdrant via payload filters keyed on group / tenant IDs, with payload indexes built before ingest ([Qdrant Filtering docs](https://qdrant.tech/documentation/search/filtering/); `high`).
- Weaviate / Milvus via metadata filters with tenant isolation.

**Caveat: pre-filter performance.** Qdrant explicitly documents that "pre-filtering should not be used over large datasets as it breaks too many links in the HNSW graph" ([Qdrant Vector Search Filtering Guide](https://qdrant.tech/articles/vector-search-filtering/); `high`). Qdrant's query planner picks pre-filter vs filter-during-traversal vs full-scan based on cardinality. The right pattern is to (a) ensure payload indexes exist on ACL keys before ingest, (b) trust the query planner.

**Layer 2 — PDP re-check at answer assembly.** Before final delivery, query the authoritative source-system policy decision point (ECM PDP) to confirm access still holds. Catches stale-ACL race conditions and revoked-since-ingest cases.

### ACL inheritance — semantics differ by source system
Generic ACL models must accommodate at least:
- **Union** semantics (SharePoint/OneDrive): file's effective ACL = parent folder ACL ∪ file ACL ([AWS OneDrive ACL docs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/onedrive-legacy-acl-crawling.html); `high`).
- **Replace** semantics (Slack DMs/groups/private channels): child ACL completely overrides parent workspace ACL ([AWS Slack ACL docs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-user-management.html); `high`).
- **Public/group-inherited** (GitHub public repos, Slack public channels): everyone in the org / workspace.

A two-layer authorization design must encode the inheritance rule, not just the final ACL value, so re-evaluation at PDP-check time can be done correctly.

### Just-in-time ACL evaluation
The pure JIT pattern queries the source PDP on every retrieval — safest, most expensive, often impractical at LLM latency budgets. The 2026 hybrid:
- Cache ACL with a TTL (minutes to hours depending on regulation).
- Force-invalidate on user-initiated events (logout, role change webhook).
- Post-retrieval PDP re-check on a sampled subset, or on every answer that touches sensitive classifications.

### ACL cache + invalidation
- TTL-based cache is the default; sub-minute TTLs are common in regulated deployments ([AWS Q Business enable/disable ACL crawling safely guide](https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/); `medium`).
- Webhook-driven invalidation on group membership change is the gold standard but requires source-system support.
- Failure mode: ACL cache stale on the same minute a user is removed from a project. Mitigation: PDP re-check at answer assembly, with fail-closed on PDP timeout.

### Failure modes (2026)
- **Stale ACL** — most common; mitigation via PDP re-check.
- **PDP timeout** — fail-closed (refuse with "permission service unavailable") is the senior-architect default in regulated deployments.
- **Filter pushdown bypass** — application code accidentally retrieving without ACL filter. Mitigation: vector store schema requires ACL on every chunk; retrieval API rejects unfiltered queries.
- **ACL drift between ingest and PDP** — source-system ACL changed after ingest but ACL store not refreshed. Mitigation: periodic full re-crawl + diff.
- **Pre-filter on huge filter sets degrades retrieval accuracy** ([Qdrant docs](https://qdrant.tech/articles/vector-search-filtering/); `high`).

### Open debates
- ACL embedded as document metadata (denormalized into vector store) vs ACL in separate authoritative store with join at query — denormalized is faster but stale-prone; separate is consistent but slower. Most 2026 enterprise platforms denormalize with TTL + PDP re-check.
- "Trust the source system PDP at every query" (pure JIT) vs "cache ACL with TTL" — regulated deployments lean JIT; latency-sensitive consumer-grade lean cache. Both are defensible in 2026.

**Confidence: high.**

---

## Topic 9 — Refusal policy / grounding taxonomy / safety patterns

### State of practice (2026)
- Defense-in-depth is "not optional — it is the only viable strategy" ([Maxim, Prompt Injection Defense 2026](https://www.getmaxim.ai/articles/prompt-injection-defense-for-production-ai-agents-a-complete-2026-guide/); `medium`).
- The 2026 mature production stack: **Llama Prompt Guard 2 (86M) as fast first-pass + Llama Guard 3 8B for hazard classification + NeMo Guardrails for orchestration / dialog state / PII redaction** ([Spheron, NeMo Guardrails 2026](https://www.spheron.network/blog/nemo-guardrails-production-deployment-llm-gpu-cloud/); `medium`).
- Prompt injection still ranks #1 on the OWASP LLM Top 10 in 2026; attack volume up 340% in 2026 ([Help Net Security, OWASP 2026](https://www.helpnetsecurity.com/2026/06/11/owasp-prompt-injection-ai-security-failures/); [Kunal Ganglani, Prompt Injection 2026](https://www.kunalganglani.com/blog/prompt-injection-2026-owasp-llm-vulnerability); `medium`).
- Refusal taxonomies in 2026 literature distinguish: complete refusal, partial refusal (competing objectives reflected), no refusal ([arXiv 2603.27518](https://arxiv.org/pdf/2603.27518); `low` — single research paper).

### Mature frameworks / models
- **NeMo Guardrails** (NVIDIA) — orchestration layer; input rails, retrieval rails, output rails; dialog state management ([Spheron 2026](https://www.spheron.network/blog/nemo-guardrails-production-deployment-llm-gpu-cloud/); `medium`).
- **Llama Guard 3 8B** — Meta's hazard classifier; binary safe/unsafe + hazard category labels.
- **Llama Prompt Guard 2 (86M)** — fast jailbreak/prompt-injection gate.
- **Guardrails AI** — output-validation library; mature 2026 option for structured-output enforcement.
- **LlamaFirewall** — open-source guardrail system for agentic AI ([arXiv 2505.03574](https://arxiv.org/pdf/2505.03574); `low`).
- **NLI verifier (DeBERTa-class)** — operationalizes faithfulness/groundedness ([Deepchecks](https://deepchecks.com/rag-evaluation-metrics-answer-relevancy-faithfulness-accuracy/); `high`).

### Layered defense pattern for RAG (2026)
1. **Input rail** — Llama Prompt Guard 2 for jailbreak / prompt-injection detection on user query.
2. **Retrieval rail** — filter / truncate retrieved chunks that match disallowed patterns. "RAG without a retrieval rail is open by default" ([Spheron 2026](https://www.spheron.network/blog/nemo-guardrails-production-deployment-llm-gpu-cloud/); `medium`).
3. **NLI grounding verifier** — atomic claim decomposition + entailment check against retrieved passages.
4. **Output rail** — Llama Guard 3 hazard classification, structured-output validation.
5. **Tool / SSRF rail** (agentic) — tool allowlist, sandboxed execution (containers + gVisor / Firecracker for network-restricted execution), human approval for high-stakes actions ([Maxim 2026](https://www.getmaxim.ai/articles/prompt-injection-defense-for-production-ai-agents-a-complete-2026-guide/); `medium`).

### Refusal patterns — typed vs binary
- **Binary** refuse/answer is the legacy pattern; brittle because all refusals look the same to the user.
- **Typed refusal** — distinct codes for: insufficient_grounding, ACL_denied, out_of_scope, safety_filtered, retrieval_empty, contradiction_detected. Enables differential UX and clearer audit. Aligned with 2026 research taxonomies ([arXiv 2603.27518](https://arxiv.org/pdf/2603.27518); `low`).
- Refusal *rate* is tracked as a quality leading indicator alongside p95 latency in 2026 dashboards.

### Audit fingerprint pattern
2026 compliance-ready audit log entries include ([Medium, Kuldeep Paul, AI Audit Trail](https://medium.com/@kuldeep.paul08/the-ai-audit-trail-how-to-ensure-compliance-and-transparency-with-llm-observability-74fd5f1968ef); [Medium, Vasanthancomrads, AI Audit Logs](https://medium.com/@vasanthancomrads/ai-audit-logs-and-compliance-architecture-b0e1b62772d7); `medium`):
- model_version (provider + name + revision/digest)
- prompt_version (template hash)
- retrieval_index_version
- threshold_set (NLI cutoff, refusal thresholds, rerank cutoff)
- user_id, session_id, tenant_id, ACL fingerprint
- retrieved chunk IDs + scores
- per-claim NLI scores
- refusal_code (typed, if refused)
- input/output tokens, cost

EU AI Act (in force 2026) classifies many enterprise LLM apps as high-risk; logs must enable post-hoc monitoring and be retained ≥ lifetime of system. HIPAA: 6 years. SOX-relevant: 7 ([Didit, AI Compliance LLM 2026](https://didit.me/blog/compliance-in-the-llm-era/); `medium`).

### Open debates
- "Refuse-by-default below confidence threshold" vs "answer with hedged confidence" — regulated industries lean refuse; consumer assistants lean hedge.
- Guardrails-as-product (NeMo / Llama Guard / Guardrails AI / LlamaFirewall stack) vs custom guardrails — the all-stack approach is recommended in 2026 but is expensive in compute and dev time; smaller teams ship with output rail + NLI verifier as the floor.
- LLM-as-judge for refusal appropriateness — calibration drift remains an unsolved problem in 2026.

**Confidence: high** on the layered-defense framing; **medium** on specific tool dominance (NeMo / Llama Guard are leading, not unique).

---

## Open debates senior architects actively disagree on (2026)

These are honest disagreements; do *not* assume a single right answer.

1. **Postgres-only vs Postgres + Redis at MVP.** Genuine senior split. Postgres-only is no longer a junior choice; it's an explicit operational-simplicity bet.
2. **Graph orchestration framework choice — LangGraph vs LlamaIndex Workflows vs Burr.** All viable; choice often stack-aligned rather than principled.
3. **Durable execution layer — wrap LangGraph in Temporal/Inngest, or trust LangGraph checkpointing?** The Temporal camp wins on regulatory durability; the LangGraph-checkpointing camp wins on operational simplicity.
4. **pgvector vs dedicated vector DB.** Real disagreement. pgvector at small scale, dedicated above ~5-10M vectors.
5. **Single-collection multi-tenancy with payload partitions vs collection-per-tenant.** Qdrant's docs say "single collection in most cases" but collection-per-tenant is still used for hard isolation in regulated deployments.
6. **Pre-filter at retrieval vs post-filter (filter-during-traversal).** Qdrant's query planner makes this implementation-detail in most cases, but for ACL the senior architect must understand both.
7. **Semantic chunking vs recursive structure-aware.** 2-3% recall gain at substantial embedding cost — not always worth it.
8. **HyDE / multi-query — universal win or selective.** Selective.
9. **Constrained decoding for citations vs free generation + post-parse.** Constrained gives structural guarantee but can degrade quality on edge cases ("structure snowballing" risk per arXiv 2604.06066).
10. **Streaming-token interception vs claim-level verification.** Streaming is the right abstraction for safety/harmfulness; claim-level is the right abstraction for grounding.
11. **vLLM vs SGLang.** Workload-dependent; both production-grade in 2026.
12. **LLM-as-judge calibration discipline.** Some teams retrain judges quarterly; others rely on weekly human-trace sampling.
13. **ACL JIT-via-PDP vs ACL-cached-with-TTL.** Regulated lean JIT; latency-sensitive lean cache.
14. **Refusal: binary vs typed.** Most senior architects favor typed in 2026; not universal.

---

## Sources index (deduplicated, alphabetised, with confidence tag)

| Source URL | Title | Access date | Used in topic(s) | Confidence |
|---|---|---|---|---|
| https://agentset.ai/rerankers/compare/cohere-rerank-4-fast-vs-baaibge-reranker-v2-m3 | Cohere Rerank 4 Fast vs BAAI/BGE Reranker v2 M3 Comparison | 2026-06-29 | 3 | medium |
| https://aimagicx.com/blog/best-open-source-ai-agent-frameworks-2026 | Best Open-Source AI Agent Frameworks 2026 | 2026-06-29 | 1 | medium |
| https://appscale.blog/en/blog/durable-execution-llm-agents-temporal-langgraph-checkpointing-2026 | Durable Execution for LLM Agents 2026: Temporal + LangGraph | 2026-06-29 | 1 | medium |
| https://arxiv.org/abs/2310.11511 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection (Asai et al., ICLR 2024) | 2026-06-29 | 1, Gap 2 | high (academic) |
| https://arxiv.org/html/2411.13154v1 | DMQR-RAG: Diverse Multi-Query Rewriting for RAG | 2026-06-29 | 3 | medium |
| https://arxiv.org/html/2502.18139v1 | LevelRAG: Multi-hop Logic Planning over Rewriting Augmented Searchers | 2026-06-29 | 3 | low |
| https://arxiv.org/pdf/2401.15884 | Corrective Retrieval Augmented Generation (CRAG, ICLR 2024) | 2026-06-29 | 1, Gap 2 | high (academic) |
| https://arxiv.org/pdf/2410.03461 | Auto-GDA: Automatic Domain Adaptation for Efficient Grounding Verification | 2026-06-29 | 1, 5, 9 | medium |
| https://arxiv.org/pdf/2505.03574 | LlamaFirewall: Open-source guardrail for secure AI agents | 2026-06-29 | 9 | low |
| https://arxiv.org/pdf/2603.02219 | NExT-Guard: Training-Free Streaming Safeguard | 2026-06-29 | Gap 2 | low |
| https://arxiv.org/pdf/2603.27518 | Over-Refusal and Representation Subspaces (refusal taxonomy) | 2026-06-29 | 9 | low |
| https://atlan.com/know/llm-evaluation-frameworks-compared/ | RAGAS, TruLens, DeepEval: LLM Evaluation Frameworks 2026 | 2026-06-29 | 5 | medium |
| https://aws.amazon.com/blogs/machine-learning/enable-or-disable-acl-crawling-safely-in-amazon-q-business/ | AWS — Enable or disable ACL crawling safely in Amazon Q Business | 2026-06-29 | 8 | medium (vendor) |
| https://blog.gopenai.com/the-fidelity-crisis-in-rag-why-late-interaction-colbert-is-the-4k-image-of-search-vs-e978d96b25b8 | The Fidelity Crisis in RAG (ColBERT advocacy) | 2026-06-29 | 3 | low |
| https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/ | RAG Evaluation: Metrics, Frameworks & Testing 2026 | 2026-06-29 | 5 | medium |
| https://blog.squeezebits.com/guided-decoding-performance-vllm-sglang | Guided Decoding Performance on vLLM and SGLang | 2026-06-29 | 1 | medium |
| https://callsphere.ai/blog/vector-database-benchmarks-2026-pgvector-qdrant-weaviate-milvus-lancedb | Vector Database Benchmarks 2026 | 2026-06-29 | 4 | medium |
| https://chatforest.com/reviews/helicone-llm-observability-gateway/ | Helicone Review: LLM Proxy + Observability (Maintenance Mode) | 2026-06-29 | 2, 6 | medium |
| https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089 | Databricks — Chunking Strategies for RAG | 2026-06-29 | 3 | medium |
| https://deepchecks.com/rag-evaluation-metrics-answer-relevancy-faithfulness-accuracy/ | RAG Evaluation Metrics: Answer Relevancy, Faithfulness, Accuracy | 2026-06-29 | 1, 5, 9 | high |
| https://deploybase.ai/articles/best-llm-inference-engine | Best LLM Inference Engines 2026: vLLM vs SGLang vs TGI vs llama.cpp | 2026-06-29 | 7 | medium |
| https://denser.ai/blog/hybrid-search-for-rag/ | Hybrid Search for RAG: BM25 + Dense (2026 Guide) | 2026-06-29 | 3 | medium |
| https://dev.to/polliog/making-redis-optional-why-im-pivoting-to-a-postgres-first-architecture-and-why-chose-valkey-as-4m0i | Making Redis Optional: Postgres-First Architecture | 2026-06-29 | 2 | medium |
| https://didit.me/blog/compliance-in-the-llm-era/ | AI Compliance in the LLM Era: Regulatory Guide 2026 | 2026-06-29 | 9 | medium |
| https://discuss.vllm.ai/t/should-vllm-consider-prefix-caching-when-chunked-prefill-is-enabled/903 | vLLM forum — prefix caching with chunked prefill | 2026-06-29 | 2, 7 | medium |
| https://dl.acm.org/doi/10.1145/3511808.3557325 | PLAID: An Efficient Engine for Late Interaction Retrieval (CIKM 2022) | 2026-06-29 | 3 | high (academic) |
| https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/box-user-management.html | AWS Q Business — Box ACL crawling | 2026-06-29 | 8 | high (vendor docs) |
| https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/onedrive-legacy-acl-crawling.html | AWS Q Business — OneDrive ACL crawling | 2026-06-29 | 8 | high (vendor docs) |
| https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/slack-user-management.html | AWS Q Business — Slack ACL crawling | 2026-06-29 | 8 | high (vendor docs) |
| https://docs.vespa.ai/en/learn/tutorials/hybrid-search.html | Vespa Hybrid Text Search Tutorial | 2026-06-29 | 3, 4 | medium (vendor docs) |
| https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/ | vLLM Automatic Prefix Caching docs | 2026-06-29 | 2, 7 | high (vendor docs) |
| https://docs.vllm.ai/en/latest/features/quantization/ | vLLM Quantization docs | 2026-06-29 | 7 | high (vendor docs) |
| https://explore.n1n.ai/blog/llm-observability-langfuse-langsmith-opentelemetry-2026-05-17 | LLM Observability: Langfuse, LangSmith, OpenTelemetry (May 2026) | 2026-06-29 | 6 | medium |
| https://futureagi.com/glossary/llm-grounding/ | What Is LLM Grounding? FutureAGI Guide 2026 | 2026-06-29 | 9 | medium |
| https://futureagi.com/glossary/nli-evaluation/ | What Is NLI-Based Evaluation? 2026 | 2026-06-29 | 1, 5 | medium |
| https://github.com/langchain-ai/langgraph | LangGraph GitHub repo (32k+ stars May 2026) | 2026-06-29 | 1, Gap 2 | high |
| https://github.com/langfuse/langfuse | Langfuse GitHub repo | 2026-06-29 | 6 | high |
| https://github.com/pgmq/pgmq | pgmq — Postgres Message Queue | 2026-06-29 | 2 | high |
| https://github.com/timgit/pg-boss | pg-boss — Postgres job queue | 2026-06-29 | 2 | high |
| https://innovativeais.com/blog/best-embedding-models-for-rag-in-2026 | Best Embedding Models for RAG in 2026 | 2026-06-29 | 3 | medium |
| https://langfuse.com/blog/2024-07-ai-agent-observability-with-langfuse | AI Agent Observability with Langfuse | 2026-06-29 | 6 | medium (vendor) — pre-2026; check still applies |
| https://langfuse.com/integrations/native/opentelemetry | Langfuse OTEL Integration docs | 2026-06-29 | 6 | high (vendor docs) |
| https://lateinteraction.com/ | Late Interaction Workshop @ ECIR 2026 | 2026-06-29 | 3 | medium |
| https://learnprompting.org/docs/retrieval_augmented_generation/corrective-rag | Corrective RAG explainer | 2026-06-29 | 1 | low |
| https://localaimaster.com/blog/reranking-cross-encoders-guide | Reranking & Cross-Encoders for RAG 2026 | 2026-06-29 | 3 | medium |
| https://localaimaster.com/tools/quantization-calculator | Quantization Calculator: VRAM 2026 | 2026-06-29 | 7 | medium |
| https://medium.com/@kuldeep.paul08/the-ai-audit-trail-how-to-ensure-compliance-and-transparency-with-llm-observability-74fd5f1968ef | The AI Audit Trail | 2026-06-29 | 9 | medium |
| https://medium.com/@mudassar.hakim/retrieval-is-the-bottleneck-hyde-query-expansion-and-multi-query-rag-explained-for-production-c1842bed7f8a | Retrieval Is the Bottleneck: HyDE, Query Expansion, Multi-Query RAG | 2026-06-29 | 3 | medium |
| https://medium.com/@nroan/autoscaling-hid-our-llm-cost-regression-85-4-cache-hit-rate-b4beab5df240 | Autoscaling Hid Our LLM Cost Regression | 2026-06-29 | 6 | medium |
| https://medium.com/@rahularyan786/sglang-structured-generation-language-revolutionizing-efficient-and-controllable-llm-programming-f3438202c673 | SGLang: Structured Generation Language | 2026-06-29 | 1, 7 | medium |
| https://medium.com/@vasanthancomrads/ai-audit-logs-and-compliance-architecture-b0e1b62772d7 | AI Audit Logs and Compliance Architecture | 2026-06-29 | 9 | medium |
| https://medium.com/@vinodkrane/next-generation-agentic-rag-with-langgraph-2026-edition-d1c4c068d2b8 | Next-Generation Agentic RAG with LangGraph (2026 Edition) | 2026-06-29 | 1, Gap 2 | medium |
| https://medium.com/algomart/evaluate-rag-systems-with-ragas-vs-trulens-26a354e573bc | Evaluate RAG Systems with RAGAS vs TruLens | 2026-06-29 | 5 | medium |
| https://medium.com/microsoftazure/10-rag-shifts-redefining-production-ai-in-2026-7acbdd66076c | 10 RAG Shifts Redefining Production AI in 2026 | 2026-06-29 | 3 | medium |
| https://milvus.io/docs/rerankers-bge.md | Milvus BGE Rerankers docs | 2026-06-29 | 3 | medium (vendor docs) |
| https://news.ycombinator.com/item?id=45380699 | HN: Redis is fast – I'll cache in Postgres | 2026-06-29 | 2 | medium |
| https://nhimg.org/complete-guide-to-the-2026-owasp-top-10-risks-for-agentic-applications | OWASP Top 10 Risks for Agentic Applications 2026 | 2026-06-29 | 9 | medium |
| https://optyxstack.com/case-studies/rag-p95-latency-reduction | Cutting P95 Latency in a RAG Pipeline | 2026-06-29 | 6 | medium |
| https://optyxstack.com/latency-serving | LLM Latency & Serving Hub: P95 | 2026-06-29 | 6 | medium |
| https://pgdog.dev/blog/scaling-postgres-listen-notify | Scaling Postgres LISTEN/NOTIFY (PgDog) | 2026-06-29 | 2 | high |
| https://qdrant.tech/articles/multitenancy/ | Qdrant — Multitenancy & Custom Sharding | 2026-06-29 | 4 | high (vendor docs) |
| https://qdrant.tech/articles/vector-search-filtering/ | Qdrant — A Complete Guide to Filtering in Vector Search | 2026-06-29 | 4, 8 | high (vendor docs) |
| https://qdrant.tech/blog/qdrant-1.16.x/ | Qdrant 1.16 — Tiered Multitenancy & Disk-Efficient Vector Search | 2026-06-29 | 4 | high (vendor) |
| https://qdrant.tech/documentation/manage-data/multitenancy/ | Qdrant Multitenancy docs | 2026-06-29 | 4 | high (vendor docs) |
| https://qdrant.tech/documentation/search/filtering/ | Qdrant Filtering docs | 2026-06-29 | 4, 8 | high (vendor docs) |
| https://reactify-solutions.com/articles/langgraph-production-agents-2026 | LangGraph in 2026: building production AI agents as state machines | 2026-06-29 | 1, Gap 2 | medium |
| https://recall.ai/blog/postgres-listen-notify-does-not-scale | Postgres LISTEN/NOTIFY does not scale (Recall.ai post-mortem) | 2026-06-29 | 2 | high |
| https://sitepoint.com/vllm-production-deployment-guide-2026 | vLLM Production Deployment: Complete 2026 Guide | 2026-06-29 | 2, 7 | medium |
| https://spheron.network/blog/ai-agent-workflow-orchestration-temporal-inngest-restate-gpu-cloud/ | AI Agent Workflow Orchestration: Temporal, Inngest, Restate 2026 | 2026-06-29 | 1 | medium |
| https://spheron.network/blog/llm-inference-slo-ttft-itl-latency-budget-guide-2026/ | LLM Inference SLO Engineering: TTFT, ITL, P99 Latency Budgets 2026 | 2026-06-29 | 6 | medium |
| https://spheron.network/blog/llm-serving-optimization-continuous-batching-paged-attention/ | LLM Serving Optimization: Continuous Batching, PagedAttention, Chunked Prefill 2026 | 2026-06-29 | 7 | medium |
| https://spheron.network/blog/nemo-guardrails-production-deployment-llm-gpu-cloud/ | NVIDIA NeMo Guardrails on GPU Cloud (2026 Guide) | 2026-06-29 | 9 | medium |
| https://spheron.network/blog/vllm-production-deployment-2026/ | vLLM Production Deployment 2026: Multi-GPU + FP8 | 2026-06-29 | 7 | medium |
| https://tensorfoundry.io/blog/llm-inference-servers-compared | LLM Inference Servers Compared — vLLM, SGLang, llama.cpp, Ollama | 2026-06-29 | 7 | medium |
| https://testquality.com/llm-regression-testing-pipeline/ | LLM Regression Testing Pipeline 2026: RAG Triad & Gold Sets | 2026-06-29 | 5 | medium |
| https://techsy.io/en/blog/vllm-vs-sglang | vLLM vs SGLang 2026: H100 Benchmarks | 2026-06-29 | 7 | medium |
| https://vllm.ai/blog/2026-05-26-eagle-3-1 | EAGLE 3.1: Advancing Speculative Decoding (vLLM blog May 2026) | 2026-06-29 | 7 | high (vendor blog) |
| https://vrlatech.com/llm-inference-engine-comparison-2026/ | vLLM vs Ollama vs llama.cpp vs SGLang 2026 | 2026-06-29 | 7 | medium |
| https://vrlatech.com/llm-quantization-explained-int4-int8-fp8-awq-and-gptq-in-2026/ | LLM Quantization Explained: INT4, INT8, FP8, AWQ, GPTQ 2026 | 2026-06-29 | 7 | medium |
| https://webscraft.org/blog/embeddingmodeli-dlya-rag-u-2026-yak-obrati-porivnyannya-provayderiv?lang=en | Best Embedding Models for RAG in 2026 | 2026-06-29 | 3 | low |
| https://www.aimagicx.com/blog/prompt-injection-attacks-ai-agent-security-guide-2026 | Prompt Injection Attacks: AI Agent Security 2026 | 2026-06-29 | 9 | medium |
| https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models | Best Open-Source Embedding Models 2026 | 2026-06-29 | 3 | medium |
| https://www.bestaiweb.ai/how-to-build-a-rag-evaluation-harness-with-ragas-deepeval-and-trulens-in-2026/ | Stop RAG Regressions: RAGAS, DeepEval & TruLens | 2026-06-29 | 5 | medium |
| https://www.calibreos.com/learn/genai-rag-evaluation | Production RAG Evaluation: From Golden Sets to LLM-as-Judge at Scale | 2026-06-29 | 5 | medium |
| https://www.confident-ai.com/knowledge-base/compare/top-7-llm-observability-tools | Top 7 LLM Observability Tools 2026 | 2026-06-29 | 6 | medium |
| https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026 | Hybrid Search: BM25, Vector & Reranking 2026 | 2026-06-29 | 3 | medium |
| https://www.digitalapplied.com/blog/llm-guardrails-production-safety-layers-reference-2026 | LLM Guardrails: Production Safety Layers Reference 2026 | 2026-06-29 | 9 | medium |
| https://www.firecrawl.dev/blog/best-chunking-strategies-rag | Best Chunking Strategies for RAG 2026 | 2026-06-29 | 3 | medium |
| https://www.firecrawl.dev/blog/best-open-source-agent-frameworks | Best Open-Source Agent Frameworks 2026 (Firecrawl) | 2026-06-29 | 1 | medium |
| https://www.getmaxim.ai/articles/prompt-injection-defense-for-production-ai-agents-a-complete-2026-guide/ | Prompt Injection Defense for Production AI Agents 2026 | 2026-06-29 | 9 | medium |
| https://www.glean.com/perspectives/best-rag-features-in-enterprise-search | Glean — Best RAG Features in Enterprise Search | 2026-06-29 | 4, 8 | high (vendor; treat as adoption signal) |
| https://www.helpnetsecurity.com/2026/06/11/owasp-prompt-injection-ai-security-failures/ | Prompt injection still drives most agentic AI security failures | 2026-06-29 | 9 | medium |
| https://www.inngest.com/compare-to-temporal | Inngest vs Temporal | 2026-06-29 | 1 | medium (vendor; treat as comparison) |
| https://www.kalviumlabs.ai/blog/vector-databases-compared-pgvector-pinecone-qdrant-weaviate/ | pgvector vs Pinecone vs Qdrant vs Weaviate 2026 | 2026-06-29 | 4 | medium |
| https://www.kunalganglani.com/blog/prompt-injection-2026-owasp-llm-vulnerability | Prompt Injection in 2026: Still OWASP #1 | 2026-06-29 | 9 | medium |
| https://www.langchain.com/resources/ai-agent-frameworks | The best AI agent frameworks in 2026 (LangChain) | 2026-06-29 | 1, Gap 2 | medium (vendor) |
| https://www.llamaindex.ai/blog/announcing-workflows-1-0-a-lightweight-framework-for-agentic-systems | Workflows 1.0: Lightweight Agentic Framework Guide (LlamaIndex) | 2026-06-29 | 1, Gap 2 | high (vendor announcement) |
| https://www.llamaindex.ai/workflows | LlamaIndex Workflows landing | 2026-06-29 | 1 | high (vendor) |
| https://www.machinelearningmastery.com/top-5-reranking-models-to-improve-rag-results/ | Top 5 Reranking Models to Improve RAG Results | 2026-06-29 | 3 | medium |
| https://www.mindstudio.ai/blog/llm-frameworks-replaced-by-agent-sdks | Why LLM Frameworks Are Being Replaced by Agent SDKs | 2026-06-29 | 1 | low |
| https://www.nordync.com/blog/redis-vs-postgresql-caching-2026 | Redis vs PostgreSQL Caching: Which Strategy Wins 2026 | 2026-06-29 | 2 | medium |
| https://www.pingcap.com/compare/best-database-for-ai-agents/ | Best Database for AI Agents 2026 | 2026-06-29 | 2 | medium (vendor) |
| https://www.recall.ai/blog/postgres-listen-notify-does-not-scale | Postgres LISTEN/NOTIFY does not scale | 2026-06-29 | 2 | high |
| https://www.spheron.network/blog/ai-agent-workflow-orchestration-temporal-inngest-restate-gpu-cloud/ | Spheron — AI Agent Workflow Orchestration 2026 | 2026-06-29 | 1 | medium |
| https://zylos.ai/research/2026-03-28-llm-output-streaming-token-delivery-architectures/ | LLM Output Streaming and Real-Time Token Delivery Architectures | 2026-06-29 | Gap 2 | medium |

---

_End of Stage 5 Round 2 benchmark. Total: 9 topics covered, 2 priority gaps addressed in dedicated sections, ~95 unique sources cited. Produced by independent market-intelligence research agent on 2026-06-29._
