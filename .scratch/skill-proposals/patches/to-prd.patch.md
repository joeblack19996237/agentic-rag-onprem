# Proposed patch — `.claude/skills/to-prd/SKILL.md`

Not applied. Lower urgency than `to-issues` — `to-prd`'s current template has no checkbox Acceptance Criteria section, so the bug found in Part A can't originate here directly. This closes the gap before a future template change (or a `to-issues` run straight off a PRD's Testing Decisions) reopens it.

## Insert into the `<prd-template>`'s "Testing Decisions" guidance

Current:

```markdown
## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)
```

Proposed addition (same section, one more bullet):

```markdown
- Whether each testing decision is actually executable in the environment implementing this PRD will have — run `/verifiable-acceptance-criteria`'s classification (grounded / borrowed-artifact / borrowed-environment / human-subjective) over this list before publishing. A testing decision that assumes infrastructure this phase doesn't have yet (cloud deployment, a live CI provider, GPU hardware) belongs under "Out of Scope" or a follow-up PRD, not here.
```

## Also add one line to Step 3 (before "Write the PRD using the template")

```markdown
If any Testing Decision or User Story implies a future capability (e.g. "verify the deployed service handles production load") that this PRD's own scope doesn't build, move it to Out of Scope now — don't let `to-issues` inherit an assumption this PRD never actually delivered on.
```
