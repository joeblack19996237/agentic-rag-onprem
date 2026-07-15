"""Full Jitter backoff for embedding-service (TEI) outage retries
(`ingest/pipeline.py`'s embed+index step), per the risk-review requirement
in `.scratch/document-ingest-pipeline/issues/02-pdf-word-parsing-retry-resilience.md`:
a non-jittered backoff risks a thundering-herd retry storm re-crashing a
just-recovered, still-fragile TEI instance.

AWS's well-known "Full Jitter" formula: `sleep = random_between(0, min(cap,
base * 2**attempt))` -- randomizes the full delay range rather than only
adding jitter on top of a deterministic exponential value, which spreads
concurrently-backed-off jobs' retry timestamps instead of synchronizing them.
"""

from __future__ import annotations

import random

DEFAULT_BASE_DELAY_SECONDS = 0.5
DEFAULT_MAX_DELAY_SECONDS = 60.0


def compute_backoff_delay(
    attempt: int,
    base: float = DEFAULT_BASE_DELAY_SECONDS,
    cap: float = DEFAULT_MAX_DELAY_SECONDS,
) -> float:
    ceiling = min(cap, base * 2**attempt)
    return random.uniform(0, ceiling)
