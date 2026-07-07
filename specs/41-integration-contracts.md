# 41 — Integration Contracts (External Systems)

> Stage 7 (`spec-writer`) deliverable. Consolidates the `ECMAdapter` contract, currently spread across `04-architecture.md` §7B's 13 subsections, into one vendor-integrator-facing document. This file cross-references §7B rather than copy-pasting it wholesale — the goal is a document a CCM/ECM vendor's own integration engineer can read to build or evaluate an adapter, without needing to read all of §7B's architecture-review history.

## Plain-English Summary

GroundedDocs never reimplements a customer's identity/ACL/retention system — it federates to it through one interface, `ECMAdapter`. This file is the contract that interface promises: what methods a vendor must implement, what GroundedDocs guarantees it will (and will never) do with the data those methods return, and the two supported transport modes for keeping GroundedDocs's local copy in sync.

## External Systems

| System class | Examples | Integration shape |
|---|---|---|
| ECM/CCM identity + ACL provider | Documentum, OpenText, M-Files, Hyland Alfresco, SharePoint/Graph | `ECMAdapter` interface (this file) |
| Identity provider (IdP) | Any OIDC-compliant IdP | `OIDCAdapter` (identity-only component of `ECMAdapter`) |
| No-ECM / self-contained demo | GroundedDocs's own Postgres `users`/`documents.acl` tables | `LocalAdapter` (reference implementation, not a real external system) |

**MVP reference implementations**: `LocalAdapter` + `OIDCAdapter` (both MVP). **V2 vendor adapters**: `DocumentumAdapter`, `OpenTextAdapter` (V2-α priority, DEC-050), `MFilesAdapter`, `SharePointAdapter`, `HylandAlfrescoAdapter` (V2-β). **V3**: Partner Adapter SDK (REQ-042) for community/partner-built adapters targeting regional CCM/ECM vendors.

## Auth Model

| Layer | Mechanism | Notes |
|---|---|---|
| End-user identity → GroundedDocs | JWT bearer (RS256/ES256/EdDSA only; `HS*`/`none` rejected, DEC-048/DEC-061) or admin API key | `06-api-contracts.md`'s auth section is the canonical spec; this file adds the ECM-federation dimension below |
| GroundedDocs → ECM (Layer 2 live RPC) | Vendor-adapter-specific (typically a service account or OAuth client credentials grant configured at install time) | Each adapter implementation owns its own ECM-side auth; GroundedDocs's `ECMAdapter` interface abstracts over this — the interface consumer never sees vendor-specific auth details |
| JWKS key distribution | Online: pulled from customer IdP at startup, refreshed per `Cache-Control: max-age`. Air-gap: static pre-imported bundle (DEC-062), manual rotation runbook (`09-deployment-ops.md`) | DEC-048, DEC-062 |
| Federated identity mapping | `map_external_user(external_id, context) -> ecm_user_id` | MVP default is 1:1 pass-through; vendor adapters override when the end-user identity at the vendor portal does not equal the ECM-internal `user_id` (a common real-world pattern: service-account + user-context propagation) |

## The `ECMAdapter` Contract

This is the single interface every vendor integration implements. Full method-by-method rationale lives in `04-architecture.md` §7B.10 — this table is the contract surface a vendor integrator needs, consolidated:

| Method | Called | Purpose | MVP-required? |
|---|---|---|---|
| `resolve_principals(token, user_id) -> EffectivePrincipals` | Per request (cached, 60s TTL) | Identity resolution — "who is asking" | Yes |
| `map_external_user(external_id, context) -> ecm_user_id` | Per request | Federated identity mapping when vendor-portal identity ≠ ECM-internal identity; MVP default is pass-through | Yes (as pass-through default; override is adapter-specific) |
| `get_effective_acl(doc_id) -> ACL` | At ingest + on CDC `acl_changed` | Layer 1 sync source — denormalized effective principal set, deny overrides, security label, retention state | Yes |
| `batch_check_access(user, doc_ids) -> dict[doc_id, bool]` | Per query (Layer 2 JIT trim, batched — 1-2 RPC per query, not per-chunk) | Live authoritative access re-check | Yes |
| `get_retention_state(doc_ids) -> dict[doc_id, RetentionState]` | Per query, alongside `batch_check_access` | Live retention re-check (catches lag between Layer 1 sync and current ECM state) | Yes |
| `write_audit_access(user, doc_ids, session_id, intent, retrieved_at, rag_audit_id) -> None` | Per query, async best-effort | ECM-side audit write-back; `intent ∈ {"granted", "denied"}` — both paths written (DEC-064) | Yes |
| `subscribe_changes(handler) -> Subscription` | Once, at CDC startup | Push-style CDC transport (webhook mode) | Conditionally — required only when `cdc_transport_mode = webhook` |
| `poll_changes(cursor: str \| None) -> tuple[list[Event], str]` | On the configured poll interval | Pull-style CDC transport (poll-only mode); cursor is opaque, adapter-defined (change-log sequence number or timestamp watermark) | Conditionally — **mandatory for any adapter offered to a poll-only customer** (DEC-108); `subscribe_changes` alone is not sufficient for a poll-only install |
| `write_metadata(doc_id, key, value) -> None` | V2 roadmap | Metadata write-back (e.g. "cited by AI N times" tags) | No — V2 only |

### Compound/Virtual Document ACL Resolution (DEC-114)

A vendor adapter implementing `get_effective_acl(leaf_doc_id)` against an ECM with compound/virtual document structures (Documentum virtual documents, OpenText compound documents) **is responsible for resolving to the correct ACL-authority node internally** — if the ECM stores the ACL only at a virtual-document root, the adapter must walk to that root and return the leaf's fully-resolved effective ACL. GroundedDocs's calling code (`ingest/`, `acl/`) always passes a leaf `doc_id` and always expects a fully-resolved ACL back; it performs no tree-walking itself. This is a contract clarification (Round 6, DEC-114) closing an ambiguity that would otherwise surface for the first time during `DocumentumAdapter`/`OpenTextAdapter` (V2-α) implementation.

### `security_label`-Only Change Events (DEC-113)

`acl_changed(doc_id)` must fire for a standalone classification-label change (e.g. `confidential` → `internal`) even when `allow_principals[]`/`deny_principals[]` are unchanged — vendor adapters must not assume `acl_changed` is only for principal-set changes. `get_effective_acl()`'s response payload already includes `security_label`, so the existing re-call-and-refresh mechanism handles this once the adapter correctly fires the event for label-only changes.

## Two-Layer JIT Authorization Pattern (Vendor-Facing Summary)

Full rationale is `04-architecture.md` §7B.1-§7B.4 — this is the vendor-integrator-facing summary of what your adapter's methods are actually protecting:

1. **Layer 1 (Sync)**: at ingest, `get_effective_acl(doc_id)` populates a denormalized ACL payload on every chunk in the vector store. Query-time filtering happens against this cached payload — fast, but potentially stale
2. **Layer 2 (JIT live RPC)**: after retrieval, `batch_check_access` + `get_retention_state` re-verify against your ECM's live, authoritative state — 1-2 RPCs per query (batched across the distinct documents in the retrieved set), not per-chunk. This catches ACL/retention changes that happened after the last sync
3. **Why both layers**: pure live-RPC-per-chunk would mean 50 RPCs per query (your ECM's ACL engine is very unlikely to be designed for that fan-out at sub-second latency); pure sync-only would mean a user offboarded five minutes ago could still see content their access was just revoked from. Two layers is the industry-consensus pattern (Glean, Microsoft Graph Connectors, AWS Q Business, Vectara all use variants of this) — your adapter is not being asked to implement something unusual

**What your adapter is never asked to do**: reimplement your ECM's ACL evaluation logic. GroundedDocs treats your ECM as the sole authoritative source of truth (federation pattern, DEC-045) — the adapter's job is to expose that authority through the contract above, not to duplicate its evaluation rules.

## CDC Transport Modes

Both are first-class MVP-supported topologies (DEC-102) — an adapter should be built to support whichever your customer's network posture requires, ideally both.

| Mode | Direction | When to use | Adapter methods required |
|---|---|---|---|
| **Webhook** | ECM → GroundedDocs (inbound push) | Default when network segmentation allows an inbound listener reachable from the ECM | `subscribe_changes(handler)` |
| **Poll-only** | GroundedDocs → ECM (outbound pull only) | Customer network policy prohibits any inbound listener reachable from the ECM's zone (common in AU/NZ financial/public-sector "AI workload zone" segmentation, per `04-architecture.md` §7B.0's procurement-risk note) | `poll_changes(cursor)` — **mandatory**, not optional, for any adapter offered to a poll-only customer (DEC-108) |

Both modes carry the same event taxonomy: `document_created`, `acl_changed`, `version_added`, `version_deleted`, `document_deleted`, `retention_expired`, `legal_hold_added`, `legal_hold_released` (§7B.5). Poll-only mode's interval is admin-configurable (default 30 min, recommended 5 min where the ECM's API rate limits allow, NFR-032) — this is the accepted SLA for that topology, not a degraded state.

## SLAs and Rate Limits

| SLA | Value | Owner |
|---|---|---|
| Retention-expiry propagation, webhook path | ≤ 60s end-to-end | Vendor adapter's webhook delivery + GroundedDocs's processing, combined (NFR-014) |
| Retention-expiry propagation, re-poll fallback | ≤ 30 min | Same, when webhook delivery unexpectedly fails on a webhook-topology install |
| Retention-expiry propagation, poll-only topology | ≤ configured interval + one poll-cycle jitter (default 30 min, recommended 5 min) | This is a deliberately-selected SLA, not a fallback (NFR-032) |
| `batch_check_access` / `get_retention_state` RPC latency | ≤ 200 ms combined (§7B.12 budget line item) | Vendor adapter's ECM-side RPC implementation — this is the number your adapter needs to hit for GroundedDocs's overall NFR-005 latency SLO to hold |
| ECM PDP circuit breaker threshold | 500 ms default, configurable (DEC-063) | If your adapter's RPC exceeds this repeatedly, the breaker trips and queries return `verification_unavailable` rather than silently skipping verification — this is GroundedDocs's protection against a slow adapter, not a punitive measure |
| Rate limits your adapter may need to respect | Vendor-ECM-API-specific — not a GroundedDocs-imposed limit | Document your ECM's own API rate limits in your adapter's own integration notes; GroundedDocs's poll-only interval recommendation (5 min) is explicitly conditioned on "where the ECM's API rate limits allow it" |

## Failure Handling

| Failure | GroundedDocs behavior | What this means for your adapter |
|---|---|---|
| `batch_check_access`/`get_retention_state` timeout or repeated failure | Circuit breaker trips (DEC-063); queries return `verification_unavailable`, never a silent skip | Your adapter should fail fast and clearly (timeout, not a hang) so the breaker can trip promptly rather than stacking up slow requests |
| Webhook delivery failure | Falls back to 30-min re-poll automatically (DEC-051/056); an ops alert fires if sustained (NFR-016) | Your adapter's webhook sender should retry with reasonable backoff on its own side too, but GroundedDocs does not depend on that — the re-poll fallback is the safety net |
| `write_audit_access` failure | Async best-effort with exponential-backoff retry; persistent failure surfaces as an ops alert, never blocks the user-facing query response (NFR-013, DEC-047) | Your adapter's audit write-back endpoint being briefly unavailable does not degrade query latency — but persistent failure is visible to the customer's ops team, so don't treat this as "safe to ignore forever" |
| Adapter returns malformed/unexpected data from any contract method | Typed exception, surfaced as `verification_unavailable` refusal with the exception trace captured in audit (§5.1.1's illegal-transitions handling, extended here) | Adapters should validate their own outputs against the typed contract (`EffectivePrincipals`, `ACL`, `RetentionState` shapes) before returning — a malformed response degrades the user experience via refusal, which is safe but not ideal |

## Retry and Idempotency

- CDC events (both transports) carry an idempotency key (`event_id` + `source_timestamp`); GroundedDocs dedups within a 7-day window (RC-T8-01) — your adapter's webhook sender or poll response **may safely redeliver** an event without GroundedDocs double-processing it
- `write_audit_access` retries with exponential backoff on the GroundedDocs side — your adapter's audit endpoint should itself be idempotent per `rag_audit_id` if practical, though this is a recommendation, not a hard contract requirement, since GroundedDocs's retry uses the same `rag_audit_id` each time

## Monitoring

Vendor integrators should expect and can rely on the following GroundedDocs-side observable signals (full detail in `08-observability-logs.md`) as the integration health surface:

- `pdp_breaker_state` (closed/open/half_open) — direct signal of your adapter's RPC health as seen from GroundedDocs
- `webhook_delivery_health` — signal of whether your webhook transport is delivering within SLA
- `poll_cycle_success` — signal of whether your poll-only transport is succeeding
- Reconciliation-crawl ops alerts (DEC-090) — surfaces drift between your ECM's document inventory and GroundedDocs's `documents` table, which can indicate a missed CDC event on your adapter's side

## Vendor Risks

| Risk | Mitigation |
|---|---|
| Per-vendor adapter maintenance ceiling (RISK-018) — each adapter is non-trivial code; solo capacity caps at ~3 actively-supported vendors | Partner pattern (DEC-029 L2/L3); Partner Adapter SDK (REQ-042, V3) lets community/customer-side developers extend beyond GroundedDocs's own maintained set |
| ECM-side `get_effective_acl()` endpoint doesn't exist for a given vendor | Reference Python sidecar shipped as fallback (DEC-049), with explicit "will drift" warnings — not the recommended path, an escape hatch |
| ACL inheritance semantics differ by vendor (union vs. replace) | Each adapter implementation encodes its own vendor's inheritance rule when constructing the `allow_principals[]`/`deny_principals[]` denormalized set at `get_effective_acl()` time — GroundedDocs's contract is vendor-agnostic on this point precisely so each adapter can correctly model its own vendor's semantics |
| Network segmentation prohibiting inbound webhook | Poll-only mode (DEC-102) — see CDC Transport Modes above |

## Contract Tests

| Test | What it verifies |
|---|---|
| `get_effective_acl()` round-trip | For a seeded test document, the adapter's returned ACL matches the vendor ECM's own side-evaluated effective ACL (per DEC-049's stated acceptance bar for `MFilesAdapter` etc.: "matches M-Files-side evaluation on a curated test set" — the same pattern applies to every vendor adapter) |
| `batch_check_access` batching correctness | A single call with N distinct `doc_ids` produces exactly one RPC to the ECM (not N), confirming the fan-in batching contract holds |
| `poll_changes` cursor advancement | Two consecutive `poll_changes` calls with the returned cursor never re-process an already-seen event and never skip an event that occurred between polls |
| Compound-document ACL resolution (DEC-114) | For a virtual/compound-document test fixture where the ACL lives only at the root, `get_effective_acl(leaf_doc_id)` returns the correctly-resolved effective ACL, not an empty/default one |
| `security_label`-only change propagation (DEC-113) | A test event that changes only `security_label` (not principals) correctly fires `acl_changed` and is reflected in the next `get_effective_acl()` call |

## Dependencies

- `04-architecture.md` §7B (full architecture-level rationale this file consolidates for a vendor-facing audience)
- `06-api-contracts.md` (end-user-facing auth model this file's ECM-side auth model sits alongside)
- `08-observability-logs.md` (monitoring signals referenced above)
- `09-deployment-ops.md` (JWKS rotation runbook, encryption-at-rest customer-configuration note)
- `13-decision-log.md` DEC-045, DEC-046, DEC-047, DEC-048, DEC-049, DEC-050, DEC-051, DEC-056, DEC-061, DEC-062, DEC-063, DEC-064, DEC-090, DEC-102, DEC-108, DEC-113, DEC-114

## Decision References

DEC-045, DEC-046, DEC-047, DEC-048, DEC-049, DEC-050, DEC-051, DEC-056, DEC-061, DEC-062, DEC-063, DEC-064, DEC-090, DEC-102, DEC-108, DEC-113, DEC-114
