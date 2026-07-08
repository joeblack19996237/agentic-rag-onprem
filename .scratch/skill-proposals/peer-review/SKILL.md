---
name: peer-review
description: Get an independent second-opinion code review from DeepSeek — a different model vendor from Claude — to catch same-model self-evaluation bias that Claude's own /review can't see. Use after /review, at the end of /implement, or whenever the user asks for "another model's opinion", "cross-model review", "a second opinion from a different LLM", "peer review", or wants to sanity-check a diff before merging. Requires DEEPSEEK_API_KEY.
---

# Peer Review

Claude's own `/review` runs two Claude sub-agents with no shared history — that removes **path-dependency** bias (a reviewer inheriting the drafting conversation's blind spots), but both reviewers are still Claude, so they share whatever's specific to Claude's training. `peer-review` removes a different bias: it sends the diff to DeepSeek, a genuinely different model vendor, so a systematic mistake Claude tends to make — or tends to forgive in its own output — gets a real chance of being caught by something that doesn't share the blind spot.

This isn't a new idea for this project. `specs/13-decision-log.md` DEC-130 already mandates a judge model from a different vendor family than the generation model for RAG answer grading, naming same-model self-evaluation as the anti-pattern it exists to prevent. `peer-review` applies that same principle one layer up — to code review instead of RAG-answer grading.

Run `/review` and `peer-review` as two separate, complementary gates. Neither replaces the other — see the comparison table at the end.

> **Not yet installed as a live skill.** This draft lives under `.scratch/skill-proposals/peer-review/` rather than `.claude/skills/peer-review/` because writing it directly into the live skill directory was blocked by this environment's auto-mode data-exfiltration classifier — sending an unredacted repo diff to an external, unlisted third-party API (DeepSeek) triggers a hard block regardless of user authorization. See "Before installing" at the end of this file for what needs to happen first.

## Step 1 — Pin the fixed point and scope the diff

Same as `/review`: whatever the user names (commit SHA, branch, tag, `main`, `HEAD~5`) is the fixed point — ask if they didn't specify one. Confirm it resolves (`git rev-parse <fixed-point>`) and capture the diff: `git diff <fixed-point>...HEAD`. A bad ref or an empty diff should fail here, before any API call gets spent on it.

## Step 2 — Gather spec context (optional but preferred)

DeepSeek can't judge "does this implement what was asked" without knowing what was asked. Use the same search `/review` step 2 uses: issue references in commit messages, a path the user passed, or a PRD/spec file under `docs/`, `specs/`, or `.scratch/` matching the branch or feature. If nothing is found, proceed without it — the rubric's Functionality dimension explicitly skips itself when there's no context to check against; Security/Performance/Design checks don't need one.

## Step 3 — Confirm DeepSeek is reachable before spending anything

Check that `DEEPSEEK_API_KEY` is set. If it isn't, **stop here** — do not attempt the call, and do not fall back to reviewing the diff yourself and calling that "peer review." Report: *"`DEEPSEEK_API_KEY` is not set — peer review cannot run. Verdict: BLOCK (peer review unavailable, not a code-quality finding)."*

This is a hard gate, not a soft warning, by explicit project decision: a peer review that couldn't run blocks exactly like one that found real problems, because "we didn't check" and "we checked and it's fine" must never look the same in a report someone might act on.

## Step 4 — Call DeepSeek

```bash
python .claude/skills/peer-review/scripts/call_deepseek_review.py \
  --diff-file <path to the captured diff, saved as a text file> \
  --rubric-file .claude/skills/peer-review/assets/deepseek-rubric.md \
  --context-file <path to the spec excerpt from Step 2, if found> \
  --out <workspace path>/deepseek-review.json
```

The full diff goes in as-is — no redaction, no file exclusion. This is an explicit project decision: the diff is treated the same way it will be treated in version control, not sanitized before showing it to a reviewer. (This is also exactly the design point the exfiltration classifier objects to — see "Before installing.")

The script's exit code is the contract:
- **0** — `--out` contains `{"issues": [...], "summary": "..."}`. Go to Step 5.
- **1** — the call was attempted and failed (network error, timeout, non-200 response, or a response that wasn't valid JSON despite requesting JSON mode).
- **2** — `DEEPSEEK_API_KEY` isn't set (same as Step 3 — the script re-checks so it's never called without the guard).

For exit codes 1 and 2: **stop, don't retry, don't fall back to self-review.** Report *"Verdict: BLOCK (peer review unavailable)"* and quote the script's stderr as the reason. Do not read partial output and try to salvage a review from it — a failed call produced no trustworthy signal, and presenting anything as if it did would misrepresent what actually happened. This mirrors the same discipline this repo's `verifiable-acceptance-criteria` skill uses for unreachable checks: an unobservable result is not the same as a passing one, and must never be reported as one.

## Step 5 — Render the report

On success, `--out` is structured JSON: a list of issues (`severity`, `dimension`, `file`, `title`, `fix`) and a `summary`. Assign sequential ids yourself when rendering (`P.1`, `P.2`, ...) — don't ask DeepSeek to number them. Write `peer_review_report.md`:

```markdown
# Peer Review (DeepSeek)

## P.1 [HIGH] — Security
File: src/api/posts.py:23
Issue: <title>
Fix: <fix>

## Summary
| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH     | 1 |
| MEDIUM   | 0 |
| LOW      | 0 |

<DeepSeek's summary paragraph>

Verdict: <APPROVE|WARN|BLOCK>
```

Verdict, from the severities DeepSeek actually reported (this is a *different* BLOCK than Step 3/4's — see below):
- `APPROVE` — no CRITICAL, no HIGH
- `WARN` — MEDIUM/LOW only
- `BLOCK` — any CRITICAL or HIGH

**Keep the two BLOCK reasons visibly distinct wherever you report them.** "BLOCK — peer review unavailable" (Step 3/4) and "BLOCK — DeepSeek found a CRITICAL issue" (Step 5) are both spelled `BLOCK`, but conflating them in what you tell the user hides the difference between "the code has a real problem" and "the review simply never happened."

## Relationship to /review

| | `/review` | `peer-review` |
|---|---|---|
| Reviewer | Two fresh Claude sub-agents | DeepSeek — a different vendor |
| Bias removed | Path-dependency (the drafting conversation's blind spots) | Model-family blind spots (Claude reviewing Claude) |
| Axes | Standards + Spec | Functionality + Security + Performance + Design/Quality |

Run both on a nontrivial diff before merging or closing an issue. Skip `peer-review` for trivial, low-risk changes (typo fixes, comment-only edits) where the API round-trip isn't worth spending — use judgment, same as `/review` does.

## Before installing

Moving this from `.scratch/skill-proposals/peer-review/` to `.claude/skills/peer-review/` re-triggers the same classifier that blocked the direct write, since the content and intent don't change by moving the file. Before installing for real, resolve one of:

1. **Explicit Bash permission rule.** The classifier's own denial message says a user can add a Bash permission rule in settings to allow this class of action. Requires you to deliberately opt in — not something to default to silently.
2. **Different backend.** Point the script at a model/gateway already inside this environment's allowed connectors instead of DeepSeek's public API directly, if one exists that the classifier doesn't flag.
3. **Reduce what leaves the repo.** Send a redacted or summarized diff instead of the full one — this was explicitly rejected as a design choice earlier in this project's discussion (the user chose full, unredacted diffs), so revisiting it means reopening that decision, not just a technical tweak.

The two files that already exist under `.claude/skills/peer-review/` (`scripts/call_deepseek_review.py`, `assets/deepseek-rubric.md`) were not blocked — only this orchestrating `SKILL.md` was. They can stay where they are; this file is the piece still pending a decision.
