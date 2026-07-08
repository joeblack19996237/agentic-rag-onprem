# Proposed patch — `.claude/skills/to-issues/SKILL.md`

Not applied. This is the highest-leverage integration point: it's where every AC found unverifiable in Part A actually got published. Apply after review.

## 1. Insert a new step between current Step 3 ("Draft vertical slices") and Step 4 ("Quiz the user")

```markdown
### 3.5 Gate acceptance criteria

Before presenting the breakdown to the user, run the `/verifiable-acceptance-criteria` skill against every draft `## Acceptance criteria` list. Rewrite anything it flags as borrowed-artifact, borrowed-environment, or human-subjective before the slices reach Step 4 — don't show the user ACs you already know can't be closed as written.

If a slice's task is TDD-Exempt in the source spec (`Verification Pattern: TDD-Exempt` in `specs/10-build-plan.md`), carry its `Verification Evidence`, `Owner Role`, and `Rollback Plan` fields into the issue — do not drop them for the sake of the bare checklist below.
```

## 2. Extend `<issue-template>`'s Acceptance Criteria section

Current:

```markdown
## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

Proposed:

```markdown
## Acceptance criteria

- [ ] Criterion 1
      Verification: <exact command> → <expected observable output>
- [ ] Criterion 2
      Verification: <exact command> → <expected observable output>

## Manual verification (if any)

- [ ] [manual-verify] <criterion that needs a human/DevOps action>
      Owner: <role>. Evidence to capture: <what to record>.

(Omit this section entirely if `/verifiable-acceptance-criteria` found nothing to split off.)
```

## 3. Triage-label rule

Current text: "these issues are considered ready for AFK agents, so publish them with the correct triage label unless instructed otherwise."

Add: If an issue's Acceptance Criteria section still contains any `[manual-verify]` item after the gate, do not publish it as `ready-for-agent` alone — either split it into two issues (an agent-scoped one and a `ready-for-human` one covering the manual items), or publish the whole issue as `ready-for-human` if the manual item blocks everything else in the slice. Never publish `ready-for-agent` over an unresolved `[manual-verify]` item.
