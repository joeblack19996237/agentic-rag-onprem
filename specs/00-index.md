# 00 — Spec Index (review anchor, not a memory doc)

Purpose: let a reviewer (human or Claude) know *what's where* and *which DEC/REQ ids it touches* without reading all ~500KB of `specs/` up front. Read this first. Only open a full doc when the review group below requires it.

`13-decision-log.md` is the single source of truth for DEC-### status. If any file below disagrees with it, the decision log wins and the file is stale.

## Review groups (use these to scope subagent review, not the whole directory)

### Group A — Product & Requirements
| File | Size | Covers | Key ids |
|---|---|---|---|
| [01-product-brief.md](01-product-brief.md) | 32K / 305 lines | Problem, personas, MVP scope, non-goals, business model, success metrics, risk register | DEC-005, DEC-010, DEC-020, DEC-024, DEC-025, DEC-072, RC-T1-12, RISK-011 |
| [02-requirements.md](02-requirements.md) | 35K / 130 lines | Functional + non-functional requirements, traceability map | NFR-001..NFR-###, REQ-### (seed list) |
| [confirmed-context.md](confirmed-context.md) | 20K / 158 lines | Stage 0 pinned scope, personas, risk-time profile, authority, stack constraints, drift log | Anchors DEC-005 scope; §Drift Log tracks changes post-pin |

### Group B — Architecture & Agent Behavior
| File | Size | Covers | Key ids |
|---|---|---|---|
| [04-architecture.md](04-architecture.md) | ~95K / ~1160 lines (grew during 2026-07-05 review fixes) | Build-approach decision, tech stack, hardware matrix, module map, typed state, JIT two-layer ECM/CCM authorization | DEC-032, DEC-041, DEC-052, DEC-053, DEC-055, DEC-075, DEC-076, DEC-077, DEC-079, DEC-082, REQ-050, NFR-001 |
| [06-api-contracts.md](06-api-contracts.md) | stub, added 2026-07-05 | Endpoint enumeration (Query/Ingest/Admin/Operational surfaces); placeholder shapes only, full schema is Stage 6 | DEC-107, REQ-057 |
| [20-agent-behavior.md](20-agent-behavior.md) | 13K / 203 lines | Turn pipeline (LangGraph), model permissions, V2 ReAct fallback, review queue, failure/refusal taxonomy | DEC-039, DEC-042, DEC-058, DEC-075, DEC-077, DEC-082, REQ-015, REQ-016, REQ-027 |

### Group C — Evals, Guardrails & Observability
| File | Size | Covers | Key ids |
|---|---|---|---|
| [23-evals-guardrails.md](23-evals-guardrails.md) | 14K / 198 lines | RAGAS metrics/thresholds, golden set, eval runner + failure routing, prompt-injection & output guardrails, context fingerprint, onboarding runbook | DEC-017, DEC-052, DEC-060, DEC-078, REQ-014, REQ-035, RC-T6-01, DEC-128 |
| [08-observability-logs.md](08-observability-logs.md) | ~17K | Log/metric/trace/dashboard/alert schema, SLOs; domain-specific span attributes + `nli_entailment_score` histogram + trace sampling + trace-to-regression path (added post-Stage-8) | DEC-016, DEC-109, NFR-026, NFR-033, DEC-128 |

### Group D — Decision Log (canonical, cross-cutting)
| File | Size | Covers |
|---|---|---|
| [13-decision-log.md](13-decision-log.md) | 56K / 92 lines | All DEC-### entries + supersede history. **Most-referenced ids: DEC-082 (53), DEC-077 (53), DEC-052 (49), DEC-075 (47), DEC-042 (38)** — these are the load-bearing decisions; any change here has the widest blast radius. |

### Group E — Process artifacts (background, not spec content — skim only)
| File | Size | Covers |
|---|---|---|
| [90-stage1-trend-research.md](90-stage1-trend-research.md) | 38K / 472 lines | Market/competitor scan, anti-hallucination patterns, on-prem LLM/rerank landscape, ECM/CCM vendor landscape (Stage 1 input, not a spec) |
| [91-stage3-ux-skip.md](91-stage3-ux-skip.md) | 3K / 61 lines | Why Stage 3 (UX) was skipped for this MVP + re-run triggers |
| [92-stage5-review-memos.md](92-stage5-review-memos.md) | 94K / 939 lines | Stage 5 architecture review findings (D1 hidden assumptions, D2 positioning, ...). **These are open findings against Group A/B/C — check whether each has been resolved into a DEC/REQ or is still outstanding.** |
| [92a-stage5r2-benchmark.md](92a-stage5r2-benchmark.md) | 76K / 578 lines | Stage 5 Round 2 benchmark against 2026 mature-practice patterns (orchestration, concurrency/queue/cache, per-claim verification) |
| [groundeddocs-handoff-2026-06-28.md](groundeddocs-handoff-2026-06-28.md) | 16K / 200 lines | Agent handoff snapshot as of 2026-06-28: locked decisions, open items, style guide. **Time-stamped — verify still current before trusting "where the workflow stands".** |

## Architecture review matrix (dimension-based, primary review axis)

Rationale: architecture review should be driven by cross-cutting quality attributes (ISO/IEC 25010 + ATAM-style quality-attribute scenarios), not by module. Module boundaries hide exactly the bugs that matter — see `92-stage5-review-memos.md` D1-02/D1-03, both cross-module contradictions that a module-by-module review would have missed. Module decomposition below is a **trace target**, not a competing review scheme: each dimension pass ends by marking which modules it touches, instead of spawning a 10th parallel document.

**Review order** (each pass may reference conclusions from passes above it; do not reorder):

**Virtual slicing, not physical file splitting.** `04-architecture.md` stays a single 1108-line source file — do not fork it into per-dimension files. Section numbers (`§7B.12`, `§8.1`, etc.) are cited as stable anchors from `02-requirements.md`, `13-decision-log.md`, `20-agent-behavior.md`, `23-evals-guardrails.md`, and `92-stage5-review-memos.md`; forking would break those references and risks re-introducing drift between copies. Instead, use `Read` with `offset`/`limit` to pull only the line range a dimension needs, plus the fixed Summary range (L7–20, L200–396) for orientation on every pass. `offset`/`limit` below are ready to pass to `Read` directly (offset = starting line, limit = line count).

**§8.1 is mandatory cross-cutting context** *(added 2026-07-05, after a Security-pass finding surfaced it)*: `04-architecture.md` §8.1 (`offset 761, limit 78`, "Verification pipeline") is the pipeline pseudocode that actually pins down node ordering — it belongs to no single dimension but silently constrains three of them (Security: where the retrieval-rail scan runs; Performance: the sequential-vs-parallel latency philosophy; Evaluability: mechanical/NLI threshold order). The Security pass (2026-07-05) found real drift specifically because §8.1 wasn't in its reading list: a first-draft fix invented a redundant `safety_retrieval/` node before noticing §8.1 already specified the ordering (see DEC-096). **Read §8.1 alongside the Summary range on every pass from here on**, not just the ones it's listed against below.

Note: offsets below were re-verified 2026-07-05 after the Summary and Security fixes (DEC-094–097) shifted line numbers by ~50 lines. If you edit `04-architecture.md` again, re-grep `^## \|^### ` before trusting these numbers for the next pass.

| # | Dimension | Primary source (offset/limit into `04-architecture.md` unless noted) | Notes |
|---|---|---|---|
| 0 | **Summary** — completeness & stability of the overall design | §1–2 elevator: `offset 7, limit 14`; §5 module map: `offset 213, limit 135` | Read first, and re-inject alongside every other pass below for orientation. ✅ Reviewed 2026-07-05 — 3 findings fixed (DEC-094, DEC-095). |
| 1 | **Security** | §4.3 SafetyRailAdapter: `offset 167, limit 46`; §7B JIT auth: `offset 460, limit 300`; **§8.1 verification pipeline: `offset 761, limit 78`**; §12.1–12.5: `offset 1036, limit 90`; plus `20-agent-behavior.md` §2.2–2.4 (`offset 74, limit 21`) | Highest blast radius — DEC-082/DEC-077 (53 refs each) live here. ✅ Reviewed 2026-07-05 — 1 finding fixed (DEC-096, DEC-097); required correcting a first-draft fix that conflicted with §8.1. |
| 2 | **Reliability / failure handling** *(added — not in original 9)* | `20-agent-behavior.md` §6: `offset 165, limit 22`; §9.4 concurrency: `offset 964, limit 19`; §7B.4 circuit breaker: `offset 522, limit 18`; **§8.1 verification pipeline (reuse pass 1's extract — early-exit/circuit-breaker ordering lives here too): `offset 761, limit 78`** | Was previously scattered, not owned by any one doc. GPU OOM, model-server crash, ECM-unreachable degradation belong here explicitly. ✅ Reviewed 2026-07-05 — 3 findings fixed (DEC-098; adds NFR-030, NFR-031). |
| 3 | **Performance** | §7B.12 latency budget: `offset 726, limit 26`; §5.0 fan-out latency note: `offset 214, limit 7`; **§8.1 verification pipeline (reuse pass 1's extract — defines the parallel/sequential latency philosophy): `offset 761, limit 78`**; `23-evals-guardrails.md` thresholds (whole file — only 14K) | Cross-check against Reliability pass — timeout/circuit-breaker values should agree with latency budget. Cold-cache headroom is now thin (110 ms per DEC-097) — worth a dedicated look. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-099). |
| 4 | **Deployment & cost** *(added — not in original 9)* | §4.2 hardware matrix + GPU/VRAM sub-sections: `offset 105, limit 62`; §9.1–9.6 deployment topologies: `offset 913, limit 87` | On-prem product — this is often the actual go/no-go dimension for a customer, not a performance sub-note. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-100) plus 2 user-raised architecture questions resolved (DEC-101 docker-compose vs K8s; DEC-102 poll-only CDC mode, adds REQ-057/NFR-032). |
| 5 | **Maintainability & extensibility** | §3 build-approach decision: `offset 21, limit 45`; §5.1 call-direction rules: `offset 348, limit 26`; §5.1.1 typed state schema: `offset 374, limit 49` | Check that V2/V3 deferred items (§8.2, §8.3, §10.2–10.3) don't require re-architecting the MVP graph. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-103). |
| 6 | **Evaluability** | `23-evals-guardrails.md` §2 + §7 (renumbered from duplicate §6 per DEC-099) (whole file — only 14K, no slicing needed); **§8.1 verification pipeline (reuse pass 1's extract — mechanical/NLI threshold ordering): `offset 761, limit 78`** | AI-specific dimension. Confirm every REQ with an acceptance criterion has a corresponding eval or is explicitly marked non-evaluable. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-104). |
| 7 | **Traceability** | §12.4 logging: `offset 1090, limit 6`; `23-evals-guardrails.md` §3.3 (whole file); audit/ module notes inside §5.0 | Enterprise/compliance-facing — check `13-decision-log.md` for anything promoted "to MVP" here (e.g. DEC-060) actually landed in the module map. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-105, DEC-106). |
| 8 | **API / interface contracts** | §7 intro + §7.1–7.4 (now 4 surfaces, was 3): re-grep for current offset; `06-api-contracts.md` now exists as a stub | ✅ Reviewed 2026-07-05 — 1 finding fixed (DEC-107): §7 was missing 4 endpoints already referenced elsewhere; `06-api-contracts.md` stub created per this row's own instruction. |
| 9 | **ECM integration** | §7B full: `offset 460, limit 300`; cdc/ module notes inside §5.0 | Do last — depends on conclusions from Security (1), Reliability (2), and API (8). Overlaps Security's §7B range; that's expected (JIT auth *is* the ECM integration surface) — don't re-read, reuse pass 1's extract. ✅ Reviewed 2026-07-05 — 2 findings fixed (DEC-108) — both were propagation gaps from this same session's own DEC-102. **All 10 review-matrix rows now complete.** |

If a tool genuinely requires whole-file input (can't accept a partial read), generate a temp extract at review time instead of hand-maintaining a split file — e.g. write the concatenated ranges above to `.scratch/review/<dimension>.md` tagged "derived from `04-architecture.md` — do not edit, regenerate before each review." Never commit it as a peer of the source file.

Item "module classification & compatibility" from the original 9-dimension list is intentionally **not** a standalone row — it's the trace target every row above reports against:

**Module trace target** (from §5.0 module map): `api/`, `safety_input/`, `safety_output/`, `policy/`, `cache/`, `retrieve/`, `acl/`, `rerank/`, `generate/`, `verify/`, `audit/`, `ingest/`, `admin/`, `eval/`, `config/`, `widget/`, `cdc/`.

Each dimension pass should end its findings with a line like: *"Touches: acl/, cdc/ — see §7B.5, §7B.8"* so the module view can be reconstructed later by filtering findings, without a separate module-by-module review pass.

## How to use this index for a review

1. **Pick a review question first** (e.g. "is Group B internally consistent with the decision log?"), not "review everything."
2. **Scope one subagent per group** (A, B, C) with the same rubric: internal consistency, REQ/DEC ids resolve to a real entry in `13-decision-log.md`, terminology matches across files, acceptance criteria present for every REQ.
3. **Run a separate cross-reference pass** over Group D: grep all `DEC-\d+` / `REQ-\d+` occurrences repo-wide, confirm every id in A/B/C exists in the log and nothing in the log is orphaned (defined but never referenced downstream).
4. **Treat Group E as evidence, not spec** — findings in `92-stage5-review-memos.md` should each map to either an accepted DEC (now in Group D) or a still-open item; flag any that are neither.
5. **For incremental review**, diff against the last-reviewed commit instead of re-reading full files: `git diff <baseline>..HEAD -- specs/`.

## Stage 6 — Selected / Skipped Specs (confirmed by user, 2026-07-06)

Slot-00 filename note: this project retains `00-index.md` as its stable slot-00 filename rather than the catalog's generic `00-spec-index.md` — an explicit Stage 6 confirmation, not an oversight. Structural fix applied ahead of Stage 7: `93-stage5r2-benchmark.md` renamed to `92a-stage5r2-benchmark.md` (DEC-119) to free catalog-reserved slot 93 for Stage 7's own final `confirmed-context.md` snapshot step — that snapshot (`93-confirmed-context.md`) now exists, a literal copy taken at Stage 7 close-out.

### Selected — Generated (Stage 7 complete, both phases)

| Slot | File | Size | Key IDs introduced | Traces to |
|---|---|---|---|---|
| 03 | `03-workflows.md` | ~17 KB | None new (references REQ-001/002/010/043/045/057) | `04-architecture.md` §5/§7B/§8.1, `20-agent-behavior.md` |
| 05 | `05-data-model.md` | ~31 KB | `legal_hold_invalidation_events` entity (no new REQ/DEC) | `04-architecture.md` §6, §7B.3-§7B.10 |
| 06 | `06-api-contracts.md` | ~21 KB | None new — expanded from DEC-107 stub; resolved the stub's sync/async eval open question | `04-architecture.md` §7, `05-data-model.md` |
| 07 | `07-database.md` | ~21 KB | None new | `05-data-model.md` (physical schema derivation) |
| 08 | `08-observability-logs.md` | ~17 KB (grew post-Stage-8) | NFR-033 (added 2026-07-08, DEC-128 — domain-specific span attributes, `nli_entailment_score` histogram) | `04-architecture.md` §12, `90-stage1-trend-research.md` §3.3, `92a-stage5r2-benchmark.md` §Topic 6, `23-evals-guardrails.md` §2.2/§6/§7 |
| 09 | `09-deployment-ops.md` | ~24 KB | None new — closes RC-T3-01/RC-T4-02/RC-T6-02 | `04-architecture.md` §4.2/§9 |
| 22 | `22-memory-context.md` | ~12 KB | None new | `20-agent-behavior.md` §2.4, `05-data-model.md` |
| 24 | `24-prompt-registry.md` | ~10 KB | None new — establishes the going-forward prompt-changelog discipline | `04-architecture.md` §5.1.1/§8.2, `23-evals-guardrails.md` §3.3 |
| 41 | `41-integration-contracts.md` | ~17 KB | None new | `04-architecture.md` §7B (consolidated for vendor-integrator audience) |
| 42 | `42-compliance-security.md` | ~12 KB | None new — intentionally light per `confirmed-context.md` §7 | `04-architecture.md` §12.5, `01-product-brief.md` §6 |
| 10 | `10-build-plan.md` | ~36 KB | `TASK-001`..`TASK-032` | Every MVP REQ/NFR; applies RC-R2-X3 (team/solo annotation on every task) |
| 11 | `11-test-plan.md` | ~18 KB | `TEST-001`..`TEST-034` | `23-evals-guardrails.md` (golden set, cross-referenced not duplicated), `06-api-contracts.md`; closes RC-T8-01's remaining half |
| 12 | `12-verification.md` | ~12 KB | `VG-001`..`VG-030` | Every `TEST-###`/`TASK-###`; demo script per `01-product-brief.md` §9.3/`confirmed-context.md` §6 |

Already existed pre-Stage-7 (Groups A-C above): `00-index.md`, `01-product-brief.md`, `02-requirements.md`, `04-architecture.md`, `13-decision-log.md`, `20-agent-behavior.md`, `23-evals-guardrails.md`, `confirmed-context.md`.

Stage 7 process artifact: `93-confirmed-context.md` (final snapshot, per `spec-catalog.md` slot 93's own definition).

Stage 8's own output (not generated by Stage 7): `14-spec-audit-report.md`.

### Traceability Summary (all 21 generated + pre-existing spec files)

Every `REQ-###`/`NFR-###`/`RISK-###`/`DEC-###` referenced across the 13 Stage 7 files above resolves to a real definition in `02-requirements.md` or `13-decision-log.md` — verified in the final Stage 7 consistency sweep (see `92-stage5-review-memos.md`'s R6/Stage-7 close-out sections). No new `REQ`/`NFR`/`RISK`/`DEC` ids were minted during Stage 7 generation; the only new id namespaces introduced are `TASK-###` (`10-build-plan.md`), `TEST-###` (`11-test-plan.md`), `VG-###` (`12-verification.md`), and `API-{Q,I,A,O}-##` (`06-api-contracts.md`, contract-ID namespace local to that file).

### Skipped (with rationale, per `.claude/skills/idea-to-specs/references/workflow.md` skip categories)

| Slot | File | Skip category | Rationale |
|---|---|---|---|
| 03a | `03a-ui-design.md` | `SKIP-NOT-APPLICABLE` | No standalone UI in MVP — the only UI surface is the embeddable iframe widget, whose contract lives in `04-architecture.md`'s integration-surface section and `06-api-contracts.md`. Formalized at Stage 2 via DEC-019; see `91-stage3-ux-skip.md` for the full skip memo (Stage 3, not Stage 6, but the same rationale carries forward — Stage 6 re-confirms it rather than re-litigating) |
| 21 | `21-tools-and-mcp.md` | `SKIP-COVERED-ELSEWHERE` | MVP ships no agent tool surface (DEC-039: no agent loop; `20-agent-behavior.md` §2.2-2.3 — the model reads query + retrieved chunks and produces a cited answer, nothing else). The only V2 tool (`sub_query_retrieve`, REQ-015 ReAct fallback) is already fully specified in `20-agent-behavior.md` §3.4 (exactly one tool, no file system/web/SQL access) — a dedicated MCP/tool-inventory spec would duplicate that content for a single V2-scoped tool that doesn't exist in MVP. Revisit if/when REQ-015 ships and the tool surface grows past one tool |
| 30-33 | `30-tenant-lifecycle.md`, `31-tenant-isolation.md`, `32-pricing-model.md`, `33-data-migration.md` | `SKIP-NOT-APPLICABLE` | Single-tenant on-prem per DEC-003; each install is a dedicated single-customer deployment with no tenancy concerns at the architecture level. Formally labeled as Stage 5 topic **T7 — Multi-Tenant Isolation: `SKIP-NOT-APPLICABLE`** (`confirmed-context.md` §2, `92-stage5-review-memos.md` §R5.4). Pricing (32) is separately deferred per DEC-024 (packaging/pricing direction not yet pinned) — not a tenancy skip, but the same non-committal posture applies at Stage 6 |
| 40 | `40-migration.md` | `SKIP-NOT-APPLICABLE` | This is a greenfield product build, not a migration of an existing GroundedDocs deployment to a new state. The brownfield-adjacent concern this slot exists for — installing *into* a host ECM/CCM system — is covered by `41-integration-contracts.md` (external-system integration) and `04-architecture.md` §7B (ECM/CCM federation), not a self-migration. Revisit if a future major-version migration (e.g. a breaking schema change requiring an existing customer install to migrate) is scoped |
| 50 | `50-analytics-events.md` | `SKIP-NOT-APPLICABLE` | GroundedDocs is not a product-analytics/growth-metrics surface — there is no self-serve funnel, no growth dashboard, no product-analytics event taxonomy to define. The operational telemetry this slot might otherwise cover (query latency, cache hit ratios, refusal rate, citation hit-rate) is already fully specified as OTel GenAI-convention spans + audit events in `04-architecture.md` §12.3 and is expanded in `08-observability-logs.md` (this phase) — a separate analytics-event catalog would duplicate that without adding a distinct concern (no marketing/growth/conversion funnel exists in a single-tenant on-prem B2B2B product) |
| 51 | `51-data-pipeline.md` | `SKIP-COVERED-ELSEWHERE` | The only data pipeline in this product is the document ingest pipeline (parse → chunk → embed → index, REQ-002) plus the CDC sync pipeline (ECM → RAG, DEC-051/DEC-102) — both are already fully specified as first-class workflows in `04-architecture.md` §5/§7B and are expanded as system workflows in `03-workflows.md` (this phase) and as schema/migration detail in `07-database.md` (this phase). A separate data-pipeline spec would duplicate rather than add a distinct data-engineering concern (there is no separate analytics ETL, data lake, or warehouse pipeline in this product) |

## Registering a new spec slot

This index is the map every downstream skill, subagent, and reviewer uses to find what exists. A spec file that isn't registered here is effectively invisible to them — treat registration as part of "done," not follow-up cleanup.

When a new file is added under `specs/` (a previously-skipped slot gets un-skipped, a new conditional slot activates, or an existing slot gets a real successor), do all of the following in the same change:

1. **Assign the slot number** from the stable slot map in `.claude/skills/idea-to-specs/references/spec-catalog.md`. Never renumber an existing slot to make room — skipped slots stay skipped, per that catalog's own rule.
2. **Add a row to the matching Review group table** (A–E above). If the file doesn't fit an existing group's theme, add a new group letter (continue the sequence, e.g. `F`) rather than forcing a mismatched fit.
3. **Move it out of the Skipped table** under "Stage 6 — Selected / Skipped Specs" if it was previously listed there, and add it to the "Selected — Generated" table instead, with slot, file, size, key IDs introduced, and what it traces to.
4. **Cross-check new IDs.** If the file mints new `REQ-### / NFR-### / RISK-### / DEC-### / TASK-### / TEST-### / VG-###` ids, confirm they don't collide with existing ones and that `REQ`/`NFR`/`RISK`/`DEC` ids are mirrored into `02-requirements.md` / `13-decision-log.md` as those two files remain canonical for their respective namespaces.
5. **Propagate outside `specs/`.** Update the Layer 1 file listing in `docs/agents/domain.md` and, if the file is now part of the always-read core set, the `### Product specs` section of the repo root `CLAUDE.md`. Downstream skills (`to-prd`, `to-issues`, `implement`, `triage`) read those two files directly — they do not parse `00-index.md` on their own, so an update here alone does not make the new file discoverable to them.
6. **If the new file supersedes or alters an existing `DEC-###` / `REQ-###`**, follow the root `CLAUDE.md` instruction: append a supersedes entry to `13-decision-log.md`, check whether anything in `docs/adr/` needs superseding, and verify whether any in-flight feature under `.scratch/` is affected.

Skipping any of these steps is how this index drifts from the actual directory contents — the failure mode `00-index.md`'s own opening line (`13-decision-log.md` wins if a file disagrees with it) exists to catch for decisions, but has no equivalent safety net for undiscoverable files.
