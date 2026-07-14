---
name: test-audit
description: Periodically audit the existing test suite for false-confidence tests — ones that pass without actually verifying the behavior they claim to cover. Fix what's unambiguously fixable, flag what needs judgment, and report like a commit-sweep. Use when a build phase's exit gate is closing, when docs/testing.md's inventory has grown since the last audit, or when the user asks to audit test quality or find weak/false-confidence tests.
---

# Test Audit

`tdd` governs how a test is written; `code-review`/`review` checks a diff against standards. Neither looks at the **test suite as it accumulates** — a test can pass review at the moment it's written and still turn out, once reread cold, to pass regardless of whether the behavior it claims to cover is actually correct. This skill is that reread, at the same zoom-level shift `commit-sweep` makes for commits: across the whole suite, not one diff at a time.

## When to run

- Before a build phase's exit gate closes (same trigger as `commit-sweep` and the specs cross-model review)
- `docs/testing.md`'s inventory table has grown since the last audit (check the most recent `.scratch/review-reports/test-audit-*.md`'s own scope line for what was last covered)
- The user asks directly, or asks to find "false-confidence" or "weak" tests

## Process

### 1. Enumerate

Read every test file in `docs/testing.md`'s inventory table, plus anything under `tests/` that isn't in that table yet — a test missing from the inventory is itself a finding (the inventory's whole job is tracking what exists).

### 2. Run the suite first

Run the tests before reading them (`pytest -v`). Know which are actually passing/failing before judging whether a pass is trustworthy — a test can't be false-confidence if it's currently red, and a deliberately-red test (see `docs/testing.md`'s "what to avoid") is a different finding than a false-confidence one: check it's red for the documented reason, not weakened.

### 3. Check each test against the existing taxonomy

Don't invent a new taxonomy — apply the one this repo already has, split across two files:

- `.claude/skills/tdd/tests.md`: **tautological** (the expected value is recomputed the way the code computes it, so the test passes by construction) and **implementation-coupled** (mocks internal collaborators, tests private methods, verifies through a side channel instead of the public interface).
- `docs/testing.md`'s "What to avoid" section: a test passing only because of an accidentally-correct `sys.path`/invocation order, a deliberately-red test whose assertion got quietly weakened instead of left red, a check-style test never proven against the real incident it's supposed to catch.

Two more, general enough not to need their own reference doc:
- **Vacuous** — no assertion, or an assertion true independent of the code under test (`assert result is not None` where `result` can't be `None` by construction; a bare `assert True`).
- **Swallowed failure** — a `try`/`except` wraps the behavior under test in a way that would let the test pass even if the real call raised.

### 4. Fix directly, or flag — don't guess

**Fix directly** only when the correct assertion is unambiguous from the test's own context — e.g. a tautological test where an independent literal is trivially derivable from the fixture already in the test (`tdd/tests.md`'s own example: replace a recomputed `expected` with the literal it evaluates to).

**Flag instead of guessing** whenever the fix requires knowing what the test was *supposed* to verify — a vacuous assertion, a mock-heavy test whose seam needs redesigning, a swallowed-failure test where the right on-failure behavior isn't obvious from reading it. Inventing an assertion here risks the exact failure mode `docs/testing.md` already warns against for deliberately-red tests: a confident-looking fix that quietly papers over a real gap. For each flagged case, report file:line, name the anti-pattern, and propose what evidence would resolve it — leave the actual rewrite to a human or a follow-up session with the missing context.

### 5. Report

Save to `.scratch/review-reports/test-audit-<date>.md`, matching `commit-sweep`'s convention: scope (files audited, date, pass/fail counts from step 2), a findings table (file:line, anti-pattern, fixed/flagged), a one-line summary. If a file is clean, say so — don't pad the findings list. `commit-sweep-2026-07-13.md`'s "Nothing else flagged" section is the reference tone.
