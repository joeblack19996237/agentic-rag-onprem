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
| The "on-prem + vendor-embedded" quadrant has no named incumbent in 2026 buyer guides | §2.2 Empty quadrant | First-mover positioning available |
| EU AI Act enforcement on 2026-08-02 reshapes enterprise procurement | §1 | Compliance-ready posture is becoming buyer hygiene; on-prem is favored |
| Quadient publicly markets "Bring Your Own AI" framework | §13.1.2 | Direct integration shape exists — no need to invent it |
| OpenText Content Aviator depends on frontier cloud models (Gemini / OpenAI / Nova) | §13.2.2 | Air-gapped buyers have an open complaint we can solve |
| Open-source serving (vLLM) + open-weights (Qwen3 Apache 2.0) + retrieval stack (bge-m3 / bge-reranker-v2-m3) are production-ready in 2026 | §4, §5, §6 | The dependency floor is finally low enough for a solo team to ship a credible MVP |

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

Five differentiators (confirmed at Stage 1):

1. **On-prem deployment** — single-host installable; air-gap viable; runs on open-weights LLMs
2. **Vendor-embeddable** — packaged so a CCM / ECM vendor can ship it as their own AI feature without re-architecting
3. **Verified citation** — runtime mechanical + NLI grounding check; ungrounded citations are blocked before delivery
4. **Refusal as a product feature** — configurable thresholds; the system says "I cannot confidently answer" rather than guess
5. **Audit-ready by default** — every query, retrieval, answer, citation, and (V2) reviewer action persisted to an append-only log

## 5. MVP Scope (DEC-005 pinned at Stage 0)

| Capability | Status | REQ ID (see `02-requirements.md`) |
|---|---|---|
| File upload (PDF text-extractable, Word, Markdown, plain text) | Must | REQ-001 |
| Parse + chunk + embed + index pipeline | Must | REQ-002 |
| Hybrid retrieval (dense + sparse + rerank) with multilingual baseline | Must | REQ-003 |
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
| Compliance certifications (SOC2 / HIPAA / PCI / MLPS L3) | First buyer profile is non-regulated; design must not block | When first regulated buyer signs |
| Multi-source connectors (SharePoint / file share / repository APIs) | Vendor handles ingest | V2 |
| Human review queue UI | Foundation laid in audit log; queue UI is V2 | V2 |
| Helm chart / HA deployment / blue-green reindex | Single-host docker-compose is MVP | V2 |

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
| **REQ-033** | **V2-LCC-enabler** | **Model adapter abstraction** — config-switch generation model (Qwen3 → Qwen4 / DeepSeek / commercial API) with no restart | LCC T1–T4 enabler |
| **REQ-034** | **V2-LCC-enabler** | **Embedding model versioning + single-host blue/green re-embedding** | LCC T3 (Migration Execution) |
| **REQ-035** | **V2-LCC-enabler** | **Per-answer context fingerprint in audit log** (model + embedding + reranker + prompt versions) | LCC forensics; all tiers |

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

### Go-to-market (DEC-025)

**First wave = OSS community + industry events.** Direct CCM/ECM vendor outreach is second wave once the project has demonstrated community traction. DEC-018 retains the *vendor priority order* for that second wave (Smart Communications / M-Files / Hyland / regional vendors first; OpenText deprioritized).

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
| Sample corpus citation-hit-rate (manual audit) | 100% on 50-question hand-curated set | User |

## 10. Product Risk Register (PM stage update)

Builds on `confirmed-context.md` §5. New / refined risks in **bold**.

| ID | Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|---|
| RISK-001 | Citation accuracy collapses on real enterprise docs (scanned, tables, multi-column) | High | High | Architect | MVP corpus limited to born-digital; OCR deferred |
| RISK-002 | "Refusal policy" stays a slogan without measured baselines | Medium | High | PM + Architect | RAGAS metrics + refusal-rate + hallucination-rate are mandatory MVP gates (see §9.1) |
| RISK-003 | Open-source LLM hardware matrix expands beyond a solo team's capacity | High | Medium | Architect | One reference stack pinned (Qwen3 + bge-m3 + bge-reranker-v2-m3 + vLLM) per DEC-013/014/012; everything else "supported targets, document yourself" |
| RISK-004 | B2B2B buyer (vendor) and end user have different needs; UX/SLA conflict | Medium | Medium | PM | Vendor integration contract is a first-class spec; widget is themable; telemetry opt-in |
| RISK-005 | Anti-hallucination guarantees imply legal exposure if mis-marketed | Low | High | PM | Position as process claim ("no answer without verifiable citation"), not outcome claim ("100% accurate") |
| RISK-006 | Solo-project scope creep | High | High | All | Hard-pin MVP; defer at every stage gate |
| RISK-007 | OpenText Content Aviator overlap dilutes positioning when vendor prospect is already on OpenText | Medium (second wave only) | Medium | PM | Deprioritize OpenText prospects (DEC-018); first wave is OSS/events (DEC-025) so this risk is dormant until second-wave vendor conversations |
| RISK-008 | Pricing / packaging shape undefined at demo time; vendor conversations bog down on commercials | Low (deferred) | Medium | PM (user) | Deferred (DEC-024); accepted that internal sizing in §8 is enough until first vendor pilot |
| RISK-009 | CCM-specific corpora are heavily templated (insurance letters, billing notices); RAGAS thresholds from generic benchmarks may not transfer | Medium | Medium | PM + Architect | Build a CCM-style synthetic golden set in MVP (REQ-014) and re-baseline; thresholds in §9.1 are a starting line, not the finish line |
| RISK-010 | **Resolved by DEC-025** — first-wave channel changed from vendor outreach to OSS/events; original "no vendor access" concern no longer blocks demo path | — | — | — | Closed |
| **RISK-011** | **TAM ceiling in service-heavy model (DEC-020)** — every customer needs your time; revenue scales linearly until partner / hiring leverage exists | Inherent | Medium | PM (user) | Honest framing in §8; partner fallback (DEC-023) on the table for technical-depth work first |
| **RISK-012** | **3-month demo deadline (DEC-026) on a stack the user is learning while renting cloud GPU** — schedule risk dominates feature risk | High | High | PM (user) | Cut, don't pad: MVP REQ-001..014 is the limit; any slip cuts further; build plan in `10-build-plan.md` must front-load risk discovery (vLLM + Qwen3 + bge-m3 vertical slice in Phase 1) |
| **RISK-013** | **Cloud-GPU dev environment ≠ customer's deployment environment** — works on RunPod, breaks on customer hardware | Medium | Medium | Architect | Architecture stage must produce a hardware compatibility matrix and at least one "borrowed real workstation" install rehearsal before any vendor demo |
| **RISK-014** | **Open-source model lifecycle risk** — base model deprecated, license changed, CVE unpatched, new model significantly better, embedding model bumped requiring re-indexing | Inevitable (when, not if) | High | PM + Architect | LCC service package (DEC-028); REQ-033/034/035 are architectural enablers |
| **RISK-015** | **Customer misled into self-training (L1/L2/L3)** by competitors or own sales — multi-month bad investment that we get blamed for when it fails | Medium | Medium | PM | DEC-029 official stance (L1 refuse; L2/L3 advisory + partner; L4 in-house); "Architecture for Insulation" white paper (DEC-031) inoculates the buyer conversation |

## 11. Open Questions for User (Stage 2 batch — all resolved)

All four questions answered 2026-06-27. Each maps to a `DEC-###` in `13-decision-log.md`.

| Q | Answer | DEC |
|---|---|---|
| Pricing/packaging direction | Defer | DEC-024 |
| First-wave channel | OSS community + industry events (vendor outreach moves to second wave) | DEC-025 |
| Demo deadline | 2026-09-27 (3 months) | DEC-026 |
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
