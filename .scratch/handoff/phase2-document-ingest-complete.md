# Phase 2 Handoff — Data Foundation + Document Ingest Complete

> Written 2026-07-15 for a fresh session with zero context on the conversation that produced it. Read this before touching anything in this repo. The user's own framing for this handoff was open-ended ("what will the next session be used for") — there is no pre-decided next task; this doc orients you and lays out the concretely-unblocked options, it doesn't pick one for you.

## What this project is

**GroundedDocs** — an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland). Answers must be grounded in verified citations, with honest refusal when grounding is weak. Fully local LLM inference, no cloud egress.

- **Canonical source of truth**: `specs/` (entry point `specs/00-index.md`). `specs/13-decision-log.md` is append-only and canonical over any conflicting prose elsewhere.
- **Issue tracker**: local markdown under `.scratch/<feature>/issues/`, not GitHub Issues. See `docs/agents/issue-tracker.md`.
- **Repo**: `D:\AI\claude_code\agentic-rag-onprem`, remote `https://github.com/joeblack19996237/agentic-rag-onprem.git` (public, MIT). **Local `master` is 13 commits ahead of `origin/master` — nothing has been pushed this whole arc.** The user's standing instruction this session was "don't push for now" (暂时不push); confirm before pushing anything.
- Read `CLAUDE.md` in full before doing anything — it has several project-specific overrides of generic skill defaults (this handoff doc's own save location is one of them) and a "Closing out a work cycle" checklist you're expected to run through before calling any substantial work done.

## What just happened (this session, in order)

1. **`document-ingest-pipeline` Issue 01** (plain-text/Markdown ingest pipeline) and **Issue 02** (PDF/Word parsing + embedding-service retry resilience) — both fully implemented, tested, code-reviewed, and closed (`Status: ready-for-human` in their own files, only `[manual-verify]` items remain). Don't re-read the implementation history from chat; the issue files themselves have inline `**Done (date)**` evidence notes under every acceptance criterion.
2. Two real mid-implementation architecture gaps were found and resolved via `update-specs`, each minting a new `DEC-###`:
   - **DEC-142**: TEI cannot serve `bge-m3`'s sparse embedding output at all (only dense) — sparse now comes from a separate dedicated SPLADE model, also via TEI.
   - **DEC-143**: Unstructured.io's PDF module has a hard, unconditional `torch`/OCR dependency — PDF's primary parser is now `pdfminer.six` instead; PyMuPDF stays the rescue path; DOCX (`python-docx`) was unaffected.
   - Both are full `specs/` corrections, not just code patches — read `specs/13-decision-log.md`'s DEC-142/DEC-143 rows for the complete rationale and rejected alternatives, don't re-derive them.
3. **Test-audit** (`.scratch/review-reports/test-audit-2026-07-15.md`) — first full pass over Phase 2's test suite (94 functions that had never been cold-read before). Found and fixed 2 real false-confidence gaps, both confirmed via mutation testing.
4. **External cross-model peer review** (`.scratch/review-reports/document-ingest-pipeline-issue01-02-peer-review.md`, deepseek-v4-pro) — verdict **APPROVE**, 1 LOW finding (bounded, edge-case redundant-recomputation cost in the embedding retry path), documented rather than fixed (the real fix would break a clean Protocol boundary for a disproportionately small gain — see `ingest/embedding.py::HybridTEIEmbeddingClient`'s own docstring).
5. `CLAUDE.md` gained two standing-rule promotions and the auto-memory system gained one refinement, both from patterns that had genuinely recurred twice this session — see `CLAUDE.md`'s "Dependency version claims" and "Closing out a work cycle" step 3 for what changed and why.

**Full verification is clean**: `bash tools/verify.sh` — ruff, mypy, the full suite (108 passing, 1 intentionally-red Phase-1 `/ready` test), import-graph, doc-drift all pass. Confirm this is still true before trusting it; re-run rather than assume.

## Current issue-tracker state

Every published issue across all three features is `ready-for-human` (agent work done, only `[manual-verify]` items — mostly live-service round-trips this sandbox can't run — remain open). **Nothing is currently `ready-for-agent` or `needs-triage`.**

| Feature | Issues | Status |
|---|---|---|
| `phase-1-bootstrap` | 01, 02, 03 | All `ready-for-human` |
| `data-foundation` | 01 (Postgres schema), 02 (Qdrant collections) | Both `ready-for-human` |
| `document-ingest-pipeline` | 01 (plain-text/MD), 02 (PDF/Word + retry) | Both `ready-for-human` |

## What's concretely unblocked next (Phase 2, not yet drafted as issues)

`specs/10-build-plan.md`'s Phase 2 ("Core Domain and Data Foundation") is **not fully closed** — TASK-006 through TASK-009 are done, but two more Phase 2 tasks have all their dependencies satisfied and nothing else drafted against them yet:

- **TASK-010: Ingest Resume + Job Queue** (`specs/10-build-plan.md:287`) — depends on TASK-008/009, both done. This is the actual **dispatcher/job-queue-polling mechanism** (`SELECT ... FOR UPDATE SKIP LOCKED`, per DEC-038) that Issue 01/02's own code explicitly flagged as *not yet existing* — `ingest/pipeline.py::_embed_with_retry`'s docstring and `.scratch/document-ingest-pipeline/issues/02-*.md`'s "Design note on 'requeues'" both say outright that the current retry loop blocks the calling thread because no dispatcher exists, and that this should be revisited once TASK-010 lands. TASK-010 is `Verification Pattern: TDD-Exempt` (chaos-test procedure, not unit-testable red→green→refactor) — read its own "Why TDD-Exempt" note before drafting an issue for it, and check `docs/agents/dev-environment.md`'s verification-ceiling section for what's actually chaos-testable in this sandbox vs. `[manual-verify]`.
- **TASK-033: HTTP API Surface** (`specs/10-build-plan.md:313`) — depends on TASK-006/009, both done. This is what finally wires `POST /v1/ingest` to the pipeline built this session (currently only directly-callable, no HTTP route) plus the admin API surface. Also unblocks TASK-034 (widget) and TASK-035 (audit-pull API), which depend on it — neither of those is unblocked yet on its own.

Everything else in Phase 2 (TASK-034 through TASK-038) is still blocked on TASK-033 or later-phase tasks. Don't assume this list is exhaustive of all possible next work — it's just what's mechanically unblocked in the build plan right now; re-check `specs/10-build-plan.md` yourself rather than trusting this table if any dependency has since closed.

## Known open items (not gaps — correctly deferred)

Every `[manual-verify]` item across all 7 issue files needs infrastructure this sandbox doesn't have (live Postgres/Qdrant/TEI, a GPU, Docker, RunPod) — see each issue's own `Owner`/`Evidence to capture` fields, already written, don't re-derive them. `docs/agents/dev-environment.md` (last probed 2026-07-11, Docker/GPU/toolchain rows re-confirmed 2026-07-14) is the ground truth for what this exact environment can and can't reach — re-probe if you suspect it changed, don't trust the date blindly.

One specific unquantified gap worth carrying forward: DEC-142's sparse-embedding SPLADE model has no measured VRAM cost yet, sitting inside an already-thin ~1.7 GB warm-cache headroom (`specs/04-architecture.md` §4.2.2). Needs a real measurement before any production sizing conversation.

## Suggested skills for the next session

- **If drafting TASK-010 or TASK-033 as issues**: `/to-prd` first (matches the established pattern for `document-ingest-pipeline`'s own PRD — check whether `data-foundation` skipped this step or not before assuming it's mandatory), then `/to-issues`, then `/verifiable-acceptance-criteria` before publishing — every issue drafted this session needed at least one correction pass to keep its acceptance criteria actually checkable in this sandbox, and TASK-010 specifically (chaos-test verification pattern) is likely to raise the same class of problem again.
- **`/implement`** once an issue is published and picked up — follow it with `code-review` (Standards + Spec sub-agents) and, for the diff's overall correctness, consider `peer-review` again (external cross-model check) given it caught one real thing `code-review` didn't this session.
- **`update-specs`** if implementation surfaces another spec-vs-reality gap (dependency capability, not just version — this recurred twice this session, see `CLAUDE.md`'s "Dependency version claims" section for the now-standing rule) — verify empirically, present options, get a decision, then propagate through `specs/` properly rather than patching code in isolation.
- **Cross-model `specs/` review** (`.claude/skills/peer-review/specs-review-prompt.md`) is *not yet due* but getting close — 8 new `DEC-###` entries (136 through 143) since the last run at DEC-135 (2026-07-13), against a ~10+ trigger threshold. Worth reminding the user if a few more decisions land before the next natural checkpoint.
- **`test-audit`** and **`commit-sweep`**: both just ran (2026-07-15) or have a recent baseline (`commit-sweep-2026-07-13.md`, ~6 commits since — well under the ~15-20 threshold). Neither is due; don't run either just because this list mentions them.

## Pitfalls already hit this session — do not repeat these

1. **A package importing cleanly doesn't mean the specific capability you need works.** Both DEC-142 (TEI/bge-m3 sparse) and DEC-143 (Unstructured/PDF) were spec-level claims that held up right until code actually called the real API/import path. Verify the exact code path you're about to build against, not just that the package/version resolves — now a standing rule in `CLAUDE.md`'s "Dependency version claims" section.
2. **`git diff <ref>...HEAD` (three-dot) is empty when nothing's committed since `<ref>` and `HEAD` still equals it.** Use two-dot (`git diff <ref>`) against the working tree when reviewing uncommitted changes — three-dot compares committed merge-bases only.
3. **Never name a shared (non-fixture-providing) test helper file `conftest.py`.** pytest auto-imports it as a bare top-level module; an explicit dotted import of the same file elsewhere makes mypy see it under two different module identities (`Source file found twice`). Use any other plain filename.
4. **Self-check a diff against its own issue's prose before invoking `code-review`.** Recurred twice (an unused query + async-wording mismatch in Issue 01; a "requeues" vs. actual-blocking-retry gap in Issue 02) — `code-review` is a second gate, not a substitute for a first one. Now a standing checklist step in `CLAUDE.md`.
5. **A test's name can claim more than its body checks — this is exactly what a test-audit exists to catch, and it's cheap to prevent at authoring time.** Both test-audit findings this session were tests whose own comments admitted (or should have admitted) they weren't really testing what their name said. If you catch yourself writing that kind of comment, fix the test right then instead of noting it and moving on.
6. **`.scratch/` is intentionally public/pushed** — don't re-litigate gitignoring it without being asked (carried forward from the Phase 1 handoff, still holds).
7. **Two large peer-review artifacts appeared mid-session from outside this conversation** (a diff patch + prompt package, later replaced by a clean review-result file) — this project's `peer-review` skill assembles a portable package for the user to run externally; don't be surprised if similar artifacts appear in `.scratch/review-reports/` from a process you didn't invoke yourself, and don't touch files you don't understand the origin of without asking first.
