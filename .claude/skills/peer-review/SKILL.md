---
name: peer-review
description: Get an independent second-opinion code review from a model outside the Claude family, to catch same-model self-evaluation bias that Claude's own /code-review can't see. Use after /code-review, at the end of /implement, or whenever the user asks for "another model's opinion", "cross-model review", "a second opinion from a different LLM", "peer review", or wants to sanity-check a diff before merging. Requires an API key for the configured peer-review model (PEER_REVIEW_API_KEY).
---

# Peer Review

Claude's own `/code-review` runs two Claude sub-agents with no shared history — that removes **path-dependency** bias (a reviewer inheriting the drafting conversation's blind spots), but both reviewers are still Claude, so they share whatever's specific to Claude's training. `peer-review` removes a different bias: it sends the diff to a model from a genuinely different vendor family, so a systematic mistake Claude tends to make — or tends to forgive in its own output — gets a real chance of being caught by something that doesn't share the blind spot.

This isn't a new idea for this project. `specs/13-decision-log.md` DEC-130 already mandates a judge model from a different vendor family than the generation model for RAG answer grading, naming same-model self-evaluation as the anti-pattern it exists to prevent. `peer-review` applies that same principle one layer up — to code review instead of RAG-answer grading.

Run `/code-review` and `peer-review` as two separate, complementary gates. Neither replaces the other — see the comparison table at the end.

This skill triggers the same way every other skill here does: the `/peer-review` command, or saying "peer review", "another model's opinion", "cross-model review" (etc. — see the description) in conversation.

## Step 1 — Pin the fixed point and scope the diff

Same as `/code-review`: whatever the user names (commit SHA, branch, tag, `main`, `HEAD~5`) is the fixed point — ask if they didn't specify one. Confirm it resolves (`git rev-parse <fixed-point>`) and capture the diff: `git diff <fixed-point>...HEAD`. A bad ref or an empty diff should fail here, before any API call gets spent on it.

## Step 2 — Gather spec context (optional but preferred)

The peer model can't judge "does this implement what was asked" without knowing what was asked. Use the same search `/code-review` step 2 uses: issue references in commit messages, a path the user passed, or a PRD/spec file under `docs/`, `specs/`, or `.scratch/` matching the branch or feature. If nothing is found, proceed without it — the Functionality dimension below explicitly skips itself when there's no context to check against; Security/Performance/Design checks don't need one.

## Step 3 — Confirm the peer-review model is reachable, then call it

Check that `PEER_REVIEW_API_KEY` is set. If it isn't, **stop here** — do not attempt the call, and do not fall back to reviewing the diff yourself and calling that "peer review." Report: *"`PEER_REVIEW_API_KEY` is not set — peer review cannot run. Verdict: BLOCK (peer review unavailable, not a code-quality finding)."*

This is a hard gate, not a soft warning, by explicit project decision: a peer review that couldn't run blocks exactly like one that found real problems, because "we didn't check" and "we checked and it's fine" must never look the same in a report someone might act on.

The review rubric lives in this file — see **Review dimensions** below — so there is exactly one place it can drift from what actually gets sent. Materialize it, the diff, and any Step 2 context to files, then run the helper under `scripts/` to get the model's structured verdict back as JSON.

The full diff goes in as-is — no redaction, no file exclusion. This is an explicit project decision: the diff is treated the same way it will be treated in version control, not sanitized before showing it to a reviewer.

The helper's exit code is the contract:
- **0** — `--out` contains `{"issues": [...], "summary": "..."}`. Go to Step 5.
- **1** — the call was attempted and failed (network error, timeout, non-200 response, or a response that wasn't valid JSON despite requesting JSON mode).
- **2** — `PEER_REVIEW_API_KEY` isn't set (same as Step 3 — the script re-checks so it's never called without the guard).

For exit codes 1 and 2: **stop, don't retry, don't fall back to self-review.** Report *"Verdict: BLOCK (peer review unavailable)"* and quote the script's stderr as the reason. Do not read partial output and try to salvage a review from it — a failed call produced no trustworthy signal, and presenting anything as if it did would misrepresent what actually happened. This mirrors the same discipline this repo's `verifiable-acceptance-criteria` skill uses for unreachable checks: an unobservable result is not the same as a passing one, and must never be reported as one.

## Review dimensions

You are an independent senior code reviewer. You are reviewing a diff you did not write and have no stake in defending — say so plainly if you find nothing wrong, and say so plainly if you find something serious.

Review the diff across four dimensions, in this order:

1. **Functionality** — does the diff implement what the provided spec/requirement context asked for? Missing requirements, wrong behavior, unmet edge cases. If no spec/context was provided, skip this dimension rather than guessing at intent.
2. **Security** — hardcoded secrets/API keys/passwords, injection (SQL, shell, path traversal) via user-controlled input, missing auth checks on protected routes, sensitive data logged in plaintext.
3. **Performance** — N+1 queries, unbounded queries on user-facing endpoints, an O(n^2) algorithm where O(n log n) or O(n) is achievable, synchronous I/O in an async code path.
4. **Design/Quality** — functions over ~50 lines, nesting over ~4 levels, missing error handling at a system boundary, new logic with no accompanying test, dead code, a bare `except:`/`catch` that swallows the specific error type.

Severity, assign consistently:
- **CRITICAL** — missing requirement, injection, hardcoded secret, auth bypass
- **HIGH** — wrong behavior (off-by-one, missed case), missing rate limiting or log redaction, an algorithmic inefficiency with a clearly better complexity available, missing error handling at a system boundary, missing test for new logic
- **MEDIUM** — N+1/unbounded query, sync I/O in an async path, an oversized private helper, deep nesting
- **LOW** — dead code, magic number, poor naming, a TODO with no tracked issue reference

Rules:
- Report only issues you are genuinely confident are real (roughly: you'd bet on it). When in doubt, omit rather than pad the list.
- Consolidate duplicates — "5 functions missing error handling" is one issue, not five.
- Skip stylistic preferences that aren't in the checklist above, and skip anything a linter/type-checker would already catch mechanically (that's not what an independent reviewer is for).
- If you genuinely find zero issues, return an empty `issues` array and say so in the summary — do not invent an issue to seem useful. A clean bill of health is a valid, useful finding.

Respond with **only** a JSON object — no prose before or after it, no markdown fence — matching exactly this shape:

```json
{
  "issues": [
    {
      "severity": "CRITICAL | HIGH | MEDIUM | LOW",
      "dimension": "Functionality | Security | Performance | Design/Quality",
      "file": "path/to/file.py:line",
      "title": "short title of the issue",
      "fix": "concrete, actionable suggested fix"
    }
  ],
  "summary": "one paragraph overall assessment"
}
```

## Step 5 — Render and save the report

On success, `--out` is structured JSON: a list of issues (`severity`, `dimension`, `file`, `title`, `fix`) and a `summary`. Assign sequential ids yourself when rendering (`P.1`, `P.2`, ...) — don't ask the model to number them.

Save the report under `.scratch/review-reports/`, named after what was reviewed:

- Reviewing a whole phase (all issues under one `.scratch/<phase-slug>/`) → `<phase-slug>-review.md`
- Reviewing a single issue → `<phase-slug>-<issue-slug>-review.md`

Example: `.scratch/review-reports/phase-1-bootstrap-review.md`, or `.scratch/review-reports/phase-1-bootstrap-project-scaffold-dependencies-review.md` for a single-issue review. Create `.scratch/review-reports/` if it doesn't exist yet.

```markdown
# Peer Review

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

<the model's summary paragraph>

Verdict: <APPROVE|WARN|BLOCK>
```

Verdict, from the severities the peer model actually reported (this is a *different* BLOCK than Step 3's — see below):
- `APPROVE` — no CRITICAL, no HIGH
- `WARN` — MEDIUM/LOW only
- `BLOCK` — any CRITICAL or HIGH

**Keep the two BLOCK reasons visibly distinct wherever you report them.** "BLOCK — peer review unavailable" (Step 3) and "BLOCK — the peer model found a CRITICAL issue" (Step 5) are both spelled `BLOCK`, but conflating them in what you tell the user hides the difference between "the code has a real problem" and "the review simply never happened."

## Relationship to /code-review

| | `/code-review` | `peer-review` |
|---|---|---|
| Reviewer | Two fresh Claude sub-agents | A model from a different vendor |
| Bias removed | Path-dependency (the drafting conversation's blind spots) | Model-family blind spots (Claude reviewing Claude) |
| Axes | Standards + Spec | Functionality + Security + Performance + Design/Quality |

Run both on a nontrivial diff before merging or closing an issue. Skip `peer-review` for trivial, low-risk changes (typo fixes, comment-only edits) where the API round-trip isn't worth spending — use judgment, same as `/code-review` does.
