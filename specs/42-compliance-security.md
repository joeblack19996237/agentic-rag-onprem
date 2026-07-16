# 42 — Compliance and Security

> Stage 7 (`spec-writer`) deliverable. **Deliberately scoped light**, per `confirmed-context.md` §7: "Compliance scope: deferred to first regulated buyer; placeholder spec slot 42 only." This is not a full compliance certification plan (SOC2/HIPAA/PCI/IRAP audit prep is explicitly out of MVP scope, DEC-006) — it consolidates the security/compliance facts already decided elsewhere into one reference document, and cross-references rather than duplicates.

## Plain-English Summary

GroundedDocs is not certified against any compliance framework in MVP, and does not claim to be. What it does have: a documented threat model, an audit trail that cannot be silently altered, an explicit and honest treatment of the one privacy right it cannot yet fully honor (GDPR erasure), and a clear "customer's responsibility vs. GroundedDocs's responsibility" line for encryption. This file exists so a customer's security/compliance reviewer has one place to check before a pilot, not so GroundedDocs can claim a certification it does not have.

## Data Classification

Full detail is `05-data-model.md`'s Privacy Classification section — summarized here for the compliance-reviewer audience:

| Classification | Entities | Handling |
|---|---|---|
| Confidential / Compliance-critical | `audit_events`, `legal_hold_invalidation_events` | Append-only, immutable, multi-year retention per customer policy |
| Confidential | `documents`, `document_versions`, `chunks`, `answer_cache`, `acl_cache` | Standard confidentiality; caches are transient and disposable |
| Internal/operational | `model_versions`, `prompt_templates`, `eval_runs`, `otel_spans` | No customer content; safe at INFO log level |

## Regulatory Obligations

**MVP positioning** (per DEC-006): first buyer profile is general B2B, non-regulated. Design must not *block* future certification, but no certification is committed for MVP. This file states the current honest posture, not a compliance roadmap.

### AU/NZ Reference Frame (First-Wave Market, DEC-072)

- **AU Privacy Act 1988** + **Notifiable Data Breaches (NDB) scheme** + **AU AI Ethics Principles 2019** — the compliance reference frame for AU customers. GroundedDocs's on-prem/air-gap posture (NFR-002, NFR-020) directly supports the "data must not leave country" procurement pattern common in AU public sector, finance, and mining
- **NZ Privacy Act 2020** + **IPP 13 principles** — the reference frame for NZ customers
- **No certification against either framework is claimed or pursued in MVP** — the architecture is designed not to block it (data-residency traceability per NFR-020: "reviewer can trace every model/config/external call to either customer-controlled or explicitly disabled in air-gap"), but achieving formal compliance status is a first-regulated-buyer-triggered engagement, per DEC-006

### GDPR (EU, if/when relevant)

- **Right-to-erasure against `audit_events` is explicitly deferred** (DEC-070) — `audit_events` is append-only and immutable in the MVP shipping posture, because the audit-ready product differentiator depends on that immutability promise. A concrete erasure-right obligation's first real trigger is the first regulated AU/EU buyer engagement, at which point this becomes a scoped design problem (likely a break-glass administrative deletion path with its own compliance-grade audit trail, per `07-database.md`'s note on the restricted `DELETE` grant), not something MVP invents speculatively
- **This is a stated, honest deferral, not a silent gap** — a customer's compliance reviewer asking "can you delete a specific user's query history" should be told directly: not in MVP, by design, and here is why (the audit-immutability promise this product's differentiation depends on)

### Compliance Certifications Not Pursued in MVP

SOC2, HIPAA, PCI, China MLPS Level 3, IRAP — none committed for MVP (DEC-006). `01-product-brief.md` §6's non-goals table is the canonical scope statement; this file does not re-litigate it, only cross-references it for the compliance-reviewer audience who may be looking specifically in this slot for that answer.

## Threat Model

Full STRIDE table is `04-architecture.md` §12.5 — reproduced here in summary form for this file's audience, not re-derived:

| Threat (STRIDE) | Mitigation |
|---|---|
| Spoofing (forged JWT) | RS256/ES256/EdDSA signature verification with algorithm whitelist (DEC-061); JWKS rotation (DEC-062) |
| Tampering (request payload) | TLS at the API surface; `audit_events` append-only (DEC-070) |
| Repudiation (denying a query was asked) | Append-only audit + ECM audit write-back including denied-access intent (DEC-064) |
| Information disclosure (cross-user data leak) | Two-layer ACL (`41-integration-contracts.md`) + retention enforcement + Layer 2 circuit breaker (DEC-063) |
| Denial of service (LLM exhaustion) | Concurrency cap (DEC-066), rate limit per token (NFR-017) |
| Elevation of privilege (prompt injection) | Layered safety rails: input rail + retrieval rail + output rail + orchestration rail + structural separators + server-reconstructed history (DEC-077, `22-memory-context.md`) |

## Trust Boundaries

- **Customer network boundary**: GroundedDocs co-locates with the ECM inside the same private network/VPC (DEC-055) — no split-firewall deployment is a supported MVP topology
- **ECM ↔ GroundedDocs boundary**: federation pattern (DEC-045) — GroundedDocs never crosses this boundary to reimplement ECM-side identity/ACL logic, only calls through the `ECMAdapter` contract (`41-integration-contracts.md`)
- **Widget ↔ host-vendor-portal boundary**: iframe/Web-Component sandboxing, CSP `frame-ancestors`, postMessage origin allowlist, no cross-origin host-state reads (NFR-018, §12.5)
- **Air-gap boundary**: no required outbound network calls at runtime (NFR-002); every model/config/external call traceable to either customer-controlled or explicitly disabled (NFR-020)

## Security Controls

Consolidated cross-reference, not restated in full:

| Control | Where specified |
|---|---|
| JWT signature algorithm whitelist (RS256/ES256/EdDSA allowed; `HS256`/`HS384`/`HS512`/`none` rejected) | DEC-048, DEC-061; `41-integration-contracts.md` Auth Model |
| Rate limiting (60 queries/token/min default, burst 10/5s) | NFR-017; `04-architecture.md` §12.5 |
| Widget CSP/postMessage/SRI | NFR-018; `04-architecture.md` §12.5 |
| ECM PDP circuit breaker (fail-closed, never silent-skip) | DEC-063 |
| Two-layer authorization | `41-integration-contracts.md` |
| Layered prompt-injection defense | DEC-077, `04-architecture.md` §12.2 |
| No identity in embedding vectors | NFR-012 |

## Access Control

- End-user access: JWT bearer, scoped per-query, re-verified per-query via Layer 2 JIT (not a standing session grant that outlives its TTL windows — `41-integration-contracts.md`'s ACL cache TTL table: 60s user, 30s document)
- Admin access: admin API key or admin-scoped JWT, required on every `06-api-contracts.md` Admin-surface endpoint. **Tracked gap (DEC-145, `RISK-023`)**: the shipped `api-surface` (`TASK-033`) implementation verifies JWT signature only — the "admin-scoped" claim check is not yet implemented, so any correctly-signed JWT currently passes on admin endpoints too. Currently inert (no end-user JWT issuance path exists yet in this codebase), but not gated by this project's own build-plan sequencing — the exposure window opens the moment any real vendor integration mints end-user JWTs. `TASK-040` closes it; this is an explicit precondition for any real (non-demo) deployment, not a theoretical future concern
- No role beyond "end user" and "admin" exists in MVP — RBAC depth (reviewer role, per-category routing) is V2 (REQ-016)

## Secrets

Full detail is `09-deployment-ops.md`'s Configuration and Secrets section — cross-referenced, not duplicated. Summary: no secret is ever baked into a container image; ECM adapter credentials, JWT signing material, admin API keys, and the webhook HMAC secret are all runtime-mounted or environment-variable-populated from the customer's own `.env`.

## Encryption

- **In transit**: TLS at the API surface (implied by "HTTPS" throughout `04-architecture.md`/`06-api-contracts.md`); webhook delivery HMAC-signed (not merely TLS-protected — HMAC verifies the specific sender, not just the transport)
- **At rest**: **customer-managed host-level disk encryption** is the MVP posture, per `09-deployment-ops.md`'s "Runbook: Encryption-at-Rest" (RC-T4-02) — GroundedDocs does not itself provide application-layer field encryption for `chunks`/`audit_events` content in MVP. This is a deliberate, documented non-goal, not an oversight: host-level disk encryption (LUKS, BitLocker, or cloud-provider volume encryption) transparently protects the plaintext GroundedDocs extracts into Qdrant/Postgres, addressing the original concern (that plaintext extraction could break an ECM's own KMS-integrated encryption posture) without requiring GroundedDocs-side code. See `09-deployment-ops.md` for the pre-install qualification question this raises with customers, and the named (not designed) V2+ direction if application-layer field encryption is ever required

## Audit Evidence

- `audit_events`: append-only, immutable, non-null `context_fingerprint` from MVP day one (DEC-060/DEC-089) — this is the primary audit-evidence artifact a compliance reviewer would examine
- ECM audit write-back (dual-write, DEC-047): the ECM's own audit log remains the compliance-authoritative sink for frameworks like Documentum DAR / OpenText Records Management; GroundedDocs's local audit is supplementary evidence, not a replacement
- `legal_hold_invalidation_events`: the specific evidentiary record for litigation-hold disputes (DEC-106/DEC-116) — proves remediation actually ran, not just that a chunk was frozen

## Abuse Cases

Cross-referenced from `04-architecture.md` §12.5 and `23-evals-guardrails.md` §3 — not re-derived:

- Prompt injection (direct and indirect via poisoned corpus content) — layered rails + structural separators + retrieval-rail scan
- Fabricated conversation history — server-side reconstruction only, client history never accepted (`22-memory-context.md`)
- ACL bypass via citation fabrication — closed by DEC-088 (mechanical check validates against `reranked_set`, not the raw pre-authorization `retrieval_set`)
- Rate-limit abuse / demo-widget flooding — NFR-017

## Security Test Plan

This is intentionally a pointer, not a restatement — `11-test-plan.md` (this phase) owns the executable security test suite (prompt-injection adversarial set, JWT algorithm-rejection tests, rate-limit load tests, widget CSP scan). This file states *what security posture* those tests verify; `11-test-plan.md` states the tests themselves.

## Explicit Scope Boundary (Restated, Not to Be Exceeded)

This file does **not** include: a compliance certification roadmap, a data processing agreement template, a formal risk-assessment methodology, or an IRAP/ASD Essential Eight attestation package. Per DEC-006 and `confirmed-context.md` §7, these remain deferred to the first regulated-buyer engagement that actually requires them. Producing any of these now, speculatively, would be scope creep beyond what this slot's own stated purpose ("placeholder spec slot 42 only") calls for.

## Dependencies

- `confirmed-context.md` §7 (Authority table — "Compliance scope: Deferred to first regulated buyer")
- `04-architecture.md` §12.5 (STRIDE threat model, source of truth)
- `05-data-model.md` (privacy classification, retention rules)
- `09-deployment-ops.md` (encryption-at-rest runbook, secrets management)
- `41-integration-contracts.md` (two-layer authorization, auth model)
- `01-product-brief.md` §6 (non-goals: certifications not committed for MVP)
- `13-decision-log.md` DEC-006, DEC-045, DEC-048, DEC-055, DEC-061, DEC-062, DEC-063, DEC-064, DEC-066, DEC-070, DEC-072, DEC-077, DEC-088, DEC-106, DEC-109, DEC-116

## Decision References

DEC-006, DEC-045, DEC-048, DEC-055, DEC-061, DEC-062, DEC-063, DEC-064, DEC-066, DEC-070, DEC-072, DEC-077, DEC-088, DEC-106, DEC-109, DEC-116
