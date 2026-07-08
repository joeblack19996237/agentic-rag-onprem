---
name: setup-pre-commit
description: Set up pre-commit hooks — Husky + lint-staged + Prettier for Node/TS repos, or the `pre-commit` framework with ruff + mypy + pytest for Python repos. Use when user wants to add pre-commit hooks, set up Husky, configure lint-staged, wire up ruff/mypy/pytest at commit time, or add commit-time formatting/typechecking/testing.
---

# Setup Pre-Commit Hooks

## Step 0 — Detect project type, and confirm there's a project to hook into

Check for:

- **Node/TS** — `package.json` plus a lockfile (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`)
- **Python** — `pyproject.toml`, `requirements*.txt`, `setup.py`/`setup.cfg`, or a source tree of `.py` files

If both are present (a polyglot repo), ask the user which to set up, or do both, one after the other. If **neither** is present, stop and say so — pre-commit hooks need an actual dependency manifest and source tree to hook into. Don't scaffold a placeholder project just to make hooks installable; that's different, larger work belonging to whatever skill actually stands up the project (e.g. this repo's own `to-issues`/`implement` flow), not this one.

Then follow the matching path below.

## Node path

### 1. Detect package manager

Check for `package-lock.json` (npm), `pnpm-lock.yaml` (pnpm), `yarn.lock` (yarn), `bun.lockb` (bun). Use whichever is present. Default to npm if unclear.

### 2. Install dependencies

Install as devDependencies:

```
husky lint-staged prettier
```

### 3. Initialize Husky

```bash
npx husky init
```

This creates `.husky/` dir and adds `prepare: "husky"` to package.json.

### 4. Create `.husky/pre-commit`

Write this file (no shebang needed for Husky v9+):

```
npx lint-staged
npm run typecheck
npm run test
```

**Adapt**: Replace `npm` with detected package manager. If repo has no `typecheck` or `test` script in package.json, omit those lines and tell the user.

### 5. Create `.lintstagedrc`

```json
{
  "*": "prettier --ignore-unknown --write"
}
```

### 6. Create `.prettierrc` (if missing)

Only create if no Prettier config exists. Use these defaults:

```json
{
  "useTabs": false,
  "tabWidth": 2,
  "printWidth": 80,
  "singleQuote": false,
  "trailingComma": "es5",
  "semi": true,
  "arrowParens": "always"
}
```

### 7. Verify

- [ ] `.husky/pre-commit` exists and is executable
- [ ] `.lintstagedrc` exists
- [ ] `prepare` script in package.json is `"husky"`
- [ ] `prettier` config exists
- [ ] Run `npx lint-staged` to verify it works

### 8. Commit

Stage all changed/created files and commit with message: `Add pre-commit hooks (husky + lint-staged + prettier)`

This will run through the new pre-commit hooks — a good smoke test that everything works.

## Python path

Sets up the [`pre-commit`](https://pre-commit.com) framework — the Python-ecosystem standard, unrelated to Husky beyond the shared name — running **ruff** (lint + format), **mypy** (type check), and **pytest**.

### 1. Install the `pre-commit` framework

Add `pre-commit` as a dev dependency (a `[dependency-groups]`/`[tool.*.dev-dependencies]` entry in `pyproject.toml` if the project has that convention, otherwise `pip install pre-commit`). Installing the package alone does nothing until Step 4's `pre-commit install` runs.

### 2. Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.20  # WebFetch github.com/astral-sh/ruff-pre-commit/tags (or `gh api repos/astral-sh/ruff-pre-commit/releases`) for the current tag before using this — don't trust this pin once time has passed, same discipline as this repo's `implement` skill applies to any fast-moving dependency
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: mypy
        language: system
        types: [python]
        pass_filenames: false

      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]  # move to [pre-push] instead if the suite is slow or hits real services — see Step 3
```

**Why `local` for mypy and pytest, not a hosted mirror repo**: the hosted mypy mirror (`pre-commit/mirrors-mypy`) runs mypy inside an isolated environment that never sees this project's actual installed dependencies — every third-party import reads as untyped/missing unless `additional_dependencies` is manually kept in sync with the real dependency set, which drifts the moment a dependency is added or bumped. A `local` hook calls whatever `mypy` is on `PATH` in the environment the hook runs in, so it sees the real installed types instead. There's no hosted mirror for pytest at all, for the same underlying reason — a test suite is too project-specific to mirror generically.

### 3. Decide where pytest runs — commit or push

A full test suite that hits real services (a database, an inference server, a vector store — anything integration- or e2e-shaped) is too slow for every commit and will train contributors to reach for `--no-verify`, which defeats the hook's purpose. This is a judgment call, not a fixed rule:

- **Fast, unit-only suite** → `stages: [pre-commit]` as written above, runs on every commit.
- **Slow suite, or one with integration/e2e tests** → `stages: [pre-push]` instead, and also run `pre-commit install --hook-type pre-push` in Step 4. Commit stays fast; push still catches regressions before they leave the machine.

Ask the user which fits if it isn't obvious from the current test suite's shape.

### 4. Install the git hook(s)

```bash
pre-commit install
```

Add `pre-commit install --hook-type pre-push` too if Step 3 put pytest on the push stage.

### 5. Verify

- [ ] `.pre-commit-config.yaml` exists
- [ ] `pre-commit install` reports the hook installed (`.git/hooks/pre-commit` exists and invokes `pre-commit`)
- [ ] Run `pre-commit run --all-files` once to confirm every hook actually *executes* without a configuration error — not just that the YAML parses. A hook that's present but fails to run at all is worse than no hook, since it gives false confidence
- [ ] If pytest is on the push stage, also confirm `.git/hooks/pre-push` exists

### 6. Commit

Stage all changed/created files and commit with message: `Add pre-commit hooks (ruff + mypy + pytest)`. This runs the new hooks — a real smoke test, not just a file-existence check.

## Notes

- Husky v9+ doesn't need shebangs in hook files (Node path only)
- `prettier --ignore-unknown` skips files Prettier can't parse (images, etc.) (Node path only)
- Python path: pin `rev:` in `.pre-commit-config.yaml` to an actual current tag rather than a remembered one — the same fast-moving-dependency discipline this repo's `implement` skill now applies generally (`specs/13-decision-log.md` DEC-131 is the concrete case that motivated it)
- Both paths: the goal is a hook that actually runs and actually fails when it should. Verify by running it — don't just confirm the config file's shape.
