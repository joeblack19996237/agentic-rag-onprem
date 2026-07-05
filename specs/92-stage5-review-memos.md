# GroundedDocs — Stage 5 Architecture Review (2026-06-28)

> Independent architectural review of the GroundedDocs spec set under `specs/`. Produced as a Stage 5 deliverable per the `architecture-reviewer` skill convention; Stage 7 `spec-writer` consumes the **Required Changes (RC) mapping table** at the end of this document directly.

- **Review date**: 2026-06-28
- **Reviewer role**: independent senior architect — combined background in enterprise ECM integration (Documentum / OpenText / SAP, 15+ yrs), production RAG (hybrid search, RRF, reranking, ACL passthrough, 5+ yrs), and AI agent systems (3+ yrs)
- **Stance**: independent advisor; does not defend the existing design
- **Review scope**: every file under `specs/` as of 2026-06-28 plus the diagram at `specs/assets/two-layer-authorization.png`
- **Source language constraint**: this document is English-only. Original spec quotes preserved verbatim
- **Severity tally**: 1 Critical / 11 High / 14 Medium / 5 Low across 31 findings

---

## Document dependency graph

```
confirmed-context.md ─┐
                      ├→ 01-product-brief.md ─┐
90-stage1-trend.md ───┤                       ├→ 02-requirements.md
                      └→ 13-decision-log.md ──┘        │
                                                       ↓
                                              04-architecture.md (§7B sources from external research)
                                                       │
                                              ┌────────┼────────┐
                                              ↓        ↓        ↓
                                              20-agent  23-evals  91-skip
                                              (handoff doc = meta)
```

`13-decision-log.md` is the **canonical authority**. The latest decision round (DEC-042..051) supersedes earlier wording in `04-architecture.md §12.1` and the module diagram (identified as concrete inconsistencies under D4).

## Dimension → Topic mapping

The seven dimensions in this review map to the standard `architecture-reviewer` skill topics for downstream traceability:

| Dimension | Maps to skill topic | Required Change ID prefix |
|---|---|---|
| D1 Hidden Assumptions | T1 Product-System Fit (cross-cutting) | RC-T1-* |
| D2 Product Positioning & Competition | T1 Product-System Fit | RC-T1-* |
| D3 Architectural Soundness | T2 Architecture Alternatives | RC-T2-* |
| D4 Design Errors & Inconsistencies | T3 Data, API, Database | RC-T3-* |
| D5 ECM Integration Completeness | T3 + T4 Security | RC-T3-* / RC-T4-* |
| D6 Non-functional Attributes | T4 + T5 Reliability/Ops | RC-T4-* / RC-T5-* |
| D7 Edge Cases | T6 Build, Test, Verification + T8 AI Production Readiness | RC-T6-* / RC-T8-* |

---

## Pre-review key finding

The user has clarified during this review that **English-only document retrieval is a hard constraint** for the MVP scope. The specs as authored heavily encode "Chinese + English multilingual baseline" as a justifying premise for several technical choices (DEC-013 Qwen3; DEC-014 bge-m3; DEC-037 deberta-v3-large-mnli; REQ-003; NFR-003; `23-evals` §2.2 multilingual slice). This conflict is the largest single change driver in the Required Changes list and is reflected in finding D1-01 (Critical) below.

---

## D1 — Hidden Assumptions

### D1-01 [Critical] Multilingual baseline embedded across model choices contradicts the English-only MVP scope
- **Location**: cross-document — `04-architecture` §4.1; `13-decision-log` DEC-013 / DEC-014 / DEC-037; `02-requirements` REQ-003 / NFR-003
- **Evidence**: DEC-013 "Strong multilingual (Chinese + English mandatory for CCM market)"; DEC-014 "100+ languages"; DEC-037 "strong publicly-evaluated multilingual fallback for mixed Chinese/English content"; `23-evals` §2.2 reserves 5 golden questions for "Multilingual mixed Chinese+English"
- **Recommendation**: trigger supersede of DEC-013 / DEC-014 / DEC-037; re-evaluate model matrix (candidates: English-only embedding such as `bge-large-en-v1.5` or `e5-large-v2`; smaller NLI such as `deberta-v3-base-mnli`); recompute VRAM occupancy and lower hardware floor where it falls out; reassign `23-evals` §2.2 multilingual slots
- **Risk if unfixed**: the entire technical stack is anchored on a "multilingual obligation" that yields no business value; hardware floor inflated; performance budget consumed by capabilities the market does not pay for

### D1-02 [High] Two-layer authorization presumes the customer ECM exposes 4 standardized endpoints and a reachable CDC channel; the no-ECM MVP path leaves §7B as dead weight
- **Location**: `04-architecture` §7B entire section
- **Evidence**: §7B.8 / §7B.10 / DEC-049: `get_effective_acl` / `batch_check_access` / `get_retention_state` / `write_audit_access` / `subscribe_changes` are all required ECMAdapter contract methods. MVP ships only `LocalAdapter` + `OIDCAdapter` (DEC-045 / REQ-036)
- **Recommendation**: explicitly distinguish "with-ECM deployment" from "no-ECM deployment" as two architecture variants; add §7B.0 path-selection clause; identify which is the MVP demo path
- **Risk if unfixed**: vendor evaluator asks "we have no standard PDP; how does this work?" and the answer is missing

### D1-03 [High] Air-gap guarantee conflicts with JWKS-based JWT key rotation; specs offer no air-gap key-rotation runbook
- **Location**: `04-architecture` §9; `02-requirements` NFR-002; `13-decision-log` DEC-048
- **Evidence**: NFR-002 "make no required outbound network calls"; DEC-048 "key rotation supported via JWKS refresh" implies reachable IdP; REQ-012 "air-gap test 100% pass"
- **Recommendation**: explicit clause: air-gap deployments use customer-preimported static JWKS + manual rotation runbook; non-air-gap deployments use JWKS endpoint refresh; both modes documented in `09-deployment-ops`
- **Risk if unfixed**: first air-gap customer install triggers security/compliance dispute; absence of plan leads to expedient workaround like disabling signature verification

### D1-04 [High] ECM PDP latency assumptions in §7B.12 (200 ms / 100 ms) lack source backing; real-world Documentum + OpenText ACL evaluation varies widely under load
- **Location**: `04-architecture` §7B.12
- **Evidence**: §7B.12 numbers "≤ 200 ms / ≤ 100 ms" are uncited; DEC-046 only cites "Glean/Graph/AWS Q industry consensus" without specific latency data
- **Recommendation**: annotate §7B.12 "to be calibrated against V2 vendor pilot data"; add NFR-016: when ECM PDP exceeds configured threshold (default 500 ms), trip a circuit breaker → explicit `verification_unavailable` refusal (never silent skip)
- **Risk if unfixed**: first real ECM integration hits a latency wall; §7B.12 closing line "silently skipping would re-introduce the stale-ACL leak" identifies this as a self-acknowledged deadlock

### D1-05 [High] "30-minute cold-start install" assumes customer network can pull ~15 GB of model weights
- **Location**: `04-architecture` §4.2 hardware matrix; REQ-011; §9.1
- **Evidence**: REQ-011 acceptance: `docker compose up to /ready in ≤ 30 minutes`; §9.1 schematic provides no offline model bundle; sum of weights: generation model ~10 GB + embedding ~2 GB + reranker ~1 GB + NLI ~1.5 GB
- **Recommendation**: split "public-network install" from "offline install bundle" as two paths; offline bundle is a first-class MVP deliverable (the only viable path for air-gap customers)
- **Risk if unfixed**: vendor evaluator first install on enterprise-network bandwidth far exceeds 30 minutes → first-impression failure

### D1-06 [Medium] 24 GB VRAM floor = consumer-class GPU (4090/A6000 family); many enterprise IT teams will not deploy consumer GPUs in production rooms
- **Location**: `04-architecture` §4.2 hardware matrix
- **Evidence**: §4.2 floor states "≥ 24 GB VRAM" without specific GPU model matrix; DEC-041 similarly generic
- **Recommendation**: add GPU compatibility sub-matrix in `09-deployment-ops` (consumer 4090/5090; workstation A6000; server-grade L40S/A10/A100) with measured throughput per tier
- **Risk if unfixed**: RISK-013 (dev rig ≠ customer rig) probability rises sharply

### D1-07 [Medium] Default AuthN = JWT bearer + admin API key + OIDC adapter; implicitly assumes customer IAM is OIDC; CCM/ECM enterprises frequently use SAML / Kerberos / LDAP / vendor-proprietary tokens
- **Location**: `04-architecture` §4.1; DEC-048
- **Evidence**: §4.1 AuthN/AuthZ row; DEC-048 only writes OIDC bearer
- **Recommendation**: add AuthN adapter layer in §4: OIDC = MVP only; SAML / Kerberos = V2 roadmap; vendor integrator doc must explicitly state "if you are not OIDC, you need a token-exchange sidecar in front"
- **Risk if unfixed**: target customer IT architecture conversation stalls on a missing piece

### D1-08 [Medium] The entire `verify/` differentiator hinges on `deberta-v3-large-mnli`; initial threshold 0.5 is "community baseline" without CCM-corpus calibration data
- **Location**: `04-architecture` §8.4; `23-evals` §2.1
- **Evidence**: §8.4 row "NLI entailment threshold 0.5 / community baseline"; `23-evals` §7 self-acknowledges "is this appropriate for multilingual content — Stage 5 to answer"
- **Recommendation**: keep NLI model as a swappable component from MVP day one (alternative candidates: cross-encoder reranker as NLI proxy; LLM-as-judge offline sampling); add NLI accuracy as a standalone golden-set metric decoupled from RAGAS faithfulness
- **Risk if unfixed**: a demo competitor uses adversarial near-miss inputs to disprove the "verified citation" differentiator outright

---

✅ D1 complete — 8 findings

---

## D2 — Product Positioning & Competition

### D2-01 [High] "On-prem + vendor-embedded empty quadrant" rationale is weak (self-tagged confidence M, inferred); 2026 competitive reality is more crowded than the trend research describes
- **Location**: `01-product-brief` §2; `90-stage1-trend` §2.2
- **Evidence**: §2.2 self-tags [M, inferred]; Microsoft Graph Connectors + Copilot for M365 / AWS Q Business with connectors / Glean dedicated VPC all cover "customer-controlled data + integrated in vendor ecosystem" in 2026 【unconfirmed — Glean's true on-prem availability needs verification】
- **Recommendation**: in `01-product-brief` §2, add direct head-to-head comparison subsections vs Copilot + Graph and vs Q Business; narrow GroundedDocs differentiation to the triple "open-weight + fully local LLM inference + model-swappable"; retire the "empty quadrant" framing
- **Risk if unfixed**: first wave of OSS-community exposure brings the immediate question "isn't this just Copilot offline?" with no rehearsed answer → positioning collapses

### D2-02 [High] "Verified citation" + "refusal as a feature" are not defensible differentiators — Vectara / RAGFlow / Hebbia / Glean all claim citations; mechanical + NLI is a public pattern
- **Location**: cross-document — `01-product-brief` §4 + `04-architecture` §8
- **Evidence**: `90-stage1-trend` §3.1 explicitly traces the pattern to ClarityArc / Nexumo / arXiv 2410.03461; §2.1 table shows Vectara/RAGFlow/Hebbia all advertise citations
- **Recommendation**: reframe the differentiator from "we do this" to "we do it as a contract-grade SLO": package NFR-004 (100% hit-rate hard gate) + 5-class typed refusal + audit dual-write + measured NLI thresholds as a "Citation SLO" vendor-contractable artifact (not just marketing copy)
- **Risk if unfixed**: head-to-head against Vectara/Glean degenerates to a feature-parity war over wording

### D2-03 [Medium] OpenText Aviator and Microsoft Copilot both support private deployment / customer-controlled tenancy in 2026 【unconfirmed】; "on-prem" alone is not a scarce differentiator
- **Location**: `01-product-brief` §4 differentiator #1 "On-prem deployment"
- **Evidence**: `90-stage1-trend` §13.2 describes Aviator as depending on cloud frontier models — but whether OpenText still insists on pure-cloud in 2026, or whether Aviator now offers BYO-model, is not in the trend research 【in question】
- **Recommendation**: reword the differentiator from "on-prem" to "open-weight + fully local LLM inference + model-swappable" — the combination is harder for cloud vendors to match directly
- **Risk if unfixed**: in sales conversation cannot answer "we can deploy Copilot privately too" — positioning weakens

### D2-04 [Medium] Three priority orders (sales / technical adapter / first-wave outreach) are intentionally divergent but lack a unified narrative
- **Location**: DEC-050 vs DEC-018 vs DEC-025
- **Evidence**: DEC-018 (sales priority) / DEC-050 (technical priority) / DEC-025 (first-wave channel) are documented as "intentionally different" but spread across three DECs
- **Recommendation**: add a three-tier timeline table in `01-product-brief` §8 GTM: "adapter priority ≠ sales priority ≠ first-wave outreach timing"; reader gets the full picture once
- **Risk if unfixed**: post-OSS launch, the question "which ECM do you support first in V2?" cannot be answered cleanly; early partnership opportunities lost

---

✅ D2 complete — 4 findings

---

## D3 — Architectural Soundness

### D3-01 [High] §5 module diagram vs §7B.11 Mermaid: MVP actually includes `acl/` + `cdc/` modules (REQ-036 / REQ-037 / REQ-041 / REQ-045 all marked MVP), but §5 ASCII diagram omits them and self-annotates as "MVP-without-ECM path". Two MVP shapes coexist without a single canonical reference
- **Location**: `04-architecture` §5 vs §7B.11
- **Evidence**: §5 ASCII lacks `acl/` + `cdc/`; REQ-036 / REQ-037 / REQ-041 / REQ-045 all flagged MVP; §7B.11 is the with-ECM MVP path
- **Recommendation**: upgrade §5 ASCII to the canonical with-ECM MVP path including `acl/` + `cdc/`; demote the no-ECM `LocalAdapter` fast-path to an appendix §5A with the label "demo fast-path variant"
- **Risk if unfixed**: Stage 7 spec-writer codes modules from §5 → MVP fast path becomes the wrongly-installed default

### D3-02 [High] §7B.12 latency budget sums to ≈ 7,805 ms against an 8,000 ms NFR-005 cap; < 200 ms remaining cannot cover FastAPI serialization, audit sync writes, network jitter, GC pauses, or concurrent queueing
- **Location**: `04-architecture` §7B.12
- **Evidence**: §7B.12 sum: 5 + 300 + 200 + 100 + 200 + 7,000 = 7,805 ms
- **Recommendation** (selected by user Q3 decision): hold NFR-005 ≤ 8 s; restructure for concurrency + caching — introduce KV-cache reuse across turns, prompt-cache for system prompts + per-customer template, reranker batching, NLI batching; mark each line item with concurrency assumption (e.g. "at ≤ 2 in-flight queries")
- **Risk if unfixed**: first vendor demo with 3-5 concurrent evaluators trips the SLO; published p95 numbers immediately questioned

### D3-03 [High] Single GPU + single vLLM instance + co-located TEI(embed) + TEI(rerank) + deberta NLI all on one GPU without concurrency model / load balancing / batch scheduler design
- **Location**: `04-architecture` §5 + §10.1; NFR-005
- **Evidence**: §9.1 schematic shows one service per container; NFR-005 p95 ≤ 8 s implicit at single in-flight; `90-stage1-trend` §4 mentions vLLM PagedAttention without batch scheduler parameter planning
- **Recommendation**: add a concurrency-model subsection in §9 — define MVP concurrency ceiling (e.g. 1-2 in-flight queries) and over-limit behavior (queue + head-of-line latency alert; never silent degradation); vendor demo doc states the concurrency cap up front
- **Risk if unfixed**: realistic demo scenario (3 vendor evaluators clicking simultaneously) trips SLO

### D3-04 [High] CDC SLA inconsistency: §7B.5 "CDC ≤ 60 s for MVP, ≤ 5 s for V2"; DEC-051 "re-poll every 30 min"; NFR-014 "retention expiry physical delete within 60 s"
- **Location**: §7B.5 vs DEC-051 vs NFR-014
- **Evidence**: 30 min re-poll vs 60 s SLA is mathematically impossible when the webhook path fails
- **Recommendation**: pick one and standardize: (a) tighten re-poll to ~60 s (high frequency but ECM-side throughput may reject); (b) rewrite NFR-014 to "60 s on webhook path + 30 min on re-poll fallback path", accepting "retention compliance delays up to 30 min during webhook outage" as a known limitation; (c) add a polling-style ECM endpoint compensation job. Recommended: (b) with NFR-016 webhook health-check + alerting
- **Risk if unfixed**: first compliance audit identifies "retention SLA unreachable on webhook-outage path"

### D3-05 [Medium] Chunking strategy undefined (chunk size, overlap, semantic vs fixed-size splitting, token vs character units) — chunk boundary directly affects verify/ span detection, citation granularity, retrieval recall
- **Location**: `04-architecture` §5 ingest + §6 chunks entity
- **Evidence**: §5 only annotates "chunk (semantic+size)"; §6 chunks table has no chunk_size / overlap fields
- **Recommendation**: pin a chunking strategy in §6 (suggested: 1024-token chunks aligned with bge-m3 input window + 128-token overlap + recursive splitter primary, structural splitter fallback); declare chunk_id immutability invariant
- **Risk if unfixed**: Stage 7 spec-writer improvises; ingest and verify/ assumptions drift; citation accuracy becomes unstable

### D3-06 [Medium] Embedding model versioning (REQ-034) is V2, but single-collection design with (corpus_id, embedding_model_version) key in §6 already requires double-collection capability at MVP, otherwise the first embedding upgrade requires downtime
- **Location**: `04-architecture` §6 + REQ-034
- **Evidence**: §6 "one collection per (corpus_id, embedding_version)"; REQ-034 flagged V2
- **Recommendation**: include "double-collection naming convention + pointer swap" infrastructure at MVP (chunks table with `embedding_model_version` column; admin API exposes swap); automate blue/green in V2. Small MVP investment unlocks the full LCC migration path
- **Risk if unfixed**: DEC-028 LCC Tier 3 ships in V2 only to discover MVP data model does not support double-collection → forced migration

### D3-07 [Medium] `04-architecture` §12.1 still lists 3 refusal classes (`low_grounding` / `no_recall` / `policy_blocked`), conflicting with DEC-042 / REQ-006d's 5-class taxonomy
- **Location**: §12.1 vs DEC-042 + REQ-006d
- **Evidence**: §12.1 table contains only 3 rows; DEC-042 explicitly lists 5 classes + `acl_denial_mode`
- **Recommendation**: replace §12.1 wholesale with DEC-042's 5 classes + transparent/opaque mode description + audit/user-view separation rule; repair §7B.13 broken cross-reference
- **Risk if unfixed**: Stage 7 spec-writer codes API types from §12.1 → integration discovers 2 missing enums

### D3-08 [Medium] §5.1 call rules vs §5 diagram arrow contradiction
- **Location**: `04-architecture` §5.1 vs §5
- **Evidence**: Rule table writes "`generate/` Never call `verify/`" but §5 ASCII arrow shows `generate/ → verify/`
- **Recommendation**: standardize to "api/ orchestrates: api → generate → api → verify → api → audit"; redraw §5 diagram with api-centric orchestration
- **Risk if unfixed**: implementer-interpretation drift quietly breaks module boundaries

### D3-09 [Medium] §3 build-approach 4-option comparison evaluates only 5 dimensions; missing "AI safety / auditability" and "compliance alignment difficulty" — both crucial for GroundedDocs and possibly hiding from-scratch's real advantage
- **Location**: `04-architecture` §3; `13-decision-log` DEC-032
- **Evidence**: §3.1 scoring table has 5 columns; DEC-032 rationale mentions verify/ but does not score auditability as a column
- **Recommendation**: add 2 columns to §3 and rescore; from-scratch should still win, with auditability now visible in the rationale; strengthen DEC-032 rationale to "differentiation + provable compliance dual-driver"
- **Risk if unfixed**: when reviewer challenges DEC-032 ("why not Haystack?"), defense lacks the compliance argument

### D3-10 [Low] §12.3 observability persists OpenTelemetry spans to a Postgres `otel_spans` table — non-mainstream choice; works for demo but lacks an adapter when customer asks "can we forward to Prometheus / Grafana?"
- **Location**: `04-architecture` §12.3
- **Evidence**: §12.3 states MVP routes spans directly to Postgres
- **Recommendation**: MVP ships an OTLP exporter configuration (env-var pointed at external collector); default still Postgres; zero added complexity but preserves a real-world customer hook
- **Risk if unfixed**: any Datadog/Grafana customer in demo conversation immediately asks "how do we wire this up?" with no answer

---

✅ D3 complete — 10 findings

---

## D4 — Design Errors & Inconsistencies

### D4-01 [Critical] Multilingual baseline vs English-only scope fundamental conflict — see D1-01
- See D1-01

### D4-02 [High] DEC-013 naming "Qwen3-30B-A3B MoE int4 at 24 GB floor" is questionable both in naming and feasibility: Qwen MoE 30B total + 3B active int4 weights ≈ 17-19 GB, leaves little for KV cache + system overhead at long context lengths on 24 GB
- **Location**: DEC-013 / §4.1 / §4.2 floor
- **Evidence**: `90-stage1-trend` §5 cites only [BenchLM.ai M] for the 35B-A3B family
- **Recommendation**: provide measured VRAM occupancy in §4.2 (one-shot cloud-rig run with hard numbers); annotate two tiers by context length (short fits, long needs downgrade); remove the blanket "floor supports" claim
- **Risk if unfixed**: demo customer triggers OOM with real long documents; positioning "commitment vs reality mismatch"

### D4-03 [High] Retention 60 s SLA + 30 min re-poll fallback mathematical inconsistency — see D3-04
- See D3-04

### D4-04 [High] Refusal taxonomy 3 vs 5 class inconsistency — see D3-07
- See D3-07

### D4-05 [Medium] `04-architecture` §10.1 + `20-agent` §2.4 state "client-supplied history is ignored, server reconstructs from audit_events indexed by conversation_id" but §6 entities + REQ-007 acceptance do not include `conversation_id` field in `audit_events`
- **Location**: §6 vs REQ-007 vs §10.1 / `20-agent` §2.4
- **Evidence**: §6 table `audit_events` columns omit `conversation_id`; REQ-007 acceptance seed likewise
- **Recommendation**: add non-null `conversation_id` to §6 + REQ-007 acceptance; in NFR-008 add "`conversation_id` is not sensitive payload, INFO level acceptable"
- **Risk if unfixed**: Stage 7 schema lacks the field → §2.4 "server reconstructs" cannot land

### D4-06 [Medium] §7B.13 cites "the `transparent`/`opaque` mode in §12.1" but §12.1 does not actually document the mode (mode lives in DEC-042)
- **Location**: §7B.13 cross-reference
- **Evidence**: §12.1 table contains 3 refusal types, no mode concept
- **Recommendation**: fix as part of the §12.1 wholesale rewrite (point §7B.13 at DEC-042)
- **Risk if unfixed**: reviewer chases the cross-reference, hits a dead link, questions spec rigor

### D4-07 [Medium] DEC-021 dev budget ¥200/month conflicts with measured RunPod 24 GB hourly rate: 4090 spot ~$0.45/h, ¥200 ≈ $28, ≈ 62 h/month ≈ 2 h/day
- **Location**: DEC-021
- **Evidence**: DEC-021 literal "≤ ¥200/month"
- **Recommendation**: revise DEC-021 number to ¥800-1,200/month (real cost for ≥ 4 h/day across 3 months), or explicitly record "development cadence budget-constrained to ≤ 2 h/day actual"
- **Risk if unfixed**: real 3-month development (DEC-026 deadline) either blows budget or runs out of time

### D4-08 [Medium] REQ-006a "neighboring docs come from already-fetched retrieval set" + "must be ACL-filtered before display" relationship is unclear — if already through Layer 2 trim why filter again? If trim hasn't run, the fallback itself is unsafe
- **Location**: REQ-006a + DEC-043
- **Evidence**: REQ-006a wording is internally ambiguous
- **Recommendation**: rewrite as "neighbors come from the post-Layer-2 retained low-score chunks, deduped to ≤ 3 distinct doc_ids; no second ACL check needed"
- **Risk if unfixed**: implementer either re-filters (redundant) or skips (unsafe)

### D4-09 [Low] DEC-048 algorithm whitelist not enumerated
- **Location**: DEC-048
- **Evidence**: DEC-048 "algorithm whitelist; `none` rejected"
- **Recommendation**: enumerate: RS256 / ES256 / EdDSA allowed; HS* / none forbidden
- **Risk if unfixed**: implementer picks the wrong algorithm (e.g. HS256 shared-secret) → bypass vector

### D4-10 [Medium] §5 module diagram says it is the "MVP-without-ECM path" but the spec also says MVP includes two-layer auth (REQ-036) — same as D3-01
- See D3-01

---

✅ D4 complete — 10 findings (4 cross-referenced to D3)

---

## D5 — ECM Integration Completeness

### D5-01 [High] (REVISED per user clarification) Out-of-scope statement for in-flight (checked-out) edits is missing
- **Location**: `04-architecture` §7B entire section
- **Original proposal**: track `checkout_started` / `checkin_completed` CDC events
- **User clarification (2026-06-28)**: GroundedDocs cannot sync in-flight uncommitted edits; the correct 2026 best-practice (Microsoft Graph Connectors, AWS Q Business, Glean) is to index only **committed versions** and treat in-flight edits as out of scope by design
- **Evidence**: §7B.5 CDC event table; §7B.9 version semantics
- **Recommendation**: in `04-architecture` §7B.9 and `01-product-brief` §6 explicitly declare GroundedDocs query semantics are **version-based** — only the latest committed `version_id` is queryable; uncommitted edits in the ECM during checkout are invisible by design; when `version_added` fires after checkin, re-ingest replaces prior chunks; **no** `checkout_started` / `checkin_completed` events are tracked
- **Risk if unfixed**: vendor evaluator asks "can the assistant see what someone is currently writing?" and an "no, by design" answer is missing — reads as a gap rather than a deliberate boundary

### D5-02 [High] doc_id treated as a flat entity; does not cover Documentum virtual document / OpenText compound document (one doc_id is a node tree, not a leaf)
- **Location**: `04-architecture` §6 entities + §7B.9
- **Evidence**: §6 entities table treats documents as flat; §7B.9 only discusses version
- **Recommendation**: in §6 add entity-hierarchy concept: `document` may have `parent_document_id`; retrieval config can choose "index by leaf doc" or "aggregate by root virtual doc"; MVP defaults to leaf only, V2 supports aggregation
- **Risk if unfixed**: Documentum / OpenText customer demo retrieval returns scattered leaf nodes lacking compound context; positioning fails

### D5-03 [High] `write_audit_access` called only on "successful access"; Layer 2 denied (access_denied) attempts are not written to ECM audit, but compliance audit (SOX, HIPAA) typically requires "failed access attempts" in the ECM audit chain
- **Location**: REQ-045 + DEC-047
- **Evidence**: REQ-045 acceptance "every query that successfully accesses..." literally excludes the denial path
- **Recommendation**: widen REQ-045 acceptance to "every query that retrieved or attempted to retrieve ECM-sourced documents"; when `refusal_reason = access_denied` also write-back with `intent = "denied"`
- **Risk if unfixed**: compliance audit finds "denied access attempts not in ECM audit" — a SOX/HIPAA red-line item

### D5-04 [Medium] Missing "folder-level ACL and move events" — document folder moves change inherited ACL but no dedicated event type
- **Location**: `04-architecture` §7B
- **Evidence**: §7B.5 CDC only has `acl_changed(doc_id)`
- **Recommendation**: document that `acl_changed` triggering conditions include "document parent folder change"; adapter implementation contract requires ECM to also fire doc-level `acl_changed` on folder moves
- **Risk if unfixed**: ECM-side folder move does not refresh GroundedDocs ACL cache until next 30-min poll

### D5-05 [Medium] Missing metadata write-back (e.g. GroundedDocs marks documents with "cited by AI N times" tags); CCM customers often want AI processing results written back for downstream governance
- **Location**: `04-architecture` §7B.10 ECMAdapter contract
- **Evidence**: §7B.10 only has audit write-back
- **Recommendation**: V2 roadmap adds `write_metadata(doc_id, key, value)`; MVP doc explicitly does not (avoid scope creep)
- **Risk if unfixed**: early vendor conversations ask "can AI references be written back for content governance" with no answer

### D5-06 [Medium] Missing federated identity mapping — CCM end-user logged into vendor portal identity is not necessarily equivalent to ECM-internal account (common pattern: service account + user_id context propagation + back-end PDP evaluation)
- **Location**: `04-architecture` §7B + REQ-038/039/040/044
- **Evidence**: OIDCAdapter only resolves principals from token; §7B assumes token user_id == ECM user_id
- **Recommendation**: add `map_external_user(external_id, context) -> ecm_user_id` to ECMAdapter; MVP defaults 1:1, allows vendor adapter override
- **Risk if unfixed**: Documentum scenarios where PDP cannot resolve true ECM user_id → Layer 2 returns false universally → system delivers no answers

### D5-07 [Low] Bulk ACL changes not planned (org restructure produces hundreds of thousands of CDC events)
- **Location**: §7B
- **Evidence**: §7B.5 CDC table designed at single-doc event granularity
- **Recommendation**: CDC consumer adds batching + priority queue (retention / legal_hold high priority; acl_changed batchable); NFR caps the rate
- **Risk if unfixed**: customer org restructure clogs CDC queue, drowns retention/legal_hold events

### D5-08 [Low] Encryption-at-rest not addressed — many ECMs use KMS to encrypt content at the back end; GroundedDocs extracts plaintext into Qdrant payload, possibly breaking encryption posture
- **Location**: DEC-046; `02-requirements` NFR-014
- **Evidence**: §7B contains no encryption-at-rest section
- **Recommendation**: in `09-deployment-ops` add an "encrypted-at-rest option" subsection (Qdrant payload + Postgres TDE); state MVP does not enforce but provides configuration
- **Risk if unfixed**: financial / healthcare customer conversation immediately asks "are chunks encrypted at rest" with no answer

---

✅ D5 complete — 8 findings

---

## D6 — Non-functional Attributes

### Maintainability
- **Current**: 10-module + call-direction rules + handoff doc system is well-formed
- **Gap**: call-direction rules enforced as "V2-grade manual review" — solo team under deadline pressure typically violates; module count vs solo capacity ratio undocumented
- **Improvement**: MVP introduces minimum-cost import-graph check (Python `ast` parser detecting cross-layer imports); does not require a test framework investment

### Scalability
- **Current**: double-collection naming convention + ECMAdapter abstraction + model adapter abstraction (V2) provide future extension hooks
- **Gap**: corpus capacity ceiling undeclared (single Qdrant node ~100M vectors performance knee); concurrent-user ceiling unstated
- **Improvement**: add explicit ceilings in NFR (MVP single corpus ≤ 1M chunks, concurrent ≤ 2 in-flight queries); over-limit triggers "V3 multi-host" upgrade signal — gives customer clarity on when to scale

### Traceability
- **Current**: DEC + REQ numbering + decision log are tight; context fingerprint (REQ-035) is well-designed
- **Gap**: REQ-035 is V2; MVP audit lacks model/threshold snapshot → demo-period disputes cannot trace which threshold caused which output
- **Improvement**: promote REQ-035 "context fingerprint columns" to MVP (db schema adds non-null columns; populate-on-write is trivial); LCC-service integration stays V2

### Security
- **Current**: two-layer auth + JWT signature verification + prompt injection structural separators + server-reconstructed history
- **Gap**: (1) no explicit threat model / STRIDE; (2) indirect prompt injection (retrieved chunk containing "ignore previous instructions") defense thin, only one line in system prompt; (3) no rate limiting / abuse detection; (4) no secret management plan; (5) widget iframe cross-origin configuration (CSP / X-Frame-Options / postMessage origin validation) unplanned
- **Improvement**: MVP adds (a) `04-architecture` §12.5 concise threat model section; (b) widget security configuration subsection (CSP allowlist, postMessage origin, frame-ancestors directive); (c) NFR adds rate-limit (per-token QPS ceiling). Secret management / indirect injection defense → V2 roadmap

### Performance
- **Current**: single-host single-GPU path is clear
- **Gap**: (1) latency budget pinned at SLO without headroom (D3-02); (2) concurrency model undefined (D3-03); (3) ingest throughput only 100 pages/min — does not support real ECM customer initial load
- **Improvement**: NFR-005 adds concurrency qualifier ("p95 ≤ 8 s @ ≤ 2 concurrent queries"); NFR-006 states "MVP assumes corpus ≤ 50k pages; enterprise initial load requires V2 multi-worker ingest pipeline"

---

✅ D6 complete — 5 categories, 12 improvements

---

## D7 — Uncovered Edge Cases

### Implementation phase (dev → first build)
- **D7-01** vLLM CUDA version mismatch with customer GPU driver — `09-deployment-ops` should ship a vLLM-CUDA-driver three-way matrix; mandatory check before demo
- **D7-02** Hugging Face token / mirror sources — China customer scenarios face HF download blocks; spec does not plan model bundle localization or mirror-source fallback
- **D7-03** `deberta-v3-large-mnli` multi-GPU/CPU scheduling — competes with vLLM for VRAM; MVP CPU inference? undefined

### Deployment phase (customer first install)
- **D7-04** Customer Docker version / SELinux / cgroup v1 vs v2 — enterprise Linux long-lifecycle; older Docker may not support compose v2 syntax; spec does not declare minimum version
- **D7-05** Inbound webhook firewall unreachable — see D1; common deployment is "RAG outbound-only allowed"; spec does not flag "reverse outbound-only" as a supported shape. **Note**: user clarified (Q4) that GroundedDocs is always co-located with ECM in the same private network, so this risk is reframed as "document the co-location assumption explicitly"
- **D7-06** Air-gap model weight import path — see D1; offline bundle missing
- **D7-07** First-time ingest progress visibility / interrupt recovery — at 100 pages/min, 100k-page customer needs 16+ hours; crash-resume undefined

### Runtime phase (production / demo)
- **D7-08** CDC event out-of-order and idempotency — `legal_hold_added` immediately followed by `legal_hold_released`; if order reverses, state machine stuck in hold state; spec lacks idempotency key / vector clock
- **D7-09** Same doc rapid acl_changed bursts — jitter → CDC storm → repeated Qdrant payload rewrites; needs debouncing
- **D7-10** LLM output format corruption — Qwen3-14B int4 occasionally produces malformed JSON / unclosed citation tokens; verify/ parser tolerance strategy unstated
- **D7-11** Same user multi-tab same conversation_id race — server reconstructs history with in-flight unaudited query; history inconsistent
- **D7-12** ACL change mid-session — user starts Q&A → ACL tightens → chunks already in LLM context displayed; no recall mechanism; spec accepts as known risk but does not document
- **D7-13** Embedding model upgrade audit replay impossible — to re-run old queries against new model to verify regression, old embeddings unavailable; REQ-034 blue/green design does not cover audit replay
- **D7-14** vLLM container crash / restart mid-query — 5xx to user; is retry safe? spec lacks idempotency-token mechanism
- **D7-15** Golden set 50 questions → real customer corpus refusal rate spikes 30-50% — Stage 5 post-runbook missing (how to lower thresholds, how to add chunk size, when to introduce LoRA); `23-evals` §6 says "when to do" but not "how to do"
- **D7-16** First-wave GTM (OSS + community) phase attackers scan public demo instance — widget exposed via iframe gives vendor demo attack surface (prompt injection, SSRF via citation render); spec lacks hardening checklist
- **D7-17** Customer requests audit pause / audit deletion — privacy regulation (GDPR right to erasure) — is audit_events deletable? append-only design conflicts with GDPR delete right; spec untouched. **User decision (Q7)**: audit append-only wins; GDPR delete request handling deferred to first regulated AU/EU buyer engagement
- **D7-18** Vendor evaluator post-install immediately asks "can we wire to Splunk" — audit pull API (REQ-043) NDJSON usable, but schema alignment with Splunk CIM unstated

### Design adjustment directions (summary)
8/9 → CDC consumer adds idempotency; 10 → verify/ parser strict-mode + fallback strip; 11 → conversation_id versioning; 12 → explicit "known limitation" + audit annotation; 13 → old embedding collection retention window policy; 14 → introduce client idempotency key; 15 → `23-evals` adds customer onboarding runbook subsection; 16 → demo instance hardening checklist; 17 → audit-events GDPR delete process (per-user delete + legally-required retention compromise); 18 → audit schema with CIM-compatible field mapping

---

✅ D7 complete — 18 edge cases

---

## Top 5 Must-Fix Items (severity + blast radius)

1. **Multilingual baseline vs English-only scope conflict** (D1-01 / D4-01 Critical) — affects DEC-013/014/037, hardware floor, golden set. User has confirmed English-only is hard constraint; supersede DECs accordingly
2. **CDC retention SLA 60 s vs 30 min re-poll mathematically unreachable** (D3-04 / D4-03 High) — compliance red-line; first audit will catch it; NFR-014 needs split-SLA rewrite
3. **§7B.12 latency budget has no headroom; no concurrency model** (D3-02 / D3-03 High) — demo day with 3-5 concurrent users trips SLO; lethal first-impression risk for OSS-first GTM. User decision (Q3): hold 8 s, restructure for concurrency + caching
4. **`04-architecture` §5 module diagram vs §7B canonical path inconsistency + §12.1 refusal taxonomy vs DEC-042 inconsistency** (D3-01, D3-07, D4-04 High) — Stage 7 spec-writer is imminent; internal contradictions land directly as bugs
5. **ECM Layer 2 failure / ambiguous scenario semantics** (D1-02, D5-03 collective High) — PDP timeout, access_denied path not in ECM audit, no-ECM path §7B dead weight — any one of these gets dissected in real customer conversation

---

## Deferred items (rationale per item)

- **D5-07 / D5-08 (encryption-at-rest / bulk ACL events)** — financial/healthcare customer trigger; first-wave OSS community customer will not ask
- **D3-10 (OTLP exporter)** — Postgres span store is sufficient for demo; add when first real vendor integrates
- **D6 (indirect prompt injection deep defense / secret management / rate limiting)** — MVP minimum (CSP + token algorithm whitelist) enough; full hardening V2
- **D2-03 (de-emphasize "on-prem" in marketing copy)** — copy-only change; landable at any Stage 5/6 point
- **D7-17 (GDPR delete right)** — first AU/EU regulated customer; compliance stack is DEC-006 V2+

---

## Locked Decisions (replaces "Open Questions" — closed 2026-06-28 by user)

| Q | Decision | Encoded as |
|---|---|---|
| Q1 English-only scope | Hard constraint; multilingual rationale superseded | DEC-052 |
| Q2 MVP demo form | With-ECM canonical path; no-ECM is fast-path variant | DEC-053 |
| Q3 NFR-005 latency p95 | Hold ≤ 8 s; restructure for concurrency + caching | DEC-054 |
| Q4 CDC network form | Inbound webhook stays; GroundedDocs co-located with ECM in same private network/VPC | DEC-055 |
| Q5 DEC-021 dev budget | Raise to ¥800-1,200/month to support 3-month deadline (≥ 4 h/day) | DEC-068 |
| Q6 `acl_denial_mode` default | `transparent` default; `opaque` config-flippable; both code paths first-class | DEC-069 |
| Q7 GDPR vs audit | Audit append-only wins; GDPR delete deferred to first regulated AU/EU buyer | DEC-070 |

**Additional context — First-wave market = Australia + New Zealand** (encoded as DEC-072):
- AU Privacy Act 1988 (Privacy Act Review 2023 amendments rolling through 2026) + Notifiable Data Breaches (NDB) scheme
- NZ Privacy Act 2020 + IPP-style 13 principles
- AU AI Ethics Principles 2019 (voluntary, referenced by regulators)
- AU/NZ "data must not leave country" procurement clauses common in public sector + finance
- On-prem air-gap positioning lands well in AU public sector + finance + mining; OpenText/Documentum installed base substantial
- Adapter priority correlates with AU/NZ ECM market share (M-Files / Hyland strong in AU; OpenText dominant in NZ public sector — aligned with DEC-018 + DEC-050)

---

## Pre-Audit Required Changes (RC) — mapping table

Consumed by Stage 7 spec-writer. ID format: `RC-T<topic>-<seq>` per `architecture-reviewer` skill convention.

| RC ID | Origin finding | Target spec file | Fix direction | Acceptance check |
|---|---|---|---|---|
| RC-T1-01 | D1-01 / D4-01 | 13-decision-log, 04-architecture §4.1+§4.2, 02-requirements REQ-003/NFR-001/NFR-003, 23-evals §2.2 | English-only stack: replace multilingual model rationale; supersede DEC-013/014/037 via new DEC-052; reallocate golden set multilingual slots | Grep `multilingual|chinese|mandarin|bge-m3|qwen3` returns only annotated/superseded mentions |
| RC-T1-02 | D1-02 / Q2 | 04-architecture §5 + §7B.0 (new) | Add path-selection clause; with-ECM canonical; no-ECM demoted to §5A | §5 ASCII diagram shows acl/+cdc/; §5A appendix exists |
| RC-T1-03 | D1-03 | 04-architecture §9.6 (new), 13-decision-log | Air-gap JWKS static-bundle path; encoded as DEC-062 | §9.6 documents both online and air-gap JWKS paths |
| RC-T1-04 | D1-04 | 04-architecture §7B.12, 02-requirements NFR-016 (new), 13-decision-log | ECM PDP circuit breaker (DEC-063); explicit refusal on timeout | NFR-016 entry; §7B.12 annotated "to be calibrated" |
| RC-T1-05 | D1-05 | 04-architecture §9.5 (new), 02-requirements NFR-019 (new), 13-decision-log | Offline model bundle as MVP deliverable (DEC-067); manifest checksum NFR | §9.5 documents bundle composition |
| RC-T1-06 | D1-06 | 04-architecture §4.2 | GPU sub-matrix (consumer / workstation / server) with measured VRAM | §4.2 table now has GPU model column |
| RC-T1-07 | D1-07 | 04-architecture §4.1 | OIDC marked MVP-only; SAML/Kerberos V2 roadmap | §4.1 AuthN row annotated |
| RC-T1-08 | D1-08 | 23-evals §2.1 | Add "NLI accuracy" as standalone metric | §2.1 table has new row |
| RC-T1-09 | D2-01 | 01-product-brief §2 | Drop "empty quadrant"; add head-to-head subsection vs Copilot+Graph / Q Business / Glean | §2 has comparison subsection |
| RC-T1-10 | D2-02 | 01-product-brief §4 | Reframe differentiator as "Contract-grade Citation SLO" | §4 differentiator #3 rewritten |
| RC-T1-11 | D2-03 | 01-product-brief §4 | Replace "on-prem" with open-weight + local LLM + model-swappable triple | §4 differentiator #1 rewritten |
| RC-T1-12 | D2-04 | 01-product-brief §8 | Add unified three-tier timeline table (adapter / sales / outreach priority) | §8 has new table |
| RC-T2-01 | D3-01 / D4-10 | 04-architecture §5 + §5A | Redraw §5 as with-ECM canonical; §5A appendix for no-ECM | Diagram includes acl/+cdc/ |
| RC-T2-02 | D3-02 / D3-03 / Q3 | 04-architecture §7B.12 + §9.4 (new), 13-decision-log, 02-requirements NFR-005 | Rework latency budget with KV/prompt cache + concurrency model (DEC-054 + DEC-066); NFR-005 adds concurrency qualifier | §7B.12 sum < 8 s @ ≤ 2 in-flight; §9.4 documents concurrency model |
| RC-T2-03 | D3-04 / D4-03 | 04-architecture §7B.5, 02-requirements NFR-014, 13-decision-log | DEC-056 split SLA: 60 s webhook / 30 min re-poll | NFR-014 split-SLA; ops alert path documented |
| RC-T2-04 | D3-05 | 04-architecture §6, 13-decision-log | DEC-065 chunking strategy: 1024 + 128 + recursive | §6 chunks entity gains chunk_size/overlap fields |
| RC-T2-05 | D3-06 | 02-requirements REQ-034, 13-decision-log | DEC-059 schema portion promoted to MVP; blue/green V2 | REQ-034 status updated; embedding_model_version column at MVP |
| RC-T2-06 | D3-07 / D4-04 / D4-06 | 04-architecture §12.1 + §7B.13, 13-decision-log | DEC-058 single source of truth = DEC-042; §12.1 rewritten; §7B.13 cross-ref repaired | §12.1 has 5 classes; §7B.13 points to DEC-042 |
| RC-T2-07 | D3-08 | 04-architecture §5 + §5.1 | api-centric orchestration; diagram/rule alignment | §5.1 rule table matches diagram |
| RC-T2-08 | D3-09 | 04-architecture §3.1, 13-decision-log | DEC-057 add 2 scoring columns | §3.1 table 7 columns |
| RC-T2-09 | D3-10 | 04-architecture §12.3 | OTLP exporter env-var config note | §12.3 documents exporter |
| RC-T3-01 | D4-02 | 04-architecture §4.2 + DEC-013 | Measured VRAM occupancy; long-context downgrade tier | §4.2 has measured numbers |
| RC-T3-02 | D4-05 | 04-architecture §6, 02-requirements REQ-007 | Add `conversation_id` + `context_fingerprint` columns to audit_events; promote per DEC-060 | REQ-007 acceptance lists new fields |
| RC-T3-03 | D4-07 / Q5 | 13-decision-log | DEC-068 dev budget raised to ¥800-1,200/month | DEC-068 entry exists |
| RC-T3-04 | D4-08 | 02-requirements REQ-006a | Rewrite neighbor fallback semantics | REQ-006a unambiguous |
| RC-T3-05 | D4-09 | 13-decision-log | DEC-061 enumerate JWT algorithms (RS256/ES256/EdDSA) | DEC-061 entry exists |
| RC-T3-06 | D5-01 (REVISED) / Q user clarification | 04-architecture §7B.9, 01-product-brief §6, 13-decision-log | DEC-071: version-based query semantics; in-flight edits non-goal; no checkout/checkin events tracked | §7B.9 strengthened; non-goal in brief §6; DEC-071 entry exists |
| RC-T3-07 | D5-02 | 04-architecture §6 + §7B.9 | Compound document hierarchy concept; MVP leaf only, V2 aggregation | §6 documents entity hierarchy |
| RC-T3-08 | D5-03 | 02-requirements REQ-045, 13-decision-log | DEC-064 widen REQ-045 acceptance to access_denied path | REQ-045 acceptance includes intent="denied" |
| RC-T3-09 | D5-04 | 04-architecture §7B.5 | acl_changed covers folder-move-induced ACL changes (clarification) | §7B.5 annotation present |
| RC-T3-10 | D5-05 | 04-architecture §7B.10 | V2 roadmap adds write_metadata; MVP excludes | §7B.10 V2 row present |
| RC-T3-11 | D5-06 | 04-architecture §7B.10 | Add map_external_user method to ECMAdapter | §7B.10 contract updated |
| RC-T4-01 | D5-07 | 02-requirements (new NFR row) | Bulk CDC batching + priority NFR | New NFR row exists |
| RC-T4-02 | D5-08 | 09-deployment-ops (Stage 7) | Encryption-at-rest option subsection — deferred to Stage 7 | Spec-writer task |
| RC-T4-03 | D6 security | 04-architecture §12.5 (new), 02-requirements NFR-017 + NFR-018 | Threat model + widget security + rate limit | §12.5 exists; NFR-017/018 exist |
| RC-T4-04 | D6 security / Q4 | 04-architecture §7B.0 (new) + 13-decision-log | DEC-055 co-location assumption | §7B.0 documents co-location |
| RC-T4-05 | D6 traceability | 02-requirements REQ-035, 13-decision-log | DEC-060 fingerprint schema promoted to MVP | REQ-035 status updated |
| RC-T4-06 | Q6 | 02-requirements REQ-006d, 13-decision-log | DEC-069 both modes first-class | REQ-006d notes both shippable |
| RC-T4-07 | Q7 / D7-17 | 13-decision-log + confirmed-context | DEC-070 audit append-only wins; GDPR deferred | DEC-070 entry exists |
| RC-T5-01 | D6 reliability | 02-requirements (new NFR row) | Concurrency cap + queue_depth metric per DEC-066 | New NFR row exists |
| RC-T6-01 | D7-15 | 23-evals §6 (new) | Customer onboarding runbook for refusal rate spikes | §6 exists |
| RC-T6-02 | D7-01..07 collective | 09-deployment-ops (Stage 7) | Driver matrix, Docker version, ingest resume — deferred to Stage 7 | Spec-writer task |
| RC-T8-01 | D7-08..14 collective | 20-agent-behavior + 04-architecture | CDC idempotency / parser tolerance / idempotency key / known limitations — partially MVP, partially V2 | Selective updates per finding |
| RC-T8-02 | Q1 / first-wave market | 01-product-brief §2 + §8 + §10, 13-decision-log | DEC-072 AU + NZ first-wave; RISK-019..021 added | §10 has new risks |

---

## Fix Audit (2026-06-28)

Phase 3 consistency sweep complete. Status of every Required Change (RC) listed in the table above:

| RC ID | Status | Landed in |
|---|---|---|
| RC-T1-01 (English-only stack) | **FIXED** | DEC-052 + 04-architecture §4.1/§4.2 + 02-requirements REQ-003/NFR-003/NFR-001 + 23-evals §2.2 + 01-product-brief §5 row + RISK-003/012 annotations + 90-stage1-trend supersede note |
| RC-T1-02 (with-ECM canonical path) | **FIXED** | DEC-053 + 04-architecture §5 + §5A + §7B.0 |
| RC-T1-03 (Air-gap JWKS path) | **FIXED** | DEC-062 + 04-architecture §9.6 |
| RC-T1-04 (ECM PDP circuit breaker) | **FIXED** | DEC-063 + 04-architecture §7B.12 + 02-requirements NFR-016 |
| RC-T1-05 (Offline model bundle) | **FIXED** | DEC-067 + 04-architecture §9.5 + 02-requirements NFR-019 |
| RC-T1-06 (GPU sub-matrix) | **FIXED** | 04-architecture §4.2.1 |
| RC-T1-07 (OIDC MVP-only) | **FIXED** | 04-architecture §4.1 AuthN row |
| RC-T1-08 (NLI accuracy metric) | **FIXED** | 23-evals §2.1 |
| RC-T1-09 (head-to-head competitive comparison) | **FIXED** | 01-product-brief §2.1 |
| RC-T1-10 (Citation SLO reframe) | **FIXED** | 01-product-brief §4 differentiator #3 |
| RC-T1-11 (Open-weight + local + swappable triple) | **FIXED** | 01-product-brief §4 differentiator #1 |
| RC-T1-12 (Three-tier priority timeline) | **FIXED** | 01-product-brief §8 GTM subsection |
| RC-T2-01 (§5 canonical diagram) | **FIXED** | 04-architecture §5 + §5A |
| RC-T2-02 (Latency restructure + concurrency) | **FIXED** | DEC-054 + DEC-066 + 04-architecture §7B.12 + §9.4 + 02-requirements NFR-005 |
| RC-T2-03 (Retention SLA split) | **FIXED** | DEC-056 + 04-architecture §7B.5 + 02-requirements NFR-014 |
| RC-T2-04 (Chunking strategy) | **FIXED** | DEC-065 + 04-architecture §4.1 + §6 |
| RC-T2-05 (Double-collection schema MVP) | **FIXED** | DEC-059 + 02-requirements REQ-034 |
| RC-T2-06 (Refusal taxonomy SSOT) | **FIXED** | DEC-058 + 04-architecture §12.1 rewritten + §7B.13 cross-ref repaired + 20-agent §6 + 02-requirements REQ-006d |
| RC-T2-07 (api-centric orchestration) | **FIXED** | 04-architecture §5 + §5.1 |
| RC-T2-08 (Comparison +2 scoring dimensions) | **FIXED** | DEC-057 + 04-architecture §3.1 |
| RC-T2-09 (OTLP exporter note) | **FIXED** | 04-architecture §12.3 |
| RC-T3-01 (Measured VRAM annotation) | **DEFERRED (Stage 7)** | 04-architecture §4.2 carries "Measured VRAM occupancy will be added in Stage 7" pointer; actual measurement requires the cloud-rig validation run which is a Stage 7 deliverable |
| RC-T3-02 (audit_events conversation_id + fingerprint) | **FIXED** | 02-requirements REQ-007 + 04-architecture §6 + 20-agent §2.4 |
| RC-T3-03 (Dev budget raised) | **FIXED** | DEC-068 + confirmed-context Drift Log |
| RC-T3-04 (REQ-006a wording) | **FIXED** | 02-requirements REQ-006a + 04-architecture §12.1 |
| RC-T3-05 (JWT alg whitelist) | **FIXED** | DEC-061 + 04-architecture §4.1 |
| RC-T3-06 (Checkout/checkin out-of-scope) | **FIXED** | DEC-071 + 04-architecture §7B.5 + §7B.9 + 01-product-brief §6 non-goals |
| RC-T3-07 (Compound document hierarchy) | **FIXED** | 04-architecture §6 + §7B.9 |
| RC-T3-08 (REQ-045 denied path) | **FIXED** | DEC-064 + 02-requirements REQ-045 |
| RC-T3-09 (acl_changed covers folder-move) | **FIXED** | 04-architecture §7B.5 |
| RC-T3-10 (write_metadata V2 roadmap) | **FIXED** | 04-architecture §7B.10 contract comment |
| RC-T3-11 (map_external_user) | **FIXED** | 04-architecture §7B.10 |
| RC-T4-01 (Bulk CDC batching NFR) | **DEFERRED (V2)** | Captured in review file D5-07; tracked for V2 NFR introduction once V2 ECM adapter work begins |
| RC-T4-02 (Encryption-at-rest) | **DEFERRED (Stage 7 in 09-deployment-ops)** | Tracked in review D5-08; will land when Stage 7 spec-writer produces 09-deployment-ops |
| RC-T4-03 (Threat model + widget security + rate limit) | **FIXED** | 04-architecture §12.5 + 02-requirements NFR-017/NFR-018 |
| RC-T4-04 (Co-location assumption DEC) | **FIXED** | DEC-055 + 04-architecture §7B.0 |
| RC-T4-05 (Fingerprint schema MVP) | **FIXED** | DEC-060 + 02-requirements REQ-035 + 23-evals §3.3 |
| RC-T4-06 (Both acl_denial_modes first-class) | **FIXED** | DEC-069 + 02-requirements REQ-006d + 04-architecture §12.1 |
| RC-T4-07 (Audit append-only vs GDPR) | **FIXED** | DEC-070 + confirmed-context Drift Log |
| RC-T5-01 (Concurrency cap NFR) | **FIXED** | DEC-066 + 02-requirements NFR-005 (concurrency qualifier) + 04-architecture §9.4 |
| RC-T6-01 (Customer onboarding runbook) | **FIXED** | 23-evals §6 |
| RC-T6-02 (Driver matrix / Docker version / ingest resume) | **DEFERRED (Stage 7 in 09-deployment-ops)** | Implementation-phase edge cases (D7-01..07) tracked for 09-deployment-ops |
| RC-T8-01 (CDC idempotency / parser tolerance / known limits) | **PARTIALLY FIXED** | CDC idempotency added to 04-architecture §7B.5; parser tolerance / idempotency-key client retry / known-limitation annotations remain partially OPEN for Stage 7 spec-writer detail |
| RC-T8-02 (AU + NZ first-wave + RISK-019..021) | **FIXED** | DEC-072 + confirmed-context Drift Log + 01-product-brief §2 / §8 / §10 |

### Phase 3 sweep results

| Check | Result |
|---|---|
| 3.1 Reference completeness — DEC IDs | **PASS** — all referenced IDs ∈ {DEC-001..DEC-072} |
| 3.1 Reference completeness — REQ IDs | **PASS** — all referenced IDs defined in 02-requirements.md |
| 3.1 Reference completeness — NFR IDs | **PASS** — all referenced IDs defined in 02-requirements.md (NFR-001..NFR-020) |
| 3.1 Cross-references (§7B.13 / §12.1 / 20-agent §6 / 23-evals §3.3) | **PASS** — all point at correct DEC/REQ targets |
| 3.2 Numerical sanity — §7B.12 sum (5+250+200+150+30+6500+50+100 = 7,285 ms ≤ 8,000 ms) | **PASS** — ~715 ms headroom |
| 3.2 Numerical sanity — NFR-14 split SLA vs DEC-056 | **PASS** — webhook 60 s + re-poll 30 min consistent |
| 3.2 Numerical sanity — hardware floor 16 GB VRAM vs revised English-only model footprint | **PASS** — Llama-3.1-8B int4 ~5 GB + bge-large-en ~1.3 GB + bge-reranker ~1.1 GB + deberta-base ~0.7 GB ≈ 8.1 GB + KV cache headroom |
| 3.3 Concept-drift — `multilingual` / `Chinese` / `Qwen3` / `bge-m3` | **PASS** — all current-spec occurrences either superseded annotation, comparative text, or historical-trend-research snapshot with explicit supersede note |
| 3.3 Concept-drift — `ECM` consistency with with-ECM canonical | **PASS** — `no-ECM` / `LocalAdapter` only mentioned as fast-path variant or contract position |
| 3.3 Concept-drift — refusal-type enumeration is 5 classes everywhere | **PASS** — no 3-class residue |
| 3.3 Concept-drift — checkout/checkin | **PASS** — only mentions are non-goal annotations and the version_id discussion |
| 3.4 Supersede chain integrity | **PASS** — every DEC-052..072 explicitly names supersedes/supplements relationships; DEC-001..051 not edited in place |
| 3.4 Append-only `git diff specs/13-decision-log.md` | **PASS** — only additions; no removed or modified historical DEC lines |
| 3.5 RC closure | **PASS** — every RC has a status above |

### Open follow-ups (post-MVP)

- RC-T3-01 (measured VRAM) — Stage 7 deliverable; requires cloud-rig validation run
- RC-T4-01 (bulk CDC batching NFR) — V2; tracked in review file D5-07
- RC-T4-02 (encryption-at-rest option) — Stage 7 deliverable in 09-deployment-ops
- RC-T6-02 (driver matrix, Docker version, ingest resume) — Stage 7 deliverable in 09-deployment-ops
- RC-T8-01 partial — CDC idempotency landed; client idempotency-key retry pattern + verify/ parser strict-mode + known-limitation annotations remain for Stage 7

**Round 1 verdict (as of 2026-06-28)**: No CRITICAL or HIGH-severity findings remained OPEN. Spec baseline was declared ready for Stage 6.

**Status update (2026-06-29)**: This Round 1 verdict is **SUSPENDED** pending Round 2 (see below). Stage 6 entry is blocked until Round 2 user-decision gate closes.

---

## Round 2 (2026-06-29) — 2026 best-practice benchmark re-run

### R2.0 — Why Round 2 was opened

Round 1 closed mechanical inconsistencies but did not benchmark the spec against **2026 RAG senior-architect mature choices**. User-initiated post-mortem flagged two material gaps Round 1 missed:

1. **Gap 1 — Concurrency / Redis trade-off**: DEC-034 (no Redis in MVP) was made before DEC-066 (≤2 in-flight cap) forced the concurrency ceiling. The trade-off "accept ≤2 cap" vs "introduce Redis to lift cap" was never explicitly compared in T2 or T5 memos.
2. **Gap 2 — Mid-flight rewriting architecture**: `04-architecture.md §3.2 #2` cites *"frameworks resist mid-flight rewriting"* as a build-from-scratch justification, but the architecture never describes **how** mid-flight rewriting (REQ-020) is implemented. The pipeline (§5 + §8.1) is strictly linear with `verify/` as a single node and no feedback edge.

Round 2 baseline: **2026 RAG senior-architect mature choices** documented in `93-stage5r2-benchmark.md` (95 sources, 22 high / 55 medium / 10 low confidence).

Planning envelope: **2-3 team / 180 days** (DEC-073), with solo-fallback clause. Policy: **MVP pragmatic / V2+ strict** on best-practice alignment (user choice Q2=c on 2026-06-29).

### R2.1 — Round 2 verdict summary

| Topic | CONFIRMED | DIVERGE-JUSTIFIED | MUST-ALIGN | Total |
|---|---|---|---|---|
| HL (headline) | 0 | 0 | 1 | 1 |
| T1 Product-System Fit | 1 | 1 | 0 | 2 |
| T2 Architecture Alternatives | 2 | 0 | 1 (= HL) | 2 (HL shared) |
| T3 Data/API/DB | 2 | 1 | 1 | 4 |
| T4 Security/Privacy/Compliance | 1 | 0 | 2 | 3 |
| T5 Reliability/Ops | 1 | 0 | 2 | 3 (1 = product-question) |
| T6 Build/Test | 1 | 0 | 1 | 2 |
| T8 AI Production Readiness | 2 | 0 | 2 | 4 |
| X Cross-cutting | 1 | 1 | 2 | 4 |
| **Total** | **11** | **3** | **11** (HL counted once) | **25** |

Severity rollup: **1 Critical** (R2-HL-01), **4 High** (R2-T4-02, R2-T4-03, R2-T5-02, R2-T8-01), **6 Medium**, **rest informational**.

### R2.HL — Headline finding (Critical)

#### R2-HL-01 [Critical] DEC-032 §3.2 rationale #2 is outdated against 2026 senior-architect default

**Evidence**: `93-stage5r2-benchmark.md` Gap 2 (`high` confidence) — LangGraph (32k stars, 34.5M monthly downloads, named adopters Klarna / Uber / LinkedIn / AppFolio) and LlamaIndex Workflows 1.0 are **explicitly designed for mid-flight critique-rewrite loops**. Industry signal: "Over 70% of production agents adopted some form of graph structure (DAG or state machine), not simple linear Chain" ([Reactify, LangGraph in 2026](https://www.reactify-solutions.com/articles/langgraph-production-agents-2026); `medium`). Self-RAG and CRAG (both ICLR 2024) describe the academic pattern; LangGraph / Workflows are the production implementation vehicles. Streaming/token-level interception is research-grade, not production default.

**Spec position**: [04-architecture.md §3.2 #2](04-architecture.md), [§5 module map](04-architecture.md), and [§8.1 pipeline](04-architecture.md) show a strictly linear pipeline: `api → retrieve → rerank → llm → format → verify → audit`. `verify/` is a single node with no feedback edge to `llm/`. REQ-020 (V2 claim decomposition) is listed inside `verify/` but the architecture has no support for it to feed back into generation.

**Severity rationale**: this directly contradicts a load-bearing rationale of DEC-032 (build-from-scratch). If the rationale is invalid, DEC-032 needs re-justification or partial reversal. Cascades into REQ-020 V2 deliverability, REQ-021/022 V2 ReAct loop, and the entire `verify/` topology. **Cannot proceed to Stage 6 without resolution.**

**Three forward paths** (decision required before Stage 6 entry):

- **(a) Keep build-from-scratch + linear pipeline; rewrite §3.2 #2 rationale.** Mid-flight rewriting becomes "hand-rolled FSM controller inside `verify/` that re-prompts `llm/` with the failed-claim list as input". Acceptable under benchmark's "hand-rolled finite-state controller acceptable for solo team if checkpoint + replay are explicit". Requires explicit checkpoint + replay design in spec. Lowest scope change; highest spec-writing cost (must design FSM correctness yourself).

- **(b) LangGraph for verify subgraph only.** [`verify/`] becomes a LangGraph state machine (`writer → fact-checker → re-write-on-fail` loop). Rest of pipeline remains hand-rolled. Lowest framework-adoption cost; REQ-020 V2 lands naturally. Compatible with Q2=c (MVP pragmatic adoption, V2+ strict alignment). **Recommended.**

- **(c) Full LangGraph adoption.** Whole pipeline becomes a graph. Maximum 2026 alignment; biggest scope + onboarding cost. Justified only if multiple subgraphs need state-machine semantics (currently only `verify/` clearly does).

**Recommendation: (b)**. Under DEC-073 envelope, team can absorb LangGraph onboarding for the most complex node. Rest of pipeline stays simple and team-owned. DEC-032 §3.2 #2 rationale gets honestly retired; rationale #1 (verify on hot path), #3 (audit fingerprint), and #4 (LCC model swap) still hold for the rest of the stack.

DEC consequence if (b) accepted: new DEC supersedes DEC-032 partial. Adopt LangGraph 0.2.x for `verify/` subgraph; document non-adoption rationale for the rest of the pipeline; preserve REQ-033 model-adapter abstraction at the graph node level.

### R2.T1 — Product-System Fit

#### R2-T1-01 [CONFIRMED] Positioning aligned with 2026 enterprise RAG market patterns
Benchmark §Topic 8 confirms two-layer authorization is the enterprise default (Glean, AWS Q Business, Microsoft Graph Connectors). GroundedDocs `04-architecture §7B` matches. Citation-grounded refusal positioning is distinctive but not contradicted by 2026 patterns.

#### R2-T1-02 [DIVERGE-JUSTIFIED] Solo-fallback clause (DEC-073) is non-standard among 2026 RAG products
No competitor product publicly maintains a "solo-fallback subset" discipline. Justified by GroundedDocs' specific planning envelope; honesty is preferable to aspirational team assumption. Maintain.

### R2.T2 — Architecture Alternatives

#### R2-T2-01 [MUST-ALIGN] Pipeline shape
Subsumed by **R2-HL-01**. Decision required.

#### R2-T2-02 [CONFIRMED] Build-from-scratch over fork (RAGFlow et al)
Remains defensible under DEC-073 envelope. DEC-032 §3.2 rationale #1 (verify on hot path), #3 (audit fingerprint), #4 (LCC model swap) still hold. Only #2 is outdated.

#### R2-T2-03 [CONFIRMED] vLLM serving choice
TGI already excluded (DEC-012, predates Round 2). Benchmark §Topic 7 confirms TGI archived March 2026; vLLM is 2026 dominant choice on 16 GB single-host. Spec is correctly aligned.

### R2.T3 — Data, API, Database

#### R2-T3-01 [CONFIRMED] Postgres SKIP LOCKED queue pattern
pg-boss + pgmq are 2026 production-grade peers using exactly the same pattern (`93-stage5r2-benchmark.md` §Topic 2). DEC-038 is 2026-aligned.

#### R2-T3-02 [DIVERGE-JUSTIFIED] Postgres-as-everything at MVP (relational + audit + queue + trace store)
Benchmark §Topic 2 explicitly endorses Postgres-only at ≤2 concurrent: "Postgres-only fully credible at ≤2 concurrent users; Redis adds operational cost not justified at that scale". DEC-034 + DEC-066 combo holds. **Verified**: no LISTEN/NOTIFY usage in spec, so the documented scaling trap (`high` confidence per Recall.ai post-mortem + PgDog analysis) does not apply.

#### R2-T3-03 [MUST-ALIGN, High] Langfuse roadmap risk
Spec lists Langfuse for V2 (`04-architecture.md §4.1` observability row, §12.3). Benchmark §Topic 6 notes **Langfuse was acquired by ClickHouse in January 2026** and Helicone went into maintenance mode March 2026 (post-Mintlify acquisition). Roadmap risk for self-hosted users. Spec must add roadmap-risk annotation and name a contingency (Phoenix Arize / LangSmith / OTEL-only with custom dashboards).

#### R2-T3-04 [CONFIRMED] Refusal taxonomy schema (5-class + acl_denial_mode + dual reason columns)
More advanced than benchmark default. Benchmark §Topic 9 rates "typed refusal taxonomy in production" at `low` confidence — academic taxonomies exist but few production references. Spec **leads the market** here; preserve as a differentiator.

### R2.T4 — Security, Privacy, Compliance

#### R2-T4-01 [CONFIRMED] Two-layer authorization matches enterprise default
Glean, AWS Q Business, Microsoft Graph Connectors all follow the same pre-filter + post-check pattern. GroundedDocs §7B is industry-aligned.

#### R2-T4-02 [MUST-ALIGN, High] Layered safety rails missing in MVP
Spec has NLI verifier but no input/output guards. Benchmark §Topic 9 (`high` confidence) shows 2026 mature layered default = **Llama Prompt Guard 2 (input rail) + retrieval rail + Llama Guard 3 / NeMo Guardrails (output rail) + NLI faithfulness check**. 

Under Q2=c: **MVP DIVERGE-JUSTIFIED** (NLI verifier + 5-class refusal alone is a functional safety floor; adding three guard models inflates VRAM beyond the 16 GB floor); **V2 MUST-ALIGN** — add explicit V2 roadmap row for layered rails (Llama Guard 3 + NeMo Guardrails). Document MVP-only rationale in `20-agent-behavior.md`.

#### R2-T4-03 [MUST-ALIGN, High] Stale-ACL TTL discipline not explicit
Benchmark §Topic 8 (`high`): "Stale-ACL detection (TTL + force-refresh) is mandatory in regulated deployments." Spec §7B.5 has CDC closure (DEC-051 webhook + 30-min re-poll) but no explicit **per-query TTL** on the local ACL cache. Add: ACL cache TTL declaration (recommended 5 min) + force-refresh-on-exceed before ACL evaluation.

### R2.T5 — Reliability, Observability, Operations

#### R2-T5-01 [CONFIRMED] ≤2 concurrency cap on single host
2026-defensible per benchmark §Topic 2 + §Topic 7. vLLM single-instance throughput on 16 GB matches this ceiling.

#### R2-T5-02 [PRODUCT-QUESTION, High] Is ≤2 concurrent sufficient for AU/NZ vendor demos?
Not a tech question. Under DEC-072 (AU/NZ first-wave) and B2B2B (vendor evaluators run multi-user pilots), ≤2 may not match evaluator expectations. Options:

- (i) **Hold cap, document upfront** as "demo-mode deliberate constraint". Vendor evaluators are told "production deployment lifts cap via Helm + multi-host (V2 roadmap)". Recommended.
- (ii) Lift cap to ≥5 via V2 multi-host topology in MVP (rejects DEC-034 partial — needs proper task queue, possibly Redis).
- (iii) Add Redis cache layer in MVP to lift cap on single host (rejects DEC-034 fully; benchmark says this is "Redis still wins" camp's choice).

Recommendation: **(i)** — hold cap + demo-mode framing. Maintains DEC-034 + DEC-066. **User decision required.**

#### R2-T5-03 [MUST-ALIGN, Medium] OTEL GenAI semantic conventions
Benchmark §Topic 6 (`high`): 2026 default = **OpenTelemetry GenAI semantic conventions** + Langfuse/equivalent. Spec §12.3 has OTLP exporter env-var (per RC-T2-09) but no explicit reference to the GenAI conventions or the standard span structure (`retrieve → rerank → generate → verify`). Add reference; align span structure.

### R2.T6 — Build, Test, Verification

#### R2-T6-01 [MUST-ALIGN, Medium] Golden set size
`23-evals-guardrails.md §2.2` specifies 50 questions. Benchmark §Topic 5 (`high`): 2026 default is **100-300 prompts** with 5-10% production sampling + weekly human review on 50-100 traces. Under DEC-073 envelope (180 days, 2-3 team) the larger set is feasible.

Recommendation: **150-200 prompts for MVP**, with 50 of those as the smoke-test subset (preserves the original 50-question goldset as an inner ring for CI fast-feedback). User confirmation on number.

#### R2-T6-02 [CONFIRMED] LLM-as-judge with distinct judge model
Spec discipline matches benchmark non-negotiable: judge model is decoupled from generation model.

### R2.T8 — AI Agent Production Readiness

#### R2-T8-01 [MUST-ALIGN, High] V2 ReAct loop architecture
REQ-020 + REQ-021/022 (V2 ReAct) need explicit design. If R2-HL-01 (b) is chosen, this is natural (LangGraph state machine in `verify/` extends to a larger ReAct subgraph). If (a), explicit checkpoint + replay design required. Decision flows from R2-HL-01.

#### R2-T8-02 [CONFIRMED] NLI verifier discipline
DeBERTa-class online classification matches benchmark §Topic 9 mature pattern. Auto-GDA-style domain adaptation is the 2026 frontier — preserve as V2/V3 candidate.

#### R2-T8-03 [CONFIRMED] Prompt registry (slot 24)
Version-tracked prompts align with benchmark §Topic 9 (`high`). Spec discipline acceptable.

#### R2-T8-04 [MUST-ALIGN, Medium] Iteration cap + cost ceiling
Spec has NLI/verify thresholds but **no explicit iteration cap** for V2 ReAct loops; **no cost ceiling per turn**. Both are mandatory per skill T8 + benchmark §Topic 9. Add NFR for MVP (trivial: N=1 since no agent loop) and V2 (e.g., N≤5 iterations, ≤$0.10 per turn at customer-chosen open-weights cost, but configurable).

### R2.X — Cross-cutting sweep (Phase C — 4 dimensions)

#### R2-X1 Compatibility [MUST-ALIGN, see HL]
REQ-020 V2 claim decomposition is mid-flight rewriting. In linear pipeline (R2-HL-01 (a)), V2 = architectural redo. In graph (R2-HL-01 (b)/(c)), V2 = node addition. **Compatibility forward-pressure favors (b).** Subsumed by R2-HL-01.

#### R2-X2 Extensibility [CONFIRMED]
LCC services (DEC-028 4-tier) + REQ-033 model adapter abstraction remain valid under any R2-HL-01 option. Framework adoption at `verify/` subgraph (option b) does not break the adapter contract — adapters wrap models, graph wraps orchestration; they are orthogonal.

#### R2-X3 Maintainability [DIVERGE-JUSTIFIED, becomes Stage 6 discipline]
Solo-current vs team-envelope (DEC-073) creates two-mode design responsibility. **Stage 6 spec-writer must annotate each MVP feature with `solo-deliverable` or `team-only` tag**. This is Phase D / Stage 6 discipline, not a Round 2 spec edit.

#### R2-X4 Traceability [MUST-ALIGN, Medium]
DEC-073 cascade — supersede chain must be explicit on every load-bearing DEC affected by the new envelope. Currently:

- DEC-073 supersedes DEC-026 (timeline) ✓ recorded
- DEC-074 supersedes DEC-068 (budget) ✓ recorded
- **DEC-032 supersede pending R2-HL-01 (b)/(c) decision**
- DEC-034 + DEC-066: not superseded (Round 2 verdict = DIVERGE-JUSTIFIED holds them)

Phase D must verify chain integrity after R2-HL-01 decision lands.

### R2.RC — Required Changes (Round 2) mapping table

ID format: `RC-R2-<topic>-<seq>`. Distinct ID space from Round 1's `RC-T<n>-<m>` to avoid collision. All Round 2 RCs are consumed by Phase D + Stage 7 spec-writer.

| RC ID | Origin | Severity | Target spec slot | Fix direction | Acceptance check |
|---|---|---|---|---|---|
| **RC-R2-HL-01** | R2-HL-01 | Critical | DEC-032 + `04-architecture` §3.2 + §5 + §8 + new DEC | Decide (a/b/c); rewrite §3.2 #2 rationale; (b)/(c) introduces LangGraph + new DEC; (a) requires explicit FSM + checkpoint+replay spec | §3.2 #2 rationale rewritten; §5/§8 reflect chosen shape |
| RC-R2-T3-03 | R2-T3-03 | High | `04-architecture` §4.1 + §12.3 | Annotate Langfuse roadmap risk (ClickHouse acquisition 2026-01) + name contingency (Phoenix / LangSmith / OTEL-only) | §4.1 has roadmap-risk note |
| RC-R2-T4-02 | R2-T4-02 | High | `04-architecture` §12 + `20-agent-behavior.md` + `02-requirements` (new V2 NFR row) | V2 roadmap for layered rails (Llama Prompt Guard 2 + Llama Guard 3 + NeMo Guardrails); MVP NLI-only with explicit rationale | V2 row exists; MVP rationale stated |
| RC-R2-T4-03 | R2-T4-03 | High | `04-architecture` §7B.5 | Explicit per-query ACL cache TTL (recommended 5 min) + force-refresh-on-exceed | §7B.5 has TTL number |
| RC-R2-T5-02 | R2-T5-02 | High | `01-product-brief` §5/§8 + `04-architecture` §9 | If user picks (i): "demo-mode" framing for ≤2 cap + V2 multi-host roadmap pointer | brief has explicit demo-mode statement |
| RC-R2-T5-03 | R2-T5-03 | Medium | `04-architecture` §12.3 | Reference OTEL GenAI semantic conventions; align span structure to retrieve→rerank→generate→verify | §12.3 cites conventions |
| RC-R2-T6-01 | R2-T6-01 | Medium | `23-evals-guardrails.md` §2.2 | Golden set 50 → 150-200; 50-prompt smoke-test inner ring preserved | §2.2 documents both numbers |
| RC-R2-T8-01 | R2-T8-01 | High | `20-agent-behavior.md` + `04-architecture` §8 | V2 ReAct architecture: graph (if HL-01 b/c) or FSM+checkpoint (if a) | V2 design exists |
| RC-R2-T8-04 | R2-T8-04 | Medium | `02-requirements` (new NFR row) | Iteration cap NFR (MVP N=1, V2 N≤5) + cost ceiling per turn | NFR row exists |
| RC-R2-X3 | R2-X3 | Medium | Stage 6 `00-spec-index.md` (future) | Per-feature `solo-deliverable` / `team-only` annotation discipline | Stage 6 spec-writer enforces |
| RC-R2-X4 | R2-X4 | Medium | `13-decision-log.md` (after HL-01) | DEC-032 supersede entry if R2-HL-01 (b)/(c) | Chain integrity verified by Phase D |

### R2.Gate — User decision gate (RESOLVED 2026-06-29)

User chose more aggressive 2026 alignment than recommended on 3 of 4 gates. Choices and resulting DECs:

| Gate | User choice | DEC issued | Supersedes |
|---|---|---|---|
| R2-HL-01 pipeline shape | **(c) Full LangGraph adoption** | DEC-075 | DEC-032 partial (§3.2 #2 rationale retired; build-from-scratch dropped at orchestration layer) |
| R2-T5-02 concurrency | **(iii) Redis in MVP to lift cap** | DEC-076 | DEC-034 partial (Redis allowed; Celery/Kafka still excluded); DEC-066 cap to be recalculated |
| R2-T4-02 safety rails | **MVP layered rails (demo date pushed)** | DEC-077 | Reverses R2-T4-02 recommendation; demo date push acknowledged |
| R2-T6-01 golden set | **150-200 + 50 smoke (recommended)** | DEC-078 | Amends `23-evals-guardrails.md §2.2` |

### R2.Cascade — Cascade decisions (RESOLVED 2026-06-29)

| Cascade | User choice | DEC issued | Supersedes |
|---|---|---|---|
| Q1 Hardware floor | **24 GB VRAM floor** | DEC-079 | DEC-041 (24 GB original), DEC-052 (16 GB English-only) |
| Q2 Demo date | **2027-03-26 (+90d conservative)** | DEC-080 | DEC-026 (2026-09-27), DEC-073 timeline portion (2026-12-26) |
| Q3 Solo-fallback | **Solo path = team scope, longer timeline (2027-05+)** | DEC-081 | DEC-073 solo-fallback clause (180-day promise withdrawn) |

Side effects recorded:
- RISK-007 severity raised to **HIGH**; team-materialization checkpoint pinned at **2026-08-29**
- `confirmed-context.md` §5 RISK-007 + §6 Time Horizon rewritten
- Stage 6 spec-writer instruction: annotate per-feature team-path vs solo-path timeline delta where meaningful

**Reference (preserved for traceability):**

#### Cascade Q1 — Hardware floor recalculation
DEC-041 (24 GB) → DEC-052 (16 GB, English-only) → ?. Approximate new VRAM budget with DEC-075/076/077 stack:

| Component | Size (int4 unless noted) | Note |
|---|---|---|
| Generation: Llama-3.1-8B-Instruct | ~5 GB | per DEC-052 |
| Embedding: bge-large-en-v1.5 | ~1.3 GB | per DEC-052 |
| Reranker: bge-reranker-v2-m3 | ~1.1 GB | per DEC-052 |
| NLI: deberta-v3-base-mnli | ~0.7 GB | per DEC-052 |
| Input rail: Llama Prompt Guard 2 | ~1.5 GB | new per DEC-077 |
| Output rail: Llama Guard 3 8B | ~5 GB | new per DEC-077 |
| NeMo Guardrails | CPU/RAM only | new per DEC-077 |
| KV cache + headroom | ~6-8 GB | concurrency-dependent |
| **Subtotal** | **~20-22 GB** | **24 GB floor likely required** |

#### Cascade Q2 — New demo date
DEC-073's 2026-12-26 was based on 4 gate items resolving toward MVP-pragmatic. User chose 3 items toward V2-strict (full LangGraph + Redis + MVP layered rails). Realistic delivery push: +30-60 days. Candidate dates: 2027-01-26 (+30d) / 2027-02-26 (+60d) / 2027-03-26 (+90d).

#### Cascade Q3 — Solo-fallback subset re-scoping
DEC-073 promised that the MVP must-have subset must remain solo-deliverable within 180 days if the team does not materialize. Adding full LangGraph + Redis + 3 guard models + 150-200 golden set is **not solo-deliverable** in 180 days. The solo-fallback subset must be redefined. Candidate scope: drop layered rails (return to NLI-only for solo path) and drop full LangGraph (return to hand-rolled FSM for solo path); keep Redis + 150-200 goldset.

---

**Round 2 verdict (final 2026-06-29)**: All gate + cascade decisions RESOLVED. 7 new DECs written (DEC-075..081), 6 prior DECs partially/fully superseded (DEC-026, DEC-032, DEC-034, DEC-041, DEC-052, DEC-068, DEC-073 timeline portion + solo-fallback clause). Stage 6 entry is **UNBLOCKED**. Stage 7 spec-writer consumes the consolidated **RC-R2-\*** mapping table (R2.RC section above) at Stage 7 entry to apply all MUST-ALIGN items.

**Phase D close-out checklist:**

- [x] DEC-075..081 written to `13-decision-log.md` with supersedes annotations
- [x] `confirmed-context.md` §5 (RISK-007 raised to HIGH; team checkpoint 2026-08-29 pinned), §6 (timeline rewritten; per-feature annotation instruction recorded), Drift Log (2 new entries for Gate + Cascade)
- [x] Round 2 memos finalized in `92-stage5-review-memos.md`
- [x] Round 1 verdict "ready for Stage 6" replaced with Round 2 verdict

### R2.FixAudit — Round 2 in-stage application audit (2026-06-29)

Following the same convention as Round 1's Fix Audit, every RC-R2-\* item was applied to existing spec files in Phase E (Stage 5 Round 2 in-stage), not deferred to Stage 7. Only RC-R2-X3 (Stage 6 spec-writer discipline) is correctly deferred to a future stage. RC-R2-X4 closed by DEC supersede entries (Phase D).

| RC ID | Status | Landed in |
|---|---|---|
| RC-R2-HL-01 (Pipeline shape = full LangGraph) | **FIXED** | DEC-075 + `04-architecture` §1 (plain-English summary rewrite) + §2 (5-line elevator rewrite) + §3.2 (rationale rewrite) + §4.1 (LangGraph orchestration row) + §5 (Round 2 supersede block + §5.0 new node/service overview) + §8.1 (verification pipeline as graph nodes with reserved feedback edge) + §8.2 (V2 extension as node addition) + §10.1 (MVP loop = one-shot graph traversal) + `20-agent-behavior` §1 + §2.1 (turn pipeline as LangGraph nodes) |
| RC-R2-T3-03 (Langfuse roadmap risk) | **FIXED** | `04-architecture` §4.1 observability row + §12.3 (roadmap-risk annotation + named contingencies: Phoenix Arize / LangSmith / OTEL-only) |
| RC-R2-T4-02 (Layered safety rails MVP) | **FIXED** | DEC-077 + `04-architecture` §4.1 (3 rail rows: input / output / orchestration) + §5.0 + §8.1 (graph node positions) + §12.2 (layered defense rewrite) + §12.5 threat model (prompt-injection row rewrite, indirect injection now MVP) + `20-agent-behavior` §1 + §2.1 + §6 (5 new failure rows for rail flags + orchestration escalation) + `02-requirements` NFR-021 / NFR-022 / REQ-048 |
| RC-R2-T4-03 (ACL cache TTL discipline) | **FIXED** | `04-architecture` §7B.5 (ACL cache discipline table with per-cache TTL + force-refresh policy) + `02-requirements` NFR-025 |
| RC-R2-T5-02 (Concurrency policy via Redis) | **FIXED** | DEC-076 + `04-architecture` §4.1 (Redis row + persistent / in-request queue split) + §7B.12 (latency budget revised with warm-cache / cold-cache columns) + §9.4 (concurrency model rewrite) + `01-product-brief` §5 MVP table (REQ-047) + `02-requirements` NFR-005 (revised) + REQ-047 |
| RC-R2-T5-03 (OTEL GenAI semantic conventions) | **FIXED** | `04-architecture` §12.3 (explicit reference + LangGraph node span structure) + `02-requirements` NFR-026 |
| RC-R2-T6-01 (Golden set 150-200 + 50 smoke) | **FIXED** | DEC-078 + `23-evals-guardrails` §2.2 (two-ring structure + expansion composition + sampling rates) + `01-product-brief` §5 MVP table + `02-requirements` REQ-049 |
| RC-R2-T8-01 (V2 ReAct architecture) | **FIXED** | `04-architecture` §8.2 (V2 extension as node + feedback edge addition under DEC-075) + `20-agent-behavior` §1 (V2 framing) + §3 (existing ReAct fallback adapted to graph) + §6 failure-table rows for feedback iteration cap |
| RC-R2-T8-04 (Iteration cap + cost ceiling) | **FIXED** | `20-agent-behavior` §3.3 hard-caps table extended (iteration cap N=1 MVP / N≤2 V2; cost ceiling per turn) + `02-requirements` NFR-023 + NFR-024 |
| RC-R2-X1 (Compatibility — REQ-020 forward-pressure) | **FIXED** | Subsumed by RC-R2-HL-01 (graph adoption makes REQ-020 a node addition rather than redo) |
| RC-R2-X3 (Solo / team annotation discipline) | **DEFERRED (Stage 6)** | Tracked as a Stage 6 spec-writer instruction in `confirmed-context.md` §6 ("Per-feature timeline annotation"); will land when `00-spec-index.md` is generated |
| RC-R2-X4 (DEC chain integrity) | **FIXED** | DEC-075..081 written with supersedes entries on DEC-026 / DEC-032 (partial) / DEC-034 (partial) / DEC-041 / DEC-052 / DEC-066 (revised) / DEC-068 / DEC-073 (timeline + solo-fallback portions); `confirmed-context.md` Drift Log has matching entries |

**Phase E sweep results (cross-reference consistency check):**

| Check | Result |
|---|---|
| Reference completeness — DEC IDs | **PASS** — DEC-075..081 referenced in 13-decision-log + supersede annotations consistent |
| Reference completeness — REQ IDs | **PASS** — REQ-046..049 added in 02-requirements §Functional |
| Reference completeness — NFR IDs | **PASS** — NFR-021..026 added in 02-requirements §Non-functional |
| Numerical sanity — 16 GB → 24 GB floor | **PASS** — every active reference uses 24 GB; 16 GB appears only in superseded-by-DEC-079 annotations or in `degraded` tier rows |
| Numerical sanity — concurrency ≤2 → 2 floor / 5-8 warm | **PASS** — §7B.12 + §9.4 + NFR-005 all carry the warm-cache / cold-cache delta framing |
| Numerical sanity — demo date 2026-09-27 → 2027-03-26 | **PASS** — all active references use 2027-03-26 with team-materialisation checkpoint 2026-08-29; older dates appear only in supersede chain annotations |
| Concept drift — "no Redis" → Redis hybrid | **PASS** — DEC-034 explicit "no Redis" framing updated in §4.1 to "Redis allowed; Celery/Kafka still excluded"; no orphan "no Redis" mentions remain in active spec sections |
| Concept drift — linear pipeline → graph orchestration | **PASS** — §5 supersede block + §8.1 graph nodes + §10.1 one-shot traversal framing consistent across 04 / 20 / 01 |
| Concept drift — NLI-only safety → layered rails | **PASS** — DEC-077 + NFR-021/022 + REQ-048 + 20-agent §6 failure table all align |
| Supersede chain integrity | **PASS** — DEC-026 → DEC-073 → DEC-080 (timeline); DEC-041 → DEC-052 → DEC-079 (hardware floor); DEC-032 partial → DEC-075 (orchestration); DEC-034 partial → DEC-076 (Redis); DEC-068 → DEC-074 (budget); DEC-073 solo-fallback → DEC-081 (withdrawal) |

- [x] **Phase E — in-stage application of 9 of 11 RC-R2-\* items complete** (RC-R2-X3 deferred to Stage 6 by design; RC-R2-X4 closed by DEC supersedes)
- [x] **Stage 6 entry is UNBLOCKED** — both gate + cascade decisions resolved AND in-stage RC application complete. Stage 7 spec-writer's only Round 2 carry-forward item is RC-R2-X3 (per-feature solo/team annotation discipline during `00-spec-index.md` generation).

---

## Round 3 (2026-06-29 cont.) — Feedback integration

### R3.0 — Why Round 3 was opened

After Round 2 close, the user received external senior-architect feedback at `specs/feedback.txt` (~180 lines, Chinese). The feedback contained ~20 specific optimization suggestions across 6 sections: hidden risks (VRAM, ops, latency), async/parallel optimization, model/compute optimization, state-graph routing, LangGraph framing, loop safety, and JIT auth + federated search.

Approach: focused Explore agent cross-checked each feedback item against the Round 2 spec set; user resolved 3 high-impact direction choices in Phase 3 (Plan-mode workflow); plan file written + approved; Phase E-style in-stage edits applied across 6 spec files.

User direction choices (Phase 3, 2026-06-29):
- **S2.1 (Llama Guard 3 footprint)**: option (a) — keep + int4 AWQ + add SafetyRailAdapter abstraction
- **S3.1 (dynamic verification routing)**: option (b) — V2 admin-configurable intent classifier with audit-always-records discipline
- **S7.3 (federated search)**: option (a) — V3 (post Helm + multi-host)

### R3.1 — Disposition table (20 feedback items)

| # | Feedback item | Coverage | Phase | Disposition |
|---|---|---|---|---|
| **S0.a** | VRAM contention single-GPU | B | F1.1 | New §4.2.2 VRAM allocation policy + co-residency rules + eviction policy |
| **S0.b** | docker-compose ops limits | B | F1.2 | REQ-026 V3 Helm sharpened with 3 trigger thresholds (corpus > 10M chunks / sustained > 8 concurrent / > 3 active pilots) |
| **S0.c** | Latency stack length | B | F1.3 | §8.1 latency philosophy note; references §7B.12 warm/cold + DEC-082 parallel saving |
| **S1.1** | Parallel `safety_input` + `retrieve` | C | F1.4 | §5 + §8.1 + §7B.12 + 20-agent §2.1 — parallel fan-out + `acl/` join; saves ~150 ms warm; DEC-082 + NFR-029 |
| **S1.2** | ACL filter pushdown to Qdrant payload | **A** | F4 | Already DEC-046 + §7B.3 Layer 1 |
| **S2.1** | Replace Llama Guard 3 8B | B | F1.5 | int4 AWQ (~2.5 GB) + new §4.3 SafetyRailAdapter Protocol + REQ-050; DEC-082 supersedes DEC-077 partial |
| **S2.2** | TEI optimization (ONNX/TensorRT) | C | F1.6 | NFR-027 rerank latency p95 ≤ 100 ms with implementation freedom; ONNX backend recommended for AU/NZ public sector |
| **S2.3** | vLLM aggressive optimization | C | F1.6 | NFR-028 chunked prefill mandatory; speculative decoding conditional on VRAM headroom; DEC-083 |
| **S3.1** | Dynamic verification routing | C | F2.1 | V2 REQ-051 + DEC-084 admin-configurable intent classifier with mechanical-fast-path + audit always-on discipline |
| **S3.2** | V2 streaming fast/slow lane | B | F2.2 | V2 REQ-052 sentence-level streaming NLI with early-stop |
| **S4.1** | Sentence-level streaming NLI | B | F2.2 | Consolidated with S3.2 → REQ-052 |
| **S4.2** | `verify/` fast vs slow path split | B | F1.7 | §8.1 explicit `mechanical_fast_path` (≤1 ms, early-exit) / `nli_slow_path` (≤600 ms warm) bifurcation; DEC-082 |
| **S4.3** | Async non-blocking NLI | C | F3.1 | V3 REQ-054 advisory NLI mode with mandatory mechanical + audit; SLA waiver gated |
| **S5** | LangGraph as runtime not architecture | B | F1.8 | §3.2 + §5 framing reword to "typed execution graph; LangGraph 0.2.x current runtime"; alternative runtimes documented as zero-cost swaps |
| **S6.1** | State reducer for failed_claims | C | F1.9 | New §5.1.1 typed state schema + Annotated reducers + termination guarantees |
| **S6.2** | Conditional rewrite prompt template | B | F2.3 | REQ-022 V2 extension + 20-agent §3.3 — `rewrite_repair` template activated on `revision_count > 0` |
| **S6.3** | Hard revision_count circuit breaker | **A** | F4 | Already 20-agent §3.3 + DEC-075 N≤2 hard |
| **S6.4** | Streaming UX two-pass display | B | F2.4 | V2 REQ-053 widget two-pass + diff display; pairs with REQ-052 |
| **S7.1** | ACL trim as JIT auth proxy | B | F1.10 | §7B title + §7B.4 terminology lift to "Just-In-Time"; semantically unchanged from DEC-046 + DEC-063 |
| **S7.2** | Reverse audit injection to ECM | **A** | F4 | Already REQ-045 + DEC-047 + DEC-064 |
| **S7.3** | Federated search for legal-hold | C | F3.2 | V3 REQ-055 + DEC-085 + new §8.3 federated retrieval path; ECMSearchAPIAdapter |

### R3.2 — RC-R3-\* mapping table

| RC ID | Origin | Severity | Target | Status | Landed in |
|---|---|---|---|---|---|
| RC-R3-F1.1 | S0.a | Medium | 04-arch §4.2.2 | **FIXED** | New §4.2.2 VRAM allocation policy + co-residency rules + eviction policy |
| RC-R3-F1.2 | S0.b | Medium | 02-req REQ-026 | **FIXED** | REQ-026 V3 trigger thresholds inserted (chunk count / concurrency / active pilots) |
| RC-R3-F1.3 | S0.c | Low | 04-arch §8.1 | **FIXED** | Latency philosophy note added; references DEC-082 + §7B.12 |
| RC-R3-F1.4 | S1.1 | High | 04-arch §5 + §8.1 + §7B.12; 20-agent §2.1 | **FIXED** | Parallel fan-out + acl/ join + diagram updated across 04-arch + 20-agent; NFR-029 |
| RC-R3-F1.5 | S2.1 | High | 04-arch §4.1 + new §4.3; 02-req REQ-050; 13-log DEC-082 | **FIXED** | int4 AWQ LG3 + SafetyRailAdapter Protocol + REQ-050; DEC-082 |
| RC-R3-F1.6 | S2.2 + S2.3 | Medium | 02-req NFR-027 + NFR-028; 13-log DEC-083 | **FIXED** | NFR-027 (TEI rerank) + NFR-028 (vLLM optimization flags); DEC-083 |
| RC-R3-F1.7 | S4.2 | Medium | 04-arch §8.1; 20-agent §6 | **FIXED** | mechanical_fast_path / nli_slow_path explicit bifurcation + 20-agent failure-table row |
| RC-R3-F1.8 | S5 | Low | 04-arch §3.2 + §5 | **FIXED** | "typed execution graph; LangGraph 0.2.x current runtime" framing reword |
| RC-R3-F1.9 | S6.1 | Low | 04-arch §5.1.1 | **FIXED** | New §5.1.1 QueryGraphState + Annotated reducers + termination guarantees |
| RC-R3-F1.10 | S7.1 | Low | 04-arch §7B title + §7B.4 | **FIXED** | JIT terminology lift; semantically unchanged |
| RC-R3-F2.1 | S3.1 | High | 02-req REQ-051; 04-arch §8.2; 13-log DEC-084 | **V2 ROADMAP** | REQ-051 V2 + DEC-084 written; §8.2 V2 extension section updated |
| RC-R3-F2.2 | S3.2 + S4.1 | High | 02-req REQ-052; 04-arch §8.2 | **V2 ROADMAP** | REQ-052 streaming NLI + §8.2 description |
| RC-R3-F2.3 | S6.2 | Medium | 02-req REQ-022 amend; 20-agent §3.3 | **V2 ROADMAP** | rewrite_repair template + activation rule documented in §3.3 |
| RC-R3-F2.4 | S6.4 | Medium | 02-req REQ-053 | **V2 ROADMAP** | REQ-053 widget two-pass + diff display |
| RC-R3-F3.1 | S4.3 | Medium | 02-req REQ-054 | **V3 ROADMAP** | REQ-054 advisory NLI mode; mechanical + audit always synchronous |
| RC-R3-F3.2 | S7.3 | High | 02-req REQ-055; 04-arch §8.3; 13-log DEC-085 | **V3 ROADMAP** | REQ-055 + DEC-085 + new §8.3 federated retrieval path; ECMSearchAPIAdapter |
| RC-R3-F4 | S1.2 / S6.3 / S7.2 | — | (already-covered audit) | **NO EDIT** | Mapping documented in §R3.1 disposition table |

### R3.3 — Phase F sweep results

| Check | Result |
|---|---|
| Reference completeness — DEC IDs | **PASS** — DEC-082..085 referenced in 13-decision-log + supersede annotations on DEC-077 partial / DEC-079 partial / DEC-012 supplement / DEC-005 supplement / DEC-046 supplement / DEC-051 supplement |
| Reference completeness — REQ IDs | **PASS** — REQ-050..055 added in 02-requirements §Functional |
| Reference completeness — NFR IDs | **PASS** — NFR-027..029 added in 02-requirements §Non-functional |
| Numerical sanity — VRAM allocation | **PASS** — §4.2.2 cold-cache subtotal ~18.1 GB / warm-cache ~22.1 GB; both ≤ 24 GB floor with documented headroom |
| Numerical sanity — §7B.12 latency budget | **PASS** — warm-cache p95 ≤ 7,160 ms (~840 ms headroom; improved from Round 2 ~690 ms via parallel `safety_input ∥ retrieve` per DEC-082); cold-cache lower bound ≤ 7,860 ms — both under NFR-005 8 s cap |
| Numerical sanity — REQ-026 V3 trigger thresholds | **PASS** — 10 M chunks / > 8 concurrency / > 3 active pilots; consistent with DEC-066 (warm-cache cap 5-8) + §9.4 |
| Concept drift — "Llama Guard 3 8B int4" → "int4 AWQ" | **PASS** — active mentions in §4.1 + §4.2.2 + 20-agent §2.1 all read "int4 AWQ" or annotated as DEC-082 supersede |
| Concept drift — "safety_input → retrieve" sequential | **PASS** — replaced with "safety_input ∥ retrieve" parallel notation across 04-arch §5 + §8.1 + §7B.12 + 20-agent §2.1 |
| Concept drift — "verify/" mechanical-fast / NLI-slow | **PASS** — §8.1 explicit split + 20-agent §6 failure-table early-exit row + 23-evals §2.2 mechanical-fast-path early-exit prompts |
| Concept drift — JIT terminology | **PASS** — §7B title + §7B.4 use Just-In-Time; REQ-036/REQ-037 references intact |
| Cross-document reference — REQ-050 SafetyRailAdapter | **PASS** — referenced from 04-arch §4.1 row + §4.3 contract + DEC-082 |
| Cross-document reference — DEC-084 NLI advisory waiver | **PASS** — referenced from REQ-051 + 04-arch §8.2 + 20-agent §3.3 |
| Cross-document reference — DEC-085 federated retrieval | **PASS** — referenced from REQ-055 + 04-arch §8.3 + 01-brief §7 V3 + 13-log |
| Supersede chain integrity | **PASS** — DEC-082 explicitly supersedes DEC-077 partial (quantization) + DEC-079 partial (allocation); DEC-083 supplements DEC-012; DEC-084 supplements DEC-005; DEC-085 supplements DEC-046 + DEC-051 |

### R3.4 — Round 3 close-out

- [x] DEC-082..085 written to `13-decision-log.md` with supersedes annotations
- [x] REQ-050..055 added to `02-requirements.md` Functional table
- [x] NFR-027..029 added to `02-requirements.md` Non-functional table; REQ-026 V3 thresholds sharpened
- [x] `04-architecture.md` updated: §1 plain-English + §2 5-line elevator (Round 2 already updated; Round 3 references hold); §3.2 LangGraph runtime framing; §4.1 LG3 int4 AWQ row; §4.2.2 NEW VRAM allocation policy; §4.3 NEW SafetyRailAdapter contract; §5 parallel fan-out + Round 3 supersede block; §5.1.1 NEW typed state reducers; §7B title + §7B.4 JIT terminology; §7B.12 latency budget recalc; §8.1 mechanical-fast / NLI-slow split + parallel pipeline; §8.2 V2 extension expanded (intent classifier + streaming + repair template); §8.3 NEW V3 federated retrieval; §8.5 renumbered (was §8.4 thresholds)
- [x] `20-agent-behavior.md` updated: §2.1 parallel pipeline diagram; §3.3 hard-caps table extended (rewrite_repair + intent classifier); §6 failure table early-exit row
- [x] `01-product-brief.md` updated: V2 deferred (REQ-051, REQ-052, REQ-053); V3 deferred (REQ-054, REQ-055)
- [x] `23-evals-guardrails.md` updated: §2.2 goldset expansion (parallel-edge join correctness + mechanical-fast-path early-exit + SafetyRailAdapter swap regression)
- [x] `confirmed-context.md` Drift Log: new Round 3 entry with explicit DEC list
- [x] Phase F sweep complete — all numerical sanity + concept drift + cross-document reference checks PASS

**Round 3 verdict (final 2026-06-29)**: 4 new DECs, 6 new REQs, 3 new NFRs, 11 in-stage edits, 5 V2 roadmap entries, 2 V3 roadmap entries, 3 already-covered audit trails. All 20 feedback items have a placed disposition; none rejected, none silently dropped. **Stage 6 entry remains UNBLOCKED** — Stage 7 spec-writer carries forward RC-R2-X3 (per-feature solo/team annotation) only.

---

## Round 4 (2026-07-03) — Independent architecture review

### R4.0 — Why Round 4 was opened

An independent architectural review (run outside the `idea-to-specs` skill flow, against the full spec set as it stood after Round 3) audited all seven review dimensions (hidden assumptions, product positioning, architectural soundness, design errors, ECM completeness, non-functional attributes, edge cases) with an explicit mandate to look past what Rounds 1-3 had already closed. The review's central observation: Rounds 1-3 were rigorous on **cross-document consistency** (do all files agree with each other) but had a blind spot on **capability preservation across substitutions** — verifying that when a DEC swapped one model/parameter for another, the substitute still provided the capability the original was standing in for. Two of the findings below are direct instances of that blind spot.

### R4.1 — Findings and disposition

| # | Finding | Severity | Disposition |
|---|---|---|---|
| F1 | DEC-052's embedding swap (`bge-m3` → `bge-large-en-v1.5`, English-only narrowing) replaced a model with native dense+sparse+ColBERT output with a **dense-only** model, silently breaking REQ-003's "hybrid dense+sparse retrieval" requirement — no sparse-vector source existed anywhere in the resulting stack | Critical | **FIXED** — user chose to revert to `bge-m3` (DEC-086) rather than bolt on a separate sparse encoder |
| F2 | `verify/.mechanical_fast_path`'s citation-verification pseudocode (`04-architecture.md §8.1`) checked citations against the raw pre-Layer-2 `retrieval_set` rather than the Layer-2-authorized `reranked_set` — a chunk removed by ACL trim but still present in the raw candidate pool could pass a hallucinated-citation check, an ACL bypass via citation fabrication | Critical | **FIXED** (DEC-088) |
| F3 | `audit_events.citations` field structure was ambiguous on whether it stores verbatim cited-span text or only a `chunk_id` pointer; given DEC-046's mandatory physical deletion on retention expiry, a pointer-only design would make historical citations unreconstructable after legitimate deletion — undermining the "audit-ready by default" differentiator | High | **FIXED** — user chose verbatim-snapshot storage (DEC-087) |
| F4 | `context_fingerprint` schema (DEC-060) predates DEC-077/082's layered safety rails and has no fields to trace a `policy_blocked` refusal to the specific rail model/version/ruleset that produced it | High | **FIXED** (DEC-089) |
| F5 | §4.2.2's warm-cache VRAM headroom (~1.9 GB pre-Round-4) is thin relative to the claimed 5-8 in-flight concurrency target, and the eviction policy (evict Prompt Guard 2, ~1.5 GB) does not meaningfully offset KV-cache-driven pressure under real multi-conversation load | High | **Documented as an explicit caveat** (§4.2.2 admission-control note, §9.4 caveat) rather than architecturally resolved — no admission-control mechanism has been designed yet; flagged for `09-deployment-ops` |
| F6 | Core competitive positioning (open-weight + local + model-swappable vs Copilot / Q Business / Glean) still rests on competitor capability claims tagged [unconfirmed] after three prior review rounds | High | **Declined by user** — no dedicated verification task opened; open question remains recorded here for future reference |
| F7 | `§9.1` docker-compose schematic and `§7B.11` Mermaid diagram had not been updated since Round 2/3 introduced Redis, three safety-rail services, and the parallel `safety_input ∥ retrieve` fan-out | Medium-High | **FIXED** |
| F8 | No periodic full-reconciliation crawl exists between the ECM document inventory and the RAG index; CDC + 30-min re-poll only cover differential drift within the poll window | Medium-High | **FIXED** (DEC-090, REQ-056, MVP scope = detect + alert only) |
| F9 | `legal_hold_added` freezes chunks in Qdrant/Postgres but did not address content already materialized in an active conversation's vLLM KV-cache | Medium | **FIXED** (DEC-091) |
| F10 | DEC-082's Llama Guard 3 8B int4 → int4 AWQ quantization was justified purely on VRAM savings with no cited hazard-detection accuracy-preservation data | Medium | **FIXED** (DEC-092, validation gate; retroactively applies to the already-shipped DEC-082 change) |
| F11 | NFR-027 documented the TEI default rerank backend (150-200 ms) as an acceptable fallback, which individually risks exceeding the ≤150 ms line item `§7B.12`'s SLO calculation assumes — meaning the simplest install path was not guaranteed to be the SLO-compliant path | Medium | **FIXED** (DEC-093, ONNX Runtime promoted to MVP default) |
| F12 | Minor: NeMo Guardrails "no GPU footprint" claim was unqualified; `otel_spans` had no retention policy distinct from `audit_events`'s compliance retention; consumer-GPU enterprise-procurement licensing was undocumented; CDC event taxonomy had no explicit `document_created`/`document_deleted` types; co-location topology was not flagged as a customer security-review risk; burst cold-cache demo-day concurrency was not modeled; DEC-081's "same scope, longer timeline" solo-path framing did not address complexity-driven (not just calendar-driven) risk | Low-Medium | **FIXED** (documentation-only additions, no new DEC required for most; RISK-007 note added for the last item) |

Stray unannotated `bge-large-en-v1.5` / `e5-large-v2` references found during the sweep were corrected in `01-product-brief.md` (§2 table, RISK-003, RISK-012). `NFR-001` was additionally found to still state the pre-DEC-079 16 GB VRAM floor as operative text (a Round 2 Phase E gap that had escaped the "PASS" sweep result at the time); corrected to 24 GB in the same pass.

### R4.2 — DEC / REQ mapping table

| ID | Landed in |
|---|---|
| DEC-086 | `13-decision-log.md`; `04-architecture.md` §1, §4.1, §4.2, §4.2.2, §9.1; `02-requirements.md` REQ-003, NFR-001, NFR-003; `01-product-brief.md` §2, RISK-003, RISK-012; `23-evals-guardrails.md` §3.3 |
| DEC-087 | `13-decision-log.md`; `04-architecture.md` §6, §7.1; `02-requirements.md` REQ-007 |
| DEC-088 | `13-decision-log.md`; `04-architecture.md` §5.1.1, §8.1; `02-requirements.md` REQ-005; `20-agent-behavior.md` §2.1, §3.3, §6; `23-evals-guardrails.md` §2.2 |
| DEC-089 | `13-decision-log.md`; `04-architecture.md` §6; `02-requirements.md` REQ-035; `23-evals-guardrails.md` §3.3; `20-agent-behavior.md` §2.1 |
| DEC-090 | `13-decision-log.md`; `04-architecture.md` §7B.5; `02-requirements.md` REQ-056 |
| DEC-091 | `13-decision-log.md`; `04-architecture.md` §7B.5, §7B.6 |
| DEC-092 | `13-decision-log.md`; `04-architecture.md` §4.1, §4.3; `23-evals-guardrails.md` §2.2 |
| DEC-093 | `13-decision-log.md`; `04-architecture.md` §4.1, §7B.12, §9.1; `02-requirements.md` NFR-027 |

### R4.3 — Sweep results

| Check | Result |
|---|---|
| Reference completeness — DEC IDs | **PASS** — DEC-086..093 referenced consistently across `confirmed-context.md`, `01-product-brief.md`, `02-requirements.md`, `04-architecture.md`, `13-decision-log.md`, `20-agent-behavior.md`, `23-evals-guardrails.md` |
| Reference completeness — REQ IDs | **PASS** — REQ-056 added to `02-requirements.md` and referenced from `01-product-brief.md` + `confirmed-context.md` |
| Numerical sanity — VRAM allocation | **PASS** — §4.2.2 recalculated subtotal (cold ~19.0 GB / warm ~23.0 GB) and headroom (cold ~5.0 GB / warm ~1.0 GB) sum correctly against the 24 GB floor; tightened headroom is explicitly flagged as a caveat, not silently absorbed |
| Numerical sanity — §7B.12 latency budget | **PASS** — rerank line item (≤150 ms) now explicitly tied to the ONNX-default backend (DEC-093); total p95 figures (≤7,160 ms warm / ≤7,860 ms cold) unchanged since the rerank budget was already stated at the ONNX-achievable figure, DEC-093 just makes that backend the shipped default rather than an aspirational one |
| Concept drift — `bge-large-en-v1.5` / `e5-large-v2` as *active* embedding choice | **PASS** — all remaining occurrences are either annotated supersede references or confined to historical/frozen documents (`13-decision-log.md` DEC-052/013/014 entries, `90-stage1-trend-research.md`, `92-stage5-review-memos.md` Round 1-3 sections, `93-stage5r2-benchmark.md`, `groundeddocs-handoff-2026-06-28.md` — all append-only or explicitly frozen snapshots per this file's own conventions) |
| Concept drift — `retrieval_set` vs `reranked_set` as the citation-verification target | **PASS** — every live occurrence of `retrieval_set` in `04-architecture.md` and `20-agent-behavior.md` is now either annotated as "not a valid verification target" or contrasted explicitly with `reranked_set` |
| Concept drift — 16 GB vs 24 GB hardware floor as *operative* NFR text | **PASS** — `02-requirements.md` NFR-001 corrected from a stale 16 GB figure to 24 GB; remaining 16 GB mentions confirmed confined to frozen/historical documents |
| Supersede chain integrity | **PASS** — DEC-086 supersedes DEC-052's embedding portion only (generation/NLI/language-scope portions of DEC-052 explicitly stated as still in force); DEC-092 explicitly applies retroactively to DEC-082's quantization change; DEC-089 explicitly extends (not replaces) DEC-060; all other new DECs supplement rather than supersede |
| Append-only `13-decision-log.md` | **PASS** — DEC-086..093 appended after DEC-085; no prior DEC row text modified |

### R4.4 — Close-out checklist

- [x] DEC-086..093 written to `13-decision-log.md` with supersedes/supplements annotations
- [x] REQ-056 added to `02-requirements.md`; REQ-003/005/007/035, NFR-001/003/027 amended
- [x] `04-architecture.md` updated: §1, §2 (no change needed), §4.1, §4.2, §4.2.1, §4.2.2, §4.3, §5.1.1, §6, §7.1, §7B.0, §7B.5, §7B.6, §7B.11, §7B.12, §8.1, §9.1, §9.4, §12.3
- [x] `20-agent-behavior.md` updated: §2.1 pipeline diagram, §3.3 rewrite-template signature, §6 failure table
- [x] `01-product-brief.md` updated: §2 table, RISK-003, RISK-012
- [x] `23-evals-guardrails.md` updated: §2.2 goldset composition, §3.3 context-fingerprint example
- [x] `confirmed-context.md` updated: RISK-007 complexity caveat, Drift Log Round 4 entry
- [x] Sweep complete — reference completeness, numerical sanity, concept drift, and supersede-chain checks all PASS

**Round 4 verdict (2026-07-03)**: 3 user decisions + 9 architect-proposed fixes (2 Critical, 3 High, 3 Medium-High/Medium, minor documentation items) actioned; 1 finding (competitor-verification, F6) explicitly declined by user and left as an open question rather than silently dropped; 1 finding (F5, VRAM/concurrency headroom) documented as a caveat rather than architecturally resolved, flagged forward to `09-deployment-ops`. No item silently dropped.

