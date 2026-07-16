# 08 — Observability, Logs, and Alerts

> Stage 7 (`spec-writer`) deliverable. Expands `04-architecture.md` §12.3-§12.4's observability sketch into full log schema, metrics, traces, dashboards, alerts, and SLOs. Follows the OpenTelemetry GenAI semantic conventions already chosen at Stage 1 (`90-stage1-trend-research.md` §3.3) and pinned at Stage 4 (DEC-016, NFR-026).
>
> **Post-Stage-8 update (DEC-128, NFR-033, 2026-07-08)**: the span structure below originally carried only generic GenAI attributes, which support latency diagnosis but not accuracy diagnosis. Domain-specific attributes, an `nli_entailment_score` histogram, a reconciled sampling statement, and a trace-to-regression-test path were added — see the Span Structure, Metrics, and Traces sections below.
>
> **Scope-vs-capacity note (added 2026-07-13, cross-model review R.15)**: the alert routing, LCC-service-tier hooks, and on-call-style severity classification in this file are production-service-grade, sized for the full-team scope DEC-081 committed to keeping rather than cutting for the solo path — see `confirmed-context.md` RISK-007 for the explicit trade-off (same scope, longer solo timeline, not a scope cut) and its acknowledged open question of whether solo capacity can sustainably operate this complexity regardless of timeline. Not every alert/runbook here needs a real on-call rotation before a first demo.

## Plain-English Summary

Three separate things are easy to conflate and must stay separate: operational logs (for debugging, short retention, no sensitive content), audit events (the compliance-critical, forever-retained record of every query), and traces (per-query timing breakdown for performance diagnosis, short retention). This file defines all three plus the alerts that page an operator when something is actually wrong versus merely worth noting.

## Observability Goals

- Diagnose a slow or failing query without reading `audit_events` (which is content-sensitive and should not be the default debugging tool)
- Prove the NFR-005 latency SLO is being met (or catch when it isn't) via traces, not guesswork
- Alert an operator on the conditions that actually predict a bad demo or a compliance gap — not alert-fatigue noise
- Give a vendor's own SRE team a forwarding path (OTLP exporter) to their existing Datadog/Grafana/Splunk stack without requiring GroundedDocs-specific tooling

## SLOs and SLIs

| SLO | SLI | Target | Source |
|---|---|---|---|
| Query latency | p95 end-to-end latency, warm-cache | ≤ 8s (comfortably ≤ 7,190ms per the §7B.12 budget, ~810ms headroom — corrected 2026-07-13, cross-model review R.18: rerank line item was 150ms, didn't match NFR-027's 100ms) | NFR-005 |
| Query latency, cold-cache | p95 end-to-end latency, cold-cache (first query of a session) | ≤ 8s (≤ 7,840ms per DEC-097 + R.18 correction, ~160ms headroom — thin, flagged as a risk to revisit if retrieval-rail scan cost grows) | NFR-005, DEC-097 |
| Citation hit-rate | % of emitted citations landing in the current turn's `reranked_set` | 100% (hard gate, not a target — any miss is a `low_grounding` refusal, not a metric to average) | NFR-004 |
| Refusal rate on golden no-answer set | % correctly refused | ≥ 95% (MVP), ≥ 98% (V2 target) | `01-product-brief.md` §9.1 |
| Ingest throughput | Pages/minute on reference hardware | ≥ 100 | NFR-006 |
| Install time | Cold-start to `/ready = true` | ≤ 30 minutes | REQ-011 |
| Air-gap compatibility | % of eval suite passing with network namespace blocked | 100% | REQ-012 |
| Concurrency (warm-cache) | Sustained in-flight queries at SLO | 5-8 | NFR-005 (DEC-076 revision) |
| Concurrency (cold-cache floor) | Sustained in-flight queries at SLO | ≥ 2 | DEC-066 |
| Retention expiry latency (webhook path) | Event → physical delete | ≤ 60s | NFR-014 |
| Retention expiry latency (re-poll fallback) | Event → physical delete | ≤ 30 min | NFR-014 |
| Retention expiry latency (poll-only topology) | Event → physical delete | ≤ configured interval (default 30 min, recommended 5 min) + one poll-cycle jitter | NFR-032 |

## Structured Log Schema

Operational logs are distinct from `audit_events` (compliance record) and `otel_spans` (trace detail). Logs are for "what is the system doing right now," not "what did this user ask."

| Field | Type | Required | Description | Example | Privacy Notes |
|---|---|---|---|---|---|
| `timestamp` | ISO8601 | Yes | — | `2026-07-06T09:00:00.123Z` | — |
| `level` | Enum: `DEBUG`, `INFO`, `WARN`, `ERROR` | Yes | — | `INFO` | — |
| `service` | String | Yes | Which container/module emitted this (e.g. `api`, `ingest`, `cdc`) | `api` | — |
| `request_id` | String, nullable | No | Correlates to the OTel trace span for this request | `req-9f21...` | — |
| `conversation_id` | String, nullable | No | Present on query-path logs; safe at INFO because it's an opaque ID, not content | `c-8f21` | Safe at INFO |
| `message` | String | Yes | Human-readable log line | `"retrieve/ completed"` | Must not contain query text, chunk text, or answer text at INFO |
| `latency_ms` | Integer, nullable | No | Per-node latency, when applicable | `240` | — |
| `status` | String, nullable | No | e.g. `success`, `timeout`, `error` | `success` | — |
| `payload_size_bytes` | Integer, nullable | No | Size, not content | `4096` | — |

**NFR-008 discipline, made concrete**: `query`, retrieved chunk content, and `answer` text may appear **only** at `DEBUG` level, and `DEBUG` is disabled by default in production installs (enabling it is an explicit, documented, temporary debugging action — not a standing configuration). `audit_events` (Postgres, separate store) is the **only** persistent, default-on store of query/answer content — this is a deliberate single point of truth, not an oversight that operational logs also happen to lack this content.

## Audit Events

Full schema is `05-data-model.md`'s `audit_events` entity — not duplicated here. This section covers the *observability-facing* view of that data: how an operator or auditor queries it, not its storage.

- **Query surface**: `GET /v1/admin/audit` (paginated, filtered by `from`/`to`/`user_id`) for interactive review; `GET /v1/admin/audit/events` (NDJSON, cursor-paginated) for vendor SIEM bulk pull (REQ-043)
- **What audit events are not**: a performance-debugging tool. An operator diagnosing "why was this query slow" should reach for traces (`otel_spans`) first; audit events answer "what happened," not "why was it slow"
- **Retention**: forever, append-only (DEC-070) — distinct from every other observability artifact in this file, all of which have bounded retention

## Metrics

| Metric | Type | Labels | Source |
|---|---|---|---|
| `gen_ai.request.duration` | Histogram | `node_name`, `model_adapter` | Per-node latency, OTel GenAI convention |
| `gen_ai.usage.prompt_tokens` / `gen_ai.usage.completion_tokens` | Counter | `model_adapter`, `model_version` | NFR-026 |
| `retrieval_top1_score` | Histogram | — | `retrieve/` node |
| `nli_entailment_score` | Histogram | `path` (`mechanical_fast_path`/`nli_slow_path`) | `verify/` node (NFR-033, DEC-128) — the score *distribution* behind `citation_hit_rate`'s pass/fail rate; `23-evals-guardrails.md` §7's threshold-tuning runbook reads this to see how much margin passing queries have, not just whether they passed |
| `citation_hit_rate` | Gauge (rolling window) | — | `verify/` node; should read 100% at all times — any deviation is itself alertable, not just a dashboard number |
| `refusal_rate` | Gauge (rolling window) | `refusal_reason` | `verify/`/`api/` |
| `cache_hit_ratio` | Gauge | `cache_type` (`prompt`, `answer`, `acl`, `embedding`) | `cache/`, per DEC-076 |
| `queue_depth` | Gauge | — | `api/` concurrency admission (DEC-066, NFR-030/031) |
| `vram_headroom_gb` | Gauge | `tier` (`floor`, `comfort`) | NFR-030 admission-control metric |
| `pdp_breaker_state` | Enum gauge: `closed`, `open`, `half_open` | — | NFR-016 ECM PDP circuit breaker |
| `cost_per_turn` | Histogram | `model_adapter` | NFR-024, DEC-129 — formula below |
| `webhook_delivery_health` | Gauge: healthy/degraded | — | §7B.5, feeds NFR-016 alert |
| `poll_cycle_success` | Counter (success/failure) | `cdc_transport_mode` | NFR-032 poll-only topology |

### `cost_per_turn` formula (NFR-024, DEC-129)

On-prem open-weights serving has no per-token API price to bill against — NFR-024's ¥0.10/turn ceiling existed since Stage 4 with no computation methodology behind it, which meant the ceiling was unimplementable. This is a projected compute-cost estimate, not a billed cost (the product does not meter or bill customer compute, per `09-deployment-ops.md`):

```
cost_per_turn = gpu_hourly_rate × (gen_ai.request.duration / 3600)
```

- `gen_ai.request.duration` is the root span's total wall-clock duration, already captured per NFR-026 — no new instrumentation needed, this formula only adds a multiplication step at emission time in `TASK-027`
- `gpu_hourly_rate` is an admin-configurable value, defaulting to the reference floor-tier GPU's cloud-rental rate already cited in this spec set (`13-decision-log.md` DEC-068: RunPod 4090-spot ≈ $0.45/h) as a proxy for the amortized cost of customer-owned hardware — a customer running comfort-tier or owned (not rented) hardware should override the default with their own rate for an accurate figure, but the default gives every install a non-zero, defensible starting number rather than requiring configuration before the metric means anything
- Sanity check against the ceiling: at the reference rate and the NFR-005 ≤8s latency budget, a turn costs ≈ ¥0.007 — comfortably under the ¥0.10 ceiling, confirming the ceiling was never intended to bind under normal operation; it exists to catch a pathological case (e.g. a runaway generation loop or a misconfigured serving tier), not to constrain routine cost

## Traces

Per the OTel GenAI semantic conventions (NFR-026), already specified in `04-architecture.md` §12.3 — this section states the concrete span tree, not a re-derivation.

### Span Structure (per query)

```
gen_ai.request (root span, request_id)
├── safety_input (parallel with retrieve, DEC-082)
├── retrieve
│   └── idp_resolve (sub-span, IdP/PDP principal resolution)
├── acl (Layer 2 join: batch_check_access, get_retention_state, retrieval-rail scan)
├── rerank
├── generate
├── safety_output
├── verify
│   ├── mechanical_fast_path
│   └── nli_slow_path (only present if mechanical passed)
└── audit
```

Required attributes per span: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`, `gen_ai.response.finish_reasons` (NFR-026). Feedback-edge invocations (V2) nest as child spans of `verify` carrying a `gen_ai.iteration` attribute.

**Domain-specific attributes (NFR-033, DEC-128)** — added because the generic GenAI set above lets a trace diagnose *latency* but says nothing about *why an answer's quality was off*, which previously forced every accuracy investigation into `audit_events` even though that store's stated job is "what happened," not "why":

| Span | Attribute | Purpose |
|---|---|---|
| `retrieve` | `candidate_count`, `retrieval_top1_score` | How many candidates came back and how strong the top match was, without opening `audit_events` |
| `rerank` | `rerank_score_delta` (top-1 score before vs. after rerank), `top_k` | Whether reranking materially changed the ranking, and at what candidate-set size |
| `verify` | `mechanical_fast_path`/`nli_slow_path` verdict; per-claim NLI entailment score array (present only when `nli_slow_path` ran) | Localizes a `low_grounding` refusal to a specific claim and score, not just a binary pass/fail |
| `safety_input` | `safety_input_flagged` (bool), `safety_input_categories` (list, e.g. `["jailbreak", "prompt_injection"]`), `safety_input_confidence` (0-1) | **Added 2026-07-13, cross-model review R.13.** Localizes a `policy_blocked` refusal to the input rail specifically — which hazard category and how confident — without opening `audit_events`. Mirrors `SafetyVerdict`'s `flagged`/`categories`/`confidence` fields (`04-architecture.md` §4.3); `raw_response` stays audit-only, not on the span, consistent with this table's no-content-on-spans rule |
| `safety_output` | `safety_output_flagged` (bool), `safety_output_categories` (list, e.g. `["s1_violence", "s4_hate"]`), `safety_output_confidence` (0-1) | **Added 2026-07-13, cross-model review R.13.** Same, for the output rail |
| root `gen_ai.request` | `prompt_version`, `embedding_model_version`, `reranker_model_version`, `safety_input_version`, `safety_output_version` | Mirrors `audit_events.context_fingerprint` (DEC-060/DEC-089) so "did quality change after a release" is answerable from traces alone, without cross-referencing content-bearing audit records |

All of these are scores, counts, or version strings — never raw query/chunk/answer text. See Privacy Rules below for why this doesn't reopen the no-content-in-traces rule.

### Storage and Export

- **Default**: persisted to Postgres `otel_spans` (`07-database.md`), no separate observability stack required for MVP
- **Sampling: 100% of queries at MVP (DEC-128), not a persistence-time sample.** Every query's trace is pullable by `request_id` — required for the Incident Investigation examples below to hold in general, not just for a sampled subset. This is distinct from the smaller sample of *already-persisted* traces pulled into weekly human quality review (`23-evals-guardrails.md` §2.2, 5-10% of production queries) — that sampling happens downstream of persistence, for review/golden-set-candidate purposes, not to decide whether a trace exists at all. **Re-evaluation trigger**: if sustained concurrency grows past the DEC-066 cold-cache floor / NFR-005 warm-cache range this MVP posture assumes, revisit whether 100% persistence remains viable or whether persistence-level sampling should be introduced.
- **Retention**: 30-90 days, admin-configurable (DEC-109) — explicitly shorter than and independent from `audit_events`'s forever retention
- **OTLP export**: configurable via `OTEL_EXPORTER_OTLP_ENDPOINT` env var; a customer's own Datadog/Grafana/Splunk collector receives the same span tree with no GroundedDocs-specific translation needed at the transport/protocol level, since the spans are already OTel-GenAI-conformant — the collector ingests and stores every attribute, standard and custom alike, with no export-side code needed. **Clarified 2026-07-16 (DEC-147, second cross-model review R.12)**: "no translation needed" is about ingestion, not visualization — NFR-033's domain-specific attributes (`retrieval_top1_score`, `nli_entailment_score`, etc.) arrive intact but won't have pre-built dashboard widgets in a customer's existing Datadog/Grafana setup; a customer wanting those attributes surfaced visually needs to build that dashboard configuration themselves (or use this product's own reference dashboards, `04-architecture.md` §12.4), the same as any product introducing custom OTel attributes to an existing observability pipeline
- **V2 dedicated tool**: Langfuse self-hosted was the original V2 pick (DEC-016); carries roadmap risk following ClickHouse's 2026-01 acquisition (§12.3). Named contingencies: Phoenix Arize, LangSmith, or OTEL-only with custom Grafana dashboards — no V2 commitment is made in this file beyond naming the contingency path, since the MVP default (Postgres `otel_spans` + OTLP export) does not depend on which V2 tool is eventually chosen

### Trace-to-Regression Promotion (MVP, DEC-128)

A production trace that reveals a genuine quality gap should be able to become a permanent regression test, not just a one-off diagnosis — this is standard practice for a system whose correctness is measured against a golden set rather than unit-tested line by line. `23-evals-guardrails.md` §2.2 already documents an automated version of this for the **V2 customer-specific golden set** (REQ-023): human-reviewed traces with disagreements promote automatically. MVP does not have that tooling yet, so it reuses an existing manual process instead of waiting for it: `23-evals-guardrails.md` §6's "Quarterly LCC review" already samples 50 production answers for manual grading — when that review turns up an answer that exposes a real gap in the standard golden set (not just a corpus-specific one-off), add it as a new smoke- or full-ring prompt, tagged with its source `request_id` so the originating trace stays traceable. No new build task or infrastructure is required; this is a documented step added to an already-scheduled review.

**MVP fallback for installations without an active LCC engagement (added 2026-07-13, cross-model review R.23)**: §6's "Quarterly LCC review" is titled an LCC-service activity without a stated tier, unlike the adjacent "Model upgrade (LCC Tier 3)" row — a self-hosted MVP install with no LCC engagement can't tell whether it applies to them. It doesn't need to: the promotion mechanism itself has no LCC dependency, only the *scheduled cadence* of sampling does. For installs without an LCC engagement, the operator runs `cli eval promote --from-traces <timerange>` manually (same CLI family as `cli eval run --suite golden`, REQ-013) to sample and review recent traces on their own schedule. The quarterly cadence is a recommendation that comes bundled with an LCC engagement, not a hard dependency of the promotion mechanism.

## Dashboards

| Dashboard | Primary audience | Key panels |
|---|---|---|
| Demo-readiness | Operator, pre-demo | `/ready` service breakdown, `queue_depth`, `vram_headroom_gb`, cache hit ratios (warm-up status before inviting evaluators) |
| Latency breakdown | Operator, ongoing | Per-node p50/p95/p99 latency (matches the §7B.12 line-item table), cold vs warm-cache split |
| Quality | Operator + LCC service | `citation_hit_rate` (should be a flat 100% line — any dip is a dashboard-visible incident), `refusal_rate` by class, RAGAS metrics trend from `eval_runs` |
| Compliance posture | Admin, periodic review | Retention-expiry latency distribution, legal-hold invalidation event count, ECM audit write-back failure rate |
| Cost | Operator + LCC service | `cost_per_turn` trend, per-model-adapter token usage |

## Alerts

| Alert | Signal | Threshold | Severity | Owner | Runbook |
|---|---|---|---|---|---|
| Citation hit-rate deviation | `citation_hit_rate` | Any value < 100% sustained over any 5-minute window | Critical | Operator | `09-deployment-ops.md` — this is not a tuning problem, it means the NFR-004 hard gate has a bug; treat as a code-red, not a threshold-tuning exercise |
| Queue depth sustained | `queue_depth > 0` | > 5 seconds | Warning | Operator | Check `vram_headroom_gb`; if near floor, this is expected admission-control behavior (NFR-030) during a burst — see the demo-facilitation staggering guidance in `09-deployment-ops.md` |
| VRAM headroom critical | `vram_headroom_gb` | < 0.5 GB sustained | Critical | Operator | New-query admission should already be gating on this per NFR-030; this alert catches the case where admission control itself is misconfigured |
| PDP circuit breaker open | `pdp_breaker_state = open` | Any occurrence | Critical | Operator | ECM PDP is unreachable/slow; queries are returning `verification_unavailable` — this is a customer-visible degradation, page immediately, not just log |
| Webhook delivery degraded | `webhook_delivery_health = degraded` | Sustained past the configured re-poll fallback threshold | Warning | Operator | Customer's retention SLA has temporarily degraded to the 30-min re-poll fallback (NFR-016); notify the customer if sustained |
| Poll cycle failures | `poll_cycle_success` failure streak | 3 consecutive failed poll cycles (poll-only topology) | Warning | Operator | ECM API may be unreachable or rate-limiting; check `09-deployment-ops.md`'s poll-only runbook |
| Refusal rate spike | `refusal_rate` | > 30% sustained over 1 hour of production traffic | Warning | Operator + LCC | Follow the customer onboarding runbook in `23-evals-guardrails.md` §7 (diagnosis steps by refusal-class cluster) |
| Cost ceiling breach | `cost_per_turn` p95 | Exceeds configured ceiling for 5 consecutive minutes | Warning | Operator | NFR-024 — observability-driven in MVP, not a hard runtime block |
| `audit_events` write failure | Any failed write to `audit_events` | Any occurrence | Critical | Operator | The one write this system must never silently drop — per §8.4, this must block/fail the request loudly, and this alert is the safety net if it doesn't |
| Legal-hold invalidation audit gap | Cache invalidation succeeds but `legal_hold_invalidation_events` write fails | Any occurrence | Critical | Operator | DEC-106/DEC-116's exact failure mode to guard against — silent success with no audit trail |
| `audit_events` capacity | Table size approaching configured storage ceiling | Admin-configured threshold (see `09-deployment-ops.md` capacity-planning runbook) | Warning | Operator | DEC-109 capacity-planning note — plan cold-archival before this becomes urgent |

## Runbook Links

Each alert above cross-references `09-deployment-ops.md` (this phase) for the concrete operational runbook — this file states *what* to alert on and *why it matters*; `09-deployment-ops.md` states the step-by-step operator response.

## Privacy Rules for Logs

- Operational logs (this file's log schema): query/chunk/answer content forbidden above `DEBUG`; `DEBUG` disabled by default in production
- Traces (`otel_spans`): span attributes follow the OTel GenAI convention's own field set (token counts, model identifiers, latencies) plus the domain-specific set added by NFR-033/DEC-128 (candidate counts, rerank score deltas, per-claim NLI scores, mechanical/nli_slow_path verdict, version identifiers) — none of which include raw query/answer text; a trace should never need to carry content, since content lives in `audit_events`
- Dashboards: no dashboard in this file displays raw query or answer text; the Quality dashboard's `refusal_rate by class` is a count, not a content sample

## Incident Investigation Examples

**Example 1 — "A customer reports slow answers today."**
1. Check the Latency Breakdown dashboard for the affected time window — is it cold-cache (session-start) or warm-cache (sustained)?
2. If warm-cache is slow, check `cache_hit_ratio` — did a cache-invalidating event (model swap, ACL mass-change) reset the warm-cache state recently?
3. Pull the specific trace via `request_id` (if the customer can supply the `audit_id` from their transcript, cross-reference to find the matching `request_id`) — inspect the per-node span breakdown against the §7B.12 budget table to find which node exceeded its line item

**Example 2 — "Citation hit-rate dashboard shows 99.7%, not 100%."**
This should not happen — treat as Critical per the alert table above, not as "close enough." Pull the specific `audit_events` rows where `verification_result.mechanical_fast_path` failed; since NFR-004 is a hard gate enforced in code, a sub-100% reading over any real time window indicates either (a) a code regression in the mechanical check, or (b) a measurement/dashboard bug undercounting refused turns as failures. Escalate to architecture review, not threshold retuning — this is explicitly not a `23-evals-guardrails.md` §7 tuning-lever scenario (that runbook is for `low_grounding`/`no_recall` clusters, not for the citation hit-rate hard gate itself).

**Example 3 — "Refusal rate crept up after last week's deploy — which claim is failing, and was it the deploy?"** (NFR-033, DEC-128)
1. Pull a handful of the newly-refused queries' traces via `request_id` — no need to open `audit_events` first
2. **Branch on refusal category first (added 2026-07-13, cross-model review R.13 — this step previously assumed every refusal was grounding-related, which is false for `policy_blocked`)**: check whether `safety_input_flagged` or `safety_output_flagged` is `true` on the trace. If either is `true`, the refusal is `policy_blocked`, not `low_grounding` — inspect that rail's `categories`/`confidence` attributes and stop here; a deploy that changed `safety_input_version`/`safety_output_version` (root span) is the first suspect, not the NLI threshold. If neither is flagged, continue to step 3 as a grounding-related (`low_grounding`) refusal
3. Check the root span's `prompt_version`/`embedding_model_version`/`reranker_model_version` against last week's known-good values — if any changed, that's the first suspect, confirmed without a separate deploy-log cross-reference
4. On the `verify` span, read the per-claim NLI scores directly: scores clustered just under the 0.5 threshold (e.g. 0.3-0.49) point to a miscalibrated threshold — the same diagnosis `23-evals-guardrails.md` §7.1 step 4 already describes, now reachable from the trace instead of requiring a manual `audit_events` sample
5. Cross-check against the `nli_entailment_score` histogram (Metrics) for the affected time window — a visible leftward shift in the whole distribution (not just individual borderline cases) points to a real regression, not query-mix noise

## Dependencies

- `04-architecture.md` §12.1-§12.5 (refusal policy, prompt-injection defense, observability sketch, logging discipline, threat model — this file expands §12.3/§12.4 specifically)
- `90-stage1-trend-research.md` §3.3 (OTel GenAI convention adoption rationale)
- `92a-stage5r2-benchmark.md` §Topic 6 (the 2026 mature-practice span-attribute research this file's domain-specific attributes, NFR-033/DEC-128, close the gap against)
- `05-data-model.md` (`audit_events`, `otel_spans`, `legal_hold_invalidation_events` entities)
- `07-database.md` (physical retention mechanics for `otel_spans` vs `audit_events`; `otel_spans.attributes` is JSONB, so the new domain-specific attributes require no schema migration)
- `09-deployment-ops.md` (this phase — concrete runbooks this file's alerts point to)
- `23-evals-guardrails.md` §2.2 (sampling reconciliation), §6 (Trace-to-Regression Promotion), §7 (`nli_entailment_score` histogram feeding the threshold-tuning runbook)
- `13-decision-log.md` DEC-016, DEC-042, DEC-060, DEC-063, DEC-066, DEC-068 (`cost_per_turn` GPU-rate reference), DEC-070, DEC-076, DEC-082, DEC-096, DEC-097, DEC-102, DEC-106, DEC-109, DEC-116, DEC-128, DEC-129

## Decision References

DEC-016, DEC-042, DEC-060, DEC-063, DEC-066, DEC-068, DEC-070, DEC-076, DEC-082, DEC-096, DEC-097, DEC-102, DEC-106, DEC-109, DEC-116, DEC-128, DEC-129
