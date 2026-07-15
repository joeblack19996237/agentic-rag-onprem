"""Tests for acl/ingest_stub.py -- the disposable Layer 1 ACL lookup the
ingest pipeline uses. Not a test of TASK-013's future real adapter, which
doesn't exist yet."""

from __future__ import annotations

import uuid

import pytest

from acl.ingest_stub import ACLLookupError, EffectiveACL, FakeACLLookup, SqlAlchemyACLLookup
from ingest.identity import DocumentIdentity
from ingest.models import DocumentVersion


def _identity(document_id: uuid.UUID | None = None) -> DocumentIdentity:
    return DocumentIdentity(document_id=document_id or uuid.uuid4(), version_id="v1", repository_id="default")


def test_fake_acl_lookup_returns_seeded_effective_acl() -> None:
    lookup = FakeACLLookup()
    identity = _identity()
    acl = EffectiveACL(allow_principals=["group:eng"], deny_principals=[], security_label="internal")
    lookup.seed(identity, acl=acl, retention_state="active")

    assert lookup.get_effective_acl(identity) == acl
    assert lookup.get_retention_state(identity) == "active"


def test_fake_acl_lookup_raises_on_unseeded_document() -> None:
    lookup = FakeACLLookup()
    with pytest.raises(ACLLookupError):
        lookup.get_effective_acl(_identity())


def test_fake_acl_lookup_raises_retention_lookup_on_unseeded_document() -> None:
    lookup = FakeACLLookup()
    with pytest.raises(ACLLookupError):
        lookup.get_retention_state(_identity())


def test_sqlalchemy_acl_lookup_maps_document_version_row_to_effective_acl(mocker) -> None:  # type: ignore[no-untyped-def]
    identity = _identity()
    row = DocumentVersion(
        document_id=identity.document_id,
        version_id=identity.version_id,
        allow_principals=["group:eng"],
        deny_principals=["user:contractor-42"],
        security_label="confidential",
        retention_state="active",
    )
    session = mocker.MagicMock()
    session.get.return_value = row

    lookup = SqlAlchemyACLLookup(session)
    acl = lookup.get_effective_acl(identity)

    assert acl == EffectiveACL(
        allow_principals=["group:eng"], deny_principals=["user:contractor-42"], security_label="confidential"
    )
    session.get.assert_called_once_with(DocumentVersion, (identity.document_id, identity.version_id))


def test_sqlalchemy_acl_lookup_maps_document_version_row_to_retention_state(mocker) -> None:  # type: ignore[no-untyped-def]
    identity = _identity()
    row = DocumentVersion(
        document_id=identity.document_id,
        version_id=identity.version_id,
        allow_principals=[],
        deny_principals=[],
        security_label="internal",
        retention_state="legal_hold",
    )
    session = mocker.MagicMock()
    session.get.return_value = row

    lookup = SqlAlchemyACLLookup(session)
    assert lookup.get_retention_state(identity) == "legal_hold"


def test_sqlalchemy_acl_lookup_raises_when_no_row_found(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.get.return_value = None

    lookup = SqlAlchemyACLLookup(session)
    with pytest.raises(ACLLookupError):
        lookup.get_effective_acl(_identity())
