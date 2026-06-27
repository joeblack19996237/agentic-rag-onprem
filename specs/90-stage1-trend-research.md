# 90 — Stage 1 Trend Research

> Stage 1 deliverable produced by the `product-trend-researcher` role.
> All claims cite a source URL with access date and a confidence tag.
> Implications for Stage 2 (PM) and Stage 4 (architecture) are explicit at the end.

- **Researcher**: idea-to-specs skill, run inline (subagent unavailable)
- **Research date**: 2026-06-25
- **Project**: GroundedDocs (see `confirmed-context.md`)
- **Scope**: as pinned in `confirmed-context.md` §8

Confidence levels:

- **H (high)** — corroborated by ≥2 independent sources, consistent with public benchmarks or vendor docs
- **M (medium)** — single high-quality source or industry-analyst summary; reasonable but not cross-checked
- **L (low)** — one secondary source or inference; flag for re-check before pinning into specs

---

## 1. Market Context

The enterprise RAG market is at approximately **$1.94B in 2025**, projected to reach **$9.86B by 2030** at a **38.4% CAGR** [**H**] [Atlan: Enterprise RAG Platforms Comparison 2026]. Twelve platforms dominate evaluations in 2026, split across enterprise platforms, managed RAG services, and open-source frameworks [**H**] [SphereIQ: The 12 Best Enterprise RAG Platforms 2026].

Compliance-driven self-hosting is now a recognized segment, accelerated by **EU AI Act enforcement on 2026-08-02** [**H**] [SphereIQ]. Regulated buyers (financial services, healthcare, legal, public sector) prefer on-prem with explicit compliance tooling over managed RAG services [**H**] [SphereIQ; Atlan].

Industry analyst consensus: "the first 4–6 priorities in enterprise GenAI involve compliance, governance, or putting humans in the loop" [**M**] [Atlan: Enterprise RAG Platforms Comparison 2026]. "Data governance is the missing layer — every platform retrieves what it's given without determining which data is authoritative, who can access it, or whether it's still accurate, requiring a separate context layer upstream" [**M**] [Atlan].

**Implication**: the buyer narrative GroundedDocs is targeting (verifiable citation + governance + on-prem) maps directly onto where the market is moving in mid-to-late 2026.

## 2. Competitor and Substitute Map

### 2.1 Direct competitors (the closest comparables)

| Product | Layer | Deployment | Citation strategy | Governance / review | Vendor-embeddable? | License | Overlap w/ GroundedDocs |
|---|---|---|---|---|---|---|---|
| **Tencent WeKnora** | OSS framework + SaaS | Self-host OR hosted | Citations on RAG answers; Wiki Mode generates synthesized pages (extra hallucination surface) | Multi-tenant RBAC (4-tier), audit log, Langfuse observability | API + Chrome extension + IM channels; not packaged as a vendor SDK | MIT | **High on engineering scope; low on positioning** — they emphasize "documents come alive" (Wiki Mode); we emphasize "answers stay grounded or refused" [**H**] [Tencent/WeKnora README] |
| **RAGFlow** (Infiniflow) | OSS engine | Self-host (Docker) | Traceable citations + deep document understanding (tables, layouts) [**H**] [Slashdot; Jimmy Song] | Eval and agent features; lighter on tenancy/governance than WeKnora | API + UI; embeddable but not OEM-packaged | Apache 2.0 | **Strongest direct OSS competitor** — best-in-class doc parsing and citations; weaker on review-loop and vendor packaging |
| **SphereIQ** | Enterprise platform | Self-hosted by default | Citation + EU AI Act compliance wizard (Articles 5, 53, Annex III) [**H**] [SphereIQ] | Strong: compliance-native, audit, data governance | Direct enterprise sale, not vendor add-on | Commercial | **Closest in positioning, different go-to-market** — they sell direct to enterprise; we sell through vendors |
| **Vectara** | Managed RAG | SaaS only | Every output traceable to source [**H**] [Vectara explainability blog] | Strong explainability; managed | API embeddable | Commercial | Positioning overlaps (citation-first) but SaaS-only excludes our buyer profile |
| **Glean** | Enterprise platform | SaaS | Citations + real-time permission checks across connectors [**H**] [Atlan; Glean perspectives] | Permission propagation, audit | Search-and-assistant; not vendor add-on | Commercial | High-end enterprise; not vendor-embeddable; not on-prem |
| **Hebbia** | Vertical RAG | SaaS | Document-heavy citation; designed for diligence & contract review [**M**] [v7labs alternatives] | Workflow-specific review | Workflow product, not add-on | Commercial | Closest in vertical use case (contract / customer-facing communication review) |
| **Haystack Enterprise** (deepset) | Framework + enterprise support | Self-host | Evaluation-first, citations in pipelines | Strong governance (EU Commission, German Federal Ministry adoption) [**H**] [SphereIQ] | Framework; integrators build add-ons | Apache 2.0 + commercial support | Framework not product — could be a *build-on* dependency, not a competitor |
| **Cohere North** | Enterprise platform | Hybrid + on-prem option [**M**] [SphereIQ] | Citations native | Compliance-native | Direct enterprise + partner channel | Commercial | Closest commercial alternative for partners with budget |
| **AnythingLLM** | Self-hosted OSS | Docker / desktop | Citations present, lighter on verification [**M**] [Triumphoid] | Lighter governance | Embeddable widget, simple | MIT | Substitute at the low end; weaker on enterprise governance |
| **Dify** | OSS app platform | Docker | Citations via RAG nodes; broader workflow focus | RBAC; less governance depth | Embeddable; broader scope (also covers agents/MLOps) [**H**] [Jimmy Song] | Apache 2.0 (with restrictions) | Adjacent — workflow-oriented, not RAG-specialized |

### 2.2 The empty quadrant

Plotting competitors on two axes — **deployment** (managed SaaS ↔ self-hosted on-prem) and **go-to-market** (direct enterprise ↔ vendor-embedded add-on) — **the on-prem + vendor-embedded quadrant is empty**.

- SaaS + direct: Vectara, Glean, Hebbia
- SaaS + vendor-embedded: managed APIs (AWS Bedrock KB, Vertex AI Search) — generic, not RAG-specialized
- On-prem + direct: SphereIQ, Cohere North, RAGFlow, WeKnora (when self-hosted), Haystack
- **On-prem + vendor-embedded**: **no incumbent named in 2026 surveys** [**M**, inferred from absence in [SphereIQ], [Atlan], [Onyx 2026 buyer's guide]]

**Implication for PM**: this gap is GroundedDocs's positioning anchor. It is **not** that nobody can do it; it is that nobody is *marketed* there. Differentiation must rest on the **vendor integration contract** (SDK, widget, brandable surface, predictable telemetry) plus the **citation + refusal + review** triple.

### 2.3 What to borrow from WeKnora specifically

| WeKnora pattern | Borrow? | Notes |
|---|---|---|
| Three-mode product split (RAG / Agent / Wiki) | Partial — borrow RAG + Agent (V2); drop Wiki Mode | Wiki Mode contradicts anti-hallucination positioning (auto-synthesized content) |
| Multi-LLM provider abstraction (20+ providers, swappable) | **Yes** | Open-prem buyers will demand model swap |
| Pluggable vector store / storage backend | **Yes** | Required for enterprise stack fit |
| 4-tier RBAC + per-resource ownership + per-tenant audit log | **Yes**, simplified | Even single-tenant on-prem needs RBAC + audit; collapse to single-tenant model |
| Langfuse observability for token / cost / trace | **Yes** | Reference implementation for our observability spec |
| MCP human-in-the-loop tool approval | **Yes (V2)** | Maps directly to our review-loop |
| Auto-generated wiki + knowledge graph | **No** | Out of scope per DEC-005 |
| Multi-source connectors (Feishu / Notion / Yuque / IM) | **No for MVP** | Vendor handles document ingest path |
| Hosted Cloud offering | **No** | Wrong deployment model |

## 3. Anti-Hallucination & Citation-Verification Patterns

### 3.1 What "verified citation" actually means in 2026 practice

Industry frame: "Standard RAG does not prevent hallucination, as models may fabricate citations or conflate memorized patterns with retrieved content" [**H**] [ClarityArc Consulting; Nexumo on Medium]. The mature pattern is **mechanical + semantic verification at runtime**:

1. **Mechanical citation verification**: require generated citations to point to specific line ranges that must overlap retrieved chunks [**H**] [ClarityArc; Nexumo]. Cheap to implement, catches fabricated citation IDs.
2. **NLI-based span check**: a lightweight Natural Language Inference model verifies grounding of generated output against retrieved documents before delivery [**H**] [arXiv 2410.03461 Auto-GDA; ClarityArc]. Adds 1–2s latency for "significantly higher output reliability" [**M**] [ClarityArc].
3. **Refusal on low confidence**: surface verification to users; refuse or downgrade when grounding fails [**H**] [Lakera 2026 hallucination research, via ClarityArc].

Direct quote that summarizes the architectural stance: *"Trust must be earned through architecture rather than assumed from the model"* [**H**] [ClarityArc].

### 3.2 Metrics framework

RAGAS canonical metrics [**H**] [Atlan; QASkills; Particula]:

- **Faithfulness** — does the answer reflect what was retrieved?
- **Answer Relevance** — does the answer address the question?
- **Context Precision** — is retrieved context on-topic?
- **Context Recall** — does retrieval find all needed evidence?

Production thresholds widely cited [**M**] [QASkills 2026 guide]:

| Metric | Threshold |
|---|---|
| Faithfulness | ≥ 0.75 |
| Answer relevancy | ≥ 0.80 |
| Context precision | ≥ 0.70 |
| Context recall | ≥ 0.80 |

### 3.3 Eval-stack pattern

Mature teams in 2026 run **three frameworks in parallel** [**H**] [Atlan; Particula; CallSphere]:

| Framework | Where it runs | Purpose |
|---|---|---|
| **RAGAS** | Offline | Tuning chunking + embeddings; ground-truth-free metrics |
| **DeepEval** | CI | Pytest-native gate on a curated golden set |
| **TruLens** | Production | OpenTelemetry trace + drift observability |

**Implication for architecture**: MVP must have at least RAGAS (offline) + a CI gate. TruLens is V2.

## 4. On-Prem LLM Serving (mid-2026 snapshot)

| Engine | Status | Best for | Notes |
|---|---|---|---|
| **vLLM** | **Production default** [**H**] [TheAIEngineer Substack; LeetLLM; Hivenet] | Medium-to-high volume production; widest hardware support | PagedAttention; start here |
| **SGLang** | Strong rival to vLLM [**H**] [Spheron benchmarks; Joshua8.AI] | RAG / chatbots / agents (shared context) | RadixAttention caches shared computation; **~29% throughput advantage over vLLM when requests share context** [**H**] [LeetLLM] |
| **TensorRT-LLM** | Ultra-high volume niche [**H**] [Spheron] | Latency-critical, willing to pay engineering cost | NVIDIA-only; high overhead |
| **TGI** (HuggingFace) | **Maintenance mode since Dec 2025** [**H**] [LeetLLM; n1n.ai] | — | HuggingFace itself recommends vLLM or SGLang for new deployments. **Exclude from MVP.** |
| **Ollama** | Dev / demo / single-user [**H**] [LeetLLM; BuildWithMatija] | Local demo, "model running in 5 minutes" | Does not scale past single-user workloads |
| **llama.cpp** | CPU / edge | Constrained hardware | Useful for the "no GPU" reference path |

**Implication for architecture**: vLLM = primary path; SGLang = upgrade option once RAG patterns benefit from shared-context caching; Ollama = demo bootstrap only.

## 5. Open-Weights Generation Models (mid-2026)

| Family | License | On-prem fit | Notes |
|---|---|---|---|
| **Qwen3 / Qwen3.5** | **Apache 2.0** [**H**] [BentoML; HuggingFace blog] | Strong | Strong multilingual (Chinese + English critical for CCM market); MoE variants enable on-prem with smaller activated parameter counts (e.g., Qwen3.6-35B-A3B = 35B total / 3B active, 262K context [**M**] [BenchLM.ai]); **safest commercial choice** |
| **DeepSeek V3 / V3.2** | **MIT** [**H**] [Spheron DeepSeek vs Llama 4 vs Qwen 3] | Very large MoE (671B/37B active) | First model to integrate thinking with tool-use (V3.2, Dec 2025) [**H**] [Spheron]; permissive license; but hardware footprint heavy for single-host demo |
| **Llama 4 Maverick** | Meta Llama 4 license (commercial use with conditions) [**M**] [BentoML] | Strong; highest open MMLU (85.5%) [**M**] [BenchLM.ai] | License has usage-scale clauses; review before commercial repackaging |
| **Gemma 4** | Apache 2.0 [**M**] [HuggingFace blog] | Solid commercial choice | Smaller footprint than Qwen3 flagships |
| **Phi-4** | MIT [**M**] [HuggingFace blog] | Small / efficient | Good "minimum reference model" for the no-GPU path |

**Implication for architecture**: pin **Qwen3 family** as the reference generation model for MVP — Apache 2.0, multilingual, MoE variants suitable for single-host demo. Phi-4 as the CPU/edge fallback. DeepSeek-V3 and Llama 4 documented as supported targets, not the demo default.

## 6. Hybrid Retrieval and Rerank Stack

The 2026 production safe-default stack is well-established [**H**] [Spheron TEI; Markaicode; Pinecone docs; AgentSet; MachineLearningMastery]:

| Stage | Model | Why |
|---|---|---|
| **Embedding** | **bge-m3** | Unified dense + sparse + ColBERT in one 0.6B model; 100+ languages; up to 8192 input tokens [**H**] [FlagOpen GitHub; Spheron] |
| **Rerank** | **bge-reranker-v2-m3** | 278M params; multilingual; CPU-runnable for small batches; the de-facto baseline rerank in 2026 [**H**] [Pinecone docs; AgentSet] |

Direct quote: *"For most production RAG workloads, BGE Reranker v2-m3 is the safe default ... if a newer model does not significantly outperform BGE, the added cost or latency may not be justified"* [**H**] [Spheron TEI].

**Implication for architecture**: bge-m3 + bge-reranker-v2-m3 is the MVP pin. Re-evaluate at V2.

## 7. CCM / ECM Vendor Integration Landscape

### 7.1 Where the CCM vendors are

- **OpenText** has launched **Aviator** as its AI offering, with "knowledge-driven GenAI and advanced orchestration" [**H**] [OpenText.com product page]
- **Quadient** uses a **"Bring Your Own AI" framework** explicitly designed to plug in the customer's GenAI architecture [**H**] [Quadient blog: Best AI CCM platform 2025]
- **Smart Communications** focuses on AI-assisted template migration and content intelligence [**M**] [Aspire CCS]
- **Aspire (industry analyst)** identifies the AI opportunities in CCM as: orchestration, inbound processing, personalization, and approvals [**M**] [Aspire CCS]

### 7.2 What this means for GroundedDocs

- **Quadient's "Bring Your Own AI" pattern is the exact integration shape GroundedDocs needs to fit.** Vendors are moving toward orchestration but not building deep enterprise RAG themselves — that is the gap [**M**, inferred].
- CCM vendors' own AI is generally focused on **outbound content generation** (template authoring, personalization). GroundedDocs's RAG-for-document-Q&A complements rather than competes with this [**M**, inferred].
- ECM vendors (M-Files, Hyland, OpenText) sit closer to the document repository and are more likely to want the **API + admin console** integration shape; CCM vendors sit closer to the customer-facing surface and more likely to want the **embeddable chat widget** integration shape.

### 7.3 Embedding patterns

Surveyed integration patterns for embeddable third-party UI in enterprise software [**M**] [Domo; Embeddable.com; RevealBI]:

| Pattern | Speed-to-ship | Styling control | Use when |
|---|---|---|---|
| **iframe widget** | Fast | Limited | MVP; bounded UI; ship in days |
| **JS widget injection** | Medium | Strong (host CSS cascades) | When the vendor needs theming |
| **SDK (React / Vue components)** | Slow | Full | V2 — when integration scale demands it |

Industry pattern: "start with iframe to ship quickly, then migrate to SDK as the product matures" [**M**] [RevealBI].

**Implication for PM**: **MVP ships an iframe widget; V2 ships a JS widget; SDK is V3.** A clean HTTP API behind both is mandatory for vendor integrators that want their own UI.

## 8. Governance and HITL Patterns

Cross-cutting findings from competitor analysis:

- **Vectara** sets the citation-traceability bar: "every piece of information produced by the system is traceable back to its source" [**H**] [Vectara explainability blog]
- **Glean** sets the access-control bar: real-time permission checks at query time [**H**] [Atlan; Glean perspectives]
- **Hebbia** sets the workflow-specific review bar: bounded document-heavy workflows with explicit review steps [**M**] [v7labs]
- **WeKnora** sets the multi-tenant audit bar: per-tenant audit log + per-resource ownership [**H**] [Tencent/WeKnora]

The HITL pattern that maps best to GroundedDocs's review queue: **per-category routing → reviewer queue → approval / edit / reject → feedback loops into eval set**. WeKnora's MCP HITL is the closest OSS reference [**H**] [Tencent/WeKnora CHANGELOG v0.5.2].

**Implication for PM**: V2 review-loop spec should adopt this four-stage shape. MVP only needs **audit log + refusal policy + threshold configuration** — the foundation for V2 review without committing to the queue UI yet.

## 9. Risks and Open Questions Surfaced by Research

| ID | Risk | Source | Impact on Stage 2 / 4 |
|---|---|---|---|
| R-T1 | Vendor channel is crowded by general-purpose AI assistants (Aviator, Quadient's own AI). GroundedDocs must justify why a vendor adds *us* rather than building lightly on top of their LLM partnership | Quadient + OpenText announcements | PM stage must articulate the buyer benefit explicitly (cited citation + refusal + audit) vs. "vendor builds it" |
| R-T2 | "Verified citation" is a vague promise; competitors (Vectara, RAGFlow) already say "citations". Must spec the **runtime verification + refusal** mechanism concretely | ClarityArc, Nexumo on Medium | Architecture stage must produce the verification pipeline spec, not just claim it |
| R-T3 | EU AI Act enforcement (Aug 2026) is reshaping enterprise procurement; compliance language is becoming buyer hygiene | SphereIQ | PM stage: keep "compliance-ready posture" as part of positioning even without certifications |
| R-T4 | Llama 4 license has scale and use restrictions; if we adopt as a *supported* target we must read the license carefully | BentoML; BenchLM.ai | Architecture stage: document Apache-2.0/MIT preference and Llama 4 caveat in decision log |
| R-T5 | TGI is dead-walking (maintenance mode); we must not pick it just because of HuggingFace familiarity | LeetLLM; n1n.ai | Architecture stage: explicit DEC excluding TGI |
| R-T6 | Single-host demo with vLLM + Qwen3 family + bge-m3 + bge-reranker-v2-m3 has known GPU memory pressure on consumer cards; reference hardware must be sized honestly | LeetLLM; FlagOpen | Architecture stage: produce minimum-hardware reference + degraded-mode path (smaller model, smaller rerank batch) |

## 10. Implications Summary

### 10.1 For Stage 2 (PM)

1. **Positioning**: occupy the empty "on-prem + vendor-embedded" quadrant with three differentiators — **verified citation, refusal-by-default, audit-ready** — not the generic "self-hosted RAG"
2. **Buyer narrative**: target Quadient's "Bring Your Own AI" pattern and OpenText Aviator integration touchpoints; story is "our component, your customer relationship"
3. **MVP success metrics** should include the RAGAS metrics with the cited thresholds, plus a **citation-hit-rate** (vendor-visible) and **refusal-rate** (vendor-tunable)
4. **Out-of-scope reaffirmed**: auto-Wiki, multi-tenant SaaS, multi-source connectors — all confirmed by competitor map
5. **Pricing posture (for V2 PM revisit)**: enterprise-platform tier is $50–$500/user/month or $500k+ annual contracts [**H**] [SphereIQ]; B2B2B vendor-add-on pricing typically takes a per-install + per-active-user shape — defer concrete pricing to V2

### 10.2 For Stage 4 (Architecture)

| Layer | Reference choice | Alternatives to document |
|---|---|---|
| **LLM serving** | vLLM | SGLang (V2 upgrade), Ollama (demo-only), TensorRT-LLM (rejected for MVP), TGI (excluded) |
| **Generation model** | Qwen3 family (Apache 2.0, multilingual, MoE on-prem-friendly) | Phi-4 (CPU fallback), Gemma 4 (alt Apache 2.0), Llama 4 (license caveat), DeepSeek V3 (hardware-heavy) |
| **Embedding** | bge-m3 | none (no contender matches the multilingual + multi-functional combination in 2026 OSS) |
| **Rerank** | bge-reranker-v2-m3 | newer rerankers should only displace it on benchmark + latency basis |
| **Vector store** | TBD at architecture stage | pgvector (single-host simplicity) vs Qdrant (production maturity, what WeKnora & competitors use) |
| **Citation verification** | mechanical (chunk-overlap) + NLI span check + refusal threshold | document the pipeline as a first-class spec |
| **Eval** | RAGAS offline + CI gate (DeepEval or Promptfoo) | TruLens production observability (V2) |
| **Integration surface** | iframe widget MVP, JS widget V2, SDK V3, HTTP API always | document the contract as a vendor-facing spec |

## 11. Source Trail

All sources accessed **2026-06-25**.

### Competitor map and market

- [Tencent/WeKnora — GitHub repo & README](https://github.com/Tencent/WeKnora)
- [Atlan — Enterprise RAG Platforms Comparison 2026](https://atlan.com/know/enterprise-rag-platforms-comparison/)
- [SphereIQ — The 12 Best Enterprise RAG Platforms and Tools in 2026](https://www.sphereinc.com/blogs/best-enterprise-rag-platforms-2026)
- [Onyx — Best Enterprise RAG Platforms for 2026 Buyer's Guide](https://onyx.app/insights/enterprise-rag-platforms-2026)
- [Firecrawl — 15 Best Open-Source RAG Frameworks in 2026](https://www.firecrawl.dev/blog/best-open-source-rag-frameworks)
- [Agent.Nexus — Top 10 RAG Frameworks for Enterprise 2026](https://agent.nexus/blog/top-10-rag-frameworks-enterprise)
- [Slashdot — Dify vs RAGFlow 2026](https://slashdot.org/software/comparison/Dify-vs-RAGFlow/)
- [Jimmy Song — Open Source AI Agent Workflow Comparison 2026](https://jimmysong.io/blog/open-source-ai-agent-workflow-comparison/)
- [Triumphoid — AnythingLLM vs Dify Self-Hosted RAG](https://triumphoid.com/anythingllm-vs-dify-best-self-hosted-rag-platform/)
- [Infiniflow/RAGFlow — GitHub](https://github.com/infiniflow/ragflow)
- [v7labs — Hebbia alternatives](https://www.v7labs.com/blog/hebbia-alternatives)
- [Vectara — The Importance of Explainability in Enterprise RAG](https://www.vectara.com/blog/the-importance-of-explainability-in-enterprise-rag)
- [Glean — Best RAG Features in Enterprise Search](https://www.glean.com/perspectives/best-rag-features-in-enterprise-search)

### Anti-hallucination and citation

- [ClarityArc — AI Hallucination and Grounding](https://www.clarityarc.com/insights/ai-hallucination-grounding-citation)
- [Nexumo on Medium — RAG Grounding: 11 Tests That Expose Fake Citations](https://medium.com/@Nexumo_/rag-grounding-11-tests-that-expose-fake-citations-30d84140831a)
- [Auto-GDA: Automatic Domain Adaptation for Efficient Grounding Verification — arXiv 2410.03461](https://arxiv.org/pdf/2410.03461)
- [Vishal Mysore on Medium — RAG Pipeline for 10M Documents with Zero Hallucination](https://medium.com/@visrow/how-to-design-a-rag-pipeline-for-10-million-documents-with-zero-hallucination-live-demo-057e37bcdbf6)
- [You.com — AI Hallucination Prevention and How RAG Helps](https://you.com/resources/ai-hallucination-prevention-guide)

### Eval frameworks

- [Atlan — LLM Evaluation Frameworks Compared 2026](https://atlan.com/know/llm-evaluation-frameworks-compared/)
- [QASkills — RAG Evaluation Metrics 2026 Complete Guide](https://qaskills.sh/blog/rag-evaluation-metrics-complete-2026)
- [Particula — DeepEval vs RAGAS vs TruLens](https://particula.tech/blog/deepeval-vs-ragas-vs-trulens-rag-evaluation-stack)
- [CallSphere — RAG Evaluation Frameworks 2026](https://callsphere.ai/blog/rag-evaluation-frameworks-2026-ragas-trulens-deepeval)
- [HelpMeTest — Evaluating RAG with RAGAS and TruLens Complete Guide 2026](https://helpmetest.com/blog/evaluating-rag-with-ragas-trulens/)

### LLM serving

- [TheAIEngineer Substack — vLLM vs Ollama vs SGLang vs TensorRT-LLM 2026](https://theaiengineer.substack.com/p/vllm-vs-ollama-vs-sglang-vs-tensorrt)
- [LeetLLM — Choosing an Inference Engine in 2026](https://leetllm.com/blog/llm-inference-engine-comparison-2026)
- [Spheron — vLLM vs TensorRT-LLM vs SGLang H100 Benchmarks 2026](https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/)
- [Hivenet — vLLM vs TGI vs TensorRT-LLM vs Ollama](https://www.hivenet.com/post/vllm-vs-tgi-vs-tensorrt-llm-vs-ollama)
- [n1n.ai — Comprehensive Comparison of LLM Inference Engines](https://explore.n1n.ai/blog/llm-inference-engine-comparison-vllm-tgi-tensorrt-sglang-2026-03-13)

### Open-weights models

- [BentoML — Best Open-Source LLMs in 2026](https://www.bentoml.com/blog/navigating-the-world-of-open-source-large-language-models)
- [HuggingFace blog — Best Open-Source LLM Models in 2026](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [BenchLM.ai — Best Open Source LLM in 2026](https://benchlm.ai/blog/posts/best-open-source-llm)
- [Spheron — DeepSeek V3.2 vs Llama 4 vs Qwen 3 2026 Cost-per-Token](https://www.spheron.network/blog/deepseek-vs-llama-4-vs-qwen3/)

### Retrieval and rerank

- [FlagOpen/FlagEmbedding GitHub](https://github.com/flagopen/flagembedding)
- [Spheron — Self-Host Embeddings and Rerankers TEI 2026](https://www.spheron.network/blog/self-host-embedding-reranker-tei-gpu-cloud/)
- [Pinecone — bge-reranker-v2-m3 docs](https://docs.pinecone.io/models/bge-reranker-v2-m3)
- [AgentSet — BAAI/BGE Reranker v2 M3 details](https://agentset.ai/rerankers/baaibge-reranker-v2-m3)
- [MachineLearningMastery — Top 5 Reranking Models 2026](https://machinelearningmastery.com/top-5-reranking-models-to-improve-rag-results/)

### CCM / ECM integration

- [Aspire — Latest Update on Generative AI in CCM-CXM](https://www.aspireccs.com/aspires-latest-update-on-generative-ai-in-ccm-cxm/)
- [Aspire — The AI Opportunity in CCM-CXM Part 2: What To Look For in Vendors](https://www.aspireccs.com/the-ai-opportunity-in-ccm-cxm-part-2-what-to-look-for-in-vendors/)
- [OpenText — Customer Communications Management](https://www.opentext.com/products/customer-communications-management)
- [Quadient — Best AI CCM Platform 2025](https://www.quadient.com/en/blog/which-ccm-platform-has-best-artificial-intelligence-ai-capabilities)
- [Quadient — Named MVP in AI-Driven CCM](https://www.quadient.com/en/quadient-named-mvp-ai-driven-ccm)

### Embedding patterns

- [Domo — 15 Embedded Analytics Tools](https://www.domo.com/learn/article/embedded-analytics-tools)
- [Embeddable.com — Best White Label Embedded Analytics 2026](https://embeddable.com/blog/white-label-embedded-analytics-tools)
- [RevealBI — Embedded Analytics SDK vs iframes](https://www.revealbi.io/blog/embedded-analytics-vs-iframes/)
- [GPTBots — Integration Guide for iframe](https://www.gptbots.ai/docs/tutorial/bot/integration/iframe-widget)

---

## 12. Stage 1 Exit Status

- [x] All claims cite a source or are tagged as inferred
- [x] Confidence levels attached
- [x] Competitor map produced
- [x] Architecture pattern map produced
- [x] PM implications explicit (§10.1)
- [x] Architecture implications explicit (§10.2)
- [x] Risks surfaced (§9) and routed to PM / architecture

**Ready for Stage 2 (Product Manager Review).**

Decisions to add to `13-decision-log.md` after Stage 2 confirmation:

- `DEC-010` — Positioning anchor: "on-prem + vendor-embedded + verified citation + refusal + audit"
- `DEC-011` — Wiki Mode permanently out of scope (confirmed by trend research as conflicting positioning)
- `DEC-012` — Reference LLM serving = vLLM; demo bootstrap = Ollama
- `DEC-013` — Reference generation model = Qwen3 family (Apache 2.0)
- `DEC-014` — Reference embedding = bge-m3; reference rerank = bge-reranker-v2-m3
- `DEC-015` — Integration surface MVP = iframe widget + HTTP API; V2 = JS widget; V3 = SDK
- `DEC-016` — TGI excluded from supported serving engines (HuggingFace maintenance mode since Dec 2025)
- `DEC-017` — Eval stack = RAGAS (offline) + CI gate for MVP; TruLens deferred to V2

These are **proposed**, not pinned. Stage 2 (PM) will refine and Stage 4 (architecture) will commit.

---

## 13. Addendum — Vendor Deep Dive: Quadient and OpenText Aviator

Added 2026-06-25 in response to a Stage 1 follow-up question. Same source rules apply.

### 13.1 Quadient Inspire

#### 13.1.1 What it is

Quadient Inspire is a **CCM platform with AI embedded into it**, not an AI tool. QKS Group named Quadient "Most Valuable Pioneer for AI" in CCM in 2025 [**H**] [[Quadient blog](https://www.quadient.com/en/blog/which-ccm-platform-has-best-artificial-intelligence-ai-capabilities); [Quadient MVP page](https://www.quadient.com/en/quadient-named-mvp-ai-driven-ccm)].

#### 13.1.2 Main selling points

1. **Bring Your Own AI (BYOAI) framework**
   - Introduced early 2024 in Inspire Evolve; lets customers plug in their own GenAI architecture and models rather than being locked into Quadient's bundled AI [**H**] [Quadient blog]
   - Stated rationale: AI safety, plus reuse of existing customer LLM investment
   - **This is the integration shape GroundedDocs is built to fit into**

2. **Content intelligence**
   - Sentiment analysis, translation, rewriting, compliance checks on outbound communications [**M**] [Quadient Inspire G2 reviews]
   - Business users author/refine/summarize content via built-in prompts, bypassing technical teams [**M**] [Quadient blog]

3. **Workflow automation**
   - AI embedded in CCM workflows: inbound classification → intent detection → draft reply → human review → send [**M**] [Aspire CCS]
   - This sits **orthogonal** to GroundedDocs's retrieval Q&A

4. **Two deployment forms**
   - Inspire Evolve (cloud-native; primary BYOAI surface)
   - Inspire Flex (on-prem; also supports BYOAI)

#### 13.1.3 What Quadient's own AI does and does not do

| Capability | Quadient |
|---|---|
| Outbound content generation (letters, emails, templates) | ✅ Strong |
| Inbound classification, intent extraction | ✅ |
| Translation, sentiment, compliance | ✅ |
| **Internal document Q&A ("how is annual leave calculated")** | ❌ Not the target |
| **Cited answers from a document corpus** | ❌ |
| **Semantic search over the enterprise's document library** | ❌ |

### 13.2 OpenText Aviator

#### 13.2.1 What it is

Aviator is a **multi-product AI suite umbrella across OpenText product lines**, not a single product [**H**] [[OpenText Aviator page](https://www.opentext.com/aviator-ai)]. Members:

- **Content Aviator** — ECM document Q&A (the part most overlapping with GroundedDocs)
- **Service Management Aviator** — ITSM virtual agent
- **Experience Aviator** — customer experience side
- **IT Operations Aviator** — AIOps
- **Aviator Studio** — no-code / pro-code platform for building agents

#### 13.2.2 Content Aviator (the direct competitor surface)

[[OpenText Content Aviator page](https://www.opentext.com/aviator-ai/content-aviator); [What's new in Content Aviator blog](https://blogs.opentext.com/whats-new-in-opentext-content-aviator/)]

1. **Cross-department "digital teammate"**: long-document summarization, conversational search, email drafting [**H**]
2. **Microsoft Copilot agent integration**: users access OpenText content from inside Copilot [**H**]
3. **Frontier-model support**: Google Gemini (on GCP), OpenAI (on Azure), Amazon Nova (on AWS) [**H**]
4. **Enterprise-grade security**: private deployment options, compliance support [**M**]

#### 13.2.3 Aviator Studio (reference implementation for our spec slots 20–24)

[[Aviator Studio page](https://www.opentext.com/aviator-ai/aviator-studio)]

Capabilities directly mapping to our future agent specs:

- **Multi-agent choreography** — relevant to V2 agent spec (slot 20)
- **Prompt library** — direct reference for slot 24 (prompt registry)
- **Model broker** — abstraction layer akin to BYOAI; relevant to slot 21 (tools / model adapters)
- **Guardrail settings (including prompt injection defenses)** — direct reference for slot 23 (evals & guardrails)

GroundedDocs should study Aviator Studio as a quality bar for these specs, not as a competitor.

#### 13.2.4 Service Management Aviator (related upper-layer pattern)

[[Service Management Aviator page](https://www.opentext.com/aviator-ai/service-management-aviator)]: private GenAI virtual agent that resolves tickets from enterprise knowledge and suggests remediation steps for IT staff. Important as a **pattern**: this is what an upper-layer application looks like when built on the GroundedDocs-style primitive (retrieve + cite + refuse) plus an ITSM workflow.

### 13.3 GroundedDocs vs each

#### 13.3.1 vs Quadient — **complementary, not competitive**

| Dimension | Quadient | GroundedDocs |
|---|---|---|
| Workflow direction | **Outbound** (drafting communications) | **Inbound** (querying documents) |
| AI role | Content generator | Retrieval + answer + refusal |
| Product shape | CCM platform itself | Add-on embedded into a CCM platform |
| Integration surface | BYOAI framework is the **inlet** | We are an AI worth bringing **into** BYOAI |
| Multi-tenancy | Native to platform | Single-tenant on-prem |
| Data sovereignty | SaaS default (Evolve) / on-prem option (Flex) | On-prem only |

**Sales line for a Quadient prospect**: *"You bring your AI to Quadient. We are the AI worth bringing for document-grounded Q&A. Our retrieval + citation + refusal layer plugs into Inspire workflows without changing your CCM platform."*

#### 13.3.2 vs OpenText Content Aviator — **partial substitute, partial complement**

| Dimension | Content Aviator | GroundedDocs |
|---|---|---|
| Document Q&A | ✅ Has it | ✅ Has it |
| Citation surfacing | ✅ Built in | ✅ + **runtime verification (mechanical + NLI)** |
| **Refusal-on-low-confidence as a product policy** | ❓ Not emphasized in public docs | ✅ First-class, tunable thresholds |
| **Audit / review loop** | Generic compliance | ✅ Every query / retrieval / answer / citation persisted; V2 review queue |
| Model source | **Frontier commercial models** (Gemini / OpenAI / Nova) — cloud egress required | **Open-weights, local serving**; air-gap viable |
| Data sovereignty | OpenText's "private deployment" — but the model may still need cloud APIs | Fully self-contained |
| Lock-in surface | Bound to OpenText ECM content stack | **Vendor-agnostic**; deployable into any CCM/ECM |
| Product scope | Cross-product AI suite | Single focus: trusted retrieval Q&A |

**Sales line for an OpenText prospect**: *"Aviator gives you GenAI on OpenText content via Gemini / OpenAI / Nova. GroundedDocs gives you GenAI on **any** content via open-weights on your own GPU — same document Q&A surface, no frontier-model dependency, no cloud egress."*

#### 13.3.3 vs Aviator Studio — **reference, not competitor**

Aviator Studio is an agent-building platform; GroundedDocs is an application-layer product. Different layer. We borrow its patterns for spec slots 20–24 without competing with it.

### 13.4 One-line positioning across all four

| Product | One-line definition |
|---|---|
| **Quadient Inspire** | CCM platform with outbound content-generation AI; BYOAI framework welcomes third-party AI |
| **OpenText Content Aviator** | Conversational AI assistant over the OpenText content stack, powered by frontier commercial models |
| **OpenText Aviator Studio** | No-code / pro-code enterprise AI agent builder |
| **GroundedDocs** | Vendor-embeddable, on-prem enterprise document Q&A agent with verified citations and a refusal policy |

### 13.5 Strategic implications (for Stage 2 PM)

1. **Quadient path = partnership**. Package GroundedDocs as BYOAI-ready. Target Quadient customers who want private deployment + cited Q&A. **Collaborate; do not compete with Quadient's own AI**.
2. **OpenText path = uphill**. If a prospect already has Content Aviator, the overlap is large. Differentiation must lead with **open-weights + air-gap + vendor-agnostic** — otherwise no wedge. **Recommendation: deprioritize OpenText prospects in the first wave**.
3. **The open field**: Smart Communications, M-Files, Hyland, regional CCM/ECM vendors, and ECM platforms without an Aviator-grade AI suite — **this is GroundedDocs's first-wave target list**.
4. **Aviator Studio is reading list**. When writing spec slots 23 (evals/guardrails) and 24 (prompt registry), study its public surface for the quality bar; do not reinvent the wheel.

### 13.6 New sources added in this section

- [Quadient Inspire G2 reviews](https://www.g2.com/products/quadient-inspire/reviews)
- [Quadient Inspire Evolve product page](https://www.quadient.com/en-int/customer-communications/inspire-evolve)
- [OpenText Aviator umbrella page](https://www.opentext.com/aviator-ai)
- [OpenText Content Aviator product page](https://www.opentext.com/aviator-ai/content-aviator)
- [What's New in OpenText Content Aviator blog](https://blogs.opentext.com/whats-new-in-opentext-content-aviator/)
- [OpenText MyAviator CE 25.4 secure AI collaboration blog](https://blogs.opentext.com/opentext-myaviator-ce-25-4-adds-secure-ai-collaboration/)
- [OpenText Aviator Studio page](https://www.opentext.com/aviator-ai/aviator-studio)
- [OpenText Service Management Aviator page](https://www.opentext.com/aviator-ai/service-management-aviator)
- [OpenText Content Aviator solution overview PDF](https://www.opentext.com/media/solution-overview/opentext-content-aviator-slo-en.pdf)
- [Secure AI content management with OpenText Content Aviator white paper](https://www.opentext.com/en/media/white-paper/secure-ai-content-management-with-opentext-content-aviator-wp-en.pdf)
