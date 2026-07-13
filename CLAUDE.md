# agentic-rag-onprem

## Project

**GroundedDocs** — an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland, etc.) whose enterprise customers need answers grounded in verified citations, with honest refusal when grounding is weak. Open-weight, fully local LLM inference, model-swappable; no cloud egress. See `specs/01-product-brief.md` for the full problem statement and positioning.

The canonical source of truth for what's being built and why is `specs/` (see below); everything else in the repo supports producing, maintaining, and implementing against that spec set. **Don't trust a build-phase description written in this file, README.md, or any other prose summary** — those drift the moment an issue closes. Check current status via `.scratch/<feature>/issues/*.md` (`Status:` line) and, if present, the newest file under `.scratch/handoff/` (a point-in-time onboarding snapshot written for a fresh session — read its own date and cross-check against `git log --oneline -5` before trusting it, since it too can go stale).

## Repo structure

- `specs/` — canonical product-level spec set (`00-index.md` is the entry point). See "Product specs" below.
- `docs/agents/` — per-repo config consumed by the engineering skills (issue tracker, triage labels, domain-doc layout, dev-environment ground truth).
- `docs/testing.md` — how to write a test in this repo, what to avoid, and a live inventory of every test that actually exists. Update it whenever a test is added, removed, or changes what it covers.
- `docs/coding-standards.md` — judgment-call coding conventions (naming, error-handling boundaries, security, logging) that a linter can't check. Mechanically-checkable rules live in `pyproject.toml`'s `[tool.ruff.lint]` instead — that file's own "What's enforced by tooling" section maps rule to code. `code-review`/`review`'s Standards axis and `implement` both consume it.
- `tools/` — standalone scripts invoked directly (not test code, not a skill's internal implementation detail). See `tools/README.md` for the current inventory and when to promote a repeated command into a script here instead of retyping it.
- `docs/adr/` — repo-level architectural decisions (created lazily by `domain-modeling`/`improve-codebase-architecture`; may not exist yet).
- `.scratch/<feature>/` — local issue tracker (markdown-based; see "Issue tracker" below).
- `.scratch/handoff/` — point-in-time onboarding snapshots written for a fresh session with no prior context. Useful starting point, not an evergreen doc — verify against recent git log and the issue tracker before trusting it.
- `.claude/skills/` — **canonical** skill definitions for this repo. Any skill reference (in this file, in other skills, or in ad-hoc instructions) must point here.
- `.agents/skills/` — a stale local mirror from an earlier skill-installer layout. It is gitignored and no longer maintained — **do not read from or cite skills in this directory**; the current version of every skill listed there now lives under `.claude/skills/`.

## Documentation conventions

Every doc under `specs/`, `docs/`, and `.scratch/` should carry a short, grep-able summary in its first ~7 lines: what it covers, and enough of a freshness signal (a date, a status, an explicit staleness caveat) that an agent can judge whether to trust it without reading the whole file. `docs/agents/dev-environment.md`'s `Last probed:` line and `specs/00-index.md`'s opening Purpose paragraph are the reference examples.

When creating a new doc, or substantially rewriting an existing one, add or update this summary. When a doc's content contradicts its own summary or contradicts observable repo state (the way this file's old "there is no application source tree yet" line contradicted the `api/` scaffold that had already landed), fix both together rather than patching only the part that was noticed first.

Two narrow slices of drift are machine-checked, not just self-discipline: `tests/docs/test_doc_drift.py` (part of CI, see below) fails if any `DEC-###` cited anywhere in `specs/`/`docs/`/`.scratch/`/this file/`README.md` doesn't resolve to a real row in `specs/13-decision-log.md`, or if `README.md`'s ✅/⏳ issue markers disagree with the referenced `.scratch/*/issues/*.md` file's own `Status:` line — the exact class of bug this file and `README.md` both had before this session's P0/P2 fixes. It does not catch other kinds of prose drift (e.g. a stale phase description); that's still on the "fix it when you notice it" discipline above.

## Running and verifying this repo

- **Environment ground truth**: `docs/agents/dev-environment.md` — probed capabilities (Docker, GPU, compiler toolchain, CI/CD access) for the current execution environment. Re-probe rather than trust its date if anything about the environment might have changed; don't assume a capability is available without checking it.
- **CI**: `.github/workflows/ci.yml` runs lint (`ruff check .`), type check (`mypy .`), the architecture import-graph check, the documentation-drift check (`tests/docs/test_doc_drift.py` — see "Documentation conventions" above), and the API smoke test. Run the same checks locally before calling a change done: `ruff check .`, `mypy .`, `pytest`, or `bash tools/verify.sh` to run all of them in one command. `pyproject.toml` pins `pythonpath = ["."]` so bare `pytest` and `python -m pytest` resolve imports identically — don't remove it.
- **Pre-commit**: `.pre-commit-config.yaml` runs ruff (`--fix`), mypy, the import-graph check, and the doc-drift check as a local git hook — the same checks CI runs, minus the deliberately-red `/ready` smoke test (a red-by-design commit gate would just train people to use `--no-verify`). Run `pre-commit install` once per clone (see README's "Getting started"); dev-tool versions are pinned in `requirements-dev.txt`, kept in sync with what CI installs. If a hook ever disagrees with CI, that's a bug in `.pre-commit-config.yaml`, not something to route around.
- **Writing/running tests**: see `docs/testing.md` for how to write a test in this repo, what to avoid, and the current inventory. Write and run a targeted test for whatever you implement, and update `docs/testing.md`'s inventory in the same commit — don't let it drift the way `CLAUDE.md`/`README.md` already did once this session.
- **A change is not verified until it has actually been run.** Writing a test is not the same as running it — execute the relevant command and read its real output before marking an acceptance criterion done (see `.claude/skills/verifiable-acceptance-criteria/SKILL.md`). This applies with extra force to autonomous/async work, where there's no human in the loop to catch a claimed-but-unverified result.
- **Known verification ceiling**: this execution environment has no Docker, no Docker Compose, no GPU, and no C/C++ build toolchain (per `dev-environment.md`). `docker-compose.yml`'s 12 services (vllm, tei-embed, tei-rerank, nli, safety-input, safety-output, policy, qdrant, postgres, redis, api, widget) cannot be started or integration-tested end-to-end here. `specs/13-decision-log.md` DEC-135 pins the Phase 2+ response: fake/stub-backed tests and contract/schema checks are the agent-executable default (see `11-test-plan.md`'s Test Environments table); anything needing a live service is `[manual-verify]` with a named owner (per `verifiable-acceptance-criteria`), never assumed passing or silently skipped. Re-check `dev-environment.md` before assuming this ceiling still holds, since it's a property of the environment, not a permanent one.

## Agent skills

### Issue tracker

Local markdown under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Product specs

Canonical product-level source of truth: `specs/`. Entry point is `specs/00-index.md` (a review anchor that maps every file to the `DEC-### / REQ-### / RC-###` IDs it touches). Before writing any PRD, issue, or implementation for this repo, align with the relevant `REQ-###` / `NFR-###` in `specs/02-requirements.md`, the `DEC-###` in `specs/13-decision-log.md` (canonical — wins over any conflicting spec text), and the `TASK-###` in `specs/10-build-plan.md` when slicing features. The current audit verdict lives in `specs/14-spec-audit-report.md`. Downstream skills (`to-prd`, `to-issues`, `implement`, `triage`, `review`) must cite these stable IDs in their output so PRDs, issues, and commits stay traceable to spec intent. Full read order and precedence between `specs/`, `CONTEXT.md`, and `docs/adr/` are defined in `docs/agents/domain.md`.

**Cross-model review of `specs/` itself** (not just of code diffs — see `.claude/skills/peer-review/specs-review-prompt.md`, a standing gap this project has: every internal audit of `specs/` has been Claude reviewing Claude, the exact anti-pattern `DEC-130` names). Remind the user this is due when any of these hold:
- Starting implementation of a new Phase (its spec content is about to become load-bearing for real code, and hasn't had non-Claude eyes yet)
- `specs/13-decision-log.md` has gained ~10+ new `DEC-###` entries since the date/count recorded in `specs-review-prompt.md`'s own "Last run" line
- A Group A or B file (`specs/00-index.md`'s Product & Requirements / Architecture groups) gets a substantial rewrite
- `specs/14-spec-audit-report.md`'s self-audit has returned READY/PASS for 5+ consecutive re-audit iterations with no intervening cross-model review (this project's own DEC-130 principle applied to the audit process itself, not just model selection — added 2026-07-13 per the first cross-model review's own R.14 finding, `.scratch/review-reports/specs-cross-model-review-2026-07-13.md`)

This review is run by the user in a different tool/model — Claude only prepares or updates the prompt, never runs it. If a specs/ review is ever done as a true one-off with no expectation of repeating, don't generalize this into a standing rule; this entry exists because the user asked for a recurring one.


Any modification to specs/ that alters a specific DEC-### or REQ-### must append a supersedes entry to 13-decision-log.md, check if anything in docs/adr/ needs to be superseded, and verify whether any in-flight features in .scratch/ are affected.

### Acceptance criteria verifiability

Every issue/PRD acceptance criterion must be checkable in the current phase and the current execution environment — no criteria assuming a later phase's artifacts or infrastructure the agent can't reach (cloud GPU, live CI, Docker where unavailable). `to-issues` and `implement` both invoke `.claude/skills/verifiable-acceptance-criteria/SKILL.md`; unreachable criteria get split into an agent-checkable proxy plus a `[manual-verify]` item with a named owner, never silently assumed passing.

### Dependency version claims

Don't trust training-data recall for fast-moving/pre-1.0 dependencies (this stack pins LangGraph) — verify via WebFetch or `gh api` before asserting a version is current. `specs/13-decision-log.md` DEC-131/132/133 is the reference precedent. `implement` and `tdd` both carry this rule.

### Handoff documents

Overrides the generic `handoff` skill's default for this repo: **save to `.scratch/handoff/<slug>.md` and commit it** — not the OS temp directory the generic skill defaults to. The point of a handoff doc here is that a future session, or a different agent picking up interrupted work, can find it in the repo's own history; a temp-dir file serves neither. `.scratch/handoff/phase1_handoff.md` (commit `076ce77`, tag `handoff/phase-1-close`) is the reference example — written for a zero-context fresh session, cross-references issues/specs by path instead of restating their content, and redacts anything sensitive (none existed at the time, but the rule stands regardless).

Write one when any of these hold, not only at a phase boundary:
- A build phase's exit gate closes (the existing case)
- A long or risky operation is about to start and the session might not survive to see it through
- The user explicitly asks to checkpoint or hand off

### Session feedback

`.scratch/session-feedback.md` is a running log of *how the work went*, not what was built — friction points, ambiguous instructions, mistakes caught late, things that worked well enough to repeat. Commit messages and `specs/13-decision-log.md` already cover *what* changed; this file is for the meta-layer neither of those capture, so don't duplicate their content here.

Append an entry before committing a substantial session's work (not for trivial Q&A). Keep entries honest and specific — a vague "went well" entry costs a future reader's attention for nothing. Don't promote every entry's observations into a new standing rule immediately; note them, and only turn a recurring one into an actual rule/checklist item once it's actually recurred (see the file's own entries for the pattern).

Skim the file's existing entries at the start of a session about to do substantial work in this repo, if it hasn't been read recently (check the file's own "Last read" line, and update it when you do). The point is closing the loop between "we noticed a friction point" and "we stopped hitting it" — not accumulating a log nobody rereads.

### Commit history sweeps

Per-commit review (`code-review`, `peer-review`) and the doc-drift check each operate on one diff or one mechanical rule at a time — neither can see a pattern that only shows up *across* many commits: the same bug class fixed twice, a file touched repeatedly for related-but-never-consolidated reasons, a commit message that's stopped accurately describing its own diff. Read `git log` and the recent diffs together, not each one in isolation, and name the pattern, not just the instance — `.scratch/review-reports/commit-sweep-2026-07-13.md` is the reference example (finding F.1: the same concurrent-session propagation risk surfacing twice in different shapes, each time fixed only for the specific instance).

Run one when any of these hold:
- ~15-20 commits have landed since the last sweep (check the most recent `.scratch/review-reports/commit-sweep-*.md`'s own date/commit-range)
- A build phase's exit gate closes
- The user asks for one directly

Unlike the specs/ cross-model review, this doesn't need a different model — the failure mode here is zoom level (per-diff vs. aggregate), not same-family bias — so Claude runs this itself within a normal session rather than handing it to a different tool. Save the report to `.scratch/review-reports/commit-sweep-<date>.md`, matching the existing peer-review/cross-model-review report convention. If `schedule`/`loop` is ever configured for genuine unattended automation, this is a reasonable candidate — but running it as a documented in-session trigger, not a background cron job, matches this project's actual demo-stage scale (see the cross-model review's own R.15 finding on production-grade process for a solo project).

After committing a handoff doc, tag that commit `handoff/<slug>` (matching the doc's own topic, not necessarily its exact filename) — `git tag -l 'handoff/*'` then finds every handoff point directly, without digging through `git log` by date. Local tags only; pushing one is a separate, explicit decision like any other push.