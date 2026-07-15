"""bge-m3's own tokenizer, used for token-accurate chunk sizing.

Character counting or a different vocabulary (e.g. tiktoken, OpenAI's BPE)
drifts from bge-m3's real XLM-RoBERTa/SentencePiece token boundaries and
degrades sparse-vector feature quality -- found during risk review,
2026-07-15 (`.scratch/document-ingest-pipeline/issues/01-plaintext-markdown-ingest-pipeline.md`).
"""

from __future__ import annotations

from typing import Protocol

from tokenizers import Tokenizer

BGE_M3_MODEL_ID = "BAAI/bge-m3"


class TextTokenizer(Protocol):
    """Minimal tokenizer surface the chunker depends on."""

    def encode(self, text: str) -> list[int]: ...

    def decode(self, token_ids: list[int]) -> str: ...


class BgeM3Tokenizer:
    """Real tokenizer, loaded from bge-m3's own HuggingFace Hub config."""

    def __init__(self) -> None:
        self._tokenizer = Tokenizer.from_pretrained(BGE_M3_MODEL_ID)

    def encode(self, text: str) -> list[int]:
        return self._tokenizer.encode(text).ids

    def decode(self, token_ids: list[int]) -> str:
        return self._tokenizer.decode(token_ids)


class FakeTokenizer:
    """Deterministic, offline stand-in for tests that exercise chunking
    orchestration rather than tokenizer correctness itself -- whitespace
    splitting, one token per word, so chunk boundaries are easy to predict
    and no network access is needed on every test run.

    Assigns each distinct word an id the first time `encode` sees it and
    remembers the mapping, so `decode` is correct regardless of how many
    other `encode` calls happened first on the same instance (a per-call
    `self._words` cache would silently decode against the wrong text once
    `encode` is called more than once)."""

    def __init__(self) -> None:
        self._id_to_word: dict[int, str] = {}
        self._word_to_id: dict[str, int] = {}

    def encode(self, text: str) -> list[int]:
        ids: list[int] = []
        for word in text.split(" "):
            if word not in self._word_to_id:
                new_id = len(self._word_to_id)
                self._word_to_id[word] = new_id
                self._id_to_word[new_id] = word
            ids.append(self._word_to_id[word])
        return ids

    def decode(self, token_ids: list[int]) -> str:
        return " ".join(self._id_to_word[i] for i in token_ids)
