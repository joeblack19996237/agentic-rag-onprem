# Specs Cross-Model Review Prompt

> Portable prompt for reviewing `specs/` with a non-Claude model in a different tool (Cursor, Codex, Gemini, etc.) — this repo's own agents are all Claude-family, and `specs/`'s entire Stage 0-8 authoring and 9-gate self-audit (`specs/14-spec-audit-report.md`) has only ever been reviewed by Claude. Not a Claude Code skill — copy this file's "What to check" section into the other tool yourself; nothing here calls out to a script.
>
> **Last run: 2026-07-16**, at `specs/13-decision-log.md` DEC-145 (145 decisions total at review time). Reviewer: DeepSeek (deepseek-v4-pro), per `.scratch/review-reports/specs-cross-model-review-2026-07-16.md` (18 findings: 3 CRITICAL, 5 HIGH, 7 MEDIUM, 3 LOW; verdict BLOCK). Prior run: 2026-07-13 (30 findings: 6C/9H/10M/5L). Findings triaged and fixed in-repo the same day, adding DEC-136 and others — see that report's per-finding "Status" notes for what was fixed vs. reclassified vs. declined. Update this line (date + DEC count at the time) every time a review actually runs, the same way `docs/agents/dev-environment.md` tracks its own `Last probed` date — this file's staleness is exactly what `CLAUDE.md`'s trigger conditions check against.

## Why this exists

`specs/13-decision-log.md` DEC-130 established that a RAG answer's judge model must come from a different vendor family than the generation model, naming same-model self-evaluation as the anti-pattern it exists to prevent. `peer-review/SKILL.md` (this skill's sibling file) applies that same principle to *code* diffs. This prompt applies it one layer further up: to the spec set itself, which has never had it — every one of the internal "Round 1-6" reviews and all 9 audit Gates in `specs/14-spec-audit-report.md` were run by the same model family that wrote the content being checked.

## How to use this prompt

1. Open a different-vendor model or IDE (not Claude — Cursor/Codex/Gemini/etc. all satisfy this).
2. Give it access to `specs/` — either let it read the directory directly if the tool supports that, or paste files in one **review group at a time**, in the order `specs/00-index.md`'s own "Review groups" table defines (Group A → B → ...). Don't skip straight to a group you already suspect has problems — the point of an independent reviewer is to *not* be steered by what the internal audit already flagged.
3. Paste the "What to check" section below as the instruction, along with the group's files.
4. Save whatever comes back **verbatim**, including hedges/uncertainty the model expresses — don't clean it up before it's on disk. Follow the report format below, and save it as `.scratch/review-reports/specs-cross-model-review-<date>.md` (see `.scratch/review-reports/phase-1-bootstrap-review.md` for the sibling convention this mirrors).
5. Bring the file back into this repo and commit it. Update this prompt file's "Last run" line above. If the review surfaces a CRITICAL/HIGH finding that needs a real spec change, route it through the `update-specs` skill rather than hand-editing `specs/` — new DEC entries, decision-log supersedes, and `00-index.md`/`14-spec-audit-report.md` propagation all need to happen together, per this repo's own `CLAUDE.md` rule.

## What to check

Paste this to the other model, verbatim, along with the spec files:

> You are an independent senior reviewer. You did not write this spec set and have no stake in defending it — say so plainly if you find nothing wrong, and say so plainly if you find something serious.
>
> This project (GroundedDocs) has already run 9 internal "Gate" self-audits (see `specs/14-spec-audit-report.md`) — all conducted by the same model family (Claude) that authored the specs. Your job is not to re-trust those verdicts; it's to independently re-verify a sample of them, and specifically hunt for the class of error a same-family, same-context reviewer is structurally prone to miss: something that looks internally consistent because the same reasoning that wrote it also checked it, not because it's actually correct.
>
> Review across these dimensions:
>
> 1. **Cross-reference integrity** — spot-check at least 5 `REQ`/`NFR` chains end-to-end (requirement → architecture section → build-plan task → test → verification gate). Don't just confirm the ids exist — confirm the content at each link actually satisfies the claim the previous link makes.
> 2. **Unverified or stale technical claims** — any library version, API behavior, or "current best practice" assertion that reads like training-data recall rather than something actually checked against a live source. This project has already found and fixed three of these itself (`specs/13-decision-log.md` DEC-131/132/133), which is evidence more may remain uncaught, not evidence the problem is solved.
> 3. **Requirement/architecture soundness** — does the two-layer ACL model, the verification pipeline (mechanical + NLI), the refusal-decision taxonomy, and the layered safety rails actually hold together as a coherent design, or are there gaps a careful outside read catches? Look specifically for authorization-bypass paths, a documented invariant (e.g. "citations are checked against `reranked_set`, never `retrieval_set`") that isn't actually enforced everywhere it's claimed to be, and refusal-taxonomy edge cases that fall through uncovered.
> 4. **Overconfidence / groupthink markers** — language asserting something is "resolved," "confirmed," or "PASS" with no concrete, checkable evidence cited right next to the claim. An internal audit that repeatedly grades its own work "READY" is exactly the situation self-evaluation bias predicts will look clean regardless of whether it actually is.
> 5. **Domain plausibility** — from a CCM/ECM enterprise-software, on-prem B2B2B lens: does anything in the market positioning, compliance framing (`specs/42-compliance-security.md`), or MVP scope assumptions look naive, miss an obvious real-world constraint, or contradict how enterprise CCM/ECM buyers and vendors actually operate?
>
> For each finding, cite the exact file and line/section, state the concrete problem, and rate it CRITICAL / HIGH / MEDIUM / LOW: CRITICAL = a missing requirement, a real security/authorization bypass, or a factual claim presented as settled that is actually wrong; HIGH = a real gap likely to cause a wrong implementation; MEDIUM = a real but contained inconsistency; LOW = cosmetic/stylistic.
>
> Report format:
>
> ```markdown
> # Specs Cross-Model Review
>
> ## Scope
> << which files/groups were actually reviewed, and which were skipped and why >>
>
> ## Findings
> ### R.1 [SEVERITY] — <dimension>
> File: <path:line-or-section>
> Issue: <what's wrong>
> Why this might be a self-review blind spot: <why a same-family reviewer could plausibly have missed it>
> Suggested fix: <concrete, actionable>
>
> (repeat per finding)
>
> ## Summary
> | Severity | Count |
> |---|---|
> | CRITICAL | |
> | HIGH | |
> | MEDIUM | |
> | LOW | |
>
> <one-paragraph overall assessment>
>
> Verdict: APPROVE (no CRITICAL/HIGH) | WARN (MEDIUM/LOW only) | BLOCK (any CRITICAL/HIGH)
> ```
>
> If you genuinely find nothing at a given severity, say so rather than inventing a finding to seem useful — an empty category is a valid, useful result.
