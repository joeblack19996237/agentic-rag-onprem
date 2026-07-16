# 09 — Deployment and Operations

> Stage 7 (`spec-writer`) deliverable. Expands `04-architecture.md` §9's deployment sketch into the full operational contract: environments, secrets, CI/CD, rollback, scaling, backup/restore, and runbooks. Closes the Round 1 review's remaining deferred items (RC-T3-01 measured VRAM, RC-T4-02 encryption-at-rest, RC-T6-02 driver matrix/Docker version/ingest resume) — this is the file those three items were always pointed at.

## Plain-English Summary

This is the "how do I actually run this thing" document: what hardware to buy, how to install it in 30 minutes, what happens when something breaks, how to back it up, and the runbooks an operator follows during a demo, a customer incident, or a routine model swap.

## Environments

| Environment | Purpose | Notes |
|---|---|---|
| Dev (cloud-rented GPU) | Solo/team development against the same docker-compose image customers run | RunPod template + Network Volume (DEC-021, DEC-068); ¥800-1,200/month solo floor, ¥2,000-3,000/month team envelope (DEC-074) |
| Customer production | Single-host docker-compose on customer-owned hardware | The only "production" this MVP targets — no separate staging tier is committed, given the demo-stage time horizon (`confirmed-context.md` §6) |
| CI | Automated test/build verification | GitHub Actions (or equivalent) running the contract tests from `06-api-contracts.md`, the architecture import-graph check (§5.1), and the golden-set smoke ring (DEC-078) |

**No staging environment is a committed MVP deliverable.** A customer's first install *is* their first real test of the system against their own corpus and ACL data — this is why the golden-set smoke ring (REQ-049, ≤5 min) exists as the de facto "did this install work" check, run immediately post-install rather than in a separate staging tier.

## Configuration and Secrets

| Secret/config class | Storage | Rotation |
|---|---|---|
| ECM adapter credentials (OIDC client secret, API keys) | `.env` file on host volume, never committed, referenced by docker-compose `env_file` | Customer-managed; documented rotation runbook below |
| JWT signing keys / JWKS bundle | Air-gap: static pre-imported bundle in `config/jwks_static` (DEC-062); non-air-gap: pulled from customer IdP at startup | Air-gap: manual runbook (replace file + restart `api/`); non-air-gap: automatic per `Cache-Control: max-age` |
| Admin API keys | Generated at install time, stored hashed in Postgres, never logged | Customer-triggered rotation via a dedicated admin endpoint (rotate, don't edit in place — old key remains valid for a grace window to avoid a hard cutover mid-session) |
| HMAC secret (webhook signature verification) | `.env`, shared with the ECM's webhook sender configuration | Customer-managed, coordinated with the ECM admin |
| Model weights (offline bundle) | `./models/` host volume, SHA-256 manifest-verified at install (DEC-067, NFR-019) | Not a "secret" in the credential sense, but integrity-verified the same way — a corrupted or tampered bundle fails the manifest check before activation |

**No secret is ever baked into a container image.** Every credential above is either a runtime-mounted file or an environment variable populated from the customer's own `.env`, so the docker-compose image itself is safe to distribute as a public artifact (consistent with the OSS/source-available business model, DEC-020).

## Infrastructure Components

Full component list is `04-architecture.md` §9.1's docker-compose service list (`api`, `vllm`, `tei-embed`, `tei-embed-sparse`, `tei-rerank`, `nli`, `safety-input`, `safety-output`, `policy`, `qdrant`, `postgres`, `redis`, `widget`) — not re-derived here. **`tei-embed-sparse` named explicitly here as of 2026-07-16 (DEC-146)** rather than left implicit via this line's own cross-reference to §9.1, since a prior gap (DEC-142's propagation missing this exact line) is what let the sparse service go undocumented across four deployment-surface files simultaneously — see DEC-146 for the full list.

### Hardware Compatibility Matrix — Measured VRAM Occupancy (closes RC-T3-01)

`04-architecture.md` §4.2 flagged "measured VRAM occupancy will be added in Stage 7 after a one-shot cloud-rig validation run." This section is that deliverable.

**Validation methodology**: a single RunPod (or equivalent) rig at the 24 GB floor tier, running the full DEC-077 layered-rail stack + DEC-086 `bge-m3` embedding + DEC-093 ONNX-backend rerank, driven by the 150-200 prompt golden-set full ring (DEC-078) at increasing concurrency (1, 2, 5, 8 in-flight), with `nvidia-smi`-sampled VRAM occupancy recorded at 1-second intervals throughout.

| Tier | Configuration under test | Cold-cache measured VRAM | Warm-cache measured VRAM (peak, 8 in-flight) | Validates |
|---|---|---|---|---|
| Floor (24 GB) | `Llama-3.1-8B-Instruct` int4, `bge-m3`, `bge-reranker-v2-m3` (ONNX), `deberta-v3-base-mnli` (CPU), Llama Prompt Guard 2, Llama Guard 3 8B int4 AWQ | Target: ~18.3 GB (§4.2.2 corrected table, DEC-109) | Target: ~22.3 GB, ~1.7 GB headroom | §4.2.2's allocation table; DEC-109's NLI CPU-residency correction |
| Comfort (32 GB) | Same stack, `Mistral-Small-24B-Instruct` int4 generation model | Proportionally higher generation-model footprint; more KV-cache headroom | Target: sustained 5-8 in-flight without admission-control queuing | §4.2's comfort-tier claim |

**Result recording convention**: this validation run's actual measured numbers (not the estimated numbers carried in `04-architecture.md` §4.2.2, which were architecture-time estimates pending this exact validation) are recorded in a dated results table appended to this section at first execution — e.g. "2026-0X-XX validation run: floor-tier cold-cache measured 18.1 GB (estimate: 18.3 GB, within tolerance)." **This spec does not fabricate a specific measured number** — the estimated figures in `04-architecture.md` §4.2.2 remain the design-time reference until an actual cloud-rig run produces measured data; inventing a precise measured figure here without having run the rig would violate this document's own "no placeholders without stated rationale" discipline in a worse way than stating the estimate is still pending confirmation.

**`gpu-check` script** (referenced in §4.2.1): validates the customer's GPU against the DEC-079 floor before install proceeds — checks total VRAM ≥ 24 GB, confirms the GPU model is not on the §4.2.1 rejection list (Tesla T4, A2, RTX A4000), and warns (does not block) on the procurement-policy note about consumer-tier cards (RTX 4090/5090) in production environments per some enterprise IT governance policies.

### Driver Matrix and Docker Version (closes part of RC-T6-02)

| Component | Minimum version | Notes |
|---|---|---|
| NVIDIA driver | 550.xx series or later | Required for the CUDA version vLLM 0.6+ and TEI's ONNX Runtime backend (DEC-093) both depend on; older drivers are the most common "works on my cloud rig, fails on customer hardware" gap per RISK-013 |
| CUDA | 12.4+ | Bundled via the container images; customer host only needs a compatible driver, not a separately-installed CUDA toolkit |
| Docker Engine | 24.0+ | Required for the container `--gpus` flag semantics and BuildKit features the compose file assumes |
| docker-compose | v2 (the `docker compose` plugin syntax, not legacy `docker-compose` v1 hyphenated binary) | The compose file uses v2-only syntax (e.g. `deploy.resources.reservations.devices` for GPU allocation) |
| Host OS | Linux (Ubuntu 22.04 LTS or RHEL 9 tested); Windows via WSL2 documented as a dev/demo path, not a recommended production path | Enterprise customer hardware in the AU/NZ target market (DEC-072) skews Linux server distributions |

**Pre-install verification script** checks all five rows above before `docker compose up` is attempted, failing fast with a specific remediation message rather than letting the customer discover a driver mismatch mid-install.

### Ingest Resume Mechanics (closes the remaining part of RC-T6-02)

Referenced in `03-workflows.md`'s Workflow 1 as "detailed in `10-build-plan.md`'s ingest-pipeline task" for build-task granularity — this section states the operational contract (what an operator observes and can rely on), while `10-build-plan.md` (Phase 2) states the implementation task breakdown.

- **Checkpoint boundary**: each of the four ingest steps (parse → chunk → embed → index) writes its output and advances `job_queue.status` **before** starting the next step. A `docker compose restart` (or a crash) mid-ingest resumes from the last completed step's output, re-running only the remaining steps — not from upload
- **Idempotency at each boundary**: re-running the `embed` step against the same `chunk` rows produces the same embeddings (deterministic given a fixed model version), so a resumed job never produces duplicate or divergent chunks — this is the same idempotency principle `chunk_id`'s immutable `(document_id, version_id, sequence)` derivation already relies on (DEC-065, `07-database.md`)
- **Operator-visible resume state**: `GET /v1/ingest/{document_id}` continues to report accurate `status`/`progress` across a restart — an operator polling during a restart sees progress hold steady (not reset to 0%), then resume advancing

## CI/CD Pipeline

| Stage | What runs | Gate |
|---|---|---|
| Lint + type check | Standard Python tooling (ruff, mypy, per `CLAUDE.md`) | Must pass to merge |
| Architecture import-graph check | AST-based cross-layer import check (§5.1's CI-enforced call-direction rules) | Must pass to merge — this is the MVP-grade enforcement mechanism named in `04-architecture.md` §5.1's closing line |
| Contract tests | `06-api-contracts.md`'s contract test table | Must pass to merge |
| Golden-set smoke ring | 50-prompt smoke subset (DEC-078), ≤5 min | Must pass to merge — this is the CI fast-feedback gate; the full 150-200 ring runs weekly, not per-PR (per DEC-078's two-ring design) |
| OpenAPI schema drift check | `06-api-contracts.md`'s contract test | Must pass to merge |
| Container build + SHA manifest | Builds the docker-compose image set; regenerates the offline model bundle manifest if models changed | Required before a tagged release |

**No automated CI eval gate runs the full RAGAS golden set on every PR** — per DEC-027, the user runs full golden-set evals manually pre-demo in MVP; CI enforces only the 50-prompt smoke ring. This is a deliberate MVP scope boundary, not an oversight — see DEC-016 for the V2 DeepEval CI-gate roadmap.

## Deployment Strategy

- **Single-host, docker-compose, no blue-green at the deployment-orchestration level for MVP** (DEC-101 — Kubernetes explicitly not adopted at MVP; revisit trigger is V3 multi-host, REQ-026)
- **Model/embedding swaps use their own blue-green pattern** at the model layer (not the deployment-orchestration layer) — see `03-workflows.md` Workflow 6 and `07-database.md`'s migration section; this is orthogonal to and does not require Kubernetes
- **Release cadence**: not GA-committed (per `confirmed-context.md` §6, this is a demo-stage product) — releases are tagged when a coherent feature/fix set is ready, not on a fixed calendar

## Rollback Strategy

| Rollback scenario | Procedure | Time budget |
|---|---|---|
| Generation model swap failure | `config/` flips the adapter pointer back to the previous `model_versions` row | ≤ 10s (REQ-033) |
| Embedding model swap failure (post-cutover RAGAS-floor failure, DEC-109) | Flip the Qdrant collection pointer back to the previous `<corpus_id>_<embedding_model_version>` collection | ≤ 60s (REQ-034) |
| Safety-rail adapter swap failure | `config/safety_rails.yaml` reverts to the prior adapter; goldset regression re-confirms (REQ-050) | No hard time budget stated in REQ-050; treat as an admin-triggered action, not an automatic rollback |
| Prompt template edit regression (V2) | Revert to the prior `prompt_templates` version (immutable versioning means the prior version is always available, never overwritten) | Immediate — versions are never deleted |
| Whole-system rollback (bad release) | `docker compose down` + redeploy the prior tagged image set against the same persisted volumes (`./models/`, `./qdrant/`, `./pg/`) | Depends on image pull time; volumes are untouched so no data migration is needed for a same-schema rollback |

## Database Migration Procedure

See `07-database.md`'s Migrations sections (Postgres: Alembic, additive-only on `audit_events`; Qdrant: double-collection blue/green) — this file adds the operational sequencing:

1. Announce the migration window to the customer (even for a same-host, low-downtime migration, given the single-tenant B2B2B relationship — surprise migrations damage the vendor-trust relationship this product's positioning depends on)
2. Run the Alembic migration against a fresh volume snapshot first (dry-run), not directly against production
3. Apply to production; verify via the post-migration data-shape assertion (per the TDD-Exempt task template's DB-migration verification pattern, `10-build-plan.md`)
4. Confirm `audit_events`'s append-only constraint (the Postgres role-level `DELETE`/`UPDATE` grant restriction, `07-database.md`) survived the migration unchanged — this is the one constraint a migration must never accidentally relax

## Scaling Plan

- **MVP scaling ceiling is single-host, single-GPU** — the concurrency model (`04-architecture.md` §9.4) is the honest ceiling: 2 in-flight cold-cache floor, 5-8 in-flight warm-cache target
- **V3 trigger thresholds** (already named in `02-requirements.md` REQ-026): corpus > 10M chunks, sustained concurrency > 8 in-flight, or > 3 concurrent customer-pilot deployments — any one of these is the signal to revisit the single-host architecture, not a signal to prematurely add Kubernetes now
- **Trace-sampling re-evaluation (DEC-128)**: `08-observability-logs.md` persists 100% of query traces at MVP, which assumes the warm-cache concurrency ceiling above (5-8 in-flight) holds. The same "sustained concurrency > 8 in-flight" trigger above is also the signal to revisit whether 100% trace persistence remains viable, or whether persistence-level sampling should be introduced — no separate threshold is defined for this, since it's the same underlying load condition
- **Comfort-tier (32 GB) hardware is the near-term scaling lever** within MVP's single-host ceiling — sizing up the GPU, not re-architecting, is the first scaling move a customer should make

## Backup and Restore

Full mechanics per store are `07-database.md`'s Backup and Restore sections — this section states the operational schedule and drill cadence.

| Store | Backup schedule | Restore drill cadence |
|---|---|---|
| Postgres (`./pg/`) | Daily volume snapshot minimum; more frequent for customers with tighter RPO requirements (customer-configured) | Recommended quarterly restore drill, verifying `audit_events`'s append-only integrity survives the restore (per `07-database.md`'s restore-integrity note) |
| Qdrant (`./qdrant/`) | Daily volume snapshot minimum, or Qdrant-native snapshot on the same cadence | Verify payload indexes are present post-restore (not just vector data) — a restore missing payload indexes silently degrades Layer 1 filtering |
| Redis | Not backed up (no system-of-record content, `07-database.md`) | N/A — a Redis restart with cold caches is an accepted, non-incident outcome |
| Model weights (`./models/`) | Not part of the recurring backup cycle — re-derivable from the offline model bundle's SHA-256 manifest (DEC-067) at any time | Verify manifest hash on restore |

**`audit_events` capacity-planning runbook (DEC-109)**: given the append-only-forever posture and AU/NZ regulated-vertical multi-year retention obligations (DEC-072), the following planning estimate should be reviewed at each customer's first-install and annually thereafter: (a) measure the average `audit_events` row size for that customer's actual query volume; (b) multiply by expected annual query volume; (c) compare against the single-host storage tier's remaining capacity; (d) if projected growth would exceed the storage tier within 3 years, plan a cold-archival path (periodic export of rows older than N years to object storage, if the customer's compliance policy permits summarized/exported retention) before it becomes an urgent capacity incident rather than a planned one.

## Incident Response

| Incident class | First response | Escalation |
|---|---|---|
| `/ready` never reaches `true` | Check per-service breakdown (`06-api-contracts.md`'s `/ready` schema) — identify which service is stuck; check its container logs | If a model-serving container (vLLM, TEI, safety-rail) is stuck, check for a corrupted offline-bundle hash mismatch first (DEC-067's manifest verification) before assuming a code bug |
| PDP circuit breaker open | Check ECM connectivity/health from the GroundedDocs host | If sustained, this is the customer's ECM having an availability issue, not a GroundedDocs bug — coordinate with the customer's ECM admin |
| Citation hit-rate alert (Critical, `08-observability-logs.md`) | Treat as code-red — pull the specific failing `audit_events` rows, do not attempt a threshold tuning fix | Escalate to architecture review immediately; this is a hard-gate violation, not a tunable metric |
| Legal-hold invalidation audit gap (Critical) | Manually verify the underlying cache invalidation actually occurred (query the cache directly) even though the audit write failed | If the invalidation itself did not occur, this is a compliance incident requiring immediate customer notification per the legal-hold obligation DEC-091/DEC-106 exist to satisfy |
| Sustained refusal-rate spike | Follow `23-evals-guardrails.md` §7's diagnosis runbook (already fully specified there — not duplicated here) | LCC Tier 2 advisory engagement if cheap tuning steps don't resolve it |

## Runbooks

### Runbook: First Customer Install

1. Run the pre-install verification script (driver matrix + `gpu-check`, above)
2. Transfer the offline model bundle (air-gap) or confirm public-network pull access; verify SHA-256 manifest
3. `docker compose up`; poll `/ready` (full-dependency check, DEC-117) — expect ≤30 minutes to `ready: true` (REQ-011)
4. Run the 50-prompt golden-set smoke ring against the sample CCM-style corpus (REQ-014) as the first-install validation
5. If ECM-connected (canonical MVP path, DEC-053): confirm CDC transport mode (webhook vs poll-only, DEC-102) and run one end-to-end CDC event test (e.g. trigger a test `acl_changed`) before declaring the install complete
6. Document the installed hardware tier and measured concurrency behavior for the customer's own capacity planning

### Runbook: Vendor Demo Facilitation

Per NFR-031's demo-day burst guidance (carried here as the operational runbook that guidance names): advise facilitators to **stagger** the first round of audience questions rather than inviting simultaneous submission, since a burst of near-simultaneous cold-cache queries queues behind the single-GPU serving path and most will exceed the 8s SLO even though the system is not broken. The widget's visible "queued" state (NFR-031) is the user-facing signal if staggering advice isn't followed — facilitators should narrate this state as "processing your question" rather than treat it as an error.

### Runbook: JWKS Rotation (Air-Gap)

Per DEC-062: replace the static JWKS bundle file at `config/jwks_static`, restart `api/`. No live IdP round-trip is possible in air-gap mode by design — this is a manual, scheduled operator action, not an automated rotation.

### Runbook: Encryption-at-Rest (closes RC-T4-02)

`92-stage5-review-memos.md`'s D5-08 finding noted that many ECMs encrypt content at rest via KMS, and that GroundedDocs extracting plaintext into Qdrant payload could break that encryption posture if left unaddressed. This is the deferred subsection that finding pointed to.

- **MVP default posture**: GroundedDocs does not itself manage KMS-integrated encryption for Qdrant/Postgres content — encryption-at-rest for the `./qdrant/`, `./pg/` host volumes is the customer's own responsibility, achieved via standard host/disk-level encryption (LUKS on Linux, BitLocker on Windows-hosted installs, or the cloud provider's volume-encryption feature for cloud-hosted deployments) — this is a documented **customer configuration responsibility**, not a GroundedDocs application-layer feature, because host-level disk encryption is transparent to the application and requires no GroundedDocs-side code
- **Why this is sufficient, not a gap left open**: the concern in D5-08 was that GroundedDocs "extracts plaintext into Qdrant payload, possibly breaking encryption posture" — host-level disk encryption addresses this because the plaintext chunk text and ACL payload are encrypted at rest by the same mechanism protecting the customer's other disk-resident data, with no GroundedDocs-specific gap. This is distinct from *application-layer* field encryption (e.g. encrypting specific columns independent of disk state), which is **not** provided in MVP and is named here as an explicit non-goal, not an oversight
- **Customer pre-install qualification question**: `09-deployment-ops` (this section) should be raised during the pre-install security review alongside the existing co-location/network-segmentation questions (§7B.0's procurement-risk note) — "does your compliance posture require host-level disk encryption, and is it already enabled on the target host?" — so this is confirmed before install, not discovered during a compliance audit afterward
- **V2+ direction, if a customer requires application-layer field encryption**: named as a future option, not designed here — would likely take the form of Postgres column-level encryption (e.g. `pgcrypto`) for `audit_events`'s most sensitive fields, evaluated against the performance cost of decrypting on every audit-pull query. Not committed to any timeline; flagged for product-scope decision if a first regulated buyer requires it (paralleling DEC-006's "no certification committed for MVP, but design must not block")

## Cost Controls

- Dev/rental budget: DEC-068 (¥800-1,200/month solo floor), DEC-074 (¥2,000-3,000/month team envelope) — dev-environment only, not customer production cost
- Customer production cost is customer-hardware-owned (DEC-020 business model) — GroundedDocs does not meter or bill for compute; the cost-control surface for a *customer's own* deployment is the `cost_per_turn` NFR-024 metric (observability-driven, not a runtime block in MVP) plus the hardware-tier choice itself (floor vs comfort vs performance, §4.2)

## Operational Ownership

| Responsibility | Owner (MVP demo stage) |
|---|---|
| Install + first-run verification | Vendor evaluator (self-service) or GroundedDocs operator (assisted first-time deployment engagement, `01-product-brief.md` §8 service tiers) |
| Ongoing monitoring | Customer's own ops team, using the dashboards/alerts in `08-observability-logs.md` forwarded to their collector via OTLP |
| Golden-set eval runs | User/operator runs manually pre-demo (DEC-027); V2 automates as a CI/scheduled job |
| LCC (Model Lifecycle Care) | GroundedDocs operator, per the 4-tier service package (DEC-028) |
| Incident response | Customer's ops team first-line; GroundedDocs operator escalation for anything requiring an architecture-level fix |

## Dependencies

- `04-architecture.md` §4.2 (hardware matrix this section's validation methodology targets), §9 (deployment sketch this file expands)
- `03-workflows.md` (Workflow 1's ingest-resume reference, Workflow 6's model-swap rollback reference)
- `07-database.md` (backup/restore mechanics per store)
- `08-observability-logs.md` (alerts this file's runbooks respond to)
- `10-build-plan.md` (this phase — ingest-pipeline task-level checkpoint detail)
- `92-stage5-review-memos.md` RC-T3-01, RC-T4-02, RC-T6-02 (the three items this file was always the deferred target for)
- `13-decision-log.md` DEC-021, DEC-062, DEC-066, DEC-067, DEC-068, DEC-074, DEC-077, DEC-079, DEC-086, DEC-093, DEC-097, DEC-101, DEC-102, DEC-109

## Decision References

DEC-020, DEC-021, DEC-027, DEC-062, DEC-066, DEC-067, DEC-068, DEC-074, DEC-077, DEC-079, DEC-086, DEC-093, DEC-097, DEC-101, DEC-102, DEC-109, DEC-128
