# Optional patch — `.claude/skills/setup-matt-pocock-skills/SKILL.md`

Not applied, and lower priority than the other three patches (see `00-gap-analysis.md` §6). Folds `dev-environment-capabilities` into the existing one-time setup flow instead of leaving it as a separate thing to remember to run.

## Add "Section D — Dev environment capabilities" after Section C ("Domain docs")

```markdown
**Section D — Dev environment capabilities.**

> Explainer: `to-issues`, `to-prd`, and `implement` need to know what this environment can actually reach before writing or closing an acceptance criterion that touches infrastructure — Docker, GPU, cloud CLIs, CI. Without this, they either guess (and get it wrong, silently) or you get build-plan-derived acceptance criteria that reference infrastructure nobody can check off. Run `/dev-environment-capabilities` to probe and record this once.

Run the `/dev-environment-capabilities` skill. It writes `docs/agents/dev-environment.md`; nothing further to confirm here beyond what that skill's own process already asks.
```

## Add to the Step 4 "Write" block's `## Agent skills` template

Current:

```markdown
### Domain docs

[one-line summary of layout — "single-context" or "multi-context"]. See `docs/agents/domain.md`.
```

Proposed addition immediately after:

```markdown
### Dev environment capabilities

[one-line summary — what's confirmed reachable, what isn't, last-probed date]. See `docs/agents/dev-environment.md`.
```

## Add to Step 5 ("Done")

Mention that `docs/agents/dev-environment.md` should be re-probed when a new phase introduces infrastructure the file doesn't cover yet — same "re-run only if switching / restarting" framing already used for the other three sections.
