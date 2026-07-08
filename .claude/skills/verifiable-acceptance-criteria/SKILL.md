---
name: verifiable-acceptance-criteria
description: Gate acceptance criteria in a PRD, issue, or build-plan task against what the current phase actually delivers and what the current execution environment can actually reach. Use before publishing any issue or PRD that contains acceptance criteria, before checking off an acceptance criterion during implementation, or when another skill (to-issues, to-prd, implement, triage) needs to verify its own output before committing to it.
---

# Verifiable Acceptance Criteria

An acceptance criterion is **grounded** when the same agent that will close it can name one command to run, right now, in this repo, and get a pass/fail answer. An AC that isn't grounded is **borrowed** — it silently reaches for an artifact, an environment, or a human that the closing agent doesn't have.

This skill exists because borrowed ACs read exactly like grounded ones on the page. A checkbox doesn't announce which kind it is — that's what makes them dangerous: they get marked done by assumption, not by observation.

## Step 1 — Load ground truth

Read `docs/agents/dev-environment.md` if it exists — it lists what this repo's actual execution environment can reach (Docker, GPU, cloud CLIs, CI, reference docs). If it doesn't exist, proceed anyway using only what you can directly confirm in this session (a tool call that succeeds or fails is ground truth; a memory of "this usually works" is not) and say explicitly, in your output, which environment facts you couldn't confirm rather than assuming either way.

Also read whatever names the **current phase's own deliverables** (the build-plan task, PRD, or issue this AC lives in, plus anything it's `Blocked by`). An AC can only be grounded against what *this phase* — not a later one — actually produces.

## Step 2 — Classify every acceptance criterion

For each AC, decide which bucket it's in:

- **Grounded** — names or implies a concrete, runnable check; the target artifact exists (or is created earlier in the same task); every tool the check needs is confirmed reachable.
- **Borrowed-artifact** — references something that doesn't exist until a *later* phase (a real service definition when this phase only scaffolds a skeleton; a populated cache when this phase only wires the plumbing).
- **Borrowed-environment** — references infrastructure the closing agent cannot drive from its own tools: cloud provider consoles/pods, GPU-dependent runtimes, a CI provider's dashboard, anything requiring credentials the agent doesn't hold.
- **Human-subjective** — describes a person's future timed or felt experience ("a new contributor reaches X in ≤ N hours", "feels intuitive"). No executing agent can self-observe this, including the one that just built the feature — it already knows the steps, so it cannot honestly stand in for someone encountering them cold.

If you can't tell which bucket an AC is in, it isn't grounded — treat "unsure" as "borrowed" and rewrite it.

## Step 3 — Rewrite each non-grounded AC

- **Borrowed-artifact** → replace with the nearest check the *current* phase's real deliverable supports (a skeleton compose file can have its YAML syntax validated even though its services aren't real yet — don't claim more than that). If no honest proxy exists at this phase, delete the AC here and move it verbatim to the future issue/task that actually produces the artifact — don't leave it stranded on a task that can never close it.
- **Borrowed-environment** → split in two:
  1. An agent-checkable proxy covering everything actually within reach (static validation, dry-run, syntax/schema check, a local stand-in for the real service).
  2. A `[manual-verify]` item: explicit owner (human/DevOps), the real-world action required, and what evidence to capture. This item is **excluded** from the agent's own definition of done and from a `ready-for-agent` triage label — it belongs on a `ready-for-human` issue or a separate manual checklist.
- **Human-subjective** → remove from Acceptance Criteria entirely. If the underlying NFR still matters, move it to a "Success metric — requires a live human trial" note, explicitly out of scope for whoever closes this issue.

## Step 4 — Attach a Verification line to every surviving AC

Every grounded AC needs: the exact command (or tool call) to run, and the expected observable output or exit condition — not just "passes" but *what* passing looks like. If the AC came from a spec-derived task that already had `Verification Evidence` / `Owner Role` / `Rollback Plan` fields (see the TDD-Exempt template in `idea-to-specs`'s `spec-templates.md`), carry those fields forward verbatim — do not let a downstream template (e.g. a bare issue-tracker checklist) silently drop them.

## Step 5 — Independent re-check

Spawn a fresh sub-agent (`general-purpose`, no conversation history) with only the drafted ACs and, if available, `docs/agents/dev-environment.md`. Ask exactly one question per AC: *"What single command would you run right now, in this repo, to get a pass/fail answer for this criterion? If you can't name one, say so and why."* Treat any AC the fresh agent can't ground as failing this gate — a second pass with no path-dependency on the drafting conversation catches the rationalization the original context is prone to ("I know what I meant by this AC" is not available to a fresh reader, which is exactly the point).

## Step 6 — Completion criterion

This gate is done when every AC in the batch is either:
- Grounded, with a Verification line the fresh sub-agent (step 5) could independently execute in principle, or
- Explicitly split into an agent-checkable proxy plus a `[manual-verify]` item with an owner.

Do not publish the issue/PRD, and do not check off the AC during implementation, until this holds.

## During implementation, not just at drafting time

If you're the agent *executing* an issue (via `/implement` or otherwise) and discover mid-task that an AC you're about to check off is actually borrowed — the environment doesn't have what you assumed, the artifact isn't there yet — **stop**. Do not silently skip it, and do not fabricate a passing result. Report exactly which AC, why it can't be verified as written, and ask the user whether to defer it, mark it `[manual-verify]`, or find an alternate proxy. A borrowed AC discovered during implementation is a finding, not an obstacle to route around quietly.

## Worked examples (from this repo's Phase 1 issues)

| As drafted | Bucket | Rewrite |
|---|---|---|
| "`docker compose config` validates the compose file without error" | Borrowed-environment (if Docker isn't confirmed reachable) | Confirm Docker reachability first (`docker compose version`); if reachable, this AC is actually grounded as written — say so. If not confirmed, proxy to a YAML syntax check and add `[manual-verify]`: run `docker compose config` once Docker is available. |
| "Every pinned dependency is importable in a smoke-import script" | Borrowed-environment for GPU-only packages (e.g. vLLM without CUDA) | Split: grounded smoke-import for CPU-installable pins; `[manual-verify]` for GPU-only pins, owner DevOps/AI, evidence = import log from a GPU-capable host. |
| "RunPod template + Network Volume boots; model cache survives pod restart" | Borrowed-environment | Agent-checkable proxy: template/IaC file passes static validation; boot script runs without syntax error against a local stub. `[manual-verify]`: actual RunPod boot + restart cycle, owner DevOps, evidence = pod log + cache-hit confirmation. |
| "A new contributor following only the dev profile reaches a working eval run in ≤ 2 hours" | Human-subjective | Remove from Acceptance Criteria. Note under Success Metrics: "NFR-011 onboarding SLA — requires a live human trial, not agent-verifiable." |
| "CI pipeline is green on the scaffold commit" | CI-access — treat as borrowed-environment unless `docs/agents/dev-environment.md` confirms live CI query access | If confirmed: grounded, Verification = `gh run list --branch <branch> --limit 1`. If not confirmed: `[manual-verify]`, owner whoever has CI dashboard access. |
