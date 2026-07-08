# Proposed patch — `.claude/skills/implement/SKILL.md`

Not applied. Closes the execution-time half of the gap: even a well-gated issue can turn out to have an AC that only reveals itself as borrowed once the agent is actually in the codebase (e.g. discovers mid-task that Docker isn't actually reachable here, contrary to what the manifest said last month).

## Current full text

```markdown
Implement the work described by the user in the PRD or issues.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /review to review the work.

Commit your work to the current branch.
```

## Proposed text

```markdown
Implement the work described by the user in the PRD or issues.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Before checking off any acceptance criterion, confirm you can actually run its Verification line in this environment. If an AC turns out unreachable as written — infrastructure the manifest assumed isn't actually there, an artifact from a "later phase" note doesn't exist, the criterion is a human-timed claim that slipped through — stop. Do not silently skip it and do not mark it done on the strength of the surrounding work being correct. Report which AC, why it can't be verified as written, and ask the user whether to defer it, mark it `[manual-verify]`, or find an alternate proxy. See `/verifiable-acceptance-criteria` for the full classification.

Once done, use /review to review the work.

Commit your work to the current branch.
```
