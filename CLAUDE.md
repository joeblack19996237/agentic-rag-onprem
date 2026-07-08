# agentic-rag-onprem

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Product specs

Canonical product-level source of truth: `specs/`. Entry point is `specs/00-index.md` (a review anchor that maps every file to the `DEC-### / REQ-### / RC-###` IDs it touches). Before writing any PRD, issue, or implementation for this repo, align with the relevant `REQ-###` / `NFR-###` in `specs/02-requirements.md`, the `DEC-###` in `specs/13-decision-log.md` (canonical — wins over any conflicting spec text), and the `TASK-###` in `specs/10-build-plan.md` when slicing features. The current audit verdict lives in `specs/14-spec-audit-report.md`. Downstream skills (`to-prd`, `to-issues`, `implement`, `triage`, `review`) must cite these stable IDs in their output so PRDs, issues, and commits stay traceable to spec intent. Full read order and precedence between `specs/`, `CONTEXT.md`, and `docs/adr/` are defined in `docs/agents/domain.md`.


Any modification to specs/ that alters a specific DEC-### or REQ-### must append a supersedes entry to 13-decision-log.md, check if anything in docs/adr/ needs to be superseded, and verify whether any in-flight features in .scratch/ are affected.

### Acceptance criteria verifiability

Every issue/PRD acceptance criterion must be checkable in the current phase and the current execution environment — no criteria assuming a later phase's artifacts or infrastructure the agent can't reach (cloud GPU, live CI, Docker where unavailable). `to-issues` and `implement` both invoke `.claude/skills/verifiable-acceptance-criteria/SKILL.md`; unreachable criteria get split into an agent-checkable proxy plus a `[manual-verify]` item with a named owner, never silently assumed passing.

### Dependency version claims

Don't trust training-data recall for fast-moving/pre-1.0 dependencies (this stack pins LangGraph) — verify via WebFetch or `gh api` before asserting a version is current. `specs/13-decision-log.md` DEC-131/132/133 is the reference precedent. `implement` and `tdd` both carry this rule.