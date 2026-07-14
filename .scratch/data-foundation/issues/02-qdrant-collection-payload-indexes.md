Status: ready-for-agent

# Issue 02: Qdrant Collection + Payload Indexes

> Source: `specs/10-build-plan.md` TASK-007 (Phase 2). Traces to `specs/02-requirements.md` REQ-003, NFR-003 and `specs/13-decision-log.md` DEC-059, DEC-086. Physical schema source: `specs/07-database.md`'s Qdrant Collections section. Verification Pattern: TDD-Exempt — Infrastructure-as-Code.

## Parent

None — traces directly to `specs/10-build-plan.md` TASK-007, no parent issue.

## What to build

One Qdrant collection, named `<corpus_id>_<embedding_model_version>` (e.g. `default_bge-m3-v2`, per DEC-059's double-collection convention), configured with both dense and sparse vectors (`bge-m3` dense + lexical output, DEC-086 — a collection with only a dense vector is not valid). Five mandatory payload indexes created before any ingest can write to it: `allow_principals`, `deny_principals`, `retention_state`, `document_id`, `security_label` (all keyword indexes, per `specs/07-database.md`'s Payload Indexes table).

Verified against the real `qdrant-client` library (already pinned, 1.18.0) running in embedded local mode (`QdrantClient(":memory:")`) wherever that's honest, per `specs/13-decision-log.md` DEC-140/DEC-141: collection vector configuration and Layer 1 filter/query semantics are genuinely provable this way — confirmed empirically this session with a real passing test, not just documentation. **Payload-index existence is not** — local mode silently no-ops `create_payload_index()` (a real `UserWarning: Payload indexes have no effect in the local Qdrant`, and `get_collection().payload_schema` stays an empty dict after calling it for all 5 fields, confirmed empirically). That criterion below uses a call-inspection proxy instead of an existence check.

## Acceptance criteria

- [ ] Collection created with both dense and sparse vector configuration
      Verification: pytest against `QdrantClient(":memory:")` — create the collection, then `client.get_collection(name).config.params.vectors` and `.sparse_vectors` both show the expected configuration
- [ ] Layer 1 filter semantics behave correctly: a point whose `allow_principals` intersects the query's `effective_principals` is returned; a point whose `deny_principals` intersects it is excluded; a point with `retention_state != active` is excluded
      Verification: pytest seeding 3+ points with varied `allow_principals`/`deny_principals`/`retention_state` payloads into a `QdrantClient(":memory:")` collection, running the Layer 1 filtered query, asserting exactly the expected point-id subset returns (not a superset or subset)
- [ ] The collection-setup code calls the payload-index-creation method for all 5 mandatory fields with the correct field name and index type
      Verification: pytest using `mocker.spy` (`pytest-mock`, **pin `pytest-mock==3.15.1` in `requirements-dev.txt` first** — confirmed live-installable via `pip install --dry-run pytest-mock`, 2026-07-14, not currently pinned despite happening to be present in this session's environment) on the client's `create_payload_index` method during setup, asserting it is called exactly 5 times with `field_name` in `{allow_principals, deny_principals, retention_state, document_id, security_label}` and `field_schema` set to the keyword-index type — a call-inspection proxy, not an existence check, since local mode makes existence unobservable (see above)
- [ ] NFR-003 schema-neutrality (mechanical proxy only — see note below): the payload field-name set matches `specs/07-database.md`'s documented list exactly, with no English-only-coded field name
      Verification: pytest asserting the collection's payload field names are exactly the documented set (`document_id`, `version_id`, `repository_id`, `chunk_id`, `sequence`, `text`, `embedding_model_version`, `allow_principals`, `deny_principals`, `security_label`, `retention_state`, `frozen_at`)

**Note on NFR-003's full scope** (not a checkbox — neither pytest-verifiable nor infra-gated, so it doesn't fit either the Acceptance Criteria or Manual Verification pattern above): the field-name check catches one failure mode (an English-coded field name) but not another — a tokenizer/analyzer config baked into the schema that assumes English text. No command can certify the absence of that; whoever reviews this issue's PR should explicitly confirm it during review, as a judgment call, not an automated check.

## Manual verification

- [ ] [manual-verify] All 5 payload indexes actually exist against a real Qdrant server and hold filter-then-search recall at scale versus an unfiltered baseline.
      Owner: DevOps / dev rig. Evidence to capture: `client.get_collection(name).payload_schema` output from a live server showing all 5 fields indexed, plus the recall-comparison test output `specs/09-deployment-ops.md`'s methodology calls for (filtered vs. unfiltered baseline recall on non-restricted content).

## Owner Role

Backend (per `specs/10-build-plan.md` TASK-007)

## Rollback Plan

Drop the collection and recreate it with the corrected configuration. No chunk data exists yet at this point (TASK-008/009's ingest pipeline depends on this issue, not the reverse), so rollback is a clean collection recreation, not a data migration (per TASK-007's own Rollback Plan).

## Blocked by

None - can start immediately (TASK-001 already done)
