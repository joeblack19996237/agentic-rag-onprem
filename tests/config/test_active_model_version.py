"""Tests for config/active_model_version.py -- the runtime query the
ingest pipeline uses to pick the target Qdrant collection name via
ingest/qdrant_setup.py's build_collection_name."""

from __future__ import annotations

import pytest

from config.active_model_version import NoActiveModelVersionError, get_active_model_version
from config.models import ModelVersion


def test_returns_the_model_version_of_the_active_row(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "bge-m3-v2"

    result = get_active_model_version(session, role="embedding")

    assert result == "bge-m3-v2"


def test_raises_when_no_active_row_for_role(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(NoActiveModelVersionError):
        get_active_model_version(session, role="embedding")


def test_query_filters_on_role_and_is_active(mocker) -> None:  # type: ignore[no-untyped-def]
    session = mocker.MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "bge-m3-v2"

    get_active_model_version(session, role="embedding")

    compiled = str(session.execute.call_args[0][0])
    assert "model_versions" in compiled
    assert "role" in compiled
    assert "is_active" in compiled


def test_selects_model_version_column_of_model_version_table() -> None:
    # Sanity check that the query targets the real table/column names,
    # not a typo -- ModelVersion is imported so a rename would be caught
    # by mypy/import errors elsewhere, this just documents the intent.
    assert ModelVersion.__tablename__ == "model_versions"
