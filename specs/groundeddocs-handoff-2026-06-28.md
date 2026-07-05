# GroundedDocs — Handoff (2026-06-28)

> Save destination: OS temp dir per `/handoff` skill (do not commit into the workspace).
> Source conversation language: Chinese (chat) + English (all spec artifacts).
> Conversation ran in `idea-to-specs` skill mode through Stage 0 → 1 → 2 → 4 (Stage 3 skipped). About to enter Stage 5 (architecture review). User explicitly paused before Stage 5 to do this handoff.

---

## 1. What this project is

**GroundedDocs** = on-premise, vendor-embeddable enterprise document Q&A agent. Five differentiators:

1. On-prem deployment (open-weights LLM, air-gap viable)
2. Vendor-embeddable (CCM/ECM add-on, not standalone SaaS)
3. Verified citation (runtime mechanical + NLI grounding check, no decorative citations)
4. Refusal as a product feature (typed 5-class taxonomy, configurable thresholds)
5. Audit-ready (dual-write to RAG local + ECM audit log)

Business model: **open-source / source-available core + paid deployment + annual support** (RedHat/RAGFlow-style). Customer provides hardware; we deploy, tune, support.

---

## 2. Project paths

| Resource | Path | Notes |
|---|---|---|
| **Workspace root** | `D:\AI\claude_code\agentic-rag-onprem\` | New project, distinct from `D:\AI\claude_code\agentic-rag\` (an older SaaS-form RAG project — **do not touch or import**) |
| Specs directory | `D:\AI\claude_code\agentic-rag-onprem\specs\` | All spec artifacts (English) |
| Architecture diagram (external research input) | `D:\AI\claude_code\agentic-rag-onprem\specs\assets\two-layer-authorization.png` | Referenced from `04-architecture.md §7B.2` |
| `idea-to-specs` skill | `D:\AI\claude_code\agentic-rag\.claude\skills\idea-to-specs\` | The skill driving the workflow; references and agents live under there |
| Handoff skill | `D:\AI\claude_code\agentic-rag-onprem\.claude\skills\handoff\` | This document follows that skill |

---

## 3. Spec artifacts (read these — do not duplicate their content here)

| File | Purpose | Approx state |
|---|---|---|
| `specs/confirmed-context.md` | Stage 0 pinned values + Drift Log | Complete, drift entries logged for DEC-020/021/025 |
| `specs/13-decision-log.md` | Canonical decision log, append-only | **DEC-001 through DEC-051 pinned** |
| `specs/90-stage1-trend-research.md` | Stage 1 market + competitor + tech survey w/ 40+ cited sources. §13 = Quadient + OpenText Aviator deep dive | Complete, READY |
| `specs/91-stage3-ux-skip.md` | Stage 3 (UX) skip memo, `SKIP-NOT-APPLICABLE` | Authority DEC-019 |
| `specs/01-product-brief.md` | Stage 2 main deliverable: problem, why-now, personas, value-prop, MVP scope, V2/V3 roadmap, business model, success metrics (RAGAS thresholds), risk register, open Qs | Complete; §11 all open Qs resolved |
| `specs/02-requirements.md` | REQ + NFR seeded outline w/ one-line acceptance | REQ-001..045 (MVP/V2/V3 mixed); NFR-001..015 |
| `specs/04-architecture.md` | Stage 4 main deliverable: 4-option build comparison, tech stack, module map, data/API/deployment direction, citation verification pipeline, AI agent direction, hardware matrix, **§7B Two-Layer Authorization** (added per user's external research) | Complete pre-Stage-5 |
| `specs/20-agent-behavior.md` | Agent shape: MVP single-step, V2 ReAct fallback, V2 review queue, failure behaviors | Drafted |
| `specs/23-evals-guardrails.md` | RAGAS thresholds, 50-question golden set composition, prompt-injection defense, audit context fingerprint, threshold-tuning protocol | Drafted |

Files **not yet written** (Stage 7 spec-writer territory): `03-workflows.md`, `05-data-model.md`, `06-api-contracts.md`, `07-database.md`, `08-observability-logs.md`, `09-deployment-ops.md`, `10-build-plan.md`, `11-test-plan.md`, `12-verification.md`, `14-spec-audit-report.md`, `21-tools-and-mcp.md`, `22-memory-context.md`, `24-prompt-registry.md`, **`41-vendor-integration.md`** (new, brownfield slot).

---

## 4. Where the workflow stands

`idea-to-specs` skill workflow:

| Stage | Status | Specialist | Deliverable |
|---|---|---|---|
| 0 — Project Intake | ✅ Done | idea-scope-facilitator | `confirmed-context.md` |
| 1 — Trend Research | ✅ Done | product-trend-researcher | `90-stage1-trend-research.md` |
| 2 — PM Review | ✅ Done | product-manager | `01-product-brief.md` + `02-requirements.md` |
| 3 — UX | ⏭️ Skipped | ux-workflow-designer | `91-stage3-ux-skip.md` (DEC-019) |
| 4 — Architecture | ✅ Done | software-architect + ai-agent-architect | `04-architecture.md` + `20-agent-behavior.md` + `23-evals-guardrails.md` |
| **5 — Architecture Review** | ⏸️ **Next** | architecture-reviewer | `92-stage5-review-memos.md` |
| 6 — Spec Set Selection | Pending | spec-writer | (in 00-spec-index.md) |
| 7 — Spec Generation | Pending | spec-writer | All remaining slot files |
| 8 — Final Quality Audit | Pending | spec-quality-auditor | `14-spec-audit-report.md` |

---

## 5. Locked-in decisions (full text in `13-decision-log.md`)

Just IDs — read the log for rationale + alternatives rejected.

| Range | Theme |
|---|---|
| DEC-001..009 | Stage 0 intake: codename, output path, on-prem, B2B2B, MVP scope, compliance posture, time horizon, trend-research run |
| DEC-010..019 | Stage 2 PM: positioning anchor, Wiki out-of-scope, vLLM/Qwen3/bge-m3 stack pins, integration surface roadmap, eval stack, RAGAS thresholds, vendor priority, Stage 3 skip |
| DEC-020..027 | Stage 2 closure post-hardware-pivot: business model (OSS + services), cloud-rent dev, V2 expanded, REQ-030 in-house first, pricing deferred, OSS-first GTM, 3-month demo deadline (target = 2026-09-27), user owns metric measurement |
| DEC-028..031 | LCC service package (4 tiers); customer self-train stance (L1 refuse / L2-L3 partner / L4 in-house); REQ-030 extended to reranker AND generator LoRA; "Architecture for Insulation" white paper |
| DEC-032..041 | Stage 4 architecture: build from scratch (rejected LlamaIndex/Haystack/RAGFlow-fork), Python+FastAPI, Qdrant+Postgres (no Redis), TEI for embed/rerank, Unstructured+PyMuPDF, deberta NLI, Postgres SKIP LOCKED queue, no agent loop in MVP, Web Component+iframe widget, customer hardware floor 24GB VRAM |
| **DEC-042..051** | **Refusal taxonomy (5 classes + acl_denial_mode), neighboring docs fallback, V2 access-request schema reserved, federation pattern, two-layer authorization, audit dual-write MVP, JWKS token verification, ECM-side `get_effective_acl()` contract, V2 adapter priority (Documentum+OpenText V2-α; SharePoint+M-Files+Hyland V2-β), CDC = webhook + re-poll fallback MVP** |
| **DEC-052..072** | **Stage 5 review-driven decisions: English-only hard constraint (DEC-052, supersedes multilingual rationale in DEC-013/014/037); MVP with-ECM canonical path (DEC-053); latency SLO held + concurrency/caching mandated (DEC-054); GroundedDocs co-locates with ECM in same private network/VPC (DEC-055); retention SLA split webhook/re-poll (DEC-056); 4-option comparison expanded with audit/compliance columns (DEC-057); refusal taxonomy single source = DEC-042 (DEC-058); double-collection schema promoted MVP (DEC-059); audit context_fingerprint columns promoted MVP (DEC-060); JWT alg whitelist RS256/ES256/EdDSA (DEC-061); air-gap JWKS static-bundle path (DEC-062); ECM PDP circuit breaker (DEC-063); audit write-back includes denied intent (DEC-064); chunking strategy 1024+128 (DEC-065); concurrency cap ≤ 2 in-flight (DEC-066); offline model bundle MVP (DEC-067); dev budget ¥800-1,200/month (DEC-068, supersedes DEC-021); both acl_denial_modes shippable MVP (DEC-069); audit append-only wins vs GDPR delete (DEC-070); checkout/checkin out of scope (DEC-071); first-wave market AU+NZ (DEC-072)** |

**Total: 72 pinned decisions.**

---

## 6. Critical context the next agent must internalize

These are the most surprising / load-bearing facts. The next agent will get them wrong unless they read them first.

1. **Two parallel projects exist**. Old: `D:\AI\claude_code\agentic-rag\` is a SaaS-form RAG and **must not be modified or imported** into GroundedDocs. The user explicitly pivoted away from it (DEC-002).
2. **All spec artifacts are English; conversation is Chinese.** Skill invariant — see `idea-to-specs/SKILL.md` §"Non-negotiable invariants". Do not write Chinese into specs.
3. **The user is a CCM consultant**, not a backend ML engineer. Frame design choices in CCM terms. They are learning the LLM/vLLM/Qdrant stack while building.
4. **Solo project, 3-month demo deadline (2026-09-27)** — DEC-026. Scope discipline is the dominant constraint. When in doubt: cut.
5. **User has no local GPU**. Dev environment = cloud rent (RunPod/Vast.ai ≤¥200/mo, DEC-021). MVP deploys on customer hardware (DEC-020 business model). This means `04-architecture.md §9.2 dev rig` and the "borrowed-rig install rehearsal" (RISK-013) are non-trivial.
6. **5-class refusal taxonomy + acl_denial_mode** (DEC-042) is the result of user-driven design conversation, not arbitrary. Default `transparent` mode shows `access_denied` to user; `opaque` masks as `no_recall`. **Audit log always records the real reason** regardless of mode.
7. **Two-layer authorization architecture (§7B)** came from user's external research (`reference.docx`). It supersedes the earlier single-layer adapter sketch. The user's research provided a key diagram now in `specs/assets/two-layer-authorization.png`. Read §7B carefully — it has 13 subsections.
8. **LCC (Model Lifecycle Care)** is a 4-tier service package (DEC-028) that converts the OSS-lifecycle hesitation into recurring revenue. T1 Monitoring (included) / T2 Advisory / T3 Migration / T4 LTS. Architecturally enabled by REQ-033/034/035 (V2).
9. **Vendor adapter priority is split**: sales-priority (DEC-018: Smart Comm / M-Files / Hyland — second-wave GTM) ≠ technical-priority (DEC-050: Documentum + OpenText V2-α because user's research scoped to those). These are intentionally different.
10. **OSS-first GTM (DEC-025)** means **no direct CCM/ECM vendor outreach in first wave**. Demo → industry events → community visibility → inbound vendor conversations. The user reaffirmed this.
11. **Stage 5 architecture review completed 2026-06-28.** Findings + Required Changes are in `review/2026-06-28-architect-review.md`. Stage 7 spec-writer consumes the `RC-T<n>-<m>` mapping table directly; Stage 5 has been folded into the spec set already and does not need to be re-run.
12. **English-only is a hard MVP constraint (DEC-052).** The model stack has been re-selected for English-only (Llama-3.1-8B or Mistral-Small-24B generation, bge-large-en-v1.5 embedding, deberta-v3-base-mnli NLI). Earlier Qwen3 / bge-m3 / deberta-v3-large multilingual rationale is superseded. Hardware floor dropped from 24 GB to 16 GB VRAM.
13. **First-wave market = Australia + New Zealand (DEC-072).** Positioning leverages AU Privacy Act 1988 + NDB + NZ Privacy Act 2020 + sovereign-cloud procurement frame. AU/NZ ECM installed base includes Documentum, OpenText, M-Files, Hyland — adapter priority remains as DEC-018 + DEC-050.

---

## 7. Open items for Stage 5

Stage 5 (architecture review) topics per `idea-to-specs/references/workflow.md`:

**Mandatory** (must run):
- T1 Product-System Fit — does architecture support MVP + future direction; complexity vs solo capacity; user workflows supported
- T6 Build, Test, Verification — phase ordering; TDD / TDD-exempt; junior-developer startable

**Conditional, applies** (must run):
- T2 Architecture Alternatives — already covered in `04-architecture.md §3`; T2 reviewer needs to verify rigor
- T3 Data, API, Database — entity lifecycle, contracts, idempotency, error schemas
- T4 Security, Privacy, Compliance — prompt injection, token verify (DEC-048), audit integrity, two-layer auth correctness, retention compliance
- T5 Reliability, Observability, Ops — demo-grade SLO; docker-compose failure domains
- T8 AI Agent Production Readiness — refusal baseline, citation grounding, iteration cap (when V2 ReAct activates), history server-reconstruction

**Skip** (record `SKIP-NOT-APPLICABLE` + rationale):
- T7 Multi-Tenant Isolation — single tenant per deployment (confirmed-context §3.2)

Stage 5 produces `92-stage5-review-memos.md`. Reviewer may emit `RC-T<n>-<m>` items routed to `spec-writer` per workflow §"Pre-Audit Required Changes Handoff" — do **not** loop back to architect.

The next agent should expect Stage 5 to produce 6 topic memos + the consolidated RC list.

---

## 8. Things the user has explicitly deferred (do not re-litigate)

- Pricing/packaging numbers (DEC-024)
- L1 pretraining for customers (DEC-029 refuse)
- IM channel connectors (Slack/WeCom/Teams)
- Wiki Mode (DEC-011 permanently out of scope)
- Multi-tenant SaaS
- SOC2/HIPAA/PCI/MLPS L3 certification

If the next conversation tries to widen scope into any of these, refer to the relevant DEC and decline.

---

## 9. Style guide for the next agent

Pulled from `C:\Users\OEM\.claude\CLAUDE.md` + observed user preferences in this conversation:

- Short sentences. Active voice.
- Don't open with "Great question!" or close with "I hope this helps."
- When asked for options, give 2–3 with trade-offs — don't pick unless asked.
- If their framing is wrong or reasoning is flawed, say so directly.
- If something is ambiguous, ask ONE clarifying question before proceeding.
- User chats in Chinese; specs are English.
- User often answers batched questions with `(a)/(b)/(c)/(d)` format — follow that pattern.
- User asks "do X" then often pivots ("but also consider Y"). Architect for that — don't get committed to a path before they finalize.

---

## 10. Suggested skills for the next session

| Skill | When to invoke |
|---|---|
| **`idea-to-specs`** | Default. Continuing Stage 5 architecture review → Stage 6 spec selection → Stage 7 generation → Stage 8 audit. Skill is at `D:\AI\claude_code\agentic-rag\.claude\skills\idea-to-specs\`. |
| `codebase-design` | If user pivots from spec writing to implementation, for module interface design (verify/ module is the natural first target). |
| `tdd` | If implementation starts, for test-first work on `verify/`, `audit/`, `acl/`. |
| `diagnosing-bugs` | If user reports an integration test failure. |
| `domain-modeling` | If terminology slippage appears (e.g., "ACL" vs "permission" vs "principal"). |
| `obsidian-vault` | Unrelated to this project — user's notes-taking system. |

`/handoff` itself is one-shot — do not invoke it again unless the next session also needs to hand off.

---

## 11. Last user message before this handoff

> "Q-I2: a / Q-I3: a / Q-I4: a / Q-I5: a. 文档更新完后不要进 Stage 5, 而是参考 /handoff skill 写一份 handoff 文档"

Translation: confirmed all four (a) answers; **do not enter Stage 5**; write handoff doc per /handoff skill.

All four Q's locked into DEC-042..051 + REQ updates. Stage 5 has not been started.

---

## 12. Picking-up checklist for the next agent

1. Read this file in full.
2. Read `D:\AI\claude_code\agentic-rag-onprem\specs\confirmed-context.md` (5 min).
3. Read `D:\AI\claude_code\agentic-rag-onprem\specs\13-decision-log.md` (10 min — at minimum DEC-042..051).
4. Skim `D:\AI\claude_code\agentic-rag-onprem\specs\01-product-brief.md` (10 min).
5. Skim `D:\AI\claude_code\agentic-rag-onprem\specs\04-architecture.md` **including §7B** (15 min).
6. Open `D:\AI\claude_code\agentic-rag\.claude\skills\idea-to-specs\references\workflow.md` and re-read Stage 5 (5 min).
7. Ask user: "Ready to enter Stage 5 architecture review? I will run topics T1, T6 (mandatory) + T2, T3, T4, T5, T8 (conditional), and skip T7."

If user confirms — proceed. If user pivots — adapt.

---

End of handoff document. Total estimated read time for new agent: ~50 minutes.
