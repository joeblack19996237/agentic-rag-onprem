# GroundedDocs

**GroundedDocs** is an on-prem, vendor-embeddable document Q&A agent for CCM/ECM vendors (Quadient, Smart Communications, M-Files, Hyland, and regional equivalents) whose enterprise customers need answers grounded in verified citations — or an honest refusal when grounding is weak.

> GroundedDocs is the on-prem, vendor-embeddable document Q&A agent for enterprises that need answers grounded in cited, verifiable sources — or no answer at all.

Five differentiators:

1. **Open-weight + fully local LLM inference + model-swappable** — no cloud egress, no proprietary lock-in
2. **Vendor-embeddable** — a CCM/ECM vendor can ship it as their own AI feature without re-architecting
3. **Verified citations, not decorative ones** — every claim in an answer is checked against what was actually retrieved, mechanically and via NLI
4. **Refusal as a product feature** — when grounding confidence is weak, the system declines or downgrades rather than guessing
5. **Audit-first** — every query, retrieval, citation, and refusal decision is recorded for after-the-fact review

See [`specs/01-product-brief.md`](specs/01-product-brief.md) for the full problem statement, market positioning, and personas.

## Project status

This repository is currently in **Phase 1 (bootstrap)** of the build plan. The scaffold is in place plus the first three Phase 1 issues, which close Phase 1's exit gate:

- ✅ Issue 01 — project scaffold (17 module directories per the architecture's module map) + core dependency pinning
- ✅ Issue 02 — architecture import-graph check (enforces the module call-direction rules in CI) + CI baseline
- ✅ Issue 03 — first failing smoke test: a minimal `GET /ready` endpoint (Pydantic-typed, no live backend calls) with a test that deliberately still fails, since `ready: true` isn't honest until real services exist

Phase 2 hasn't started. If this list looks out of date, [`.scratch/phase-1-bootstrap/issues/`](.scratch/phase-1-bootstrap/issues/) (or the next phase's issue directory) is the authoritative status, not this README.

The canonical source of truth for what's being built and why is [`specs/`](specs/), not this README — start at [`specs/00-index.md`](specs/00-index.md).

## Repo structure

```
specs/              Canonical product-level spec set (entry point: specs/00-index.md)
docs/agents/        Per-repo config consumed by the engineering skills (issue tracker, triage labels, dev-environment ground truth)
docs/testing.md     How to write a test here, what to avoid, and the current test inventory
.scratch/            Local issue tracker (markdown-based) — PRDs and implementation issues
.claude/skills/       Skill definitions used to draft, gate, and implement work in this repo
.pre-commit-config.yaml  Local commit-time gate: ruff, mypy, import-graph check, doc-drift check (see docs/testing.md)
tests/architecture/   Import-graph check enforcing specs/04-architecture.md §5.1's module call-direction rules
tests/docs/           Documentation-drift check — DEC-### reference integrity + README/issue-status sync (CI-enforced)
{api,retrieve,acl,rerank,generate,verify,audit,ingest,admin,eval,config,widget,cdc,
 safety_input,safety_output,policy,cache}/   Module scaffold (placeholder, per the architecture's module map)
```

## Tech stack (pinned)

Python 3.14, FastAPI, LangGraph 1.2.x, vLLM, TEI (text-embeddings-inference), Qdrant, PostgreSQL 16, Redis/Valkey. See [`requirements.txt`](requirements.txt) and [`specs/13-decision-log.md`](specs/13-decision-log.md) for the pinned versions and the reasoning behind each choice.

## Getting started

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # dev-only tools (ruff, mypy, pytest, pre-commit) — same versions CI uses
ruff check .
mypy .
pytest
pre-commit install  # one-time: installs the local pre-commit git hook (see .pre-commit-config.yaml)
```

`requirements-llama-cpp.txt` (the Phase 5 RAGAS judge-model dependency) and vLLM are intentionally not in `requirements.txt` — they need a C/C++ build toolchain and a CUDA-capable host respectively, and are tracked as `[manual-verify]` items in the relevant issue until run on a host that has them.

## License

MIT — see [`LICENSE`](LICENSE).
