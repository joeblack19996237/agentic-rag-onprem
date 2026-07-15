Status: ready-for-agent

# Issue 01: Auth Foundation + OpenAPI Contract Scaffolding + Query Stub

> Source: `specs/10-build-plan.md` TASK-033 (Phase 2, partial — auth middleware, OpenAPI schema-drift infrastructure, and the `POST /v1/query` stub route only; ingest/admin routes are Issues 02-04). Traces to `specs/02-requirements.md` REQ-008. `specs/06-api-contracts.md`'s Authentication/Versioning sections and API-Q-01 (Query API stub). `specs/13-decision-log.md` DEC-061 (JWT alg whitelist), DEC-062 (air-gap JWKS), DEC-107 (API contracts origin), DEC-117 (`/ready` shape, regression-only). Verification Pattern: TDD.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-033. No PRD: TASK-033 is a single, already-well-specified build-plan task (like `data-foundation`'s Issue 01/02, this skips `/to-prd`).

## What to build

Everything every other route in this feature depends on: JWT bearer + admin API key authentication, the OpenAPI schema-drift contract test, and `POST /v1/query` registered as a deliberate, temporary stub. This issue delivers no product-visible query/ingest/admin behavior by itself — it's the prefactor that makes Issues 02-04's routes protectable and their combined schema snapshottable in one place, rather than each issue reinventing auth.

**Auth.** Two acceptable credentials per route, per `06-api-contracts.md`'s Authentication section:
- JWT bearer, algorithm-whitelisted to RS256/ES256/EdDSA only (DEC-061) — HS256/HS384/HS512 and `none` must be rejected even if the token is otherwise well-formed and signed with a key the server would accept under a whitelisted algorithm. This is a known JWT vulnerability class (alg confusion / alg=none bypass), not a hypothetical edge case.
- Admin API key, as a flat alternative to JWT on admin-scoped routes (NFR-009) — a config-driven static value (e.g. an env var compared against a header), not a database-backed key registry; that's out of scope here.

JWKS comes from a static, pre-imported bundle (air-gap install, DEC-062) — no live OIDC/JWKS-endpoint fetch in MVP scope.

**Dependency gap, resolve first**: no JWT library is in `requirements.txt`/`requirements-dev.txt` today. `PyJWT` is the likely pick (smallest surface, a native `algorithms=[...]` allowlist parameter that maps directly onto DEC-061's whitelist) but this is not yet verified — per this repo's dependency-capability-verification rule (`CLAUDE.md`, DEC-142/DEC-143 precedent), empirically confirm the chosen library actually rejects `none`/HS256 and actually validates RS256/ES256/EdDSA against a JWKS-shaped key set before writing the ACs below against it, and pin the version live (PyPI JSON API) rather than from memory.

**Pitfall already found while drafting this issue**: `import jwt` (PyJWT) succeeds in at least one known dev sandbox for this repo *without* being added to any requirements file, because PyJWT happens to ride in as an unrelated transitive dependency of a globally-installed tool (`mcp`) that has nothing to do with this project (confirmed via `pip show pyjwt` → `Required-by: mcp`). This will not hold on a clean CI runner (`.github/workflows/ci.yml` installs only from `requirements.txt` + `requirements-dev.txt`). Add whichever library is chosen to `requirements.txt` explicitly, and don't trust a local green run alone — confirm `pip show <library>`'s `Required-by` doesn't only list unrelated tools, or confirm green on a genuinely clean install.

**OpenAPI schema-drift test.** Generate the OpenAPI schema from the FastAPI app in-process (`app.openapi()` via `TestClient`, no live server needed) and commit an initial snapshot file; the test fails when a future route change drifts from the committed snapshot without updating it. The snapshot's *initial* correspondence to `06-api-contracts.md`'s documented shapes is established once, by hand, at authoring time — this test only catches drift after that point, it does not mechanically re-verify spec-conformance on every run. Say so in the test's own docstring so a future reader doesn't over-read what a passing run means.

**`POST /v1/query` stub.** Registered, auth-enforced, returns `501` — matches this repo's existing pattern for "the real logic isn't built yet" (`GET /ready`'s Phase 1 all-`false` scaffold is the precedent). Real generation logic lands in Phase 3 onward (TASK-011+); this issue's job is only that the route exists, is documented in the OpenAPI schema, and correctly requires auth.

## Acceptance criteria

- [ ] A request to `POST /v1/query` with no bearer token and no admin API key returns `401 unauthenticated` with the standard error shape (`06-api-contracts.md`'s Error Schema)
      Verification: `pytest tests/api/test_auth.py -k missing_credentials -v`
- [ ] A JWT signed with HS256, or an unsigned token with `alg: none`, is rejected with `401` even though it is otherwise well-formed (DEC-061)
      Verification: `pytest tests/api/test_auth.py -k rejects_hs256_and_none -v`
- [ ] A JWT signed with RS256, ES256, or EdDSA, using a key present in a locally-constructed test JWKS bundle, is accepted
      Verification: `pytest tests/api/test_auth.py -k accepts_whitelisted_alg -v`
- [ ] A valid admin API key is accepted as an alternative to a JWT on an admin-scoped route
      Verification: `pytest tests/api/test_auth.py -k admin_api_key -v`
- [ ] `GET /ready` remains reachable with no credentials after auth middleware lands (the sole unauthenticated exception, per `06-api-contracts.md`)
      Verification: `pytest tests/api/test_ready.py::test_ready_returns_dec117_schema_shape -v` (not the whole file — its second test is deliberately red per Phase 1, excluded by `tools/verify.sh`)
- [ ] OpenAPI 3.x schema, generated from the running FastAPI app, matches a committed schema snapshot; an intentionally introduced undocumented route/field change fails the test
      Verification: `pytest tests/api/test_openapi_contract.py -v`
- [ ] `POST /v1/query` is registered, requires auth, and returns `501` (not `404`) for an authenticated request
      Verification: `pytest tests/api/test_query_stub.py -v`

## Blocked by

None - can start immediately (no dependency on TASK-006/009's schema; this issue only touches `api/`)
