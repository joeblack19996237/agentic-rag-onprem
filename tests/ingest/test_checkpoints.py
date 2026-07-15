"""Tests for ingest/checkpoints.py -- local-filesystem storage for bulk
step output, kept out of job_queue.payload (risk review, 2026-07-15)."""

from __future__ import annotations

import uuid
from pathlib import Path

from ingest.checkpoints import read_checkpoint, write_checkpoint


def test_write_then_read_checkpoint_round_trips(tmp_path: Path) -> None:
    job_id = uuid.uuid4()
    data = {"text": "parsed document content", "pages": 3}

    path = write_checkpoint(tmp_path, job_id, "parsed", data)

    assert read_checkpoint(path) == data


def test_write_checkpoint_creates_the_base_directory_if_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / "does_not_exist_yet"
    path = write_checkpoint(base_dir, uuid.uuid4(), "parsed", {"ok": True})
    assert Path(path).exists()


def test_different_jobs_get_different_checkpoint_files(tmp_path: Path) -> None:
    path_a = write_checkpoint(tmp_path, uuid.uuid4(), "parsed", {"job": "a"})
    path_b = write_checkpoint(tmp_path, uuid.uuid4(), "parsed", {"job": "b"})
    assert path_a != path_b
    assert read_checkpoint(path_a) == {"job": "a"}
    assert read_checkpoint(path_b) == {"job": "b"}


def test_different_steps_of_the_same_job_get_different_checkpoint_files(tmp_path: Path) -> None:
    job_id = uuid.uuid4()
    parsed_path = write_checkpoint(tmp_path, job_id, "parsed", {"step": "parsed"})
    chunked_path = write_checkpoint(tmp_path, job_id, "chunked", {"step": "chunked"})
    assert parsed_path != chunked_path
