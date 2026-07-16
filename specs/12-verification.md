# 12 — Verification

> Stage 7 (`spec-writer`) deliverable. Final acceptance matrix (`VG-###` verification gates), demo script matching the actual MVP demo scenario (`01-product-brief.md`/`confirmed-context.md`), release gates, and production-readiness checklist. This is the last file `10-build-plan.md`'s Phase 6 exit gate points to — everything here should already be testable via `11-test-plan.md`'s `TEST-###` suite; this file's job is to state the pass/fail bar and evidence requirement, not invent new tests.

## Plain-English Summary

This is the "are we actually done" checklist. Every gate below has a testable pass criterion and points to the evidence that proves it — no gate here is satisfied by "looks good" or a verbal confirmation.

## Final Acceptance Matrix

| Gate ID | Requirement | Evidence Required | Pass Criteria | Owner |
|---|---|---|---|---|
| VG-001 | REQ-001 (upload) | TEST-023 output | `document_id` + `status_url` returned within 1s; unsupported format returns 415 | Backend |
| VG-002 | REQ-002 (parse/chunk/embed/index) | TEST-023 output, timed | 100-page born-digital PDF reaches `ready` in ≤60s | Backend |
| VG-003 | REQ-003 (hybrid retrieval) | TEST-006 output | Filtered recall matches unfiltered baseline; both dense and sparse vectors independently contribute (not dense-only) | Backend |
| VG-004 | REQ-004 (cited generation) | TEST-023 output | Every assertion-bearing sentence carries ≥1 citation resolving to a `reranked_set` chunk | Backend/AI |
| VG-005 | REQ-005 (citation verification) | TEST-001, TEST-002, TEST-021, TEST-022, TEST-023 (added 2026-07-16, DEC-147, second cross-model review R.6) | Mechanical + NLI checks correctly reject fabricated/malformed citations, including the DEC-088 adversarial case — TEST-001/002/021/022 cover the mechanical half only (`verify/.mechanical_fast_path`); REQ-005's own text requires both mechanical *and* NLI entailment, and had no test exercising the NLI half at all until TEST-023 (E2E happy path, which runs both) was added here | Backend/AI |
| VG-006 | REQ-006 (refusal policy) | TEST-005, TEST-024 | All 5 refusal classes correctly triggerable, all HTTP 200 | Backend/AI |
| VG-007 | REQ-007 (audit log) | TEST-024 output | Every turn (answered or refused) produces exactly one complete `audit_events` row with non-null `context_fingerprint` | Backend |
| VG-008 | REQ-008 (HTTP API) | `06-api-contracts.md`'s contract tests | OpenAPI spec generated; every documented endpoint exercised by the integration test suite | Backend |
| VG-009 | REQ-009 (embeddable widget) | Manual widget-load test | Widget loads via iframe; theme tokens honored; no cross-origin host-state reads (TEST-029) | Frontend |
| VG-010 | REQ-010 (admin API) | `06-api-contracts.md`'s admin-surface contract tests | Document lifecycle, ACL edit, pagination all functional | Backend |
| VG-011 | REQ-011 (docker-compose install) | TEST-025 | `docker compose up` to `/ready: true` (full-dependency check, DEC-117) in ≤30 min | DevOps |
| VG-012 | REQ-012 (air-gap) | TEST-026 | 100% eval-suite pass with network namespace blocked; zero outbound calls attempted | DevOps |
| VG-013 | REQ-013/REQ-014/REQ-049 (eval harness + golden set) | TASK-029 output | Smoke ring ≤5 min; full ring produces DEC-017-threshold pass/fail report; RAGAS judge model is `Qwen2.5-14B-Instruct` (DEC-130), independently confirmed distinct from the `generate/` model on that run, with no outbound call | AI |
| VG-014 | REQ-036 (two-layer authorization) | TEST-006, TEST-007 | Layer 1 filter + Layer 2 JIT re-check both independently verified correct | Backend |
| VG-015 | REQ-041/REQ-057 (CDC, both transports) | TEST-009, TEST-010 | Webhook idempotency + poll-only cursor advancement both correct | Backend |
| VG-016 | REQ-045 (ECM audit write-back) | Integration test against a stub `ECMAdapter` | Both `granted` and `denied` intents written; async, non-blocking (NFR-013) | Backend |
| VG-017 | REQ-046 (LangGraph orchestration) | TASK-011 verification evidence | Graph traversal matches the canonical sequence; node internals framework-agnostic | Backend |
| VG-018 | REQ-047 (Redis cache) | TEST-043 (corrected 2026-07-16, DEC-147, second cross-model review R.4 — previously cited `TEST-025`, an install-timing E2E test with no cache-behavior coverage at all; a `TASK-025`↔`TEST-025` numbering coincidence, not a real cross-reference) | Cache-hit + TTL/invalidation discipline verified | Backend |
| VG-019 | REQ-048 (layered safety rails) | TEST-013, TEST-014 | All 4 rail layers independently verified with correct verdict-to-refusal mapping | AI |
| VG-020 | REQ-050 (`SafetyRailAdapter` protocol) | TEST-036 | Stub adapter swap changes refusal behavior predictably; audit captures the swapped verdict; no code change required to swap | AI |
| VG-021 | REQ-056 (reconciliation crawl) | TEST-020 | Orphaned document correctly flagged; no auto-remediation | Backend |
| VG-022 | NFR-004 (citation hit-rate hard gate) | Continuous dashboard signal (`08-observability-logs.md`) + TEST-001/002 | 100%, monitored, any deviation is Critical-severity, not a metric to average | AI |
| VG-023 | NFR-005 (latency SLO) | TEST-032 | p95 ≤8s across the documented cold/warm-cache concurrency regime | Backend |
| VG-024 | NFR-012 (no identity in embeddings) | TEST-003 | CI-enforced static check passes | Backend |
| VG-025 | NFR-014/NFR-015 (retention + legal hold) | TEST-011, TEST-012 | Physical delete + freeze semantics correct; both cache layers correctly invalidated on legal hold | Backend |
| VG-026 | NFR-025 (ACL cache TTL discipline) | Integration test per NFR-025's own acceptance criterion | Force-refresh on TTL expiry mandatory, verified | Backend |
| VG-027 | NFR-030/NFR-031 (VRAM admission control + burst visibility) | Manual burst-simulation test | `queue_depth` visible in widget UI; new-query admission gated on VRAM headroom | DevOps |
| VG-028 | Round 6 DEC-109 fix (NLI VRAM/CPU accounting) | `04-architecture.md` §4.2.2's corrected table | Design-time headroom figures internally consistent (5.7 GB cold / 1.7 GB warm); real measurement pending TASK-032 | Architect |
| VG-029 | Round 6 DEC-116 fix (answer-cache legal-hold invalidation) | TEST-012 | Answer-cache entries referencing a frozen document are evicted, not just KV-cache | Backend |
| VG-030 | Round 6 DEC-117 fix (`/ready` full-dependency check) | TEST-025, `06-api-contracts.md`'s `/ready` contract test | `/ready` aggregates all 10 backend services, not just `api/` | DevOps |
| VG-031 | REQ-037 (retention-state capture at ingest) | TEST-035 | `retention_state` correctly captured at ingest and enforced as a Qdrant filter at retrieval | Backend |
| VG-032 | REQ-043 (audit-pull NDJSON endpoint) | TEST-037 | NDJSON pull endpoint idempotent and correctly cursor-paginated across repeated pulls | Backend |
| VG-033 | NFR-033 (domain-specific span attributes, DEC-128) | TEST-038 | Trace carries the full domain-specific attribute set (retrieve/rerank/verify per-span + root-span version identifiers), values consistent with the same query's `audit_events` row, no raw content present | Backend |
| VG-034 | NFR-024 (cost-per-turn formula + eval-harness reporting, DEC-129) | TEST-039 | `cost_per_turn` metric matches the documented formula; golden-set eval report includes cost-per-turn mean/p95 | Backend/AI |
| VG-035 | NFR-028 (vLLM optimization flags, DEC-129) | TEST-040 | `vllm.config` introspection confirms flag values match the tier/VRAM-conditional rule at both floor and comfort tier, and under a simulated low-VRAM validation result | Backend |
| VG-036 | NFR-007 (restart-durability, DEC-129) | TASK-039 output | Previously-ingested document and previously-written `audit_events` row both intact and unchanged after `docker compose down && docker compose up` | DevOps |
| VG-037 | NFR-022 (per-rail latency budget, added 2026-07-16, DEC-147) | TEST-041 output | `safety_input` p95 ≤ 150ms; `safety_output` p95 ≤ 250ms; `policy/` additive overhead p95 ≤ 30ms, each measured via its own OTEL GenAI span | AI |
| VG-038 | REQ-010/NFR-009 (admin-scope JWT claims, TASK-040, added 2026-07-16, DEC-147) | TEST-042 output | A validly-signed, insufficiently-scoped JWT returns `403` on every admin-surface route; a correctly-scoped JWT and the admin API key both continue to work with no regression | Backend |
| VG-039 | DEC-065 (`chunk_id` determinism, added 2026-07-16, DEC-147) | TEST-004 | A fixed `(document_id, version_id, sequence)` tuple always produces the same `chunk_id`, confirmed across a re-run, not just a single computation | Backend |
| VG-040 | NFR-016 (ECM PDP circuit breaker, added 2026-07-16, DEC-147) | TEST-008 | Breaker opens under simulated 1s+ PDP latency; queries return `verification_unavailable`, never a silent skip; `pdp_breaker_state` observable | Backend |
| VG-041 | DEC-114 (compound-document ACL resolution, added 2026-07-16, DEC-147) | TEST-018 | `get_effective_acl(leaf_doc_id)` on a compound/virtual document correctly resolves to the root-node ACL, not empty/default | Backend |
| VG-042 | DEC-113 (`security_label`-only ACL propagation, added 2026-07-16, DEC-147) | TEST-019 | A `security_label`-only change fires `acl_changed` and refreshes `chunks.security_label`; `allow_principals[]`/`deny_principals[]` unchanged | Backend |
| VG-043 | NFR-017 (rate limiting, TASK-042, added 2026-07-16, DEC-147) | TEST-028 | 100 QPS to a single token produces `429` responses with `Retry-After`; abuse alert emitted; a token under the limit is unaffected | Backend |
| VG-044 | `22-memory-context.md` (server-reconstructed history, added 2026-07-16, DEC-147) | TEST-030 | A fabricated client-supplied `history` field has zero influence on the actual assembled prompt (verified by inspecting the prompt itself, not just the response) | Backend/AI |
| VG-045 | NFR-006 (ingest throughput, TASK-009, added 2026-07-16, DEC-147) | TEST-033 | ≥ 100 pages/minute ingest throughput on reference hardware | Backend |
| VG-046 | NFR-027 (TEI rerank latency, added 2026-07-16, DEC-147) | TEST-034 | p95 ≤ 100ms at top-K=50, ONNX Runtime backend | Backend |

**`VG-039`..`VG-046` added 2026-07-16 (second cross-model review R.15)**: 8 of the review's 12 named orphaned tests had no gate mechanism at all (neither a `VG-###` row nor a Release Gates entry) — closed above. The other 3 (`TEST-015`, `TEST-016`, `TEST-017`) are **not** newly gated here — they were already release-blocking via the Release Gates table below (`DEC-092`'s and `DEC-109`'s rows), just not cross-referenced by `TEST-###` id, which the Release Gates table itself now states explicitly. Not a gap in gate *coverage*, only in this file's own internal cross-referencing.

**`VG-037`/`VG-038` added 2026-07-16 (second cross-model review R.3)**: `TEST-041` (per-rail latency, added 2026-07-13 review R.17) had existed in `11-test-plan.md` since that review but was never given a verification gate here — an orphaned test with no release-gate consequence. `TASK-040` (admin-scope JWT claims, added same day as this fix) had neither a `TEST-###` nor a `VG-###` at all — `11-test-plan.md` gains `TEST-042` alongside this row.

## Demo Script

Matches the actual MVP demo scenario stated in `confirmed-context.md` §6 ("a working end-to-end demo that a CCM/ECM vendor evaluator can install, ingest a sample corpus, ask questions, and see verifiable citations + refusals") and `01-product-brief.md` §9.3's adoption metrics.

### Script

1. **Install** (target: ≤30 min, REQ-011): vendor evaluator runs `docker compose up` against the offline model bundle; polls `/ready` until `ready: true` (full-dependency check, DEC-117)
2. **Ingest** (target: ≤60s for a 100-page PDF, REQ-002): upload the sample CCM-style corpus (REQ-014); poll ingest status to `ready`
3. **Ask a grounded question**: submit a query with a known answer in the corpus; observe a cited answer with a verified citation, click through to the source span
4. **Ask an out-of-corpus question**: submit a query with no answer in the corpus; observe a `no_recall` refusal with up to 3 suggested neighboring documents (REQ-006a)
5. **Ask an ambiguous/adversarial question**: submit a deliberately ambiguous or borderline-grounded query; observe either a correctly-hedged answer or a `low_grounding` refusal, not a fabricated confident answer
6. **Attempt a prompt-injection query**: submit a known jailbreak-pattern query; observe a `policy_blocked` refusal
7. **Show the audit trail**: pull `GET /v1/admin/audit` for the session; show the complete `context_fingerprint` for one of the above turns, demonstrating "which exact model/prompt/threshold produced this answer" is answerable
8. **Show a refusal-threshold change taking effect without restart**: adjust `PUT /v1/admin/config/thresholds`; show the next query reflects the new threshold within the same session (NFR-010)

### Success Criteria (Per `01-product-brief.md` §9.3, Corrected Per DEC-111)

- ≥ 1 successful first-touch demo install
- 100% citation-hit-rate on the 150-200 prompt full golden set (50-prompt smoke subset preserved as the CI fast-feedback ring) — corrected per DEC-111 from the stale "50-question" figure

## Release Gates

| Gate | Condition | Blocking? |
|---|---|---|
| All VG-### rows above pass | Every gate's evidence collected and reviewed | Yes — no release without full VG-### pass |
| Air-gap test 100% pass | VG-012 | Yes |
| No Critical-severity observability alert active | Per `08-observability-logs.md`'s Alerts table | Yes |
| DEC-092 safety-rail accuracy-preservation check on file | Before any safety-rail quantization/adapter ships as default (evidence: `TEST-015`'s documented F1/recall comparison — cross-referenced here 2026-07-16, DEC-147, second cross-model review R.15; this row was always the release-blocking mechanism for `TEST-015`, just not previously cited by test id) | Yes, specifically for that class of change |
| DEC-109 quality gate satisfied | Before any generation/embedding-model swap ships as default (evidence: `TEST-016`'s embedding blue/green check, `TEST-017`'s generation-model swap check — cross-referenced here 2026-07-16, DEC-147, same review) | Yes, specifically for that class of change |
| Golden-set full ring passes DEC-017 thresholds | Per `10-build-plan.md` TASK-029 | Yes |
| Hardware-validation rig run recorded | TASK-032, updates `09-deployment-ops.md`'s measured-VRAM table | Recommended before first customer install, not a hard release blocker for an internal/demo-only release |

## Required Evidence

Every VG-### row's "Evidence Required" column above is the concrete artifact (test output, log, timed walkthrough) that must exist and be reviewable before that gate is marked passed — not a verbal confirmation. Evidence is retained (test run logs, timed walkthrough recordings) as part of the release record, consistent with this product's own audit-ready positioning being applied reflexively to its own release process.

## Production Readiness Checklist

- [ ] All 30 VG-### gates pass
- [ ] `09-deployment-ops.md`'s pre-install verification script (driver matrix + `gpu-check`) runs clean on the target hardware
- [ ] Backup/restore drill completed at least once (per `09-deployment-ops.md`'s recommended cadence) before the first real customer install, not just tested in the abstract
- [ ] `audit_events` capacity-planning estimate reviewed for the specific customer's expected query volume (DEC-109's capacity-planning note, applied per-install)
- [ ] CDC transport mode (webhook vs. poll-only) confirmed with the customer's network-segmentation posture during the pre-install security review (`04-architecture.md` §7B.0's procurement-risk note)
- [ ] Encryption-at-rest qualification question raised and answered (`09-deployment-ops.md`'s Runbook: Encryption-at-Rest)

## Rollback Verification

Cross-references `09-deployment-ops.md`'s Rollback Strategy section — this section states the verification bar, not the mechanics:

- [ ] Generation-model rollback rehearsed at least once (not just designed) — confirm ≤10s adapter-pointer flip actually measured, not assumed
- [ ] Embedding-model rollback rehearsed — confirm ≤60s collection-pointer flip actually measured
- [ ] Whole-system rollback (bad release → prior tagged image + existing volumes) rehearsed at least once in a non-production environment

## Observability Verification

- [ ] Every alert in `08-observability-logs.md`'s Alerts table has been manually triggered at least once (via `10-build-plan.md` TASK-028) and confirmed to actually fire, not just configured
- [ ] OTLP export verified against a real external collector (not just the default Postgres `otel_spans` sink), if the customer intends to use their own observability stack

## Security Verification

- [ ] TEST-027 through TEST-031 (security test suite, `11-test-plan.md`) all pass
- [ ] Widget CSP/postMessage scan (TEST-029) achieved grade B+ or better
- [ ] JWT algorithm whitelist rejection verified against all 4 forbidden algorithms (`HS256`, `HS384`, `HS512`, `none`), not just spot-checked against one

## User Acceptance Verification

- [ ] The demo script above runs clean, end-to-end, without operator intervention beyond the scripted steps
- [ ] A vendor evaluator (or a stand-in reviewer playing that role) successfully completes the install-to-first-answer path using only the documented runbook (`09-deployment-ops.md`), with no undocumented tribal-knowledge steps required

## Dependencies

- `01-product-brief.md` §9 (success metrics this matrix verifies, including the DEC-111-corrected golden-set figure)
- `02-requirements.md` (every REQ/NFR this matrix traces to)
- `04-architecture.md`, `20-agent-behavior.md`, `23-evals-guardrails.md` (behavior source)
- `09-deployment-ops.md` (rollback/observability/security runbooks this file's checklists point to)
- `10-build-plan.md` (Phase 6's exit gate is this file)
- `11-test-plan.md` (every `TEST-###` referenced as evidence above)

## Decision References

DEC-006, DEC-042, DEC-088, DEC-090, DEC-091, DEC-092, DEC-096, DEC-105, DEC-109, DEC-111, DEC-113, DEC-114, DEC-116, DEC-117, DEC-128, DEC-129
