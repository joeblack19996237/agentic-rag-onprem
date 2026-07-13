# 01 — Product Brief: GroundedDocs

> Owner: `product-manager` (Stage 2).
> Reads `confirmed-context.md` + `90-stage1-trend-research.md` as input.
> Final form retained for Stage 7 spec-writer polish. All decisions referenced by stable `DEC-###` from `13-decision-log.md`.

## 1. Problem (before the solution)

Enterprises that have already invested in a CCM or ECM platform (Quadient, Smart Communications, M-Files, Hyland, regional vendors, etc.) sit on **document repositories that their own staff cannot reliably query in natural language**. Generic RAG add-ons solve the surface problem but break in production for three reasons:

1. **Citations are decorative**, not verified. Models fabricate plausible-looking source IDs that do not actually appear in the retrieval set. End users cannot tell a real citation from a hallucinated one.
2. **Refusal is treated as a failure mode rather than a product feature.** When grounding is weak, generic RAG products generate fluent guesses; in regulated B2B contexts that liability is unacceptable.
3. **Audit and review are bolted on after the fact.** There is no first-class store of "who asked what, what did the system retrieve, what did it cite, what got shown" that an admin can review later, sample for accuracy, or feed back into improvement.

CCM and ECM vendors who want to ship a "private AI assistant" feature to their enterprise customers face a build-versus-buy decision: build their own (slow, expensive, off-mission) or embed an existing RAG product (fast, but most existing options are SaaS-only or do not address the three failures above).

## 2. Why this product, why now

| Signal | Source (from `90-stage1-trend-research.md`) | What it implies |
|---|---|---|
| Enterprise RAG market growing $1.94B → $9.86B 2025→2030, 38.4% CAGR | §1 Market Context | The category is now large enough that vendors will pay for a differentiated component |
| EU AI Act enforcement on 2026-08-02 reshapes enterprise procurement | §1 | Compliance-ready posture is becoming buyer hygiene; on-prem is favored |
| **AU Privacy Act 1988 review amendments rolling through 2026 + NDB scheme** [unconfirmed exact 2026 status — verify before vendor pitch] | new context (DEC-072) | AU/NZ first-wave buyers (DEC-072) face concrete data-residency procurement clauses; on-prem + sovereign-cloud-tenancy lands well |
| Quadient publicly markets "Bring Your Own AI" framework | §13.1.2 | Direct integration shape exists — no need to invent it |
| OpenText Content Aviator depends on frontier cloud models (Gemini / OpenAI / Nova) | §13.2.2 | Air-gapped buyers have an open complaint we can solve |
| Open-source serving (vLLM) + open-weights (Llama-3.1 / Mistral-Small, English-optimized per DEC-052) + retrieval stack (`bge-m3` / bge-reranker-v2-m3, embedding reverted from `bge-large-en-v1.5` per DEC-086 to restore hybrid dense+sparse retrieval) are production-ready in 2026 | §4, §5, §6 | The dependency floor is finally low enough for a solo team to ship a credible MVP |

### 2.1 Why not the obvious cloud-vendor alternatives

Stage 5 review (`92-stage5-review-memos.md` D2-01) flagged that the "empty quadrant" framing from earlier drafts was weakly supported and that the realistic 2026 competitive map is more crowded. Direct comparisons:

| Cloud-vendor alternative | Why a customer might still choose GroundedDocs |
|---|---|
| Microsoft Copilot + Graph Connectors | Requires the customer to be inside M365 + Microsoft tenancy; cannot serve Documentum / OpenText / M-Files / Hyland customers without bringing the documents into Microsoft's index; LLM is closed-weight Azure OpenAI; air-gap not viable |
| AWS Q Business | Requires AWS account + Bedrock; permission propagation works inside AWS but not into on-prem ECMs without connector-side ACL replication; LLM is closed-weight (Bedrock-hosted); air-gap not viable |
| Glean (dedicated VPC) | Hosted in Glean-controlled cloud or customer VPC, but proprietary model and proprietary ranking stack; not model-swappable; license cost orientation does not match the OSS-first GTM (DEC-025) |
| OpenText Content Aviator | Requires being already on OpenText; LLM is cloud frontier model (Gemini/OpenAI/Nova); air-gap not viable; competes for the same shelf inside the OpenText customer |

**The GroundedDocs wedge against all four** is the combination of **open-weight + fully local LLM inference + model-swappable** (the §4 differentiator #1, revised) — none of these alternatives matches all three.

## 3. Personas (refined from `confirmed-context.md` §4)

The same persona table holds; PM-stage additions in **bold**.

| Persona | Primary surface | What they need first | **Pain that GroundedDocs uniquely addresses** |
|---|---|---|---|
| End user (vendor's customer's staff) | Embedded chat widget in vendor console | A cited answer or honest refusal | **Trust that the cited source actually says what the answer claims** |
| Enterprise admin | Admin API (MVP), admin console (V2) | Document upload, ACL, audit log, threshold tuning | **A reviewable record of what the system told users yesterday** |
| Reviewer (V2 only) | Review queue UI (V2) | Approve/edit/reject pending answers | (V2 capability; out of MVP) |
| CCM/ECM vendor integrator | Integration docs + HTTP API + iframe widget | Clean install, brandable surface, predictable telemetry | **A component their architect will approve: on-prem, no cloud egress, no proprietary lock-in** |
| GroundedDocs operator (us) | CLI + logs | Demo, eval, ship | (operator pain, not customer pain) |

## 4. Value Proposition (positioning anchor, DEC-010)

> **GroundedDocs is the on-prem, vendor-embeddable document Q&A agent for enterprises that need answers grounded in cited, verifiable sources — or no answer at all.**

Five differentiators (confirmed at Stage 1; revised at Stage 5 per RC-T1-10/11; **Round 2 (2026-06-29) added explicit 2026-aligned safety + orchestration language per DEC-075 / DEC-077**):

1. **Open-weight + fully local LLM inference + model-swappable** (the triple — revised from "On-prem deployment" because on-prem alone is no longer scarce in 2026; see §2.1)
2. **Vendor-embeddable** — packaged so a CCM / ECM vendor can ship it as their own AI feature without re-architecting
3. **Contract-grade Citation SLO** — runtime mechanical + NLI grounding check inside a **LangGraph-orchestrated verify node** (DEC-075) with measured thresholds (100% citation hit-rate hard gate per NFR-004 — **a mechanical guarantee that every emitted citation resolves to an actually-retrieved passage; a process guarantee on citation validity, not a claim that every answer is factually complete or accurate, per RISK-005's positioning**; 5-class typed refusal, audit dual-write to ECM); packaged as a vendor-contractable SLO, not just a marketing claim. The graph's typed feedback edge (`verify/` → `generate/`) carries V2 mid-flight rewriting (REQ-020) as a node addition, not an architectural redo
4. **Refusal as a product feature** — configurable thresholds; the system says "I cannot confidently answer" rather than guess; 5-class taxonomy per DEC-042 with both transparent and opaque modes shippable; **MVP layered safety rails** (DEC-077) — `Llama Prompt Guard 2` (input) + `Llama Guard 3 8B` (output) + `NeMo Guardrails` (orchestration policy) — match 2026 enterprise-RAG production default
5. **Audit-ready by default** — every query, retrieval, answer, citation, **safety-rail verdict**, and (V2) reviewer action persisted to an append-only log; ECM audit write-back including denied-access attempts (DEC-064) closes the compliance audit chain

## 5. MVP Scope (DEC-005 pinned at Stage 0)

| Capability | Status | REQ ID (see `02-requirements.md`) |
|---|---|---|
| File upload (PDF text-extractable, Word, Markdown, plain text) | Must | REQ-001 |
| Parse + chunk + embed + index pipeline | Must | REQ-002 |
| Hybrid retrieval (dense + sparse + rerank), **English baseline only per DEC-052** | Must | REQ-003 |
| Generation with cited answers | Must | REQ-004 |
| Runtime citation verification (mechanical chunk-overlap + NLI span check) | Must | REQ-005 |
| Refusal policy with configurable threshold | Must | REQ-006 |
| Audit log (append-only) | Must | REQ-007 |
| HTTP API for vendor integrators | Must | REQ-008 |
| Embeddable chat widget (iframe) | Must | REQ-009 |
| Admin API: document upload / delete / list / per-document ACL | Must | REQ-010 |
| Single-host installable artifact (docker-compose) | Must | REQ-011 |
| Air-gap compatible runtime (no required outbound calls) | Must | REQ-012 |
| RAGAS-based eval harness (offline) | Must | REQ-013 |
| End-to-end example with sample CCM-style corpus | Must | REQ-014 |
| **LangGraph 1.2.x pipeline orchestration with typed-state graph (DEC-075, version corrected DEC-131)** | **Must** | **REQ-046 (added Round 2)** |
| **Redis / Valkey hot-path cache + ACL TTL discipline (DEC-076)** | **Must** | **REQ-047 (added Round 2)** |
| **Layered safety rails: `Llama Prompt Guard 2` input + `Llama Guard 3 8B` output + `NeMo Guardrails` orchestration (DEC-077)** | **Must** | **REQ-048 (added Round 2)** |
| **Golden set 150-200 prompts with 50-prompt smoke-test subset (DEC-078)** | **Must** | **REQ-014 (amended Round 2)** |

## 6. Non-Goals (MVP — confirmed at Stage 0, reaffirmed here)

| Non-Goal | Reason | Where deferred |
|---|---|---|
| ReAct-style multi-step agent | Citation guarantee harder under multi-step | V2 |
| Auto-generated Wiki / knowledge graph from documents | Auto-synthesis is a new hallucination surface that contradicts positioning | **Permanently out of scope (DEC-011)** |
| Multi-tenant SaaS hosted by us | Wrong deployment model for B2B2B | Permanently out of scope |
| Self-serve sign-up, billing, quotas, pricing metering | No need before vendor pilots | V3 + |
| IM channel connectors (Slack, WeCom, Teams) | Vendor owns the channel surface | V2+ on request |
| Mobile native apps | Vendor owns the surface | V3+ |
| OCR for scanned PDF, complex table extraction | Citation accuracy collapses on these inputs (RISK-001) | V3+ |
| Compliance certifications (SOC2 / HIPAA / PCI / MLPS L3 / IRAP) | First buyer profile is non-regulated; design must not block; AU/NZ regulated buyers may eventually need IRAP-aware posture | When first regulated buyer signs |
| Multi-source connectors (SharePoint / file share / repository APIs) | Vendor handles ingest | V2 |
| Human review queue UI | Foundation laid in audit log; queue UI is V2 | V2 |
| Helm chart / HA deployment / blue-green reindex | Single-host docker-compose is MVP | V2 |
| **Real-time access to in-flight (checked-out, uncommitted) document edits** (DEC-071) | GroundedDocs query semantics are **version-based** — only committed versions are queryable; matches 2026 best-practice of Microsoft Graph Connectors, AWS Q Business, Glean | **Permanently out of scope** — re-indexing happens via `version_added` CDC after checkin |
| Multilingual baseline at MVP | DEC-052: English-only is hard constraint; schema reserves space for future language extension | When demand from a non-English market customer materializes |

## 7. Deferred Scope (explicitly named, not killed)

This is **roadmap intent**, not a commitment. Strategy after DEC-020 (open-source + paid services + annual support): each V2 capability is a billable deployment / tuning engagement; expansion is **vertical** (deeper in document Q&A) not **horizontal** (new use cases).

### V2 — vertical expansion ("the citation / governance / tuning triple, deeper")

| ID | Block | Capability | Revenue lever |
|---|---|---|---|
| REQ-015 | V2-α | ReAct multi-step agent (degrades to multi-step only when single-step recall is insufficient) | Tuning |
| REQ-016 | V2-α | Review queue UI + per-category routing + reviewer-feedback-to-eval loop | Implementation + annual support |
| REQ-017 | V2-γ | Pluggable connector framework (SharePoint / file share / generic REST) | Implementation per connector |
| REQ-018 | V2-β | JS widget (deeper host theming than iframe) | Implementation |
| **REQ-019** | **V2-citation-deep** | **Citation span highlighting + source-snippet rendering** (highlights the exact span inside the chunk; renders the originating PDF page region as an image) | Tuning |
| **REQ-020** | **V2-citation-deep** | **Claim decomposition + per-claim verification** (decompose the answer into atomic claims; each claim gets its own NLI check + citation; partial failures only grey out the failing claim) | Tuning |
| **REQ-021** | **V2-governance-deep** | **Document lifecycle + authority marking** (admin marks docs as authoritative / draft / deprecated; authority influences ranking; system flags potentially contradictory document pairs) | Implementation + annual support |
| **REQ-022** | **V2-governance-deep** | **Per-customer prompt template registry** (system prompts, refusal phrasing, citation format saved & versioned per customer) | Annual support |
| **REQ-023** | **V2-tuning-deep** | **Customer-specific golden set** (admin curates 50–200 Q/A pairs in the admin UI; runs as the customer's own RAGAS baseline; used for regression checks) | Implementation + tuning |
| **REQ-024** | **V2-tuning-deep** | **A/B prompt + model traffic split** (admin splits traffic across two prompts or two model adapters; RAGAS deltas reported) | Tuning |
| **REQ-033** | **V2-LCC-enabler** | **Model adapter abstraction** — config-switch generation model (e.g. Llama-3.1 → Llama-3.2 / Mistral / commercial API per DEC-052 English stack) with no restart | LCC T1–T4 enabler |
| **REQ-034** | **V2-LCC-enabler** | **Embedding model versioning + single-host blue/green re-embedding** | LCC T3 (Migration Execution) |
| **REQ-035** | **V2-LCC-enabler** | **Per-answer context fingerprint in audit log** (model + embedding + reranker + prompt versions) | LCC forensics; all tiers |
| **REQ-006d** | **MVP-promoted** | **5-class refusal taxonomy + `acl_denial_mode`** (real reason always in audit) | Adds `access_denied` + `verification_unavailable` |
| **REQ-006a** | **MVP-promoted** | **Neighboring docs fallback on `no_recall`** (ACL-filtered) | Near-zero cost; high UX value |
| **REQ-036** | **MVP-promoted** | **Two-layer authorization** (Layer 1 Qdrant filter pushdown + Layer 2 batch_check_access) + `ECMAdapter` interface + `LocalAdapter` + `OIDCAdapter` | Core ECM/CCM integration architecture |
| **REQ-037** | **MVP-promoted** | **Retention state ingest + retrieval filter** | Physical delete; legal hold freeze |
| **REQ-041** | **MVP-promoted** | **CDC consumer**: webhook + 30-min re-poll fallback | All ECM change event types |
| **REQ-043** | **MVP-promoted** | **Audit pull API** (NDJSON + cursor) for vendor SIEM forwarding | Compliance audit chain |
| **REQ-045** | **MVP-promoted** | **ECM audit write-back** (async best-effort) | Compliance — feeds Documentum DAR / OpenText RM's own audit trail (async best-effort; ECM's own log remains compliance-authoritative per `42-compliance-security.md`) |
| **REQ-038** | V2 | M-Files adapter | V2-β |
| **REQ-039** | V2 | SharePoint / Graph adapter | V2-β |
| **REQ-040** | V2 | Hyland Alfresco adapter | V2-β |
| **REQ-044** | V2 | **Documentum + OpenText adapters (V2-α priority)** | Research-context primary targets |
| **REQ-006b** | V2 | Query log + similar-question suggestions | Cross-user ACL safety required |
| **REQ-006c** | V2 | Access-request workflow | Schema reserved in MVP (DEC-044) |
| **REQ-051** | **V2** (Round 3, S3.1, DEC-084) | **Admin-configurable intent classifier + per-intent NLI policy** — may downgrade `nli_slow_path` to advisory for low-risk intents (chitchat / FAQ); per-customer SLA waiver required; mechanical-fast-path + audit are never skipped | Latency-saving for high-volume low-risk traffic; preserves SLO positioning via explicit waiver gate |
| **REQ-052** | **V2** (Round 3, S3.2 + S4.1) | **Sentence-level streaming NLI** parallel to vLLM token streaming with early-stop on first failed claim | Cuts feedback-loop tail latency materially when feedback edge fires |
| **REQ-053** | **V2** (Round 3, S6.4) | **Widget two-pass streaming UX** — first-pass output with `Correcting in progress…` indicator; corrected output diff-style against first pass | Turns feedback-edge mechanism into a trust-building UX surface |

### V3 — scale + customer-specific depth

| ID | Capability | Notes |
|---|---|---|
| REQ-025 | SDK (React / Vue components) | Drop-in for vendor frontends |
| REQ-026 | Helm chart + HA deployment + blue/green reindex | Multi-host customers |
| REQ-027 | TruLens production observability + drift monitoring | Aligns with DEC-016 V3 step |
| REQ-028 | OCR + complex table extraction | Unlocks scanned-contract corpora |
| REQ-029 | First compliance audit prep package (SOC2 / HIPAA / MLPS L3 — chosen by first regulated customer) | Triggered by first regulated buyer |
| **REQ-030** | **Customer-corpus LoRA fine-tuning of BOTH reranker AND generator** (two independent adapters, trained separately, each on customer hardware) | DEC-023 + DEC-030: user attempts in-house; partner fallback |
| **REQ-031** | **Corpus health dashboard** (admin sees stale docs / contradicting docs / low-citation docs / high-refusal query clusters → tells the customer what to curate) | Sticky annual-support deliverable |
| **REQ-032** | **Tuning playbook as a product artifact** (your know-how distilled into executable recipes — "the 5 steps after first install"; also doubles as customer-team training material) | Annual support enabler |
| **REQ-054** | **Advisory-only NLI mode** (Round 3, S4.3) — paired with REQ-051 V2 intent classifier; answer emitted immediately; NLI runs async; widget surfaces delayed disclaimer on fail. Mechanical citation + audit remain synchronous and authoritative | Service-level downgrade for high-volume / low-risk traffic; explicit per-customer SLA waiver |
| **REQ-055** | **Federated retrieval path for `legal_hold` / `sensitivity: high` documents** (Round 3, S7.3, DEC-085) — bypasses pre-ingestion; `ECMSearchAPIAdapter` queries ECM Search API at runtime; ECM enforces ACL natively; no RAG-side retention | Canonical answer for AU/NZ regulated-vertical evaluators asking about content they can't risk replicating |

### Out of scope (any horizon, reaffirmed)

- Auto-generated wiki / knowledge graph from documents (DEC-011)
- Multi-tenant SaaS
- Self-serve billing / pricing meter
- IM channel connectors (Slack / WeCom / Teams) — vendor territory
- General-purpose agent orchestration platform — Aviator Studio / Dify territory
- Mobile native apps

## 8. Business Model / Packaging (DEC-020 pinned; pricing deferred per DEC-024)

**Model**: open-source / source-available core + **paid deployment service** + **annual support subscription** (RedHat / RAGFlow-style). The customer provides hardware; deployment, tuning, and operational support are billable engagements.

### Service tier framing (internal sizing only — not a price sheet)

| Engagement | Typical duration | Internal sizing reference |
|---|---|---|
| First-time on-site deployment + golden-set validation | 1–2 weeks | mid-five-figure RMB |
| Citation-depth upgrade pack (REQ-019 + REQ-020) | 3–5 days | low-five-figure RMB |
| Customer golden set + A/B (REQ-023 + REQ-024) | 1–2 weeks | mid-five-figure RMB |
| Reranker LoRA fine-tuning engagement (REQ-030) | ~1 week | low-five-figure RMB (or partner subcontract per DEC-023) |
| Annual support + quarterly tuning retainer | Continuous | low-six-figure RMB / year |

These numbers are for capacity planning, not selling. Actual pricing pinned only after first vendor pilot conversation (DEC-024).

### Go-to-market (DEC-025 + DEC-072)

**First wave = OSS community + industry events.** Direct CCM/ECM vendor outreach is second wave once the project has demonstrated community traction. DEC-018 retains the *vendor priority order* for that second wave (Smart Communications / M-Files / Hyland / regional vendors first; OpenText deprioritized).

**Target market = Australia + New Zealand (DEC-072)** — user's existing customer relationships are AU/NZ; sovereign-cloud + "data must not leave country" procurement clauses common in AU public sector + finance + mining + NZ public sector; OpenText/Documentum installed base is substantial; compliance reference frame = AU Privacy Act 1988 + NDB + AU AI Ethics Principles 2019; NZ Privacy Act 2020 + IPP 13 principles.

### Three-tier priority timeline (RC-T1-12)

These three priority orderings are intentionally divergent; the table makes the timing explicit so vendor conversations can answer "who first?" cleanly:

| Tier | Ordering | When |
|---|---|---|
| **First-wave channel** (DEC-025) | OSS community + industry events | Now → demo (originally DEC-026 3-month, **now 2027-03-26 per DEC-080**) |
| **Sales priority** (DEC-018) | Smart Comm → M-Files → Hyland → regional CCM/ECM (OpenText deprioritized) | Second wave, post community traction |
| **Technical adapter priority** (DEC-050) | V2-α = Documentum + OpenText (user's research context); V2-β = SharePoint + M-Files + Hyland; V2-γ = regional via partner | V2 build sequence (post-demo) |

The asymmetry: technical adapters lead with Documentum + OpenText because that is where the user's research scoped; sales outreach starts elsewhere because the OpenText buyer overlap with Aviator is hostile. AU/NZ market reality (DEC-072) bridges the gap — both Documentum + OpenText and M-Files + Hyland are installed in AU/NZ.

### TAM ceiling honesty (RISK-011)

Service-heavy model is bounded by your time. Sizing reference: 5 customers + full V2 service stack ≈ ¥600–800k annual revenue at ~6–8 months of solo capacity. Past this point, partner subcontracting (per DEC-023) or hiring becomes the only growth lever.

## 9. Success Metrics

### 9.1 Quality metrics (MVP gate)

Industry RAGAS thresholds adopted as starting point (DEC-017, confirmed by user 2026-06-25). Re-tune after first golden-set eval run.

| Metric | Baseline (MVP gate) | Target (V2 ship) | Measurement window | Owner |
|---|---|---|---|---|
| **Faithfulness** (RAGAS) | ≥ 0.75 | ≥ 0.85 | Per eval run on golden set | Project owner (user) |
| **Answer relevancy** (RAGAS) | ≥ 0.80 | ≥ 0.85 | Per eval run | Project owner |
| **Context precision** (RAGAS) | ≥ 0.70 | ≥ 0.80 | Per eval run | Project owner |
| **Context recall** (RAGAS) | ≥ 0.80 | ≥ 0.85 | Per eval run | Project owner |
| **Citation hit-rate** (every emitted citation lands on a chunk actually in this turn's retrieval set) | **100% (hard gate)** | 100% | Per query (runtime) | System |
| **Refusal rate on golden no-answer set** | ≥ 95% | ≥ 98% | Per eval run | Project owner |
| **Hallucination rate** (random-sampled human review) | ≤ 2% | ≤ 1% | Weekly during demo period | Project owner |

### 9.2 Runtime metrics (operational gate)

| Metric | MVP target | Measurement | Owner |
|---|---|---|---|
| End-to-end query latency p95 | ≤ 8 sec on reference single-host hardware | Per query | System |
| Cold-start install time (docker-compose up to first answer) | ≤ 30 minutes | First install | User |
| Ingest throughput | ≥ 100 pages / minute on reference hardware | Per ingest job | System |
| Air-gap test pass | 100% — system runs end-to-end with network namespace blocked | Per release | User |

### 9.3 Adoption metrics (demo-stage)

| Metric | MVP target | Owner |
|---|---|---|
| Vendor evaluator install success rate | ≥ 1 successful first-touch demo install | User |
| Sample corpus citation-hit-rate (manual audit) | 100% on the 150-200 prompt full golden set (50-prompt smoke subset preserved as the CI fast-feedback ring) — **corrected 2026-07-06, DEC-109; this row was never updated after DEC-078 (2026-06-29) expanded the golden set from 50 to 150-200 prompts** | User |

## 10. Product Risk Register (PM stage update)

Builds on `confirmed-context.md` §5. New / refined risks in **bold**.

| ID | Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|---|
| RISK-001 | Citation accuracy collapses on real enterprise docs (scanned, tables, multi-column) | High | High | Architect | MVP corpus limited to born-digital; OCR deferred |
| RISK-002 | "Refusal policy" stays a slogan without measured baselines | Medium | High | PM + Architect | RAGAS metrics + refusal-rate + hallucination-rate are mandatory MVP gates (see §9.1) |
| RISK-003 | Open-source LLM hardware matrix expands beyond a solo team's capacity | High | Medium | Architect | One reference stack pinned (Llama-3.1-8B/Mistral-Small-24B + `bge-m3` + bge-reranker-v2-m3 + vLLM per DEC-052 + DEC-086; embedding reverted to `bge-m3` — DEC-052's interim `bge-large-en-v1.5` swap is superseded, DEC-014's original `bge-m3` pin is reinstated to restore hybrid dense+sparse retrieval); everything else "supported targets, document yourself" |
| RISK-004 | B2B2B buyer (vendor) and end user have different needs; UX/SLA conflict | Medium | Medium | PM | Vendor integration contract is a first-class spec; widget is themable; telemetry opt-in |
| RISK-005 | Anti-hallucination guarantees imply legal exposure if mis-marketed | Low | High | PM | Position as process claim ("no answer without verifiable citation"), not outcome claim ("100% accurate") |
| RISK-006 | Solo-project scope creep | High | High | All | Hard-pin MVP; defer at every stage gate |
| RISK-007 | OpenText Content Aviator overlap dilutes positioning when vendor prospect is already on OpenText | Medium (second wave only) | Medium | PM | Deprioritize OpenText prospects (DEC-018); first wave is OSS/events (DEC-025) so this risk is dormant until second-wave vendor conversations |
| RISK-008 | Pricing / packaging shape undefined at demo time; vendor conversations bog down on commercials | Low (deferred) | Medium | PM (user) | Deferred (DEC-024); accepted that internal sizing in §8 is enough until first vendor pilot |
| RISK-009 | CCM-specific corpora are heavily templated (insurance letters, billing notices); RAGAS thresholds from generic benchmarks may not transfer | Medium | Medium | PM + Architect | Build a CCM-style synthetic golden set in MVP (REQ-014) and re-baseline; thresholds in §9.1 are a starting line, not the finish line |
| RISK-010 | **Resolved by DEC-025** — first-wave channel changed from vendor outreach to OSS/events; original "no vendor access" concern no longer blocks demo path | — | — | — | Closed |
| **RISK-011** | **TAM ceiling in service-heavy model (DEC-020)** — every customer needs your time; revenue scales linearly until partner / hiring leverage exists | Inherent | Medium | PM (user) | Honest framing in §8; partner fallback (DEC-023) on the table for technical-depth work first |
| **RISK-012** | **Demo deadline 2027-03-26 (DEC-080, supersedes DEC-026 3-month) on a stack the user is learning while renting cloud GPU** — schedule risk dominates feature risk; under Round 2 scope expansion (DEC-075/076/077) the critical path is now LangGraph onboarding + Redis integration + layered-rail integration + RAGAS curation | High | High | PM (user) | Cut, don't pad: MVP scope is now REQ-001..014 + REQ-046..050 + REQ-056 + NFR-021..029 (see `02-requirements.md`); any slip cuts further; build plan in `10-build-plan.md` must front-load risk discovery (vLLM + English-only reference model + `bge-m3` vertical slice per DEC-086 + LangGraph skeleton in Phase 1, per DEC-052 + DEC-075). Team-materialisation checkpoint at 2026-08-29 per RISK-007 |
| **RISK-013** | **Cloud-GPU dev environment ≠ customer's deployment environment** — works on RunPod, breaks on customer hardware. **GPU vendor note (added 2026-07-13, cross-model review R.28, fact-checked against live sources)**: the reference stack assumes NVIDIA/CUDA; some enterprise procurement (including AU/NZ public sector) may standardize on non-NVIDIA GPUs or no discrete GPU at all. vLLM's AMD ROCm support reached "first-class" status in January 2026 (official Docker images, datacenter-class MI300/MI350 GPUs at 90-95% of H100 throughput) — the cross-model review's own claim that AMD is "not supported by vLLM" was already stale by the review's 2026-07-13 date; consumer-grade AMD (RDNA) and Intel Arc (IPEX backend) remain more experimental. None of this is validated by this spec's own testing either way — the hardware compatibility matrix below should record actually-tested configurations, not assume NVIDIA-only or repeat unverified vendor-support claims in either direction | Architecture stage must produce a hardware compatibility matrix and at least one "borrowed real workstation" install rehearsal before any vendor demo |
| **RISK-014** | **Open-source model lifecycle risk** — base model deprecated, license changed, CVE unpatched, new model significantly better, embedding model bumped requiring re-indexing | Inevitable (when, not if) | High | PM + Architect | LCC service package (DEC-028); REQ-033/034/035 are architectural enablers |
| **RISK-015** | **Customer misled into self-training (L1/L2/L3)** by competitors or own sales — multi-month bad investment that we get blamed for when it fails | Medium | Medium | PM | DEC-029 official stance (L1 refuse; L2/L3 advisory + partner; L4 in-house); "Architecture for Insulation" white paper (DEC-031) inoculates the buyer conversation |
| **RISK-016** | **ACL drift between vendor truth and our Layer 1 cache** → user sees results they should not, or vice versa | High (it will happen) | High (compliance + trust) | Architect | Two-layer authorization (DEC-046): Layer 2 batch_check_access catches Layer 1 drift; CDC keeps Layer 1 fresh; periodic re-poll fallback (REQ-041); short PDP cache TTL (30–60s) |
| **RISK-017** | **Retention / legal-hold lag** — `retention_expired` or `legal_hold_added` event arrives late or is missed; LLM context leaks compliance-killed content. **Extended 2026-07-13 (cross-model review R.10)**: a related but distinct sub-case exists even with zero CDC lag — §7B.4's Layer 2 authorization/retention check runs once, upfront (before rerank/generate), not again immediately before response delivery. A CDC event landing in that multi-second in-flight window (bounded by NFR-005's p95 ≤ 8s) is not caught by the same query's response, since there is no pre-delivery re-check. DEC-091's KV-cache invalidation does not cover this either — it addresses stale content resurfacing in *later conversation turns*, not the *current* turn's own in-flight response | Medium-High | Critical (audit fail) | Architect + PM | CDC webhook + re-poll fallback (DEC-051); physical-delete-not-soft-flag (DEC-046); Layer 2 retention re-check on every query; integration tests NFR-014/015. **MVP**: the in-flight window is accepted as a documented residual risk — narrow (single query's generation time) and low-probability (requires a CDC event for a specifically-cited doc_id to land in that exact window). **V2 direction**: a post-retrieval, pre-response re-check of `retention_expired` for cited doc_ids, or a response-delivery timestamp compared against the last known CDC event timestamp |
| **RISK-018** | **Per-vendor adapter maintenance ceiling** — each adapter is non-trivial code; solo capacity caps at ~3 supported vendors actively | High | Medium | PM | Partner pattern (DEC-029 L2/L3); Partner Adapter SDK (REQ-042) in V3 lets community / customer extend; sequence V2-α (Documentum + OpenText) before V2-β |
| **RISK-019** | **English-only MVP scope (DEC-052) blocks non-English market entry** until V2 — Australian / NZ market is English so no MVP impact, but global expansion (especially Asia-Pacific outside ANZ) requires multi-language schema extension first | Low (no MVP impact); medium (V2+) | Medium | PM | DEC-052 schema-neutral provision; revisit when first non-English customer materializes |
| **RISK-020** | **Positioning competitors** — Microsoft Copilot + Graph Connectors, AWS Q Business, Glean dedicated VPC all cover adjacent ground in 2026 [unconfirmed exact state]; sales conversation must reach the open-weight + local LLM + model-swappable wedge quickly | Medium | High | PM | §2.1 head-to-head subsection; demo material leads with the wedge; do not lean on "on-prem" as the sole differentiator |
| **RISK-021** | **AU/NZ sovereign-cloud + IRAP procurement clauses (DEC-072)** may require additional attestation paperwork (e.g. IRAP assessment for federal customers, ASD Essential 8 alignment) before public-sector pilots | Medium | Medium | PM | Defer to first regulated AU buyer; `09-deployment-ops` includes a "compliance posture" section so the attestation evidence chain is ready |
| **RISK-022** | **(Added 2026-07-13, cross-model review R.12)** MVP iframe widget cannot embed into any host page serving `X-Frame-Options: DENY` or a CSP `frame-ancestors` directive that excludes it — no MVP workaround | Medium | High (demo-blocking) | PM + Architect | Pre-demo CSP posture check with vendor; V2 JS widget (REQ-018) is the structural fix |

## 11. Open Questions for User (Stage 2 batch — all resolved)

All four questions answered 2026-06-27. Each maps to a `DEC-###` in `13-decision-log.md`.

| Q | Answer | DEC |
|---|---|---|
| Pricing/packaging direction | Defer | DEC-024 |
| First-wave channel | OSS community + industry events (vendor outreach moves to second wave) | DEC-025 |
| Demo deadline | **2027-03-26 (team path) / 2027-05+ (solo path)** per DEC-080 + DEC-081. Originally 2026-09-27 (DEC-026, superseded), then 2026-12-26 (DEC-073 timeline portion, superseded), now lifted to 2027-03-26 under Round 2 scope (DEC-075/076/077) | DEC-026 → DEC-073 → DEC-080 |
| Metric ownership | User runs RAGAS golden-set evals manually pre-demo | DEC-027 |

Additional decisions from this round (hardware-pivot conversation):

| Topic | Decision | DEC |
|---|---|---|
| Business model | Open-source + paid services + annual support | DEC-020 |
| Dev hardware | Cloud GPU rental | DEC-021 |
| V2 scope | All of REQ-019..024 in | DEC-022 |
| REQ-030 ownership | User attempts in-house first, partner fallback | DEC-023 |

## 12. Stage 2 Exit Checklist

- [x] Problem framed before solution (§1)
- [x] Why-now justified (§2)
- [x] Personas mapped to pains (§3)
- [x] Value proposition + differentiators stated (§4)
- [x] MVP scope itemized with REQ seeds (§5)
- [x] Non-goals explicit (§6)
- [x] Deferred scope explicit and separated from MVP (§7)
- [x] Success metrics with baseline / target / window / owner (§9)
- [x] Risk register updated (§10)
- [x] Open questions batched (§11)
- [x] User confirmed §4 differentiators (2026-06-25)
- [x] User confirmed §5 MVP boundary (Stage 0 + Stage 2)
- [x] User confirmed §6 non-goals (Stage 0)
- [x] User confirmed §9 RAGAS thresholds as starting point (DEC-017)
- [x] §11 open questions resolved (DEC-020..027)
- [x] Stage 3 (UX) decision = **skip** (DEC-019); skip memo at `91-stage3-ux-skip.md`

PM Stage 2 deliverable **complete**. Ready for Stage 4 (Architecture).
