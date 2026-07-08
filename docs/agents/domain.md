# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

**Layer 1 — product-level specs (canonical source of truth; always read the relevant slots first).**

Start with `specs/00-index.md` — it is a purpose-built review anchor that maps every file to the `DEC-### / REQ-### / RC-###` IDs it touches, grouped into review groups (A–H). Use it to scope which full docs to open; do not read the entire 500KB spec set up front.

*Core specs (always applicable to this product):*

- **`specs/00-index.md`** — master index and review-group map. Read first.
- **`specs/01-product-brief.md`** — problem, personas, MVP scope, non-goals, business model, success metrics, product risk register.
- **`specs/02-requirements.md`** — functional and non-functional requirements, indexed by stable `REQ-### / NFR-###` IDs.
- **`specs/03-workflows.md`** — user workflows and journey maps.
- **`specs/04-architecture.md`** — stack, hardware matrix, module map, typed state, JIT two-layer ECM/CCM authorization, rationale.
- **`specs/05-data-model.md`** — entities, ownership, lifecycle, retention.
- **`specs/06-api-contracts.md`** — Query / Ingest / Admin / Operational endpoint contracts.
- **`specs/07-database.md`** — schema, indexes, migrations.
- **`specs/08-observability-logs.md`** — logs, metrics, traces, dashboards, alerts.
- **`specs/09-deployment-ops.md`** — deployment topology, rollout, rollback, backups, runbooks.
- **`specs/10-build-plan.md`** — phased TDD build plan with 38 `TASK-###` items. Primary input when slicing features into PRDs or issues.
- **`specs/11-test-plan.md`** — `TEST-###` catalog with prior-art references.
- **`specs/12-verification.md`** — `VG-###` verification gates for production readiness.
- **`specs/13-decision-log.md`** — canonical `DEC-###` log, including all supersedes chains. If any other spec disagrees with this file, the decision log wins and the other file is stale.
- **`specs/14-spec-audit-report.md`** — final quality-audit verdict (currently `READY`) and per-gate findings. Consult before assuming the spec set is safely actionable.

*Conditional slots enabled for this product:*

- AI agent → **`specs/20-agent-behavior.md`**, **`specs/22-memory-context.md`**, **`specs/23-evals-guardrails.md`**, **`specs/24-prompt-registry.md`**.
- Brownfield / enterprise integration → **`specs/41-integration-contracts.md`**.
- Compliance / security → **`specs/42-compliance-security.md`**.

*Live context anchor:*

- **`specs/confirmed-context.md`** — Stage 0 pinned scope, personas, risk-time profile, authority, stack constraints, and the drift log tracking post-pin changes. This is the *live* version — append here, never rewrite pinned values. Do not confuse it with `specs/93-confirmed-context.md`, which is a stage-frozen historical snapshot.

*Process artifacts (decision provenance; read on demand, not by default):*

- **`specs/90-stage1-trend-research.md`** — Stage 1 market and trend research with citations.
- **`specs/91-stage3-ux-skip.md`** — Stage 3 UX skip rationale.
- **`specs/92-stage5-review-memos.md`** — Stage 5 architecture review findings and the `RC-###` (Required Changes) mapping table consumed by Stage 7.
- **`specs/92a-stage5r2-benchmark.md`** — Stage 5 Round 2 benchmark results.
- **`specs/93-confirmed-context.md`** — historical snapshot of `confirmed-context.md` at a stage boundary. Use for provenance only.

Session-scoped documents such as `specs/groundeddocs-handoff-*.md` are NOT specs — they are prior-session handoffs and should not be treated as canonical inputs.

**Layer 2 — repo-level domain docs (implementation-level vocabulary and decisions):**

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

**Precedence.** `specs/` defines *what* to build (product level, stable `REQ-### / DEC-###` IDs). `CONTEXT.md` + `docs/adr/` define *how* it lands in this codebase (repo-level vocabulary and reversible implementation trade-offs). When an ADR carries an `Origin: specs/13-decision-log.md#DEC-###` back-reference, treat the spec entry as the source of truth for intent and the ADR as the source of truth for implementation shape.

**Missing-file behavior.** If Layer 2 files (`CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`) don't exist yet, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved. Layer 1 files, by contrast, always exist — if a referenced spec slot is missing, stop and flag it rather than proceeding.

## File structure

This repo is **single-context**:

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

For reference, a multi-context repo (presence of `CONTEXT-MAP.md` at the root) would look like:

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
