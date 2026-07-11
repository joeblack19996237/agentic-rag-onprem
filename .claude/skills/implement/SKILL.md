---
name: implement
description: "Implement a piece of work based on a PRD or set of issues."
disable-model-invocation: true
---

Implement the work described by the user in the PRD or issues.

Follow [CODING-STANDARDS.md](CODING-STANDARDS.md) for the judgment calls a linter can't make — naming clarity, error-handling boundaries, input validation, sensitive-data logging. Everything mechanically checkable (line length, bare `except`, hardcoded secrets, casing) belongs to this repo's linter/pre-commit setup instead, not to a rules file an agent has to remember — that file explains the split in full.

Use /tdd where possible, at pre-agreed seams.

Before writing code against a fast-moving or pre-1.0 dependency — this project pins LangGraph, for instance, and anything `specs/04-architecture.md`'s tech-stack table cites by an exact or minor version rather than treating as a stable major line counts too — don't trust training-data memory of its API. WebFetch the official docs, or the library's GitHub source/release notes, first if you're not certain the signature or behavior you're about to rely on still matches what's actually pinned. This isn't hypothetical: `specs/13-decision-log.md` DEC-131 records a case in this exact project where a pinned version was already wrong the day it was decided, because the deciding agent trusted training-data recall over a live check. A wrong guess here compiles fine and breaks at runtime or silently does the wrong thing.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Before checking off any acceptance criterion, confirm you can actually run its Verification line in this environment. If an AC turns out unreachable as written — infrastructure the manifest assumed isn't actually there, an artifact from a "later phase" note doesn't exist, the criterion is a human-timed claim that slipped through — stop. Do not silently skip it and do not mark it done on the strength of the surrounding work being correct. Report which AC, why it can't be verified as written, and ask the user whether to defer it, mark it `[manual-verify]`, or find an alternate proxy. See `/verifiable-acceptance-criteria` for the full classification, and `docs/agents/dev-environment.md` for this environment's known capabilities before assuming one is missing.

Once done, use /code-review to review the work.

Commit your work to the current branch.
