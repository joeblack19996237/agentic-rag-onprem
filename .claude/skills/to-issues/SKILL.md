---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices.
disable-model-invocation: true
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The issue tracker and triage label vocabulary should have been provided to you — run `/setup-matt-pocock-skills` if not.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

Look for opportunities to prefactor the code to make the implementation easier. "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

<vertical-slice-rules>

- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Each slice is sized to fit in a single fresh context window
- Any prefactoring should be done first

</vertical-slice-rules>

**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer bullet; sequence it as **expand–contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own issue blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in an issue blocked by every migrate batch. When even the batches can't stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify issue — green is promised only there.

### 3.5 Risk-review the design

Before the groundedness gate below, run an adversarial pass over the draft — a different question than "can this be tested," which is what Step 3.6 checks. `verifiable-acceptance-criteria` only asks whether a stated AC is verifiable; it says nothing about whether the *design* is secure, protocol-correct, performant, internally consistent, or complete against real edge cases. Skipping straight to groundedness-gating produces issues that are rigorously testable and still wrong — a batch of issues that only went through Step 3.6 needed three separate rounds of manual review to catch a JWT `kid`-handling gap, a mismatched HTTP status/body shape, missing-index assumptions, and a testing-infrastructure inconsistency between two ACs on the same route, none of which a groundedness check was ever going to surface.

**The lens matters more than the freshness.** A sub-agent with no conversation history but the same generic "review this" prompt defaults to the same blind spots the drafting pass had — freshness of context is not the same as diversity of scrutiny. Assign each reviewer one specific, named lens, not a general "find problems" brief.

Pick the lenses that apply to what this batch of slices actually touches (skip lenses that don't apply — a doc-only issue needs none of these):

- **Security** — the draft touches auth, crypto, secrets, or a trust boundary with user input. Check algorithm/key-handling edge cases, timing side-channels, injection surfaces, and what happens on malformed/missing/ambiguous input, not just the happy path an existing whitelist/DEC already covers.
- **Protocol/contract semantics** — the draft implements or consumes an HTTP (or other wire) contract. Check status-code-to-body-shape correctness, which layer a check actually operates on (e.g. the outer request's `Content-Type` vs. one multipart part's own `content_type` — a vague AC can conflate these), URL/path construction, and whether the cited spec doc actually defines what the draft assumes it defines.
- **Data layer** — the draft issues real queries against a real schema. Check that indexes actually exist for the filter/sort combination used (read the migration, don't assume), sort-order and tie-break determinism, and which concurrency/isolation properties no in-memory fake can prove.
- **Test-architecture consistency** — multiple ACs in the same slice touch the same route/table via *different* test infrastructure (e.g. one AC mocks a `Session` and compiles a query, another uses a stateful in-memory fake). Check whether they're stated to be complementary (each proving something the other can't) or accidentally contradictory, and whether an "X is observable after Y" AC can actually be satisfied by the test mechanism its own Verification line names — a bare mock across two separate calls proves nothing about persistence.
- **Edge-case completeness** — the "What to build" prose describes only the happy path. Check empty/absent optional fields, conflicting field combinations, and what an unmapped/unknown enum value does (fail loud, or silently default) — an unhandled case here is a design gap, not a testability gap, and `verifiable-acceptance-criteria` won't catch it.

For whichever lenses apply, spawn one sub-agent per lens (parallel, independent, no shared context between them) with the concrete draft text and pointers to the real files it references — brief it to read the actual code/schema/spec it's reasoning about, not just the draft's own claims about them (same "reproduce, don't just reason about" discipline as `verifiable-acceptance-criteria`'s own Step 5). Verify anything a lens flags against real project state before accepting it — a plausible-sounding objection can still be wrong once checked against what the code/schema/library actually does; don't apply a fix without confirming the underlying claim first. Fix what holds up directly in the draft before Step 4 presents it to the user, the same way Step 3.6's groundedness fixes happen before presentation, not after.

### 3.6 Gate acceptance criteria

Before presenting the breakdown to the user, run the `/verifiable-acceptance-criteria` skill against every draft `## Acceptance criteria` list — including any AC added or changed by the risk review above. Rewrite anything it flags as borrowed-artifact, borrowed-environment, or human-subjective before the slices reach Step 4 — don't show the user ACs you already know can't be closed as written.

If a slice's task is TDD-Exempt in the source spec (`Verification Pattern: TDD-Exempt` in `specs/10-build-plan.md`), carry its `Verification Evidence`, `Owner Role`, and `Rollback Plan` fields into the issue — do not drop them for the sake of the bare checklist below.

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?

Iterate until the user approves the breakdown.

### 5. Publish the issues to the issue tracker

For each approved slice, publish a new issue to the issue tracker. Use the issue body template below. These issues are considered ready for AFK agents, so publish them with the correct triage label unless instructed otherwise.

Publish issues in dependency order (blockers first) so you can reference real issue identifiers in the "Blocked by" field.

If an issue's Acceptance Criteria section still contains any `[manual-verify]` item after the gate in Step 3.6, do not publish it as `ready-for-agent` alone — either split it into two issues (an agent-scoped one and a `ready-for-human` one covering the manual items), or publish the whole issue as `ready-for-human` if the manual item blocks everything else in the slice. Never publish `ready-for-agent` over an unresolved `[manual-verify]` item.

<issue-template>
## Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit this section).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it here and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Acceptance criteria

- [ ] Criterion 1
      Verification: <exact command> → <expected observable output>
- [ ] Criterion 2
      Verification: <exact command> → <expected observable output>

## Manual verification (if any)

- [ ] [manual-verify] <criterion that needs a human/DevOps action>
      Owner: <role>. Evidence to capture: <what to record>.

(Omit this section entirely if `/verifiable-acceptance-criteria` found nothing to split off.)

## Blocked by

- A reference to the blocking issue (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.

Work the frontier — any issue whose blockers are all done — one at a time with `/implement`, clearing context between issues.
