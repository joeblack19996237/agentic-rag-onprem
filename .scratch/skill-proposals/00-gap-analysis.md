# Gap Analysis — Acceptance-Criteria Verifiability in the Phase 1 Skill Loop

Status: DRAFT for review. Nothing under `.claude/skills/` was modified. All findings below were produced by reading `.claude/skills/**` and `.scratch/phase-1-bootstrap/issues/**` only.

## 1. Existing skill inventory

| Skill | Invocation | Purpose (one line) |
|---|---|---|
| `idea-to-specs` | model-invoked | Vendored (external git remote `joeblack19996237/idea-to-specs`), 9-agent pipeline that generates `specs/` from scratch. Not a target for local edits — see §4. |
| `update-specs` | model-invoked | Keeps `specs/` internally consistent after `idea-to-specs` has run once; ID minting, decision-log discipline, blast-radius greps. |
| `to-prd` | user-invoked | Synthesizes conversation context into a PRD (Problem/Solution/User Stories/Implementation Decisions/Testing Decisions/Out of Scope), publishes to issue tracker. |
| `to-issues` | user-invoked | Slices a plan/PRD into tracer-bullet issues with an `## Acceptance criteria` checkbox list, publishes with a triage label. |
| `implement` | user-invoked | Executes a PRD/issue: TDD where possible, typecheck, test, `/review`, commit. |
| `tdd` | model-invoked | Red→green→refactor discipline; behavior-based tests over public interfaces; anti-horizontal-slicing. |
| `review` | model-invoked | Two parallel no-shared-context sub-agents review a diff: Standards axis + Spec axis. |
| `triage` | user-invoked | State machine for issues/PRs (`needs-triage`→`ready-for-agent`/`ready-for-human`/etc.), includes a "verify the claim" step for bugs/PRs. |
| `diagnosing-bugs` | model-invoked | Feedback-loop discipline for hard bugs; explicit "stop and ask" fallback when no tight loop can be built. |
| `codebase-design` | model-invoked | Deep-module vocabulary (module/interface/depth/seam/adapter); testability heuristics. |
| `domain-modeling` | model-invoked | Maintains `CONTEXT.md`/ADRs as the living glossary; sharpens vague terms; offers ADRs sparingly. |
| `improve-codebase-architecture` | user-invoked | Scans for shallow modules, visual HTML report, grilling loop into a redesign. |
| `setup-matt-pocock-skills` | user-invoked | One-time per-repo scaffolding: issue tracker location, triage label vocabulary, domain-doc layout → `docs/agents/*.md`. |
| `writing-great-skills` | user-invoked | Meta-reference for how to write skills (context load, completion criteria, leading words, pruning). |
| `handoff` | user-invoked | Compacts a conversation into a handoff doc for a fresh agent/session. |
| `grilling` / `grill-me` / `grill-with-docs` | mixed | Interview loops that stress-test a plan before building. |
| `ask-matt`, `teach`, `loop-me`, `prototype`, `ubiquitous-language`, `obsidian-vault`, `resolving-merge-conflicts`, `setup-pre-commit` | mixed | Not relevant to this audit's scope (unrelated to issue/PRD generation or verification). |

**Not read in full** (out of the audit's critical path, confirmed by name/description only): `grill-me`, `grill-with-docs`, `teach/*`, `prototype/*`, `ubiquitous-language`, `obsidian-vault`, `resolving-merge-conflicts`, `setup-pre-commit`, `loop-me`, `ask-matt`. None of these touch issue/PRD/AC generation.

## 2. Phase 1 issues audit — every unverifiable/inapplicable AC found

Read in full: `01-project-scaffold-dependencies.md`, `02-dev-rig-ci-baseline.md`, `03-first-failing-smoke-test.md`. Every checkbox AC was classified. Four failure categories emerged — the user's two examples are instances of the first two; the audit surfaced two more categories that recur across all three issues.

| # | File : line | Acceptance criterion | Category | Why it fails |
|---|---|---|---|---|
| 1 | `01-project-scaffold-dependencies.md:19` | `docker compose config` validates the compose file without error | **Borrowed-environment** | Assumes `docker`/`docker compose` is installed and runnable in *whatever environment the implementing agent actually has*. Nothing in the issue, the skill chain, or a repo doc confirms that. On a Windows host without WSL2/Docker Desktop enabled, this AC is unreachable regardless of how correct the compose file is. |
| 2 | `01-project-scaffold-dependencies.md:21` | Dependency install (e.g. `pip install`) succeeds with zero conflicts | **Borrowed-environment** | The pinned set includes vLLM, which is Linux/CUDA-oriented. "Succeeds with zero conflicts" is only checkable on a host that can actually resolve/build that wheel — not guaranteed for the agent's runtime. |
| 3 | `01-project-scaffold-dependencies.md:22` | Every pinned dependency is importable in a smoke-import script | **Borrowed-environment** | Same root cause as #2 — `import vllm` typically requires a CUDA-capable runtime; a plain CPU dev sandbox cannot produce a real pass/fail here, only an artificial one. |
| 4 | `02-dev-rig-ci-baseline.md:19` | RunPod template + Network Volume boots; model cache survives pod restart | **Borrowed-environment** (the user's own example) | Requires a live RunPod account, a real pod boot/restart cycle, and persistent-volume behavior — none of which an in-repo coding agent can drive from a local shell. |
| 5 | `02-dev-rig-ci-baseline.md:20` | A new contributor following only the dev profile reaches a working eval run in ≤ 2 hours | **Human-subjective / time-boxed** | This is `NFR-011`'s onboarding SLA, measured by a *real, fresh human*, on a *wall clock*. It is not a system behavior any executing agent — including the one that just wrote the docs — can self-observe. The agent already knows the steps; it cannot honestly simulate "a new contributor's" first encounter or a 2-hour timer. |
| 6 | `02-dev-rig-ci-baseline.md:21` | CI pipeline is green on the scaffold commit | **CI-access-uncertain** | Verifiable *only if* the repo has a real, connected CI provider the agent can query (`gh run list` et al.) at the moment this AC is checked. Nothing establishes that this repo's CI is wired up and observable from the agent's tool access — and this very issue is the one that's supposed to stand CI up in the first place. |
| 7 | `02-dev-rig-ci-baseline.md:22` | Import-graph check step exists and runs in CI | **CI-access-uncertain** (partial) | "Exists" is locally verifiable (file present, runs locally). "Runs in CI" needs the same live-CI observation as #6. The AC conflates a local-checkable half with a not-locally-checkable half without separating them. |
| 8 | `03-first-failing-smoke-test.md:24` | `docker compose up` reaches a container-healthy state for every service (even if not yet wired together) | **Borrowed-environment / borrowed-artifact** | Same Docker-availability problem as #1, compounded: some of these service images (vLLM) cannot reach "healthy" without a GPU and cached model weights that don't exist until a later phase. The AC describes an end-state several phases ahead of what Phase 1 actually delivers. |
| 9 | `03-first-failing-smoke-test.md:25` | CI runs and fails the deliberately-failing smoke test | **CI-access-uncertain** | Same as #6/#7. |
| 10 | `03-first-failing-smoke-test.md:26` | A new contributor following only the `NFR-011` dev profile reaches this state in ≤ 2 hours | **Human-subjective / time-boxed** | Same as #5 — repeated verbatim as a Phase 1 exit-gate criterion, meaning the exit gate itself cannot be closed by any agent alone. |

**Pattern**: every non-grounded AC in this batch is either (a) borrowing an artifact or environment that belongs to a later phase or a different execution context, or (b) asking the agent to attest to a human's future timed experience. Neither failure mode is exotic to this project — it will recur every time a build-plan task references infrastructure (cloud, CI, GPU) or an NFR phrased as a human-timed onboarding target.

**Root cause, traced upstream**: `specs/10-build-plan.md` tasks are generated by the vendored `idea-to-specs` pipeline using the template in `.claude/skills/idea-to-specs/references/spec-templates.md`. That template's TDD-Exempt task shape *already* carries `Verification Evidence` (command + expected output), `Owner Role` (Frontend/Backend/AI/**DevOps**/QA), and — for infra tasks — a `Rollback Plan`. None of that survives into `to-issues`' output: its `<issue-template>` (`.claude/skills/to-issues/SKILL.md:59-82`) has only a bare `## Acceptance criteria` checklist. The information needed to tell "this needs a human/DevOps action against real infrastructure" from "this is a local, agent-checkable command" exists one layer up and is silently dropped in translation. This is the load-bearing finding for Part B.

## 3. Principle-by-principle coverage

| # | Principle | Coverage today | Gap |
|---|---|---|---|
| 1 | Claude self-judges completion / asks for more context when needed | **Strong** in `diagnosing-bugs` (explicit "stop and say so" completion criterion) and `triage` ("verify the claim" step). **Absent** in `implement` and `to-issues`/`to-prd` — `implement.md` has no instruction for what to do when an AC turns out unreachable mid-task; it can only "run typecheck/tests" and move on. |
| 2 | Codebase stays clean; Claude mimics existing patterns | **Strong** — `tdd`, `codebase-design`, `improve-codebase-architecture` all reinforce this directly. |
| 3 | Team-approved "excellent code" standards written down so Claude can self-check | **Partial** — `tdd`'s checklist and `codebase-design`'s deletion test cover *code* quality. Nothing equivalent exists for *acceptance-criteria* quality — no written standard says "an AC must name a command and an expected observable output," even though the project's own `spec-templates.md`/`quality-gates.md` (Gate 4, Gate 7) already assert this at the TASK level. The standard exists upstream and isn't propagated. |
| 4 | Official framework/codebase docs reachable to the agent | **Not covered anywhere** in the read skill set. Nothing tells `implement`/`tdd` to pull current docs for fast-moving libraries in this stack (LangGraph 0.2.x, vLLM, TEI) rather than rely on training-data recall, which is a real risk for exactly the kind of dependency-pinning task in Issue 01. |
| 5 | A second, no-history agent reviews to reduce bias/path-dependency | **Strong for code** (`review`'s parallel Standards/Spec sub-agents). **Absent for issue/PRD drafting** — `to-issues` and `to-prd` publish straight from the same context window that drafted them; nothing re-checks the draft with a fresh agent before it goes to the tracker. This is exactly the class of miss the user caught by hand. |
| 6 (proposed) | Verification claims must be checked against what the *current phase* delivers and what the *current execution environment* can actually reach — not the system's idealized end state | **Not covered.** This is not invented from nothing: it is the enforcement of a discipline `quality-gates.md` Gate 4 ("testable acceptance criteria") and Gate 7 ("verification evidence required... TDD-exempt tasks lack a rollback plan or evidence-bearing acceptance criteria" is a fail condition) already declare as mandatory at the spec layer. `to-issues` is the point where that discipline is lost. |

## 4. Scope note on `idea-to-specs`

`.claude/skills/idea-to-specs/.git` points at `https://github.com/joeblack19996237/idea-to-specs.git` — this is a vendored, separately-versioned skill package (has its own README/LICENSE/git history), not a project-local skill. Editing it directly would fork it silently. The fixes below therefore target `to-issues`, `to-prd`, and `implement` (all project-local, editable in place) and the two new skills, rather than proposing changes inside `idea-to-specs`. If the same gap should be fixed upstream too, that's a separate decision for wherever `idea-to-specs` is maintained.

## 5. Gaps → proposed fixes (Part B)

| Gap | Proposed fix |
|---|---|
| No standard for what makes an AC verifiable, no current-phase/current-environment check | New skill `verifiable-acceptance-criteria` (hard constraint gate) |
| No ground truth for what the execution environment can actually reach (Docker? GPU? CI? cloud creds?) | New skill `dev-environment-capabilities` → `docs/agents/dev-environment.md` |
| `to-issues` template drops Verification Evidence / Owner Role / Rollback Plan from the source TASK | Patch: `patches/to-issues.patch.md` |
| `to-prd`'s Testing Decisions section has no phase/environment grounding check | Patch: `patches/to-prd.patch.md` |
| `implement` has no "stop and ask" behavior when an AC proves unreachable mid-task | Patch: `patches/implement.patch.md` |
| No second no-history agent audits drafted issues before publish | Folded into `verifiable-acceptance-criteria`'s own process (step 5) rather than a separate skill — avoids duplicating the `review` skill's sub-agent mechanism for a different moment (pre-publish, not post-diff). |
| No official-docs-reachable habit for fast-moving libraries | Folded into `dev-environment-capabilities`'s manifest (a "Reference docs" section) rather than a standalone skill — keeps one file as the single source of truth for "what this environment can reach," docs included. |
| `setup-matt-pocock-skills` has no environment-capability step alongside issue-tracker/triage-labels/domain-docs | Optional patch: `patches/setup-matt-pocock-skills.patch.md` (Section D) |

## 6. Priority recommendation

Land `verifiable-acceptance-criteria` first, and land it together with the minimal `to-issues` patch — not the full `dev-environment-capabilities` manifest.

Why: the manifest skill is the "right" long-term ground truth, but it's the higher-effort piece (probing tooling, cloud creds, CI access) and the current damage is happening at a narrower point: `to-issues` is publishing checkbox ACs with no Verification line and no distinction between agent-checkable and human/DevOps-only work. The gate skill can run in a degraded-but-useful mode with no manifest at all — steps 2–4 (classify → rewrite → require a Verification line) already catch every issue found in §2 just by reasoning about the *current phase's own deliverables* and asking "what command would I actually run right now." The manifest sharpens category (b) borrowed-environment calls (is Docker *really* absent here, or just unconfirmed?) but isn't required to stop the bleeding.

Suggested landing order:
1. `verifiable-acceptance-criteria` skill (draft in this folder)
2. `patches/to-issues.patch.md` (the actual publishing surface — highest leverage, single integration point)
3. `patches/implement.patch.md` (closes the loop so an ungrounded AC can't be silently checked off during execution either)
4. `dev-environment-capabilities` skill + `patches/setup-matt-pocock-skills.patch.md` (once the gate skill is in daily use and its "unconfirmed environment" guesses start costing real time)
5. `patches/to-prd.patch.md` (lowest urgency — `to-prd`'s template doesn't emit checkbox ACs today, so the immediate bug can't originate there; still worth closing so a future template change doesn't reopen it)
