# tools/

> Small, standalone scripts an agent (or human) invokes directly — not test code, not a skill's internal implementation detail. Read this before writing a new one-off command for the second time in a session; that's usually the signal it belongs here instead. Current inventory and what each script covers is below; keep it in sync the same way `docs/testing.md` tracks its own inventory.

## When to write a script here vs. just run the command

If you notice yourself retyping the same multi-step command, or the same one-liner (a `python -c "..."` PyPI lookup, a multi-step verification sequence), more than once in a session — that's the signal to promote it, not respin it a third time. A script that's actually reusable earns its keep the first time someone else (human or agent) doesn't have to reconstruct it from scratch.

Don't promote something that's only ever going to run once (a scratch/throwaway check for a specific bug) — that's what an inline command is for. The bar is *reuse*, not *complexity*.

**The within-session signal above is blind to cross-session recurrence — check for that too, not just this session's own retyping.** A fresh session has no memory of a prior session's inline commands, so the same hand-rolled check can recur across multiple sessions without ever tripping the "twice in one session" trigger, since each individual session only used it once. Concrete case this repo already hit: a `pip install --dry-run` dependency-installability check was hand-rolled in `specs/13-decision-log.md` DEC-134 (2026-07-11) and again, independently, while gating Phase 2's first issues (2026-07-14) — two different sessions, same underlying need, never promoted, because neither session repeated it *within itself*. Before writing an inline verification command for a "has this kind of check come up before" situation (dependency-version/installability checks, environment-capability probes, spec cross-reference sweeps), grep `specs/13-decision-log.md` and recent commit messages for the same pattern first — if it's there, that's a second occurrence even though this session only used it once.

## How to write a good script for this repo

- **Stdlib-only Python, or portable bash calling only tools already required elsewhere in this repo** (`ruff`, `mypy`, `pytest`, `git`, `gh`) — no new dependency to install before the script itself becomes usable. `tools/call_peer_review_model.py`'s own docstring states this reasoning; it's the standing convention, not a one-off choice.
- **Work from the repo root regardless of the caller's current directory.** A bash script should `cd "$(dirname "${BASH_SOURCE[0]}")/.."` at the top (see `tools/verify.sh`); a Python script should use paths relative to `Path(__file__).resolve()`, never assume the caller's cwd.
- **Exit codes are the contract.** Document what 0 vs. non-zero means in the script's own docstring/header comment — a caller (agent or CI) should be able to branch on the exit code without reading the script's body. `tools/call_peer_review_model.py`'s docstring is the reference example (0/1/2, each with a one-line meaning).
- **A short header comment explaining *why* the script exists and what problem it's solving** — not a restatement of what each line does. Match `docs/coding-standards.md`'s own no-comments-unless-non-obvious rule; a script is code too.
- **Actually run it before trusting it**, the same discipline as everything else in this repo (`CLAUDE.md`'s "Running and verifying this repo"). `tools/verify.sh`'s first real run caught a genuine regression — moving `call_peer_review_model.py` here broke its `pyproject.toml` `per-file-ignores` exception, since that config still pointed at the script's old path. Writing a script and never running it is exactly the failure mode this whole convention exists to catch.

## Current inventory

| Script | Purpose | Usage |
|---|---|---|
| `verify.sh` | Local verification matching CI: `ruff check .`, `mypy .`, the full suite except the deliberately-red `tests/api/` smoke test (run separately, shown but non-gating) | `bash tools/verify.sh` |
| `check_pypi_version.py` | Look up a package's actual current version on PyPI — the one-line `urllib` check this repo's dependency-version-claims rule (`CLAUDE.md`) requires before pinning or citing a version as current, promoted from an inline `python -c "..."` into something reusable | `python tools/check_pypi_version.py <package>` — prints `<package>==<version>` to stdout, exit 1 if the lookup fails |
| `call_peer_review_model.py` | Calls an OpenAI-compatible chat-completions endpoint (defaults to DeepSeek) for a structured JSON code review of a diff. **Not currently invoked by `.claude/skills/peer-review/SKILL.md`** — that skill's own text never references this script; it appears to predate the skill's "drop API-key requirement" revision and was left orphaned rather than removed. Usable standalone (`--dry-run` needs no API key) but whether it should be wired back into the skill, or removed, is an open question this move doesn't resolve | `python tools/call_peer_review_model.py --diff-file <f> --rubric-file <f> --out <f> [--dry-run]` |

Not built yet: a GitHub-release-tag equivalent of `check_pypi_version.py` (used by hand this session for `ruff-pre-commit`'s pinned `rev:` via `gh api repos/<owner>/<repo>/tags`) — a smaller, rarer need so far, not promoted until it's actually been retyped more than once.
