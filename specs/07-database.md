# 07 — Database

> Stage 7 (`spec-writer`) deliverable. Physical schema for the three stores named in `04-architecture.md` §4.1: Postgres 16 (relational + audit + persistent queue), Qdrant (vector + payload), Redis 7.x/Valkey 8.x (hot-path cache). Derives directly from `05-data-model.md`'s entity definitions — does not introduce new entities.

## Plain-English Summary

Three stores, three different jobs. Postgres is the system of record for everything that must survive forever and be queried relationally (documents, audit trail, model version history). Qdrant holds the actual searchable content — chunk text, embeddings, and the ACL payload that makes retrieval permission-aware without a live ACL check on every candidate. Redis holds nothing that isn't disposable — every Redis key can vanish and the system degrades to a cache-miss, never a data-loss.

## Database Choice and Rationale

Already decided (DEC-034, DEC-076 — not re-litigated here):

- **Postgres 16**: relational entities, append-only audit, persistent task queue (`SKIP LOCKED` pattern, DEC-038)
- **Qdrant single-node**: vector store with dense + sparse + payload filter in one collection (REQ-003, DEC-034)
- **Redis 7.x or Valkey 8.x**: hot-path cache only, never a system of record (DEC-076)

No pgvector, no Weaviate, no Celery/Kafka — see DEC-034 for the full rejected-alternatives list; this file does not re-derive that comparison.

## Postgres Schema

### Tables

| Name | Purpose | Primary Key | Important Fields | Indexes | Retention |
|---|---|---|---|---|---|
| `documents` | Document identity + lifecycle | `document_id` (UUID) | `repository_id`, `parent_document_id`, `lifecycle_state`, `authority_state` | `(repository_id, document_id)` unique; `parent_document_id` for compound-doc lookups | Physical delete on `document_deleted` |
| `document_versions` | Version identity + Layer 1 ACL source-of-truth | `(document_id, version_id)` | `is_committed`, `security_label`, `retention_state`, `allow_principals[]`, `deny_principals[]`, `superseded_by_version_id` | `(document_id, is_committed)`; GIN index on `allow_principals`/`deny_principals` for reconciliation-crawl queries (DEC-090) | Physical delete on `version_deleted` |
| `audit_events` | Append-only compliance + forensics record | `audit_id` (UUID) | See `05-data-model.md` full field list; `conversation_id`, `context_fingerprint` (JSONB), `citations` (JSONB), `retrieval_safety_verdicts` (JSONB) | `(conversation_id, timestamp DESC)` for server-side history reconstruction (§2.4); `(user_id, timestamp)` for audit pull API (REQ-043); `timestamp` for range queries (`GET /v1/admin/audit`) | Append-only forever (DEC-070); no deletion path |
| `legal_hold_invalidation_events` | Legal-hold remediation evidence | `event_id` (UUID) | `triggering_doc_id`, `invalidation_target`, `conversation_id` nullable, `evicted_query_hashes` (JSONB) nullable | `(triggering_doc_id, invalidation_timestamp)` | Same posture as `audit_events` — append-only |
| `model_versions` | Model/adapter version history | `(role, model_version)` | `is_active` (partial unique index enforces exactly one active row per `role`), `pre_swap_ragas_report_id` | Partial unique `(role) WHERE is_active = true` | Indefinite |
| `prompt_templates` | Prompt template versions (MVP: one default row; V2 schema-reserved for per-customer) | `prompt_template_id` | `customer_id` nullable, `version`, `body` | `(customer_id, version)` | Indefinite |
| `eval_runs` | RAGAS run history | `run_id` (UUID) | `suite`, `metrics` (JSONB), `model_versions_snapshot` (JSONB), `pass` | `(suite, run_at DESC)` | Indefinite |
| `job_queue` | Persistent task queue (ingest jobs, CDC re-poll jobs) | `job_id` (UUID) | `job_type`, `payload` (JSONB), `status`, `locked_until` | `(status, locked_until)` for `SKIP LOCKED` polling (DEC-038) | Deleted on completion + short grace window for debugging (7 days) |
| `otel_spans` | Operational diagnostic traces | `span_id` | `trace_id`, `parent_span_id`, `node_name`, `attributes` (JSONB per OTel GenAI conventions) | `(trace_id)`; `(timestamp)` for retention cleanup | 30-90 days, admin-configurable (DEC-109) |

### Constraints

- `document_versions.document_id` → `documents.document_id` (FK, `ON DELETE RESTRICT` — a `document_versions` row must never outlive its parent `documents` row without going through the explicit `version_deleted`/`document_deleted` event path; no cascading delete, because deletion here is a compliance-significant action that must go through the CDC event handler, not an incidental side effect of a Postgres cascade)
- `model_versions`: partial unique index `(role) WHERE is_active = true` enforces "exactly one active row per role" at the database level, not just in application code
- `audit_events`: **no `UPDATE` or `DELETE` grants** on this table for the application's runtime database role, enforced at the Postgres role level, not just by application discipline — this is the concrete mechanism behind DEC-070's "immutable forever" claim. Only a separate, break-glass administrative role (used exclusively for the deferred GDPR-erasure path, per DEC-070's stated deferral) has `DELETE` privilege, and any such use is itself required to write a `legal_hold_invalidation_events`-style remediation record (extending the same evidentiary pattern) before this becomes a real feature
- `job_queue`: `CHECK (status IN ('pending', 'in_progress', 'complete', 'failed'))`

### Indexes and Query Patterns

| Query pattern | Index | Rationale |
|---|---|---|
| Server-side conversation history reconstruction (§2.4: last N=5 turns by `conversation_id`) | `audit_events(conversation_id, timestamp DESC)` | Hot path — runs on every turn of a multi-turn conversation |
| Audit pull API for vendor SIEM (`GET /v1/admin/audit/events`, REQ-043) | `audit_events(timestamp)` with cursor pagination on `(timestamp, audit_id)` | Idempotent paginated read; cursor must be stable under concurrent inserts |
| Reconciliation crawl (DEC-090, weekly) | `document_versions(document_id, is_committed)` full scan, batched | Low-frequency, batch-oriented — no need for a specialized index beyond the existing PK |
| `model_versions` active-adapter lookup (every turn, `config/`) | Partial index `(role) WHERE is_active = true` | Every query's `context_fingerprint` construction reads this |

### Transactions and Consistency

- **`audit_events` write is the last step before `api/` returns** (§8.4) — this write must complete (or the request must fail loudly) before the response is sent; a fire-and-forget async write here would reopen the "audit is supplementary, not authoritative" gap DEC-047 was written to close for the *local* audit sink (the ECM write-back stays async per DEC-047; the local write does not)
- **`model_versions.is_active` flip is a single-row `UPDATE ... WHERE role = ? AND is_active = true` paired with an `INSERT` of the new active row, inside one transaction** — prevents a window where two rows are simultaneously active for the same role
- **`legal_hold_invalidation_events` write happens in the same logical unit of work as the cache-invalidation action it records** (best-effort: if the invalidation succeeds but the audit write fails, this is itself an ops-alerting condition — silent success with no audit trail is the one failure mode this design cannot tolerate, given DEC-106's rationale)

### Migrations

- **Framework**: Alembic (standard for Python/SQLAlchemy-adjacent stacks; matches the project's Python pin — originally DEC-033's 3.12, re-pinned to 3.14 by DEC-134)
- **`audit_events` schema changes are additive-only** — new nullable columns with a stated default for historical rows; no migration may `ALTER ... DROP COLUMN` or reinterpret an existing column's semantics on this table, per `05-data-model.md`'s migration-implications section
- **Embedding-model-version migrations do not touch this schema** — they are a Qdrant-side collection migration (see below), with only a `model_versions` row insert + active-flip on the Postgres side

### Seed Data

- One default `prompt_templates` row (`prompt_template_id = "default-v1"`, `customer_id = null`) — required for the system to construct any prompt at all; this is not optional seed data, it is a first-boot requirement
- One `model_versions` active row per role (`generation`, `embedding`, `rerank`, `nli`, `safety_input`, `safety_output`, `policy`) reflecting the reference stack (`04-architecture.md` §4.1) — populated by the install script from `config/` at first boot, not hand-seeded

### Backup and Restore

- **Volume-level backup**: `./pg/` host-mounted volume (NFR-007: all durable state survives container restart) is included in the customer's standard backup procedure — `09-deployment-ops.md` (this phase) documents the concrete backup schedule and restore drill
- **`audit_events` backup integrity is the single highest-stakes restore scenario** — a restore that reintroduces rows deleted via the deferred GDPR break-glass path, or fails to preserve the append-only guarantee, would violate DEC-070. Restore procedures must restore to a point-in-time snapshot, never a selective row restore that could reintroduce a compliance-deleted row
- **Retention-driven physical deletes must not be undone by a later restore from an older backup** — this is the same concern DEC-046 raised about soft-deletes ("vector DB rebuilds/migrations/restores can revive soft-deleted content"), extended to the backup/restore procedure itself: `09-deployment-ops.md` must document that a backup taken *before* a `retention_expired` event, if restored *after* that event, would resurrect compliance-killed content — the restore runbook must cross-check the CDC event log's `retention_expired`/`legal_hold_added` history against the backup's timestamp before considering a restore complete

### Performance Risks

- **`audit_events` unbounded growth** (DEC-109 capacity-planning note, carried from `05-data-model.md`) — single-host Postgres has no built-in archival tier; `09-deployment-ops.md` must specify a cold-archival path (e.g. periodic export to object storage of rows older than N years, if the customer's compliance policy allows summarized/exported retention) before this becomes an operational surprise
- **`job_queue` `SKIP LOCKED` polling frequency vs re-poll CDC interval** — the poll-only CDC transport mode (DEC-102) writes its poll cycles through this same queue; a very short poll interval (the "recommended 5 min" floor per NFR-032) combined with a large customer document count could create queue contention with ingest jobs. `09-deployment-ops.md` should document a recommended queue-priority separation (ingest jobs vs CDC re-poll jobs on distinct `job_type` values, with independent worker pool sizing)

### Database Tests

| Test | What it verifies |
|---|---|
| `audit_events` immutability | Attempt `UPDATE`/`DELETE` as the runtime application role → must fail with a permissions error, not merely application-level refusal |
| `model_versions` single-active-row constraint | Attempt to set two rows `is_active = true` for the same `role` in a race → partial unique index must reject the second write |
| Retention physical-delete completeness | After `retention_expired`, verify zero rows remain in `chunks` (Qdrant) or `document_versions` for that version — no orphaned rows in either store |
| Legal-hold freeze prevents re-ingest | Attempt `version_added` re-ingest for a version currently under `legal_hold` → must be refused with a hold-active reason (NFR-015 acceptance criterion, carried here as a DB-level check: the frozen `chunks` rows must not be touched by the ingest job) |

## Qdrant Collections

### Collection Naming and Design

- **One collection per `(corpus_id, embedding_model_version)`** — the double-collection naming convention (DEC-059), e.g. `default_bge-m3-v2`. This is in place from MVP day one, even though the blue/green re-embedding *automation* (REQ-034) is V2 — the naming convention alone is what makes that automation possible without a breaking migration later. **Open question, not resolved by DEC-142**: `embedding_model_version` now tracks two independently-versionable models (dense `bge-m3` + a separate sparse SPLADE model) but the naming convention still carries only one version string — fine for MVP (no automated re-embedding yet, REQ-034 is V2), but whoever builds the V2 blue/green automation needs to decide whether a sparse-model-only version bump also needs a new collection
- **Vectors per point**: dense (`bge-m3` dense output, DEC-086) + sparse (a dedicated SPLADE model's output, **DEC-142, 2026-07-15 — corrects the prior "bge-m3 lexical output" claim; TEI cannot serve bge-m3's own sparse output**) — both required for REQ-003's hybrid dense+sparse claim; a collection with only a dense vector is not a valid MVP collection
- **Payload per point** (mirrors `chunks` entity fields from `05-data-model.md`): `document_id`, `version_id`, `repository_id`, `chunk_id`, `sequence`, `text`, `embedding_model_version`, `allow_principals[]`, `deny_principals[]`, `security_label`, `retention_state`, `frozen_at`

### Payload Indexes

**Mandatory, created before ingest** (not an optimization — Qdrant's own filtering guidance treats pre-existing payload indexes as required for Layer 1 filter-then-search to hold recall at scale, `93-stage5r2-benchmark.md` §Topic 4/8):

| Payload field | Index type | Used by |
|---|---|---|
| `allow_principals` | Keyword index | Layer 1 filter: `allow_principals INTERSECTS effective_principals` |
| `deny_principals` | Keyword index | Layer 1 filter: `NOT (deny_principals INTERSECTS effective_principals)` |
| `retention_state` | Keyword index | Layer 1 filter: `retention_state == "active"` |
| `document_id` | Keyword index | Layer 2 batch RPC grouping (collect distinct `document_id`s from top-K) |
| `security_label` | Keyword index | Reserved for future customer-configurable classification-level filtering (not queried at MVP, but indexed now to avoid a reindex later if this becomes a filter dimension) |

### Constraints

- **No user/role/group/principal identifier may appear in the vector input text** (NFR-012) — this is enforced upstream at the embedding-service boundary (`ingest/` never passes ACL fields into the text sent to the TEI embedding service), not as a Qdrant-level constraint, since Qdrant cannot itself verify what went into a vector
- **`chunk_id` immutability** (DEC-065) is enforced by convention (the ingest pipeline never reuses a `(document_id, version_id, sequence)` tuple), not by a Qdrant-native uniqueness constraint — Qdrant point IDs are derived deterministically from this tuple so a re-ingest of the same tuple would overwrite rather than duplicate, which is the desired idempotent behavior for CDC retry safety (RC-T8-01)

### Migrations (Blue/Green Re-Embedding, REQ-034 V2 Automation)

1. New embedding model version bumps `model_versions.embedding` row (Postgres, gated by the DEC-109 RAGAS-floor quality check)
2. Re-embedding job creates the new Qdrant collection `<corpus_id>_<new_embedding_model_version>` and populates it from source `chunks` text (not from the old collection's vectors — must re-embed from source text)
3. Dual-write window: new ingests write to both old and new collections until cutover
4. Cutover: `config/` flips the active collection pointer; queries route to the new collection
5. Rollback: flip the pointer back within ≤ 60 seconds (REQ-034 acceptance criterion) — the old collection is retained, not deleted, until the admin explicitly confirms cutover success

### Backup and Restore

- Qdrant's own snapshot mechanism, scheduled against the `./qdrant/` host-mounted volume (NFR-007)
- **Restore must restore both the collection data and the payload indexes** — a restore that recreates vectors but loses payload indexes would silently degrade Layer 1 filtering from "filter-then-search" to a full-scan-then-filter pattern, which Qdrant's own documentation flags as breaking HNSW recall at scale (`93-stage5r2-benchmark.md` §Topic 4)

### Performance Risks

- **Pre-filter cardinality at scale** — Qdrant's query planner degrades if payload indexes are missing or if filter cardinality is very high; this is why payload indexes above are marked mandatory, not optional. `09-deployment-ops.md` should include a post-install verification step confirming payload indexes exist (a `gpu-check`-style script, analogous to the existing GPU floor check per §4.2.1)
- **Retrieval-rail scan cost scaling with authorized-chunk count** (DEC-097's flagged risk, carried here): the retrieval-rail scan runs over `acl_trimmed_set` (typically 5-15 chunks); if a corpus's ACL structure produces unusually large authorized sets per query, both this scan and the rerank step scale up, eating into the already-thin cold-cache latency headroom

## Redis Schema (Keys, Not Tables)

Redis has no schema in the relational sense — this section documents key shapes, TTLs, and invalidation triggers as the closest equivalent.

| Key pattern | Value | TTL | Invalidation trigger |
|---|---|---|---|
| `answer:{query_hash}:{acl_set_hash}:{model_version}` | JSON: cached `POST /v1/query` response | 600s | `model_version` rotation; embedding-model swap cutover; admin flush; targeted eviction via `docref:{doc_id}` lookup on `legal_hold_added` (DEC-116) |
| `docref:{doc_id}` | Set of `answer:*` keys whose cached answer cited `doc_id` | Same as longest-lived referencing `answer:*` key (self-cleaning as answer-cache entries expire) | Reverse index maintained on every `answer:*` write; consulted (not itself invalidated) on `legal_hold_added` |
| `acl:user:{user_id}` | JSON: `effective_principals[]` | 60s | Inbound `acl_changed` event touching this user; `POST /v1/admin/acl/refresh_user/{user_id}` |
| `acl:doc:{document_id}` | JSON: PDP decision (`{allowed: bool, retention_state}`) | 30s | Inbound `acl_changed(doc_id)`; `POST /v1/admin/acl/refresh_doc/{doc_id}` |
| `prompt:{template_id}` | Rendered prompt template (system prompt + per-customer template) | Until `prompt_templates` version change | Admin edits a prompt template (V2) |
| `embed:{text_hash}` | Cached embedding vector for repeated chunk text | Until embedding-model version change | `model_versions.embedding` rotation |

### Constraints

- **No Redis key is a system of record** — every key above has a Postgres or Qdrant equivalent that is authoritative; a total Redis data loss (e.g. container restart without persistence) degrades performance (all caches cold) but never loses data
- **`docref:{doc_id}` reverse index is additive to, not a replacement for, the primary answer-cache key** — read-path lookups always use the primary `answer:{query_hash}:{acl_set_hash}:{model_version}` key; the reverse index exists solely to make `legal_hold_added`-triggered targeted eviction possible without a full-keyspace scan (DEC-116)

### Backup and Restore

- **Not backed up** — by design, given the "no system of record" constraint above. A Redis restart with no persistence configured is an accepted, documented operational behavior, not an incident. If the customer's install uses Redis persistence (RDB/AOF) for faster warm-cache recovery after a planned restart, that is an optimization, not a requirement

### Performance Risks

- **`docref:{doc_id}` set growth for a heavily-cited document** — a document referenced by many distinct cached answers produces a large reverse-index set; this is bounded in practice by the 600s answer-cache TTL (the set self-prunes as underlying `answer:*` keys expire) but should be monitored if a customer's query pattern produces unusually high cache-hit repetition on a small set of documents

## Database Tests (Cross-Store)

| Test | What it verifies |
|---|---|
| Legal-hold cross-store consistency | `legal_hold_added(doc_id)` → verify (a) Qdrant `chunks` payload `retention_state = legal_hold` + `frozen_at` set, (b) Postgres `document_versions.retention_state = legal_hold`, (c) Redis `docref:{doc_id}` lookup returns and evicts matching `answer:*` keys, (d) Postgres `legal_hold_invalidation_events` row exists for both the KV-cache and answer-cache invalidation actions |
| Retention-expiry cross-store consistency | `retention_expired(doc_id)` → verify zero rows in Qdrant for that version, zero rows in Postgres `document_versions` for that version, and that `audit_events` rows citing that document's chunks remain fully readable (citations are verbatim snapshots, DEC-087 — no orphaned reference) |
| Embedding swap rollback | Trigger a blue/green cutover, force a RAGAS-floor failure post-cutover → verify `model_versions.is_active` flips back to the old collection within 60s and the new (failed) collection is retained for post-mortem, not deleted |

## Dependencies

- `05-data-model.md` (entity source for every table/collection/key in this file)
- `04-architecture.md` §4.1 (store choices), §7B.3-§7B.4 (two-layer ACL mechanics this schema implements), §9.1 (docker-compose volumes)
- `09-deployment-ops.md` (this phase — backup schedule, restore drills, capacity-growth runbook execution)
- `13-decision-log.md` DEC-034, DEC-038, DEC-046, DEC-059, DEC-065, DEC-070, DEC-076, DEC-086, DEC-090, DEC-096, DEC-097, DEC-102, DEC-109, DEC-116, DEC-142

## Decision References

DEC-034, DEC-038, DEC-046, DEC-059, DEC-065, DEC-070, DEC-076, DEC-086, DEC-090, DEC-096, DEC-097, DEC-102, DEC-109, DEC-116, DEC-142
