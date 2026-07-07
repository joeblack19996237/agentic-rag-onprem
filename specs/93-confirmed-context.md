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
  - **Skipped**: 30–33 (multi-tenant SaaS lifecycle, isolation, pricing, blue/green) — single-tenant on-prem. Stage 5 topic **T7 — Multi-Tenant Isolation: `SKIP-NOT-APPLICABLE`** (rationale: single-tenant on-prem per DEC-003; no tenancy concerns arise at the architecture level; each install is a dedicated single-customer deployment). Formal label added 2026-07-05 during Stage 5 Round 5 write-up (`92-stage5-review-memos.md` §R5.4) as bookkeeping/formalization of this already-decided skip — see also `04-architecture.md` line ~1202 for the pre-existing formal instance
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
| **RISK-006** | Demo-grade product is a personal-time project; scope creep kills it | All | Hard-pin MVP; defer ruthlessly; review scope at each stage gate. **Updated 2026-06-29 per DEC-073: severity reduced to MEDIUM under 2-3 team / 180-day planning envelope; HIGH retained against solo-fallback path** |
| **RISK-007** | **[HIGH per DEC-081] Team / timeline planning envelope (2-3 members / 180 days per DEC-073) is aspirational; actual headcount is still solo. Solo-fallback subset clause is WITHDRAWN per DEC-081 — solo path now delivers the same scope on a longer (2027-05+) timeline rather than a cut scope on the 180-day timeline. Demo date 2027-03-26 (DEC-080) is conditional on team materializing by 2026-08-29 (60 d ramp window). **Complexity caveat (added 2026-07-03, review finding)**: DEC-081's "same scope, longer timeline" framing assumes complexity is purely a function of calendar time; it does not address whether a single person, without code review or knowledge redundancy, can sustainably operate this system's accreted complexity (LangGraph full-graph orchestration + Redis + three safety-rail models + two-layer ACL + CDC + eval harness) at any timeline length — cognitive load and defect rate under solo maintenance may not scale linearly with time** | PM + Architect | **Pre-commit to a 2026-08-29 team-materialization checkpoint.** If no second contributor by that date, publicly drop the 2027-03-26 target and announce solo extension; do not silently slip. Stage 6 spec-writer adds team/solo timeline annotation per feature. Re-evaluate at 2026-08-29. **Added 2026-07-03**: if the 2026-08-29 checkpoint is reached without a second contributor, the re-evaluation must explicitly consider a complexity-scope cut (not just a timeline extension) as one of the options on the table, rather than treating DEC-081's "no scope cut" posture as permanently fixed |
| **RISK-008** | **DEC-073 budget envelope (¥2,000-3,000/month for full team) vs current spend (¥800-1,200/month solo) creates a procurement gap if a second contributor onboards mid-cycle** | PM | Treat DEC-074 as planning headroom; do not pre-spend; trigger procurement only on actual onboarding |

## 6. Time Horizon

- **Stage**: personal project → demo. Planning envelope expanded 2026-06-29 to support 2-3 team / 180-day spec sizing (DEC-073); current headcount remains solo
- **Goal**: a working end-to-end demo that a CCM/ECM vendor evaluator can install, ingest a sample corpus, ask questions, and see verifiable citations + refusals
- **Target demo date (team path)**: **2027-03-26** per DEC-080 (supersedes 2026-12-26 and DEC-026's 2026-09-27). Conditional on team materialization by 2026-08-29
- **Solo path date**: **2027-05+ (extends beyond team-path date)** per DEC-081 — solo-fallback delivers same scope on longer timeline; original 180-day promise withdrawn
- **Team-materialization checkpoint**: **2026-08-29** — if no second contributor by this date, publicly drop the 2027-03-26 target and announce solo extension. Do not silently slip
- **Per-feature timeline annotation**: Stage 6 spec-writer must annotate each MVP feature with the team-path vs solo-path delta where it is meaningful (e.g., layered rails integration: team ~15 d, solo ~30-45 d)
- **Decision-log materialized view (DEC-109, Round 6, 2026-07-06)**: `13-decision-log.md` has grown past 115 entries with dense supersede chains (e.g. DEC-052 partially superseded by DEC-086; DEC-079 revised by DEC-082). Stage 6/7 spec-writer should generate a one-time "currently-effective decisions" materialized view (grouped by topic, latest-effective value only, linking back to the full supersede history) so implementers/auditors are not required to manually trace supersede chains inline in the append-only log. This is additive tooling, not a change to the log's append-only format or convention
- **Not committed**: production GA timeline, certification, paying customer, actual team hire
- **Specs depth target**: enough that a junior developer (1–2 yr, on the chosen stack, has read the project's `CLAUDE.md`) could build it without inventing decisions; production-readiness specs (T5 reliability/ops) target *demo deployability*, not 24/7 SLA. Round 2 (2026-06-29) re-baselines this against 2026 RAG senior-architect best practice — see `92-stage5-review-memos.md` Round 2 section and `92a-stage5r2-benchmark.md`

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
| 2026-06-28 | 5 | Stage 0 §3 MVP scope "multilingual baseline (must work for Chinese + English at minimum)" — **scope is narrowed to English-only document retrieval** as a hard MVP constraint. Multilingual schema extension stays non-blocking but not committed | Stage 5 architecture review surfaced that all reference model choices (DEC-013/014/037) inflated hardware floor for capabilities the AU/NZ first-wave market (DEC-072) does not require. User confirmed English-only | DEC-052 |
| 2026-06-28 | 5 | Stage 0 §2 MVP form clarified: with-ECM canonical path is the default MVP demo shape; no-ECM `LocalAdapter`-only path is a documented variant for self-contained demos | Stage 5 review exposed two coexisting MVP shapes without a single canonical reference; AU/NZ first-wave market is ECM-rich | DEC-053 |
| 2026-06-28 | 5 | Stage 0 §9 / DEC-021 dev hardware budget revised from ¥200/month to ¥800-1,200/month | ¥200/month limited actual dev cadence to ~2 h/day vs the ~4 h/day needed across the 90-day DEC-026 deadline | DEC-068 |
| 2026-06-28 | 5 | Stage 0 §6 Time Horizon now includes explicit first-wave target market: **Australia + New Zealand**. Compliance reference frame = AU Privacy Act 1988 + NDB + AU AI Ethics Principles 2019; NZ Privacy Act 2020 + IPP | User customer relationships are AU/NZ; sovereign-cloud + data-residency procurement clauses common in target verticals | DEC-072 |
| 2026-06-28 | 5 | Stage 0 §3 audit posture pinned: `audit_events` is append-only and immutable in MVP shipping posture. GDPR right-to-erasure handling against `audit_events` is deferred to first regulated AU/EU buyer engagement | Audit-as-product-pillar requires immutability promise; first concrete erasure-right trigger is the first regulated buyer — honest deferral | DEC-070 |
| 2026-06-29 | 5→6 | Stage 5 review memo relocated from repo-root `review/2026-06-28-architect-review.md` to standard slot `specs/92-stage5-review-memos.md`; root-level `review/` folder removed; cross-references in `01-product-brief.md §2.1` updated. Historical handoff doc `groundeddocs-handoff-2026-06-28.md` left unchanged (dated snapshot) | Skill convention (workflow.md §Stage 5 + architecture-reviewer.md §Deliverables) places Stage 5 deliverable at slot `92-stage5-review-memos.md`; prior location was a position drift that Stage 6 / 8 audits would flag | — |
| 2026-06-29 | 5R2 | Stage 5 re-opened (Round 2 full-scan) per user decision: two material gaps surfaced (Redis/concurrency trade-off vs DEC-034; mid-flight rewriting architecture vs linear pipeline in §3.2 / REQ-020); benchmark policy = 2026 RAG senior-architect mature choices, MVP pragmatic / V2+ strict (Q2=c); per-topic deep research (Q1=b). Round 2 outputs: `92a-stage5r2-benchmark.md` (new) + Round 2 section appended to `92-stage5-review-memos.md`. Stage 6 spec-writer **blocked** until Round 2 closes | Round 1 Fix Audit closed mechanical inconsistencies but did not benchmark against 2026 best practice; the two user-named gaps were missed. Q2=c selected because solo+90day let-downs were over-pragmatic; V2 path must not be self-capped | — |
| 2026-06-29 | 5R2 | §5 Risk-Time Profile: RISK-006 severity reduced to MEDIUM (was HIGH); RISK-007 added (team/timeline envelope is aspirational); RISK-008 added (budget envelope procurement gap). §6 Time Horizon: target demo date 2026-09-27 → 2026-12-26; solo-fallback clause added; spec-depth pointer to Round 2 outputs added | DEC-073 + DEC-074 cascade into Stage 0 risk + horizon framing | DEC-073, DEC-074 |
| 2026-06-29 | 5R2 Gate | Round 2 gate decisions resolved by user: (1) full LangGraph adoption (DEC-075, supersedes DEC-032 partial); (2) Redis in MVP (DEC-076, supersedes DEC-034 partial); (3) layered safety rails in MVP (DEC-077, MVP-promoted from V2); (4) golden set 150-200 + 50 smoke (DEC-078). Cascade questions still open: hardware floor recalculation, new demo date, solo-fallback subset re-scoping | User chose Q2=c (V2-strict) interpretation more aggressively than recommended; demo-date push and hardware-floor lift accepted as part of the package | DEC-075, DEC-076, DEC-077, DEC-078 |
| 2026-06-29 | 5R2 Cascade | Cascade decisions resolved: (1) hardware VRAM floor lifted 16 GB → 24 GB (DEC-079, supersedes DEC-041/DEC-052); (2) demo date 2026-12-26 → 2027-03-26 (+90d, DEC-080, supersedes DEC-026 + DEC-073 timeline portion); (3) solo-fallback subset = full team scope on longer (2027-05+) timeline (DEC-081, withdraws DEC-073 180-day clause). RISK-007 severity raised to HIGH; team-materialization checkpoint pinned at 2026-08-29. §6 Time Horizon rewritten | User chose conservative push (+90d) + explicit honesty on solo path (no scope cut) over preserving the original 180-day commitment | DEC-079, DEC-080, DEC-081 |
| 2026-06-29 | 5R3 | Round 3 feedback integration applied. External senior-architect critique (`specs/feedback.txt`, 20 items) mapped: 3 already-covered (S1.2 / S6.3 / S7.2), 11 MVP-now in-stage edits (S0.a / S0.b / S0.c / S1.1 / S2.1 / S2.2 / S2.3 / S4.2 / S5 / S6.1 / S7.1), 4 V2 roadmap (S3.1 / S3.2 / S4.1 / S6.2 / S6.4), 2 V3 roadmap (S4.3 / S7.3). 4 new DECs (DEC-082..085), 6 new REQs (REQ-050..055), 3 new NFRs (NFR-027..029). Headline changes: Llama Guard 3 8B int4 → int4 AWQ (~2.5 GB VRAM); SafetyRailAdapter Protocol added (REQ-050); parallel `safety_input ∥ retrieve` (saves ~150 ms warm); `verify/` explicitly bifurcated into mechanical_fast_path / nli_slow_path; "LangGraph is current runtime" framing; JIT auth terminology lift; V2 streaming + intent classifier + repair-only prompt template; V3 federated retrieval path. Latency p95 warm-cache now ≤ 7,160 ms (~840 ms headroom). No change to demo date (2027-03-26 DEC-080) | External feedback (Phase 3 user review) requested deeper 2026-best-practice alignment than Round 2 produced; user resolved 3 direction choices (S2.1 (a) / S3.1 (b) / S7.3 (a)) before Phase E edits; no item rejected | DEC-082, DEC-083, DEC-084, DEC-085 |
| 2026-07-03 | 5R4 | Independent architecture review (outside the `idea-to-specs` skill flow, run against the full spec set as of 2026-06-29) surfaced 3 user-actioned findings + 6 architect-proposed fixes, all resolved same-day. User decisions: (1) embedding model reverted `bge-large-en-v1.5` → `bge-m3` to restore REQ-003 hybrid dense+sparse retrieval, which DEC-052's English-only narrowing had silently broken (no sparse-vector source existed for the dense-only interim pick); (2) `audit_events.citations` now stores a verbatim cited-span text snapshot at answer time, not a `chunk_id` pointer, so the audit record survives the source chunk's later physical deletion under DEC-046 retention policy; (3) declined a dedicated competitor-verification task (open question, not a spec change). Architect-proposed fixes (approved via the same review-response): `verify/.mechanical_fast_path` now validates citations against `reranked_set` (Layer-2-authorized) instead of the raw pre-authorization `retrieval_set` — closes a citation-based ACL-bypass gap; `context_fingerprint` extended with safety-rail adapter/version + policy-ruleset-version fields; a periodic ECM↔RAG reconciliation crawl added (detect+alert, MVP); `legal_hold_added` now invalidates KV-cache for active conversations referencing the frozen document; safety-rail quantization/adapter changes require a documented hazard-detection accuracy-preservation check before shipping as MVP default; ONNX Runtime promoted from "recommended" to MVP-default TEI rerank backend so the shipped install path matches the SLO-compliant path. 8 new DECs (DEC-086..093), 1 new REQ (REQ-056), stale `§9.1` docker-compose and `§7B.11` Mermaid diagram corrected, VRAM budget recalculated (headroom ~1.9 GB → ~1.0 GB warm-cache at the 24 GB floor) | Independent review found that internal Round 1-3 self-review, despite being thorough on cross-document consistency, had a systematic blind spot: verifying that a model/parameter swap preserved the *capability* it was standing in for (sparse retrieval; correct citation-verification target), not just that the swap was internally consistently referenced. See review findings for full reasoning | DEC-086, DEC-087, DEC-088, DEC-089, DEC-090, DEC-091, DEC-092, DEC-093 |
| 2026-07-05 | 5R5 | Round 5 (10-pass dimension-based architecture review, run directly against `00-index.md`'s Architecture review matrix rather than through the skill's T1-T8 topic framing) resolved 15 findings across all 10 matrix dimensions (Summary, Security, Reliability, Performance, Deployment & Cost, Maintainability, Evaluability, Traceability, API/interface contracts, ECM integration). Highlights: `§1` summary/refusal-architecture correction; retrieval-rail indirect-injection scan formally aligned to `acl/` across module map, call-direction table, and typed state (was asserted in prose but absent from the implementable artifacts); `§7B.12` latency budget gains the retrieval-rail scan line item (warm headroom 840→760 ms); reliability failure-table corrections + 2 new NFRs (NFR-030, NFR-031) for previously-untracked VRAM admission-control and cold-cache burst risks; `23-evals-guardrails.md` top-K correction + duplicate-heading renumbering; GPU sub-matrix made authoritative over the coarser hardware-floor tier (16-20 GB GPUs formally unsupported, not "degraded"); docker-compose-vs-Kubernetes decided (K8s not adopted at MVP); poll-only CDC promoted to a first-class topology (REQ-057, NFR-032) with a corresponding `ECMAdapter.poll_changes()` interface method; `cdc/`→`cache/` call-direction gap closed; `QueryGraphState` V2-reserved fields added for REQ-051 parity with REQ-020; audit/traceability extended to cover per-chunk retrieval-safety verdicts and KV-cache legal-hold invalidation events; API surface corrected to 4 surfaces + `06-api-contracts.md` created as a stub. This Drift Log row and the corresponding `92-stage5-review-memos.md` "Round 5" write-up were both produced retroactively on 2026-07-05 as part of reconciling the process deviation (matrix-driven review never written up in the skill's own memo/drift-log artifacts, unlike Rounds 1-4) | DEC-094 through DEC-108 existed in `13-decision-log.md` (tagged 5R5) since the same-day review, but the two artifacts this skill's convention requires for every Stage 5 round — a memo section and a Drift Log row — had not been produced; this row closes that gap. No architecture decision was re-litigated or invented in the process | DEC-094, DEC-095, DEC-096, DEC-097, DEC-098, DEC-099, DEC-100, DEC-101, DEC-102, DEC-103, DEC-104, DEC-105, DEC-106, DEC-107, DEC-108 |
| 2026-07-06 | R6.FixAudit | Round 6 (independent D1-D5 re-review, report-only) surfaced 12 findings (1 High, 7 Medium, 4 Low); user resolved the 3 open questions from that review and directed a same-day Fix Audit. Applied: (1) NLI VRAM/CPU accounting corrected in `04-architecture.md` §4.1/§4.2.2, VRAM headroom recalculated ~1.0→~1.7 GB warm-cache (time-budget headroom from DEC-097 is unaffected — different quantity); (2) V2 `intent_classifier/` latency-budget gap flagged in §8.2 (left as an open V2 design question, not resolved); (3) `01-product-brief.md` §9.3 stale 50-question golden-set figure corrected to match DEC-078's 150-200 expansion; (4) DEC-092's safety-rail quantization/adapter-change accuracy gate extended to REQ-033 (generation model swap) and REQ-034 (embedding model swap) per user decision; (5) `acl_changed(doc_id)` event contract clarified to cover standalone `security_label` reclassification; (6) `ECMAdapter.get_effective_acl()` contract clarified for compound/virtual-document ACL-authority resolution ahead of V2-α; (7) two Maintainability process notes added (decision-log materialized view instruction here in §6; `audit_events` capacity-planning instruction in `04-architecture.md` §12.3); (8) Redis answer cache gains a `doc_id` reverse index for targeted `legal_hold_added` invalidation per user decision, extending DEC-091's KV-cache fix to the answer-cache layer; explicit non-need of a serving-config-hash cache-key dimension recorded; (9) `/ready` health-check contract defined as a full-dependency aggregate check per user decision, updated in `04-architecture.md` §9.1, `06-api-contracts.md`, and REQ-011's acceptance criterion; (10) D1's "no material issues" verdict formally logged. 10 new DECs (DEC-109..118). A same-day cross-validation pass re-verified VRAM/latency numbers, cache-key consistency, `/ready` vs REQ-011 timing, and the extended DEC-092 gate against REQ-034's blue/green migration design — all PASS, no further corrections required | User resolved all 3 open questions from Round 6 (answer-cache doc_id indexing: agreed; `/ready` strictness: full dependency check; DEC-092 gate: extend to REQ-033/034) and requested immediate in-stage application, mirroring the Round 1-4 Fix Audit convention rather than deferring to a separate stage | DEC-109, DEC-110, DEC-111, DEC-112, DEC-113, DEC-114, DEC-115, DEC-116, DEC-117, DEC-118 |
| 2026-07-06 | 6→7 | Stage 6 spec-set selection confirmed by user (no changes to the proposed slot list). Structural fix applied ahead of Stage 7 generation: `specs/93-stage5r2-benchmark.md` renamed to `specs/92a-stage5r2-benchmark.md` (git history preserved) to free catalog-reserved slot 93 for Stage 7's own final `confirmed-context.md` snapshot step; every in-repo reference to the old filename updated. `00-index.md` retained as this project's stable slot-00 filename per user/coordinator confirmation (not renamed to the catalog's generic `00-spec-index.md`) | Slot 93 is catalog-designated for the Stage 7 process's own snapshot artifact per `spec-writer.md` process step 9; the Round 2 benchmark memo occupying that slot number is Group E background evidence, not a numbered catalog deliverable, so renaming it (rather than picking a different slot for the Stage 7 snapshot) is the smaller, lower-risk change | DEC-119 |
