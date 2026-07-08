# Coding Standards (Judgment Rules)

Split from a general-purpose `coding-standards.md` brought over from another project. That file mixed two different kinds of rule; only one kind belongs here.

Every mechanically-checkable rule — function length, nesting depth, magic numbers, dead code, `print()` left in, bare `except:`, hardcoded secrets, SQL string concatenation, naming-case conventions, a skipped test with no reason — is **not** in this file. Those belong in a linter/pre-commit config (ruff, bandit, a secret scanner), not in a document an agent has to remember on every pass. This repo's own `/review` skill already states the principle: "Skip anything tooling enforces." A deterministic check that runs on every commit is strictly more reliable than a stochastic read of a rules file, so restating what a tool already enforces here would just add context load for nothing a careful read adds on top.

What's left is the part a linter genuinely can't do: judgment calls, where the right answer depends on knowing intent, not on matching a pattern.

## Naming

- A name must be descriptive enough that a reader doesn't need to jump to the definition to know what a variable holds or a function does. Single-letter names are fine only for trivial loop indices — nowhere else.
- Functions read as verb-noun (`fetch_user`, `validate_input`) — a noun-only name (`user`, `validation`) reads like a value, not an action, and misleads the caller about what calling it does.
- Boolean names carry an `is_`/`has_`/`can_` prefix when doing so actually clarifies the value's meaning — skip it where the prefix would just be redundant with the name itself.
- Avoid abbreviations unless truly universal (`url`, `id`, `db`) — one you had to think twice about is one a future reader will too.

## Error handling

- Validate at system boundaries — user input, external API responses, anything crossing a trust line. Trust internal code past that boundary; re-validating what your own code already guaranteed is waste, not safety.
- When an exception is caught, decide deliberately whether to log-and-continue, wrap-and-re-raise, or let it propagate — never let it vanish silently. The judgment call is which of the three fits *this* failure; it isn't a rule to apply uniformly, it's a decision to make every time.
- Don't leak internal error detail across a trust boundary to a caller (stack traces, internal file paths, raw query text) — wrap in a domain error or a generic message instead. Internal-to-internal calls don't need this; it's a boundary rule, not a blanket one.

## Security judgment calls

- Sanitize and validate all user input before it's used. This is the one rule here that doesn't bend on "when" — it's listed as a judgment call because *which* input and *which* sanitization can't be reduced to a static pattern a scanner catches reliably every time.
- Treat any file path built from user-controlled input as traversal-risk until proven otherwise — normalize it and confirm it stays inside its intended root before use.

## Logging

- Never log a token, password, credential, or other PII. This needs judgment about what's sensitive in *this* domain — a secret scanner catches hardcoded literals, not values assembled at runtime from user data, so this one can't be fully delegated to tooling the way the others above can.

---

**Still open, not covered by this file**: this repo's `/setup-pre-commit` skill currently only wires up the Node/Husky/Prettier toolchain. This project is Python (FastAPI/LangGraph). There's no equivalent pre-commit setup yet for `ruff`/`mypy`/`pytest` to actually enforce the mechanical half of the original `coding-standards.md` — that's a separate, still-open gap, not resolved by this split.
