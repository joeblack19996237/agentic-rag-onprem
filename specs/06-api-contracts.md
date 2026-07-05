# 06 — API Contracts (STUB — added 2026-07-05, DEC-107)

> **This is a stub, not a complete contract.** It exists so the endpoint surface has exactly one canonical home instead of being scattered across `04-architecture.md` (where four endpoints were referenced but never listed in §7, discovered during the 2026-07-05 API-contract review pass). Full request/response JSON Schema, error-code enumeration, and OpenAPI generation are a **Stage 6 deliverable** — do not treat the shapes below as final.
>
> Source of truth for *behavior* (what each endpoint does, why) remains `04-architecture.md` §7 and the cross-referenced sections noted per endpoint below. This file's job is enumeration + shape sketch, not re-deriving rationale.

## Auth

All endpoints require JWT bearer (RS256/ES256/EdDSA, DEC-061) or admin API key, except `GET /ready` (NFR-009). Rate limiting per NFR-017.

## 1. Query API

| Endpoint | Sketch | Behavior source |
|---|---|---|
| `POST /v1/query` | Req: `{query: str, conversation_id?: str}` — Res: `{answer: str, citations: Citation[], refusal_reason?: RefusalClass, audit_id: str, latency_ms: int}` | `04-architecture.md` §7.1, §12.1 (refusal taxonomy) |

`RefusalClass` = `no_recall \| low_grounding \| access_denied \| policy_blocked \| verification_unavailable` (DEC-042, single source of truth in `13-decision-log.md`).

## 2. Ingest API

| Endpoint | Sketch | Behavior source |
|---|---|---|
| `POST /v1/ingest` | multipart upload → `{document_id: str, status_url: str}` | `04-architecture.md` §7.2 |
| `GET /v1/ingest/{document_id}` | → `{status: pending\|parsing\|indexing\|ready\|failed, progress: float, errors: string[]}` | `04-architecture.md` §7.2 |

## 3. Admin API

| Endpoint | Sketch | Behavior source |
|---|---|---|
| `GET/PUT /v1/admin/documents` | list, soft-delete, ACL edit | `04-architecture.md` §7.3 |
| `GET /v1/admin/audit` | query params `from`, `to`, `user_id`; paginated | `04-architecture.md` §7.3, REQ-007 |
| `PUT /v1/admin/config/thresholds` | refusal threshold config | NFR-010 |
| `GET/PUT /v1/admin/config/models` | model adapter swap (V2) | REQ-033 |
| `POST /v1/admin/eval` | trigger golden-set eval run | REQ-013, REQ-014, `23-evals-guardrails.md` §2.3 |
| `POST /v1/admin/acl/refresh_user/{user_id}` | force-refresh `effective_principals[]` cache ahead of TTL | `04-architecture.md` §7B.5 |
| `POST /v1/admin/acl/refresh_doc/{doc_id}` | force-refresh Layer 2 PDP cache ahead of TTL | `04-architecture.md` §7B.5 |
| `PUT /v1/admin/config/cdc` | set `cdc_transport_mode` (`webhook`\|`poll_only`) + poll interval | REQ-057, NFR-032, DEC-102 |

## 4. Operational surface

| Endpoint | Sketch | Behavior source |
|---|---|---|
| `GET /ready` | health check; 200 gates widget load and install verification; unauthenticated | REQ-011, `04-architecture.md` §9.1 |

## Open items for Stage 6 (do not resolve here)

- Full JSON Schema / Pydantic models per endpoint
- Error response shape (HTTP status + typed error body) beyond the refusal-as-200 pattern already fixed by DEC-042
- OpenAPI 3.x generation pipeline and versioning policy
- Pagination cursor shape for `GET /v1/admin/audit`
- Whether `POST /v1/admin/eval` is synchronous or returns a `status_url` like ingest does — not yet decided
