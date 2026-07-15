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

**Phase 1 (bootstrap)** is closed. The scaffold is in place plus the three Phase 1 issues, which close Phase 1's exit gate:

- ✅ phase-1-bootstrap Issue 01 — project scaffold (17 module directories per the architecture's module map) + core dependency pinning
- ✅ phase-1-bootstrap Issue 02 — architecture import-graph check (enforces the module call-direction rules in CI) + CI baseline
- ✅ phase-1-bootstrap Issue 03 — first failing smoke test: a minimal `GET /ready` endpoint (Pydantic-typed, no live backend calls) with a test that deliberately still fails, since `ready: true` isn't honest until real services exist

**Phase 2 (core domain + data foundation)** has started. Two issues published and agent-closeable work complete on both — each still has a live-service `[manual-verify]` item (no Docker in this environment, `docs/agents/dev-environment.md`):

- ✅ data-foundation Issue 01 — Postgres schema migration (9 tables per `specs/07-database.md`, hand-authored Alembic migration; offline `--sql` DDL rendering verified, live Postgres run pending)
- ✅ data-foundation Issue 02 — Qdrant collection + 5 mandatory payload indexes (vector config + Layer 1 filter semantics verified against a real embedded client; live-server index-existence check pending)

- ✅ document-ingest-pipeline Issue 01 — plain-text/Markdown ingest pipeline (parse→chunk→embed→ACL-enrich→index, job-store checkpointing, a disposable `acl/` stub; real Postgres job-store round-trip pending, no live server in this sandbox)
- ✅ document-ingest-pipeline Issue 02 — PDF/Word parsing (`pdfminer.six` primary + PyMuPDF rescue, corrected from Unstructured.io mid-implementation — DEC-143) + embedding-service retry resilience (Full Jitter backoff); 100-page reference-hardware timing check pending

If this list looks out of date, [`.scratch/phase-1-bootstrap/issues/`](.scratch/phase-1-bootstrap/issues/), [`.scratch/data-foundation/issues/`](.scratch/data-foundation/issues/), and [`.scratch/document-ingest-pipeline/issues/`](.scratch/document-ingest-pipeline/issues/) (or the next phase's issue directory) are the authoritative status, not this README.

The canonical source of truth for what's being built and why is [`specs/`](specs/), not this README — start at [`specs/00-index.md`](specs/00-index.md).

## Repo structure

```
specs/              Canonical product-level spec set (entry point: specs/00-index.md)
docs/agents/        Per-repo config consumed by the engineering skills (issue tracker, triage labels, dev-environment ground truth)
docs/testing.md     How to write a test here, what to avoid, and the current test inventory
docs/coding-standards.md  Judgment-call coding conventions a linter can't check (mechanical rules live in pyproject.toml)
.scratch/            Local issue tracker (markdown-based) — PRDs and implementation issues
.scratch/session-feedback.md  Running log of how sessions went, not what was built — see CLAUDE.md
.claude/skills/       Skill definitions used to draft, gate, and implement work in this repo
.pre-commit-config.yaml  Local commit-time gate: ruff, mypy, import-graph check, doc-drift check (see docs/testing.md)
tools/               Standalone scripts (bash tools/verify.sh, tools/check_pypi_version.py, ...) — see tools/README.md
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
