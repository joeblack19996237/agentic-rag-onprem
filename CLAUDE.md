# agentic-rag-onprem

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.


Any modification to specs/ that alters a specific DEC-### or REQ-### must append a supersedes entry to 13-decision-log.md, check if anything in docs/adr/ needs to be superseded, and verify whether any in-flight features in .scratch/ are affected.