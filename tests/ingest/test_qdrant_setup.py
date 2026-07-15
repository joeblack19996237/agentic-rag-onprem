"""Verifies ingest/qdrant_setup.py against
.scratch/data-foundation/issues/02-qdrant-collection-payload-indexes.md's
acceptance criteria.

Vector config and Layer 1 filter semantics run against a real
`QdrantClient(":memory:")` -- confirmed empirically (specs/13-decision-log.md
DEC-140) that local mode implements these correctly. Payload-index
*existence* cannot be checked this way -- local mode silently no-ops
`create_payload_index()` (DEC-141) -- so that criterion uses a call-inspection
proxy (`mocker.spy`) instead; real existence is `[manual-verify]` against a
live server, per this issue's Manual Verification section.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue, PointStruct

from ingest.qdrant_setup import (
    DENSE_VECTOR_NAME,
    DENSE_VECTOR_SIZE,
    MANDATORY_PAYLOAD_INDEXES,
    SPARSE_VECTOR_NAME,
    build_collection_name,
    create_collection,
    resolve_index_target,
)

COLLECTION = build_collection_name("default", "bge-m3-v2")


def test_collection_name_follows_corpus_embedding_version_convention():
    assert COLLECTION == "default_bge-m3-v2"


def test_collection_created_with_dense_and_sparse_vector_config():
    client = QdrantClient(":memory:")
    create_collection(client, COLLECTION)

    info = client.get_collection(COLLECTION)

    assert DENSE_VECTOR_NAME in info.config.params.vectors
    assert info.config.params.vectors[DENSE_VECTOR_NAME].size == DENSE_VECTOR_SIZE
    assert info.config.params.sparse_vectors is not None
    assert SPARSE_VECTOR_NAME in info.config.params.sparse_vectors


def test_layer1_filter_semantics_correct():
    client = QdrantClient(":memory:")
    create_collection(client, COLLECTION)

    dummy_vector = [0.1] * DENSE_VECTOR_SIZE
    client.upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=1,
                vector={DENSE_VECTOR_NAME: dummy_vector},
                payload={
                    "allow_principals": ["group:eng"],
                    "deny_principals": [],
                    "retention_state": "active",
                    "document_id": "d1",
                },
            ),
            PointStruct(
                id=2,
                vector={DENSE_VECTOR_NAME: dummy_vector},
                payload={
                    "allow_principals": ["group:eng"],
                    "deny_principals": ["user:bob"],
                    "retention_state": "active",
                    "document_id": "d2",
                },
            ),
            PointStruct(
                id=3,
                vector={DENSE_VECTOR_NAME: dummy_vector},
                payload={
                    "allow_principals": ["group:eng"],
                    "deny_principals": [],
                    "retention_state": "expired",
                    "document_id": "d3",
                },
            ),
        ],
    )

    results = client.query_points(
        collection_name=COLLECTION,
        query=dummy_vector,
        using=DENSE_VECTOR_NAME,
        query_filter=Filter(
            must=[
                FieldCondition(key="allow_principals", match=MatchAny(any=["group:eng"])),
                FieldCondition(key="retention_state", match=MatchValue(value="active")),
            ],
            must_not=[
                FieldCondition(key="deny_principals", match=MatchAny(any=["user:bob"])),
            ],
        ),
        limit=10,
    )

    returned_ids = sorted(p.id for p in results.points)
    assert returned_ids == [1]


def test_create_payload_index_called_for_all_five_mandatory_fields(mocker):
    client = QdrantClient(":memory:")
    spy = mocker.spy(client, "create_payload_index")

    create_collection(client, COLLECTION)

    assert spy.call_count == 5
    called_field_names = {call.kwargs["field_name"] for call in spy.call_args_list}
    assert called_field_names == set(MANDATORY_PAYLOAD_INDEXES)


def test_resolve_index_target_builds_collection_name_from_active_model_version(mocker):
    session = mocker.MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "bge-m3-v2"

    target = resolve_index_target(session, "default")

    assert target.embedding_model_version == "bge-m3-v2"
    assert target.collection_name == "default_bge-m3-v2"


def test_mandatory_index_field_names_match_documented_set_exactly():
    """NFR-003 mechanical proxy, narrowed during /implement -- see this
    issue's own note on why the check is scoped to the 5 indexed fields,
    not the full chunk payload (which this module never writes)."""
    assert set(MANDATORY_PAYLOAD_INDEXES) == {
        "allow_principals",
        "deny_principals",
        "retention_state",
        "document_id",
        "security_label",
    }
