# agentic-rag-onprem

## Project

**GroundedDocs** — an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland, etc.) whose enterprise customers need answers grounded in verified citations, with honest refusal when grounding is weak. Open-weight, fully local LLM inference, model-swappable; no cloud egress. See `specs/01-product-brief.md` for the full problem statement and positioning.

The canonical source of truth for what's being built and why is `specs/` (see below); everything else in the repo supports producing, maintaining, and implementing against that spec set. **Don't trust a build-phase description written in this file, README.md, or any other prose summary** — those drift the moment an issue closes. Check current status via `.scratch/<feature>/issues/*.md` (`Status:` line) and, if present, the newest file under `.scratch/handoff/` (a point-in-time onboarding snapshot — read its own date and cross-check against `git log --oneline -5` before trusting it, since it too can go stale).

## Repo structure

- `specs/` — canonical product-level spec set (`00-index.md` is the entry point). See "Product specs" below.
- `docs/agents/` — per-repo config consumed by the engineering skills (issue tracker, triage labels, domain-doc layout, dev-environment ground truth).
- `docs/testing.md` — how to write a test here, what to avoid, and a live inventory of every test that exists. Update it whenever a test is added, removed, or changes coverage.
- `docs/coding-standards.md` — judgment-call coding conventions (naming, error-handling, security, logging) a linter can't check; mechanical rules live in `pyproject.toml`'s `[tool.ruff.lint]` instead (see its own "What's enforced by tooling" section). Consumed by `code-review`/`review`'s Standards axis and `implement`.
- `tools/` — standalone scripts invoked directly. See `tools/README.md` for the current inventory and when to promote a repeated command here instead of retyping it.
- `docs/adr/` — repo-level architectural decisions (created lazily by `domain-modeling`/`improve-codebase-architecture`; may not exist yet).
- `.scratch/<feature>/` — local issue tracker (markdown-based; see "Issue tracker" below).
- `.scratch/handoff/` — point-in-time onboarding snapshots for a fresh session with no prior context. Useful starting point, not an evergreen doc — verify against recent git log and the issue tracker before trusting it.
- `.claude/skills/` — **canonical** skill definitions for this repo. Any skill reference (in this file, in other skills, or in ad-hoc instructions) must point here.

## Documentation conventions

Every doc under `specs/`, `docs/`, and `.scratch/` should carry a short, grep-able summary in its first ~7 lines: what it covers, and a freshness signal (a date, a status, an explicit staleness caveat) so an agent can judge whether to trust it without reading the whole file. `docs/agents/dev-environment.md`'s `Last probed:` line and `specs/00-index.md`'s opening Purpose paragraph are the reference examples.

Add or update this summary whenever a doc is created or substantially rewritten. When a doc's content contradicts its own summary or contradicts observable repo state, fix both together rather than patching only the part that was noticed first.

Two narrow slices of drift are machine-checked, not just self-discipline: `tests/docs/test_doc_drift.py` (part of CI, see below) fails if any `DEC-###` cited anywhere in `specs/`/`docs/`/`.scratch/`/this file/`README.md` doesn't resolve to a real row in `specs/13-decision-log.md`, or if `README.md`'s ✅/⏳ issue markers disagree with the referenced `.scratch/*/issues/*.md` file's own `Status:` line. It does not catch other kinds of prose drift (e.g. a stale phase description); that's still on the "fix it when you notice it" discipline above.

## Running and verifying this repo

- **Environment ground truth**: `docs/agents/dev-environment.md` — probed capabilities (Docker, GPU, compiler toolchain, CI/CD access) for the current execution environment. Re-probe rather than trust its date if anything about the environment might have changed; don't assume a capability is available without checking it.
- **CI**: `.github/workflows/ci.yml` runs lint (`ruff check .`), type check (`mypy .`), the architecture import-graph check, the documentation-drift check (`tests/docs/test_doc_drift.py` — see "Documentation conventions" above), and the API smoke test. Run the same checks locally before calling a change done — `bash tools/verify.sh` runs all of them in one command. `pyproject.toml` pins `pythonpath = ["."]` so bare `pytest` and `python -m pytest` resolve imports identically — don't remove it.
- **Pre-commit**: `.pre-commit-config.yaml` runs ruff (`--fix`), mypy, the import-graph check, and the doc-drift check as a local git hook — the same checks CI runs, minus the deliberately-red `/ready` smoke test (a red-by-design commit gate would just train people to use `--no-verify`). Run `pre-commit install` once per clone (see README's "Getting started"); dev-tool versions are pinned in `requirements-dev.txt`, kept in sync with what CI installs. If a hook ever disagrees with CI, that's a bug in `.pre-commit-config.yaml`, not something to route around.
- **Writing/running tests**: see `docs/testing.md` for how to write a test in this repo, what to avoid, and the current inventory. Write and run a targeted test for whatever you implement, and update `docs/testing.md`'s inventory in the same commit.
- **A change is not verified until it has actually been run.** Writing a test is not the same as running it — execute the relevant command and read its real output before marking an acceptance criterion done (see `.claude/skills/verifiable-acceptance-criteria/SKILL.md`). This applies with extra force to autonomous/async work, where there's no human in the loop to catch a claimed-but-unverified result.
- **Known verification ceiling**: this execution environment has no Docker, no Docker Compose, no GPU, and no C/C++ build toolchain (per `dev-environment.md`). `docker-compose.yml`'s services cannot be started or integration-tested end-to-end here. `specs/13-decision-log.md` DEC-135 pins the Phase 2+ response: fake/stub-backed tests and contract/schema checks are the agent-executable default (see `11-test-plan.md`'s Test Environments table); anything needing a live service is `[manual-verify]` with a named owner (per `verifiable-acceptance-criteria`), never assumed passing or silently skipped. Re-check `dev-environment.md` before assuming this ceiling still holds, since it's a property of the environment, not a permanent one.

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Product specs

Canonical product-level source of truth: `specs/`. Entry point is `specs/00-index.md` (a review anchor that maps every file to the `DEC-### / REQ-### / RC-###` IDs it touches). Align any PRD, issue, or implementation with the relevant `REQ-###`/`NFR-###` (`specs/02-requirements.md`), the `DEC-###` (`specs/13-decision-log.md` — canonical, wins over any conflicting spec text), and the `TASK-###` (`specs/10-build-plan.md`) it traces to. Current audit verdict: `specs/14-spec-audit-report.md`. Downstream skills (`to-prd`, `to-issues`, `implement`, `triage`, `review`) must cite these stable IDs in their output so PRDs, issues, and commits stay traceable to spec intent. Read order and precedence between `specs/`, `CONTEXT.md`, and `docs/adr/` are defined in `docs/agents/domain.md`.

**Editing specs/ content**: use the `update-specs` skill (`.claude/skills/update-specs/SKILL.md`) — it owns blast-radius mapping, ID minting, decision-log append, index propagation, and re-audit. Don't hand-edit a `specs/*.md` file for a substantive content change (typos/formatting excepted) without going through it.

**Cross-model review of `specs/` itself** (not just of code diffs — see `.claude/skills/peer-review/specs-review-prompt.md`, a standing gap this project has: every internal audit of `specs/` has been Claude reviewing Claude, the exact anti-pattern `DEC-130` names). Remind the user this is due when any of these hold:
- Starting implementation of a new Phase (its spec content is about to become load-bearing for real code, and hasn't had non-Claude eyes yet)
- `specs/13-decision-log.md` has gained ~10+ new `DEC-###` entries since the date/count recorded in `specs-review-prompt.md`'s own "Last run" line
- A Group A or B file (`specs/00-index.md`'s Product & Requirements / Architecture groups) gets a substantial rewrite
- `specs/14-spec-audit-report.md`'s self-audit has returned READY/PASS for 5+ consecutive re-audit iterations with no intervening cross-model review

This review is run by the user in a different tool/model — Claude only prepares or updates the prompt, never runs it. This entry exists because the user asked for a recurring practice; if a future specs/ review is ever a genuine one-off instead, don't generalize that into a new standing rule.

### Acceptance criteria verifiability

Every issue/PRD acceptance criterion must be checkable in the current phase and the current execution environment — no criteria assuming a later phase's artifacts or infrastructure the agent can't reach (cloud GPU, live CI, Docker where unavailable). `to-issues` and `implement` both invoke `.claude/skills/verifiable-acceptance-criteria/SKILL.md`; unreachable criteria get split into an agent-checkable proxy plus a `[manual-verify]` item with a named owner, never silently assumed passing.

### Dependency version claims

Don't trust training-data recall for fast-moving/pre-1.0 dependencies (this stack pins LangGraph) — verify via WebFetch or `gh api` before asserting a version is current. `specs/13-decision-log.md` DEC-131/132/133 is the reference precedent. `implement` and `tdd` both carry this rule.

### Handoff documents

Overrides the generic `handoff` skill's default: **save to `.scratch/handoff/<slug>.md` and commit it**, not the OS temp dir — the point is a future session or agent can find it in the repo's own history. Reference example: `.scratch/handoff/phase1_handoff.md` (commit `076ce77`, tag `handoff/phase-1-close`) — written for a zero-context fresh session, cross-references issues/specs by path rather than restating them, redacts anything sensitive.

Write one when:
- A build phase's exit gate closes
- A long/risky operation is starting and the session might not survive it
- The user asks to checkpoint or hand off

Tag the commit `handoff/<slug>` afterward (matching the doc's topic, not necessarily its filename) — `git tag -l 'handoff/*'` then finds every handoff point without digging through `git log`. Local tags only; pushing is a separate, explicit decision.

### Session feedback

`.scratch/session-feedback.md` logs *how the work went* — friction points, ambiguous instructions, late-caught mistakes, things worth repeating — not *what* changed (that's commit messages / `specs/13-decision-log.md`; don't duplicate here).

Append an entry at the first of these that happens (skip trivial Q&A): immediately before a `git commit` covering substantial work, or — for a session running long without committing — at a natural checkpoint (a topic/chapter shift, or the user asking what's next) once real friction has already accumulated. Don't rely on the commit trigger alone: a session that goes a long stretch without committing never fires it, which is exactly what happened during Phase 2 kickoff (2026-07-14) — three real friction points accumulated and went unlogged until the user asked directly whether this file had been updated. Be specific — a vague "went well" wastes a future reader's attention. Only promote a repeated observation into a standing rule once it's actually recurred, not on first mention.

Skim existing entries at the start of a session doing substantial work in this repo, if not read recently (check/update the file's own "Last read" line). The goal is closing the loop between noticing friction and no longer hitting it — not accumulating a log nobody rereads.

### Commit history sweeps

Per-commit review (`code-review`, `peer-review`) and the doc-drift check each operate on one diff/rule at a time — neither sees a pattern that only shows up *across* commits: the same bug class fixed twice, a file touched repeatedly without consolidating why, a commit message that's stopped matching its own diff. Read `git log` and recent diffs together and name the pattern, not just the instance — `.scratch/review-reports/commit-sweep-2026-07-13.md` is the reference example.

Run one when any of these hold:
- ~15-20 commits have landed since the last sweep (check the latest `.scratch/review-reports/commit-sweep-*.md`'s date/range)
- A build phase's exit gate closes
- The user asks for one directly

No different model needed (the failure mode is zoom level, not same-family bias — unlike the specs/ cross-model review), so Claude runs this itself. Save to `.scratch/review-reports/commit-sweep-<date>.md`. Run in-session on trigger, not as unattended cron automation — matches this project's demo-stage scale, not production process.

### Test-quality audits

`.claude/skills/test-audit/SKILL.md` — periodic reread of the *existing* test suite for false-confidence tests (pass without actually verifying the behavior claimed), distinct from `tdd`'s authoring-time discipline and `code-review`/`review`'s diff-scoped check. Same zoom-level shift as commit-sweeps, applied to tests.

Run it when any of these hold:
- Before a build phase's exit gate closes
- `docs/testing.md`'s inventory has grown since the last audit (check the latest `.scratch/review-reports/test-audit-*.md`)
- The user asks for one directly

Mechanically-obvious fixes get applied directly; anything needing judgment about intended behavior gets flagged, not guessed — see the skill for the full rule. Report to `.scratch/review-reports/test-audit-<date>.md`, matching the commit-sweep convention.

### Closing out a work cycle

Before calling substantial work done (not trivial Q&A), run through what applies. Each step already exists with its own trigger elsewhere in this file — this just strings them together so nothing gets missed by not re-reading every section:

1. **Code-level verification** — `bash tools/verify.sh`. Non-negotiable for any code change; see "Running and verifying this repo" above.
2. **Performance, once it exists** — Phase 1 has no perf-sensitive code yet (`specs/11-test-plan.md`'s Performance Tests are all Phase 2+). Once a `TEST-03x`/`TEST-041` is implemented, compare against the last recorded baseline, not just the threshold — a rising latency can pass a fixed threshold every time and still be a regression.
3. **Agent review, for a nontrivial diff** — `code-review`/`review` plus `peer-review`; see `peer-review/SKILL.md`'s own trigger guidance.
4. **Global scans, if their cadence is hit** — `commit-sweep` and `test-audit` (see their own sections above); don't run either just because this checklist is being followed.
5. **Tools/ promotion check** — did a command get retyped more than once this session? Also check across sessions, not just this one: grep `specs/13-decision-log.md` and recent commit messages for the same pattern before assuming this is the first occurrence — see `tools/README.md`'s promotion criteria (a within-session-only check misses a pattern that recurred once per session across several sessions and never got promoted).
6. **Session feedback** — per "Session feedback" above.
7. **Handoff, if warranted** — per "Handoff documents" above.

Not every step fires every cycle — a small, contained fix might only need step 1.
