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
| [04-architecture.md](04-architecture.md) | 90K / 1108 lines | Build-approach decision, tech stack, hardware matrix, module map, typed state, JIT two-layer ECM/CCM authorization | DEC-032, DEC-041, DEC-052, DEC-053, DEC-055, DEC-075, DEC-076, DEC-077, DEC-079, DEC-082, REQ-050, NFR-001 |
| [20-agent-behavior.md](20-agent-behavior.md) | 13K / 203 lines | Turn pipeline (LangGraph), model permissions, V2 ReAct fallback, review queue, failure/refusal taxonomy | DEC-039, DEC-042, DEC-058, DEC-075, DEC-077, DEC-082, REQ-015, REQ-016, REQ-027 |

### Group C — Evals & Guardrails
| File | Size | Covers | Key ids |
|---|---|---|---|
| [23-evals-guardrails.md](23-evals-guardrails.md) | 14K / 198 lines | RAGAS metrics/thresholds, golden set, eval runner + failure routing, prompt-injection & output guardrails, context fingerprint, onboarding runbook | DEC-017, DEC-052, DEC-060, DEC-078, REQ-014, REQ-035, RC-T6-01 |

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
| [93-stage5r2-benchmark.md](93-stage5r2-benchmark.md) | 76K / 578 lines | Stage 5 Round 2 benchmark against 2026 mature-practice patterns (orchestration, concurrency/queue/cache, per-claim verification) |
| [groundeddocs-handoff-2026-06-28.md](groundeddocs-handoff-2026-06-28.md) | 16K / 200 lines | Agent handoff snapshot as of 2026-06-28: locked decisions, open items, style guide. **Time-stamped — verify still current before trusting "where the workflow stands".** |

## Architecture review matrix (dimension-based, primary review axis)

Rationale: architecture review should be driven by cross-cutting quality attributes (ISO/IEC 25010 + ATAM-style quality-attribute scenarios), not by module. Module boundaries hide exactly the bugs that matter — see `92-stage5-review-memos.md` D1-02/D1-03, both cross-module contradictions that a module-by-module review would have missed. Module decomposition below is a **trace target**, not a competing review scheme: each dimension pass ends by marking which modules it touches, instead of spawning a 10th parallel document.

**Review order** (each pass may reference conclusions from passes above it; do not reorder):

**Virtual slicing, not physical file splitting.** `04-architecture.md` stays a single 1108-line source file — do not fork it into per-dimension files. Section numbers (`§7B.12`, `§8.1`, etc.) are cited as stable anchors from `02-requirements.md`, `13-decision-log.md`, `20-agent-behavior.md`, `23-evals-guardrails.md`, and `92-stage5-review-memos.md`; forking would break those references and risks re-introducing drift between copies. Instead, use `Read` with `offset`/`limit` to pull only the line range a dimension needs, plus the fixed Summary range (L7–20, L200–396) for orientation on every pass. `offset`/`limit` below are ready to pass to `Read` directly (offset = starting line, limit = line count).

| # | Dimension | Primary source (offset/limit into `04-architecture.md` unless noted) | Notes |
|---|---|---|---|
| 0 | **Summary** — completeness & stability of the overall design | §1–2 elevator: `offset 7, limit 14`; §5 module map: `offset 200, limit 197` | Read first, and re-inject alongside every other pass below for orientation. |
| 1 | **Security** | §4.3 SafetyRailAdapter: `offset 167, limit 33`; §7B JIT auth: `offset 433, limit 315`; §12.1–12.5: `offset 1025, limit 84`; plus `20-agent-behavior.md` §2.2–2.4 (`offset 74, limit 21`) | Highest blast radius — DEC-082/DEC-077 (53 refs each) live here. |
| 2 | **Reliability / failure handling** *(added — not in original 9)* | `20-agent-behavior.md` §6: `offset 165, limit 22`; §9.4 concurrency: `offset 951, limit 19`; §7B.4 circuit breaker: `offset 510, limit 18` | Was previously scattered, not owned by any one doc. GPU OOM, model-server crash, ECM-unreachable degradation belong here explicitly. |
| 3 | **Performance** | §7B.12 latency budget: `offset 714, limit 25`; §5.0 fan-out latency note: `offset 216, limit 4`; `23-evals-guardrails.md` thresholds (whole file — only 14K) | Cross-check against Reliability pass — timeout/circuit-breaker values should agree with latency budget. |
| 4 | **Deployment & cost** *(added — not in original 9)* | §4.2 hardware matrix + GPU/VRAM sub-sections: `offset 105, limit 62`; §9.1–9.6 deployment topologies: `offset 902, limit 88` | On-prem product — this is often the actual go/no-go dimension for a customer, not a performance sub-note. |
| 5 | **Maintainability & extensibility** | §3 build-approach decision: `offset 21, limit 45`; §5.1 call-direction rules: `offset 341, limit 22`; §5.1.1 typed state schema: `offset 363, limit 34` | Check that V2/V3 deferred items (§8.2, §8.3, §10.2–10.3) don't require re-architecting the MVP graph. |
| 6 | **Evaluability** | `23-evals-guardrails.md` §2 + §6 (whole file — only 14K, no slicing needed) | AI-specific dimension. Confirm every REQ with an acceptance criterion has a corresponding eval or is explicitly marked non-evaluable. |
| 7 | **Traceability** | §12.4 logging: `offset 1077, limit 6`; `23-evals-guardrails.md` §3.3 (whole file); audit/ module notes inside §5.0 | Enterprise/compliance-facing — check `13-decision-log.md` for anything promoted "to MVP" here (e.g. DEC-060) actually landed in the module map. |
| 8 | **API / interface contracts** | §7 intro + §7.1–7.3: `offset 412, limit 21` (full contracts deferred to `06-api-contracts.md`, not yet written) | If `06-api-contracts.md` doesn't exist yet, this pass should produce its stub, not just findings. |
| 9 | **ECM integration** | §7B full: `offset 433, limit 315`; cdc/ module notes inside §5.0 | Do last — depends on conclusions from Security (1), Reliability (2), and API (8). Overlaps Security's §7B range; that's expected (JIT auth *is* the ECM integration surface) — don't re-read, reuse pass 1's extract. |

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
