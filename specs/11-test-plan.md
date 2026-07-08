# 11 — Test Plan

> Stage 7 (`spec-writer`) deliverable. `TEST-###` ids, traced to `REQ-###`. Cross-references `23-evals-guardrails.md`'s golden-set categories rather than redefining them — this file's job is the executable test suite structure (unit/integration/E2E/manual/perf/security), not re-authoring the AI-quality eval methodology that file already owns. Closes the remaining half of RC-T8-01 (`verify/` parser strict-mode + known-limitations appendix).

## Test Strategy

Four layers, in ascending scope: unit (single node/function), integration (multi-node/cross-store), contract (API shape, already detailed in `06-api-contracts.md`), end-to-end (full turn, matching `12-verification.md`'s demo scenario). AI-specific evaluation (RAGAS, golden set, guardrail adversarial prompts) is owned by `23-evals-guardrails.md` and referenced, not duplicated, throughout this file.

## Test Environments

| Environment | Purpose |
|---|---|
| Local/CI | Unit + integration tests against dockerized Postgres/Qdrant/Redis test instances; no real GPU (mocked model responses where a test doesn't need real inference) |
| Dev rig (RunPod) | Full-stack integration + E2E tests requiring real model inference (safety-rail accuracy, NLI scoring, generation quality) |
| Air-gap simulation | REQ-012 verification: network namespace blocked, full eval suite run |
| Customer-representative rig | Hardware-validation tests per `09-deployment-ops.md`'s measured-VRAM methodology |

## Test Data and Fixtures

- **Golden set**: owned by `23-evals-guardrails.md` §2.2 — 50-prompt smoke ring + 150-200 prompt full ring, composition table there is authoritative. This file's E2E and AI-quality tests consume that golden set; they do not maintain a separate copy
- **Synthetic ACL corpus**: a fixture corpus with deliberately mixed ACLs (some documents restricted, some open, some under simulated legal hold) — used across integration tests for Layer 1/Layer 2 authorization correctness (referenced from `10-build-plan.md` TASK-012/013)
- **Poisoned-content fixture**: seeded chunks designed to trigger the retrieval-rail scan (mirrors `23-evals-guardrails.md`'s "Retrieval-rail refusal prompts" golden-set category, +5 prompts) — used in integration tests, not re-derived here
- **Compound-document fixture**: a virtual/compound-document test structure (mirrors `41-integration-contracts.md`'s DEC-114 contract test) for adapter-correctness testing

## Unit Tests

| Test ID | Type | Related Requirement | Scenario | Data | Expected Result | Automation |
|---|---|---|---|---|---|---|
| TEST-001 | Unit | REQ-005 | `verify/.mechanical_fast_path` given a citation to a `chunk_id` present in `reranked_set` | Synthetic single-citation answer | Passes, no fabrication flag | Automated |
| TEST-002 | Unit | REQ-005, DEC-088 | `verify/.mechanical_fast_path` given a citation to a `chunk_id` in `retrieval_set` but absent from `reranked_set` | Synthetic adversarial citation | Rejected — `low_grounding`, early-exit (no NLI cost) | Automated |
| TEST-003 | Unit | NFR-012 | Embedding-service input construction never includes an ACL/identity field | Synthetic chunk with populated ACL metadata | Static check fails the build if any ACL field appears in embedding input text | Automated (CI) |
| TEST-004 | Unit | DEC-065 | `chunk_id` derivation is deterministic and immutable for a fixed `(document_id, version_id, sequence)` | Synthetic chunk | Same tuple always produces the same `chunk_id` | Automated |
| TEST-005 | Unit | DEC-042 | `refusal_decision()` returns the correct typed class for each of the 5 documented trigger conditions in isolation | Synthetic per-condition inputs | 5/5 correct class mapping | Automated |

## Integration Tests

| Test ID | Type | Related Requirement | Scenario | Data | Expected Result | Automation |
|---|---|---|---|---|---|---|
| TEST-006 | Integration | REQ-036 | Layer 1 filter-then-search recall vs. unfiltered baseline | Mixed-ACL synthetic corpus | Filtered recall matches unfiltered recall on non-restricted content (no HNSW-breaking regression) | Automated |
| TEST-007 | Integration | REQ-036, DEC-046 | Layer 2 catches a Layer-1-stale revoked-access chunk | Seeded ACL-revocation scenario | Chunk dropped before rerank | Automated |
| TEST-008 | Integration | NFR-016, DEC-063 | ECM PDP circuit breaker trips under simulated 1s+ latency | Stubbed slow PDP | Breaker opens; queries return `verification_unavailable`; `pdp_breaker_state` observable | Automated |
| TEST-009 | Integration | REQ-041, RC-T8-01 | CDC webhook idempotency — redelivered event within 7-day window | Duplicate `acl_changed` event | Second delivery is a no-op | Automated |
| TEST-010 | Integration | REQ-057, NFR-032 | Poll-only CDC cursor advancement, no event loss/duplication across 2 consecutive polls | Simulated ECM event stream | Cursor advances correctly; every event processed exactly once | Automated |
| TEST-011 | Integration | NFR-014, NFR-015 | Retention-expiry physical delete + legal-hold freeze | Seeded `retention_expired`/`legal_hold_added` events | Zero orphan rows post-expiry; hold-active refusal on re-ingest attempt | Automated |
| TEST-012 | Integration | DEC-091, DEC-106, DEC-116 | Legal-hold cross-store cache invalidation (KV-cache + answer-cache) | Active conversation + cached answer referencing the frozen doc | Both caches invalidated; both actions in `legal_hold_invalidation_events` | Automated |
| TEST-013 | Integration | REQ-048, DEC-082 | Parallel `[safety_input ∥ retrieve]` fan-out, `acl/` join discards retrieval on flag | Injection-pattern query | `policy_blocked`; trace shows simultaneous parallel spans (NFR-029) | Automated |
| TEST-014 | Integration | DEC-096, DEC-105 | Retrieval-rail scan flags and drops poisoned chunks, distinct refusal class from query-level injection | Poisoned-content fixture | `verification_unavailable`, not `policy_blocked`; `retrieval_safety_verdicts` populated | Automated |
| TEST-015 | Integration | DEC-092 | Safety-rail quantization change (int4 → int4 AWQ) accuracy-preservation check | HarmBench-derived red-team subset | Documented F1/recall comparison recorded before shipping as default | Manual (gate, not automatable — requires human-reviewed red-team labeling) |
| TEST-016 | Integration | REQ-034, DEC-109 | Embedding blue/green cutover blocked on RAGAS-floor failure | Simulated post-swap metric regression | Cutover blocked; old collection remains active; rollback path confirmed | Automated |
| TEST-017 | Integration | REQ-033, DEC-109 | Generation-model swap blocked on RAGAS-floor failure | Simulated post-swap metric regression | Adapter pointer not promoted; rollback confirmed | Automated |
| TEST-018 | Integration | DEC-114 | Compound/virtual-document `get_effective_acl(leaf_doc_id)` correctly resolves to root-node ACL | Compound-document fixture | Correctly-resolved effective ACL returned, not empty/default | Automated (against a stub adapter implementing the fixture) |
| TEST-019 | Integration | DEC-113 | `security_label`-only change correctly fires `acl_changed` and propagates | Seeded label-only change event | `chunks.security_label` refreshed; `allow_principals[]`/`deny_principals[]` unchanged | Automated |
| TEST-020 | Integration | REQ-056 (reconciliation, DEC-090) | Weekly reconciliation crawl flags an orphaned document | Seeded RAG-side document with no ECM counterpart | Ops alert/report generated; no auto-remediation performed | Automated |
| TEST-035 | Integration | REQ-037, DEC-046 | Retention-state capture at ingest — `retention_state` populated on every chunk from `ECMAdapter.get_retention_state()` at ingest time, and enforced as a Qdrant filter at retrieval | Seeded document with a non-`active` retention state (e.g. `legal_hold`) at ingest time | Chunk payload correctly carries the captured retention state; query filter excludes it from retrieval (`retention_state != active` is filtered) | Automated |
| TEST-036 | Integration | REQ-050 | `SafetyRailAdapter` Protocol swap — swap the active output adapter to a stub via `config/safety_rails.yaml` with no code change | `StubFlaggyAdapter` (always `flagged=true`) and `StubFalseyAdapter` (always `flagged=false`), per `04-architecture.md` §4.3's documented stub pattern | Every query refuses with `policy_blocked` under the flaggy stub; `audit_events.safety_output_verdict` reflects the swapped adapter's verdict; no code change required to perform the swap | Automated |
| TEST-037 | Integration | REQ-043 | Audit-pull NDJSON endpoint — `GET /v1/admin/audit/events` returns a correctly cursor-paginated NDJSON stream, idempotent across repeated pulls with the same cursor | Seeded `audit_events` spanning multiple pages | Response is valid NDJSON; `X-Next-Cursor` header present; re-pulling with an already-consumed cursor returns no duplicate records; vendor-SIEM-style incremental pull produces the complete, non-overlapping record set | Automated |
| TEST-038 | Integration | NFR-033, DEC-128 | Domain-specific span attributes — a query's trace carries the full NFR-033 attribute set: `retrieve` span's `candidate_count`/`retrieval_top1_score`, `rerank` span's `rerank_score_delta`/`top_k`, `verify` span's `mechanical_fast_path`/`nli_slow_path` verdict + per-claim NLI scores (when the slow path runs), and the root span's five version identifiers | A query that exercises both the mechanical and NLI verification paths (one citation that mechanically passes, one that requires NLI scoring) | Every listed attribute is present on its span with a value consistent with that same query's `audit_events` row; the version identifiers match the currently-active `prompt_templates`/`model_versions` rows; no attribute contains raw query/chunk/answer text | Automated |

## `verify/` Parser Strict-Mode (Closes the Remaining Half of RC-T8-01)

`92-stage5-review-memos.md`'s RC-T8-01 named "parser tolerance" as a still-open item after CDC idempotency was fixed in Round 1. This section is that closure.

**Decision**: `verify/.mechanical_fast_path`'s citation-token parser operates in **strict mode** — a citation token that does not parse into the expected `[chunk_id]` or `[chunk_id, span_offset]` shape is treated as equivalent to a fabricated citation (mechanical failure, `low_grounding` refusal), not silently dropped or ignored. Rationale: a malformed citation token is either (a) a generation-model formatting bug, in which case surfacing it as a refusal is the correct fail-safe (better to refuse than to silently strip an assertion's citation and present unverified prose as verified), or (b) itself a sign of prompt-injection-influenced output that evaded the input/retrieval rails, in which case treating it leniently would be a security regression. This is consistent with NFR-004's "100% citation hit-rate hard gate, not tunable" — a lenient parser would effectively create an untracked exception to that gate.

| Test ID | Type | Related Requirement | Scenario | Data | Expected Result | Automation |
|---|---|---|---|---|---|---|
| TEST-021 | Unit | REQ-005, NFR-004 | Malformed citation token (missing bracket, non-existent field shape) | Synthetic malformed-citation answer | Treated as mechanical failure; `low_grounding` refusal, not silently dropped | Automated |
| TEST-022 | Unit | REQ-005 | Citation token referencing a syntactically valid but semantically absent `chunk_id` format (e.g. wrong ID length/pattern) | Synthetic malformed-ID citation | Same strict-mode rejection as TEST-021 | Automated |

## Contract Tests

Full table is `06-api-contracts.md`'s Contract Tests section — not duplicated here; cross-referenced as the API-layer test suite this file's E2E tests build on top of.

## End-to-End Tests

| Test ID | Type | Related Requirement | Scenario | Data | Expected Result | Automation |
|---|---|---|---|---|---|---|
| TEST-023 | E2E | REQ-001..REQ-007 | Full happy path: upload → ingest → query → cited answer → audit record | Sample CCM-style corpus (REQ-014) | Answer with valid citations; `audit_events` row complete | Automated |
| TEST-024 | E2E | REQ-006 | Full refusal path for each of the 5 classes | Golden-set no-answer prompts (per `23-evals-guardrails.md` §2.2's "No-answer" category) | Correct typed refusal, HTTP 200, correct audit fields | Automated |
| TEST-025 | E2E | REQ-011 | Cold install to first successful query | Fresh docker-compose environment | `/ready: true` within 30 min; first query succeeds | Manual (timed walkthrough, per `09-deployment-ops.md`'s install runbook) |
| TEST-026 | E2E | REQ-012 | Air-gap full-suite pass | Network namespace blocked | 100% of eval suite passes with zero outbound calls attempted | Automated |

## Manual Exploratory Tests

| Focus | What to probe |
|---|---|
| Widget citation-click UX | Click a citation, confirm the source chunk/span highlight renders correctly (V2 deepens this per REQ-019; MVP verifies the basic click-through works) |
| Demo-day burst behavior | Simulate a burst of near-simultaneous cold-cache queries; confirm `queue_depth` surfaces visibly (NFR-031), not a silent stall |
| Admin threshold tuning | Walk through `23-evals-guardrails.md` §7's onboarding runbook manually against a deliberately-mistuned threshold, confirm the diagnosis steps actually lead to the right fix |

## Accessibility Tests

MVP's only UI surface is the embeddable widget (`91-stage3-ux-skip.md`) — basic ARIA + keyboard navigation per Stage 7's widget spec section (deeper accessibility work deferred to V2 admin console per that skip memo's own stated scope). No dedicated accessibility test suite beyond this baseline is committed for MVP, consistent with the UX-skip decision (DEC-019) not being re-litigated here.

## Security Tests

| Test ID | Type | Related Requirement | Scenario | Expected Result |
|---|---|---|---|---|
| TEST-027 | Security | DEC-061 | JWT with `HS256` or `none` algorithm | Rejected — not merely unverified, actively rejected by the algorithm whitelist |
| TEST-028 | Security | NFR-017 | Rate-limit burst test (100 QPS to a single token) | 429 responses observed; abuse alert emitted |
| TEST-029 | Security | NFR-018 | Widget CSP/postMessage scan | Baseline grade B+ or better (Mozilla Observatory or similar); no cross-origin host-state reads in source review |
| TEST-030 | Security | `22-memory-context.md` | Fabricated client-supplied `history` field in request body | Zero influence on server-reconstructed context (verified via inspecting the actual assembled prompt, not just the response) |
| TEST-031 | Security | `23-evals-guardrails.md` §3.1 | Prompt-injection adversarial set (golden-set "Layered-rail trigger prompts" category, +15) | Cross-referenced, not redefined — see that file for the executable adversarial cases |

## Performance Tests

| Test ID | Type | Related Requirement | Scenario | Expected Result |
|---|---|---|---|---|
| TEST-032 | Performance | NFR-005 | Latency at 1/2/5/8 concurrent users, cache-priming sweep | p95 ≤ 8s at every concurrency level within the documented cold/warm-cache regime |
| TEST-033 | Performance | NFR-006 | Ingest throughput | ≥ 100 pages/minute on reference hardware |
| TEST-034 | Performance | NFR-027 | TEI rerank latency, ONNX Runtime backend | p95 ≤ 100ms at top-K=50 |

## AI Evals

Owned entirely by `23-evals-guardrails.md` — this file does not redefine RAGAS metrics, golden-set composition, or judge-decoupling policy. Cross-reference: `23-evals-guardrails.md` §2 (framework + golden set), §3 (guardrails), §3.3 (context fingerprint). **Judge decoupling**: the NLI model (`deberta-v3-base-mnli`) is architecturally distinct from the generation model (never the same weights, never the same family) — this satisfies the judge-decoupling requirement without needing a separate LLM-as-judge step in MVP, since the verification mechanism here is a purpose-built classifier, not a second generation model asked to judge the first.

## Regression Suite

- CI-gated: 50-prompt smoke ring (`23-evals-guardrails.md` §2.2) + TEST-001 through TEST-010 (fast unit/integration subset) run on every PR
- Weekly: 150-200 prompt full ring + the complete integration suite (TEST-001 through TEST-034)
- Pre-demo: full regression suite + manual exploratory pass, per DEC-027's "user runs manually pre-demo" ownership

## Coverage Expectations

- **Every MVP REQ-### has at least one TEST-### tracing to it** (cross-check performed in this file's own final consistency pass, and again in `12-verification.md`'s acceptance matrix)
- **No coverage percentage target is set for code-line coverage** — this system's correctness is better characterized by scenario coverage (does every documented refusal class, every ACL edge case, every CDC event type have a test) than by a line-coverage percentage, consistent with the AI-agent-product nature of this codebase

## Test Ownership

| Test layer | Owner |
|---|---|
| Unit + Integration + Contract | Backend/AI engineers, run in CI |
| E2E (automated) | CI, gated on merge to main |
| E2E (manual, install/demo timing) | Operator, per `09-deployment-ops.md`'s runbooks |
| AI evals (golden set) | User, manual pre-demo run (DEC-027) |
| Security | Backend/AI engineers + periodic external scan (widget CSP) |

## Known Limitations Appendix (Closes the Remaining Half of RC-T8-01)

Consolidated, single-location list of documented MVP limitations that are **not bugs** — each is a deliberate scope boundary with a named source decision, gathered here so a reviewer doesn't have to hunt across a dozen files to find "what does this system deliberately not do."

| Limitation | Why | Source |
|---|---|---|
| No agent loop / multi-step reasoning in MVP | Anti-hallucination guarantee is harder to keep under multi-step reasoning | DEC-039 |
| No cyclic feedback edge (mid-flight rewriting) active in MVP | Reserved for V2 (REQ-020); MVP is one-shot graph traversal | NFR-023 |
| Client-supplied conversation history never accepted | Closes a fabricated-history prompt-injection vector | `22-memory-context.md` |
| Checkout/checkin (in-flight ECM edits) invisible to RAG | Version-based query semantics only; matches 2026 best practice (Graph Connectors, AWS Q Business, Glean) | DEC-071 |
| No application-layer field encryption (host-level disk encryption only) | Customer-managed responsibility; sufficient for the stated concern per `42-compliance-security.md` | RC-T4-02 |
| GDPR right-to-erasure against `audit_events` not implemented | Deferred to first regulated AU/EU buyer engagement; conflicts with the audit-immutability product promise otherwise | DEC-070 |
| No compliance certification (SOC2/HIPAA/PCI/IRAP) | Not committed for MVP; design must not block, not the same as having it | DEC-006 |
| Concurrency ceiling is single-host, single-GPU | 2 in-flight cold-cache floor, 5-8 warm-cache target; V3 multi-host is the scale-out answer | `04-architecture.md` §9.4 |
| No OCR / complex table extraction | Citation accuracy collapses on these inputs | RISK-001, REQ-028 (V3) |
| `verify/` citation parser is strict, not lenient | A malformed citation is treated as a fabrication, not silently dropped | This file's "Parser Strict-Mode" section above |
| No semantic retrieval over conversation history | Recency-window read only, not similarity search | `22-memory-context.md` |
| `intent_classifier/`'s latency budget is unresolved (V2) | Flagged, not yet resolved — a genuine open V2 design question | DEC-110 |

## Dependencies

- `23-evals-guardrails.md` (golden-set categories, RAGAS framework — authoritative, cross-referenced not duplicated)
- `06-api-contracts.md` (contract tests — authoritative, cross-referenced)
- `04-architecture.md`, `20-agent-behavior.md` (behavior source for scenario definitions)
- `09-deployment-ops.md` (install-timing test procedure)
- `10-build-plan.md` (tasks this test plan verifies)
- `12-verification.md` (this phase — the acceptance matrix these tests feed)

## Decision References

DEC-006, DEC-039, DEC-042, DEC-046, DEC-061, DEC-063, DEC-065, DEC-070, DEC-071, DEC-088, DEC-090, DEC-091, DEC-092, DEC-096, DEC-105, DEC-106, DEC-109, DEC-110, DEC-113, DEC-114, DEC-116
