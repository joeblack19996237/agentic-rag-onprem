---
name: dev-environment-capabilities
description: Probe and record what this repo's actual execution environment can and cannot reach — Docker, GPU, cloud/infra CLIs, CI access, and current framework docs — into docs/agents/dev-environment.md, so acceptance-criteria gating has ground truth instead of guesses. Run once per environment, and re-run whenever a new phase introduces infrastructure not yet in the manifest.
disable-model-invocation: true
---

# Dev Environment Capabilities

`verifiable-acceptance-criteria` needs ground truth to tell a **borrowed-environment** acceptance criterion from a genuinely reachable one. Guessing "probably no GPU" or "probably has Docker" defeats the point. This skill produces that ground truth once, as a file, so every future gate check reads it instead of re-guessing.

## Process

### 1. Probe what you can confirm directly

Run each check; record the actual result (success, failure, or "blocked by sandbox") — never infer a result you didn't observe:

- **Container runtime**: `docker version`, `docker compose version`
- **GPU**: `nvidia-smi` (or the platform's equivalent)
- **CI**: is there a `.github/workflows/` (or equivalent) directory; can `gh run list` / `gh workflow list` actually reach a live provider from here
- **Cloud/infra CLIs** named in the project's deployment docs (e.g. `runpodctl`, `terraform`, `aws`/`gcloud` — whatever the stack actually uses): version check or auth-status check, not just "is the binary on PATH"
- **Network egress**: only probe this if doing so is safe and low-cost (e.g. a HEAD request already needed for another step) — don't add a network probe purely to populate this file

### 2. Ask the user for what you can't probe

Anything requiring credentials or account state you can't inspect (a RunPod API key being configured for *this agent's* use, not just existing somewhere; whether CI is actually connected to this repo's remote) — ask directly rather than guessing from absence of evidence. Absence of a probe result is not the same as absence of the capability.

### 3. Pull reference-doc pointers from the architecture spec

If `specs/04-architecture.md`'s tech-stack table exists, list the official documentation URL for each pinned framework/library that's fast-moving or version-sensitive (the kind where training-data recall risks being stale — e.g. a library still under 1.x with breaking changes between minor versions). This gives `implement`/`tdd` a concrete pointer to fetch current docs instead of relying on memory when uncertain about an API shape.

### 4. Write `docs/agents/dev-environment.md`

Use the template in [dev-environment.md.template](dev-environment.md.template). Every row states what was probed, the result, and the date — a stale, unprobed row is worse than an honest "not tested."

### 5. Point consumers at it

Confirm (or add, via the matching patch files) that `to-issues`, `to-prd`, `implement`, and `verifiable-acceptance-criteria` all read this file before making or checking claims that touch infrastructure.

## Completion criterion

Done when `docs/agents/dev-environment.md` exists, every row is either a directly-observed probe result or a user-confirmed answer (never a guess), and the file's date is current.

## Re-run triggers

- First use in this repo.
- A new phase's build plan introduces infrastructure (a new cloud service, a new CI job, a new hardware dependency) not yet listed.
- An acceptance-criteria gate check (`verifiable-acceptance-criteria`) hits an environment question this file doesn't answer.
