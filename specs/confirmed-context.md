# Confirmed Context — GroundedDocs

> Single source of truth for every downstream specialist (PM, researcher, architect, reviewer, spec-writer, auditor).
> Read this first. Append new confirmations at the bottom. Never delete a pinned value.
> All durable decisions are mirrored into `13-decision-log.md` (canonical) using stable IDs `DEC-###`.

Stage 0 owner: `idea-scope-facilitator`. Stage 0 completion date: 2026-06-25.

---

## 1. Idea Brief (plain English)

GroundedDocs is an **on-premise, vendor-embeddable Agentic RAG product** that lets enterprise users ask questions against their own document repositories and receive **only answers grounded in cited, verifiable source passages**. Three pillars distinguish it from generic RAG:

1. **Governance** — every document carries source, version, owning department, and ACL; every query and answer is auditable; admins can answer "who asked what, what did the system retrieve, what was cited, and who saw it" after the fact.
2. **Anti-hallucination as a product policy, not a prompt trick** — every assertion in a generated answer must be linked to a retrieved passage that the runtime independently verifies; if grounding confidence falls below a configured threshold, the system refuses or downgrades rather than guesses.
3. **Reviewable** — selected categories of questions (e.g., compliance, contract terms, customer-facing replies) can route through human review before the answer is shown or persisted; reviewer verdicts feed back into evals and content curation.

GroundedDocs is **sold as an add-on through CCM (Customer Communication Management) and ECM (Enterprise Content Management) vendors** to their enterprise customers. The vendor integrates GroundedDocs into their existing customer portal / agent console; the enterprise installs GroundedDocs on its own infrastructure.

## 2. Product Type and Likely Spec Families

- **Core type**: software product + AI Agent product (LLM-driven retrieval + answer)
- **Deployment model**: single-tenant **on-premise** (installable artifact / Helm / VM image). **Not** multi-tenant SaaS.
- **Distribution**: B2B2B — primary buyer = CCM/ECM vendor; end user = vendor's enterprise customer's staff
- **Likely spec slot families**:
  - Always: core slots 00–14
  - AI agent slots 20–24 (behavior, tools, memory, evals, prompt registry)
  - Brownfield / enterprise integration slots 40–42 (this product is always installed *into* a host system)
  - **Skipped**: 30–33 (multi-tenant SaaS lifecycle, isolation, pricing, blue/green) — single-tenant on-prem
  - **Skipped**: 03a UI design — MVP has no standalone UI; it embeds in the vendor's UI via API/widget (revisit at Stage 3)

## 3. Scope (pinned at Stage 0)

### MVP — must-have (V1 demo)

- **Document ingest**: file upload + parse + chunk + embed + index. MVP supports common business document formats (PDF, Word, plain text, Markdown). Scanned PDFs and complex tables are deferred.
- **Retrieval**: hybrid dense + sparse + rerank; multilingual baseline (must work for Chinese + English at minimum).
- **Cited Q&A**: every answer carries inline citations; runtime verifies each citation lands on a chunk actually retrieved this turn; ungrounded assertions are rejected at the formatting layer.
- **Refusal policy**: when retrieval confidence or grounding confidence is below threshold, the system refuses with an explicit "no confident answer" response rather than generating.
- **Audit log**: every query, retrieval set, answer, citation, and reviewer action is persisted to an append-only audit store.
- **Vendor integration surface**: a stable HTTP API + minimal embeddable chat widget (iframe or web component) suitable for a vendor to drop into their console.
- **Installable artifact**: single-host docker-compose for demo; Helm chart deferred to post-demo.
- **Open-source LLM compatible**: must run end-to-end against a fully self-hosted LLM stack (e.g., a local-served open-weights model) with no outbound calls. Commercial APIs are an optional adapter, not required.

### V2 — should-have (post-demo)

- ReAct-style multi-step agent (search → narrow → cross-reference → answer) on top of the same retrieval and citation primitives
- Human-in-the-loop review queue with per-category routing rules
- Pluggable connectors beyond file upload (SharePoint, file shares, CCM repository APIs)
- Eval harness with refusal-rate / grounding-rate / answer-rate dashboards
- Multi-host / HA deployment, Helm chart, blue/green reindex

### Out of scope (explicitly)

- **Auto-generated wiki / knowledge graph from documents** (WeKnora's Wiki Mode). Reason: auto-generated synthesis is a new hallucination surface that contradicts the "anti-hallucination" positioning.
- Multi-tenant SaaS hosted by us
- Self-serve sign-up, billing, pricing/quota metering
- Real-time chat connectors (IM channels, Slack, WeCom, etc.) — vendor-driven integration only
- Mobile native apps
- Speech / ASR / image OCR (deferred to V3+)
- Compliance certifications (SOC2 / HIPAA / PCI / China MLPS Level 3). MVP targets general B2B; the design must not block these, but no certification is committed for MVP.

### Deferred (named, not killed)

- Human review queue UI (V2)
- Connector framework (V2)
- Helm + HA + blue/green (V2)
- Eval automation (V2)
- Multi-language prompt registry (V2)

## 4. Personas

| Persona | Description | Primary surface | Key needs |
|---|---|---|---|
| **End user (vendor's customer's staff)** | Knowledge worker inside the enterprise that bought the CCM/ECM product | Embedded chat widget inside vendor console; or vendor-built UI calling our API | Get a cited answer or an honest refusal; click through to source passage |
| **Enterprise admin** | IT / KM owner at the enterprise that installed GroundedDocs | Admin API + (V2) admin console | Upload/curate docs, set ACL, view audit log, configure refusal thresholds, run eval |
| **Reviewer (V2)** | Compliance / SME inside the enterprise | Review queue UI (V2) | Approve / edit / reject pending answers in routed categories |
| **CCM/ECM vendor integrator** | The buyer of GroundedDocs; integrates it into their own product | Integration docs + API + widget | Predictable contract, clean install, brandable UI surface, no surprise telemetry |
| **GroundedDocs operator (us)** | The product team during demo phase (single person) | CLI + logs | Run demos, capture eval, ship fixes |

## 5. Risk-Time Profile

| ID | Risk | Owner | Mitigation direction |
|---|---|---|---|
| **RISK-001** | "Verified citation" is hard on real enterprise documents (scanned PDFs, table-heavy contracts, multi-column layouts); citation accuracy may collapse on non-trivial inputs | Architect | Constrain MVP corpus to born-digital text-extractable documents; defer OCR; measure citation-hit-rate as a first-class metric |
| **RISK-002** | Refusal policy without measured baselines becomes a slogan; vendors can't tell us apart from generic RAG | PM + Architect | Make refusal-rate, grounding-rate, hallucination-rate (by sampled human review) part of MVP metrics; expose them to vendor as configurable thresholds |
| **RISK-003** | On-prem with open-source LLMs forces us to support a wide hardware matrix and model zoo | Architect | MVP fixes a **reference stack** (one embedding model + one rerank model + one open-weights generation model + one vector store) and documents extension points; resist the urge to be "model-agnostic on day 1" |
| **RISK-004** | B2B2B sales path means our actual buyer (vendor) and end user have different needs; vendor wants stability and brandability, end user wants accuracy. Conflict surfaces in UX and SLA decisions | PM | Treat the vendor's integration contract as a first-class spec deliverable; widget is themable; telemetry is opt-in per install |
| **RISK-005** | Anti-hallucination guarantees can imply legal exposure if mis-marketed | PM | Position as "no answer without verifiable citation" (process claim), not "100% accurate" (outcome claim) |
| **RISK-006** | Demo-grade product is a personal-time project; scope creep kills it | All | Hard-pin MVP; defer ruthlessly; review scope at each stage gate |

## 6. Time Horizon

- **Stage**: personal project → demo
- **Goal**: a working end-to-end demo that a CCM/ECM vendor evaluator can install, ingest a sample corpus, ask questions, and see verifiable citations + refusals
- **Not committed**: production GA timeline, certification, paying customer
- **Specs depth target**: enough that a junior developer (1–2 yr, on the chosen stack, has read the project's `CLAUDE.md`) could build it without inventing decisions; production-readiness specs (T5 reliability/ops) target *demo deployability*, not 24/7 SLA

## 7. Authority

| Domain | Owner |
|---|---|
| Product scope, non-goals, MVP boundary | User (project owner) + PM specialist |
| Trend research scope and skip decisions | User + product-trend-researcher |
| Architecture selection | software-architect + ai-agent-architect, with user as final tie-breaker |
| Anti-hallucination policy thresholds | ai-agent-architect (proposes) + user (approves) |
| Compliance scope | Deferred to first regulated buyer; placeholder spec slot 42 only |

## 8. Trend Research Decision

**Run Stage 1.** Rationale: this is a contested category with several mature alternatives (Tencent WeKnora, Glean, Vectara, Cohere RAG, LangChain templates, plus open-source like RAGFlow, Dify, AnythingLLM). Need explicit competitor map, differentiation evidence, and architecture pattern survey before PM and architecture stages.

Research focus areas:

- **Competitor map** focused on *on-prem*, *vendor-embeddable*, *citation-verified* RAG; classify each by deployment model, citation strategy, and review/governance features
- **Anti-hallucination patterns** in production RAG: citation-grounding verification, refusal strategies, eval frameworks (RAGAS, TruLens, Ragas-style metrics), runtime guardrails
- **On-prem LLM serving** state of art (vLLM, TGI, Ollama, llama.cpp) and reference open-weights model choices as of mid-2026
- **Hybrid retrieval + rerank** patterns and reference models (bge-m3, bge-reranker, ColBERT-style, GTE)
- **CCM / ECM integration patterns** — how vendors in this space typically embed third-party AI add-ons (widget, API, SDK, white-label)
- **Audit / review-loop patterns** in enterprise AI products

## 9. Stack and Constraints

- **Tech stack**: not locked at Stage 0; architecture stages will choose with explicit alternatives
- **Hardware**: must run on a single host with a modern consumer or workstation GPU for demo; large-model dependencies must be optional
- **Language**: not pinned; will be chosen at architecture stage based on stack maturity and team familiarity (user's primary professional context is CCM consulting, not deep backend engineering; this will influence stack choice)
- **Outbound network**: an air-gapped install path must be possible (no required outbound calls at runtime). Optional commercial LLM adapters allowed but not required.

## 10. Output Path

All spec artifacts under `D:\AI\claude_code\agentic-rag-onprem\specs\` using stable slot names from `references/spec-catalog.md`.

---

## Drift Log

| Date | Stage | Changed | Reason | New DEC |
|---|---|---|---|---|
| 2026-06-27 | 2 | First-wave channel — original implicit pin in §1 of `confirmed-context.md` ("CCM/ECM vendor add-on") is now executed in **two waves**: wave 1 = OSS community + industry events; wave 2 = direct vendor outreach using the priority order from DEC-018 | User confirmed during Stage 2 hardware-pivot conversation; solo project has no sales motion so OSS reputation is the cheaper channel-building path | DEC-025 |
| 2026-06-27 | 2 | Stage 0 §9 "Hardware: must run on a single host with a modern consumer or workstation GPU for demo" — **dev-time** hardware is now cloud-rented; **deployment-time** hardware is customer-provided per DEC-020 business model | User has no local 24 GB+ GPU; cloud-rent for dev (DEC-021); customer-provided for production (DEC-020) | DEC-020, DEC-021 |
