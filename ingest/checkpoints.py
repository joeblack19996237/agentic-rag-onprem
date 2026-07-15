"""Local-filesystem checkpoint storage for bulk step output.

`job_queue.payload` stays lightweight (phase, progress, small flags) --
bulk intermediate data (parsed text, chunk lists) lives here instead, to
avoid Postgres WAL/TOAST write amplification on multi-MB documents (risk
review, 2026-07-15). Mirrors the host-mounted-volume pattern
`specs/07-database.md` already uses for Postgres/Qdrant's own data --
`job_queue.payload` stores a pointer to a file here, never the content.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

CheckpointStep = Literal["parsed", "chunked"]

DEFAULT_CHECKPOINT_DIR = Path("./ingest_checkpoints")


def write_checkpoint(base_dir: Path, job_id: uuid.UUID, step: CheckpointStep, data: object) -> str:
    """Writes `data` as JSON to a job- and step-scoped file, returns its
    path. `step` is always one of this module's own internal constants,
    never passed through from external input, so there's no path-traversal
    surface to guard against here."""
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{job_id}-{step}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def read_checkpoint(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))
