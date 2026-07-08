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