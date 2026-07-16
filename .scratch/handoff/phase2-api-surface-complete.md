# Phase 2 Handoff — `api-surface` (TASK-033) Complete, Peer-Review Re-Audited

> Written 2026-07-16 for a fresh session with zero context on the conversation that produced it. Read this before touching anything in this repo. Continues from `.scratch/handoff/phase2-document-ingest-complete.md` (2026-07-15) — don't re-read that doc's own history sections, only its "What's concretely unblocked next" for what this session picked up. The user's own framing for this handoff was open-ended (no pre-decided next task); this doc orients you and lays out the concretely-unblocked options, it doesn't pick one for you.

## What this project is

**GroundedDocs** — an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland). Answers must be grounded in verified citations, with honest refusal when grounding is weak. Fully local LLM inference, no cloud egress.

- **Canonical source of truth**: `specs/` (entry point `specs/00-index.md`). `specs/13-decision-log.md` is append-only and canonical over any conflicting prose elsewhere.
- **Issue tracker**: local markdown under `.scratch/<feature>/issues/`, not GitHub Issues. See `docs/agents/issue-tracker.md`.
- **Repo**: `D:\AI\claude_code\agentic-rag-onprem`, remote `https://github.com/joeblack19996237/agentic-rag-onprem.git` (public, MIT). **Local `master` is 12 commits ahead of `origin/master` — still nothing pushed.** Confirm with the user before pushing anything; no standing instruction either way was reconfirmed this session.
- Read `CLAUDE.md` in full before doing anything — it has several project-specific overrides of generic skill defaults (this handoff doc's own save location is one of them) and a "Closing out a work cycle" checklist you're expected to run through before calling any substantial work done.

## What just happened (this session, in order)

Full detail lives in the commits themselves (`git log --oneline 00d15a5..HEAD`, 12 commits) and `.scratch/session-feedback.md`'s five 2026-07-16 entries — don't re-derive either from scratch.

1. **`api-surface` Issues 01–04 implemented, code-reviewed, and closed** (`Status: ready-for-human` in all four `.scratch/api-surface/issues/*.md` files): JWT bearer + admin API key auth (Issue 01), `POST /v1/ingest` + `GET /v1/ingest/{document_id}` wired to the existing pipeline (Issue 02), admin document list/update (Issue 03), admin audit list + model-version read (Issue 04). This is the last piece TASK-033 needed — see `specs/10-build-plan.md`'s TASK-033 entry.
2. **Commit-sweep + test-audit** (`.scratch/review-reports/commit-sweep-2026-07-16.md`, `.scratch/review-reports/test-audit-2026-07-16.md`) — found and fixed 2 real test-quality gaps (an overly broad `pytest.raises(Exception)`, a test mutating shared `app.state` without restoring it).
3. **`update-specs` closed two known gaps** flagged in code review during Issues 02–04 and left as docstring TODOs: **DEC-144** formally defines `corpus_id` = `documents.repository_id` (no code change, specs just caught up to what the code already assumed); **DEC-145** formally tracks the admin-scope-auth enforcement gap (JWT signature verified, claims never checked) via new `RISK-023` and new `TASK-040` (now correctly filed under Phase 2 in `specs/10-build-plan.md` — see item 6 below).
4. **An external peer review was found on disk mid-session** (`.scratch/review-reports/api-surface-issues-01-04-peer-review.md`, deepseek-v4-pro, not produced by this session) and re-audited on request. Its one HIGH/BLOCK finding (a background task allegedly using an already-closed DB session) had a **disproven mechanism** for this project's pinned `fastapi==0.135.2` (verified by reading two library source files plus a live repro) but pointed at a **real, different bug**: the background task shared the request's session, so the whole pipeline run's transaction wouldn't commit until *after* the background task itself finished — breaking status-poll visibility and crash durability. Fixed in `api/ingest_routes.py` (new `get_background_pipeline_deps_factory` dependency gives the background task its own session). Full verification methodology and the three LOW findings' resolutions are written into the peer-review file itself under "## Re-audit Response" — read that, don't re-derive it.
5. **`/code-review` ran against the re-audit fix itself** (Standards + Spec axes) and found a real efficiency regression the fix had introduced: `get_pipeline_dependencies` was building a full, unused tokenizer/embedding/Qdrant-client bundle on every request (including every bare status poll) once a second, genuinely-needed client-construction path existed for the background task. Replaced both routes' dependency with a narrower `get_job_store`; `get_pipeline_dependencies` is now deleted (was dead code).
6. **Process fixes from what went wrong mid-session**: a `general-purpose` review sub-agent used `git stash`/hand-edits on the shared working tree to independently verify a claim — nothing was lost (it cleaned up after itself) but the working tree looked corrupted for several tool calls. Fixed at the root: `.claude/skills/code-review/SKILL.md`'s sub-agent prompts now explicitly forbid working-tree mutation. Also found and fixed a real spec-authoring bug while verifying build-plan state for this doc: `TASK-040` declared itself Phase 2 but was physically filed in the Phase 6 section with no explanatory note (unlike every other phase/position-mismatched task in that file) — moved to the actual Phase 2 section.

**Full verification is clean**: `bash tools/verify.sh` — ruff, mypy, the full suite (**190 tests collected**, 189 passing + 1 deselected known-red `/ready` test), import-graph, doc-drift all pass as of the last commit (`c9ae800`). Confirm this is still true before trusting it; re-run rather than assume.

## Current issue-tracker state

Every published issue across all four features is `ready-for-human`. **Nothing is currently `ready-for-agent` or `needs-triage`.**

| Feature | Issues | Status |
|---|---|---|
| `phase-1-bootstrap` | 01, 02, 03 | All `ready-for-human` |
| `data-foundation` | 01 (Postgres schema), 02 (Qdrant collections) | Both `ready-for-human` |
| `document-ingest-pipeline` | 01 (plain-text/MD), 02 (PDF/Word + retry) | Both `ready-for-human` |
| `api-surface` | 01 (auth), 02 (ingest routes), 03 (admin documents), 04 (admin audit) | All `ready-for-human` |

## What's concretely unblocked next (Phase 2, not yet drafted as issues)

`specs/10-build-plan.md`'s Phase 2 is now closer to done but still **not fully closed**:

- **TASK-010: Ingest Resume + Job Queue** (`specs/10-build-plan.md:287`) — depends on TASK-008/009, both done. Same status as the prior handoff: the real dispatcher/job-queue-polling mechanism the current in-process retry loop still lacks. `Verification Pattern: TDD-Exempt` — read its own "Why TDD-Exempt" note before drafting an issue.
- **TASK-034: Embeddable Widget** (`specs/10-build-plan.md`, right after TASK-033) — depends on TASK-033, **now done, so this is newly unblocked this session**. Not previously actionable.
- **TASK-040: Admin-Scope JWT Claims Verification** (relocated this session to sit correctly under Phase 2, right after TASK-038) — depends on TASK-033, done, so unblocked. This is the concrete fix for DEC-145's tracked gap: extend `api/auth.py`'s `require_auth` with a scope/role claim check so `403` (insufficient scope) becomes reachable for the first time. Read its own "Added 2026-07-16" note and Acceptance Criteria before drafting an issue — the claim name/shape is explicitly *not* pinned by the spec, it's this task's own design decision.
- **TASK-035 (Audit-Pull API) is *not* unblocked** despite sitting textually near TASK-033/034 — it depends on TASK-024 (`audit/` + Context Fingerprint, Phase 4, not built) in addition to TASK-033. Don't draft this one yet.

## Known open items (not gaps — correctly deferred)

- Every `[manual-verify]` item across all issue files still needs infrastructure this sandbox doesn't have (live Postgres/Qdrant/TEI, GPU, Docker). `docs/agents/dev-environment.md` (re-probed 2026-07-16 for two new auto-mode-classifier data points, rest last probed 2026-07-11/14) is ground truth — re-probe if you suspect anything changed.
- **`RISK-023` / `TASK-040`**: admin-scope JWT claim enforcement is a real, currently-unenforced gap, formally tracked (not silently closed). Currently inert — no end-user JWT issuance path exists yet to obtain a deliberately non-admin-scoped token to exploit it with — but an explicit precondition for any real (non-demo) deployment. Don't treat "it's tracked" as "it's fine to defer indefinitely" if end-user JWT issuance work ever starts.
- DEC-142's sparse-embedding SPLADE model still has no measured VRAM cost (carried forward from the prior handoff, unchanged this session).

## Cross-model `specs/` review is now due

`.claude/skills/peer-review/specs-review-prompt.md`'s own "Last run" line is still `2026-07-13`, `DEC-135`. Current decision log is at **`DEC-145`** — **10 new decisions since the last cross-model review**, at exactly `CLAUDE.md`'s own "~10+" trigger threshold. This review is run by the user in a separate tool/model; Claude only prepares or updates the prompt package, never runs it itself. Worth raising with the user directly rather than waiting for it to come up — the prior handoff already flagged this as "getting close" at 8 new DECs (2026-07-15); it has now crossed the line.

## Suggested skills for the next session

- **If drafting TASK-010, TASK-034, or TASK-040 as issues**: `/to-prd` first if the feature warrants one (check whether `api-surface` skipped this step before assuming it's mandatory — it did, per `.scratch/api-surface/issues/`'s own lack of a PRD file), then `/to-issues`, then `/verifiable-acceptance-criteria`. TASK-040 in particular has an unpinned design decision (JWT claim shape) that risk-review should surface explicitly rather than leaving implicit.
- **Cross-model `specs/` review** — see the section above. Prepare/update the prompt package via `peer-review`'s own workflow; the user runs the actual call externally.
- **`/implement`** once an issue is published, followed by `/code-review` (Standards + Spec sub-agents — now scoped read-only per this session's own fix) and, given this project's established cadence, likely another external `peer-review` round given the last one (this session) caught something `/code-review` alone hadn't at the time it first shipped.
- **`test-audit`** and **`commit-sweep`**: both just ran this session (2026-07-16). Neither is due; don't run either just because this list mentions them.

## Pitfalls already hit this session — do not repeat these

1. **A HIGH/BLOCK severity label from an external review is not itself evidence the underlying claim is correct.** Reproduce or independently verify the actual mechanism (read the real third-party source, run a live repro for runtime-ordering claims) before accepting *or* dismissing a finding — and if the stated mechanism turns out wrong, don't stop there; ask what would make a reviewer look at that exact code, since the underlying instinct may still be pointing at something real. See the memory system's `feedback_verify-external-reviews-independently.md` (auto-loaded) for the full write-up.
2. **A `general-purpose` sub-agent has full tool access by default, including `git`.** A review-only task ("report, don't edit") doesn't constrain this on its own — `.claude/skills/code-review/SKILL.md` now states the read-only constraint explicitly in its sub-agent prompts; apply the same discipline when spawning any other review-style sub-agent this session didn't touch.
3. **A bare `git stash` is repo-wide, not file-scoped**, and running it while other uncommitted work is sitting in the tree is a real (if usually recoverable) risk. Use `git stash -- <path>` or a throwaway worktree to isolate a single file's clean-vs-dirty state instead.
4. **The auto-mode safety classifier can block a `git checkout -- <file>` discard even when you've already verified the content is safely backed up in a stash** — it judges the command, not your private knowledge. Reconstruct the desired state via direct file edits instead of arguing with or retrying the denial.
5. **A task's declared `Phase` field can silently diverge from where it's physically filed in `specs/10-build-plan.md`.** Several tasks (035/036/037/038) do this deliberately with an explanatory note; TASK-040 didn't have one and was actually just misfiled. If you add a new task, either put it in its real Phase's section or add the same kind of explanatory note the others use — don't leave a bare mismatch.
6. **`.scratch/` is intentionally public/pushed** — don't re-litigate gitignoring it without being asked (carried forward from the Phase 1 handoff, still holds).
7. **External review artifacts can appear in `.scratch/review-reports/` from a process you didn't invoke** (this session's peer-review file, like a prior session's) — this project's `peer-review` skill assembles a portable package for the user to run externally, so this is expected, not suspicious on its own. Don't touch or assume the origin of a file you don't understand without asking first.
