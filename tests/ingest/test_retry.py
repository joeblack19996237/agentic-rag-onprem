"""Tests for ingest/retry.py -- Full Jitter backoff for embedding-service
outage retries. See the AC in
`.scratch/document-ingest-pipeline/issues/02-pdf-word-parsing-retry-resilience.md`:
computing the backoff delay for the same attempt count across multiple
concurrently-retrying jobs must not produce identical delays.
"""

from __future__ import annotations

from ingest.retry import compute_backoff_delay


def test_backoff_delay_is_jittered_not_deterministic() -> None:
    delays = {compute_backoff_delay(attempt=3) for _ in range(30)}
    assert len(delays) > 1


def test_backoff_delay_is_non_negative() -> None:
    for attempt in range(10):
        assert compute_backoff_delay(attempt) >= 0


def test_backoff_delay_never_exceeds_the_cap() -> None:
    for _ in range(50):
        assert compute_backoff_delay(attempt=20, base=1.0, cap=10.0) <= 10.0


def test_backoff_delay_ceiling_grows_with_attempt() -> None:
    # Not a statistical assertion on any single draw -- the *ceiling*
    # (base * 2**attempt) is deterministic even though the draw isn't;
    # sampling enough times should reliably show attempt=5's max exceeding
    # attempt=0's max.
    low_attempt_max = max(compute_backoff_delay(attempt=0, base=0.1, cap=1000.0) for _ in range(20))
    high_attempt_max = max(compute_backoff_delay(attempt=5, base=0.1, cap=1000.0) for _ in range(20))
    assert high_attempt_max > low_attempt_max
