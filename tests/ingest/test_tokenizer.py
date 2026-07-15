"""Tests for ingest/tokenizer.py -- bge-m3's own tokenizer for chunk sizing."""

from __future__ import annotations

from ingest.tokenizer import BgeM3Tokenizer, FakeTokenizer


def test_fake_tokenizer_round_trips_word_boundaries() -> None:
    tok = FakeTokenizer()
    text = "one two three four five"
    ids = tok.encode(text)
    assert len(ids) == 5
    assert tok.decode(ids) == text


def test_fake_tokenizer_slice_decodes_to_the_matching_substring() -> None:
    tok = FakeTokenizer()
    ids = tok.encode("alpha beta gamma delta")
    assert tok.decode(ids[1:3]) == "beta gamma"


def test_bge_m3_tokenizer_produces_real_sentencepiece_tokens() -> None:
    """Needs outbound network access on first run in a fresh environment --
    downloads BAAI/bge-m3's tokenizer config from HuggingFace Hub, then
    caches it locally (huggingface_hub's standard cache behavior). Confirmed
    reachable in this sandbox, 2026-07-15 -- not a live-service Tier-3
    dependency in the DEC-135 sense (a one-time small config download, not
    an ongoing service call).
    """
    tok = BgeM3Tokenizer()
    ids = tok.encode("This is a test sentence.")
    assert len(ids) > 0
    assert "test sentence" in tok.decode(ids).lower()


def test_bge_m3_tokenizer_is_not_character_count() -> None:
    """A 40-character sentence should not encode to 40 tokens -- guards
    against a regression back to character-count-as-token-count, the exact
    mistake flagged during risk review (2026-07-15)."""
    tok = BgeM3Tokenizer()
    text = "This is a test sentence for tokenization."
    assert len(tok.encode(text)) < len(text) // 2
