"""Tests for ingest/parsing.py -- format-dispatched document parsing.

.md/.txt use direct UTF-8 decode (no external library). PDF uses
pdfminer.six primary + PyMuPDF rescue (DEC-143); DOCX uses python-docx
directly. Real PDF/DOCX fixtures come from pdf_docx_fixtures.py's
build_pdf_bytes/build_docx_bytes (shared with test_pipeline.py, imported
bare -- pytest's own sys.path insertion for this directory, same pattern
as tests/docs/doc_drift.py) rather than committing binary fixture files.
"""

from __future__ import annotations

import pytest
from pdf_docx_fixtures import build_docx_bytes, build_pdf_bytes

from ingest.parsing import DocumentDecodeError, ParseResult, UnsupportedFormatError, parse_document


# --- .md / .txt -------------------------------------------------------------


def test_parses_markdown_as_utf8_text() -> None:
    result = parse_document(b"# Title\n\nBody text.", "notes.md")
    assert result == ParseResult(text="# Title\n\nBody text.", used_fallback_parser=None)


def test_parses_txt_as_utf8_text() -> None:
    result = parse_document(b"plain text", "notes.txt")
    assert result.text == "plain text"
    assert result.used_fallback_parser is None


def test_invalid_utf8_raises_decode_error() -> None:
    with pytest.raises(DocumentDecodeError):
        parse_document(b"\xff\xfe not valid utf-8", "notes.txt")


# --- PDF ----------------------------------------------------------------------


def test_pdf_happy_path_uses_pdfminer_primary_parser() -> None:
    pdf_bytes = build_pdf_bytes("Hello from pdfminer primary")
    result = parse_document(pdf_bytes, "report.pdf")
    assert "Hello from pdfminer primary" in result.text
    assert result.used_fallback_parser is False


def test_pdf_rescue_path_fires_when_primary_parser_raises(mocker) -> None:  # type: ignore[no-untyped-def]
    mocker.patch("ingest.parsing.pdfminer_extract_text", side_effect=ValueError("malformed PDF"))
    pdf_bytes = build_pdf_bytes("Hello from PyMuPDF rescue")

    result = parse_document(pdf_bytes, "report.pdf")

    assert "Hello from PyMuPDF rescue" in result.text
    assert result.used_fallback_parser is True


def test_pdf_raises_decode_error_when_both_primary_and_rescue_parsers_fail(mocker) -> None:  # type: ignore[no-untyped-def]
    mocker.patch("ingest.parsing.pdfminer_extract_text", side_effect=ValueError("malformed PDF"))

    with pytest.raises(DocumentDecodeError):
        parse_document(b"not a real pdf at all", "report.pdf")


# --- DOCX -----------------------------------------------------------------------


def test_docx_happy_path_uses_python_docx() -> None:
    docx_bytes = build_docx_bytes("Hello from python-docx")
    result = parse_document(docx_bytes, "memo.docx")
    assert "Hello from python-docx" in result.text
    assert result.used_fallback_parser is None


def test_docx_raises_decode_error_on_malformed_bytes() -> None:
    with pytest.raises(DocumentDecodeError):
        parse_document(b"not a real docx file", "memo.docx")


# --- unsupported format --------------------------------------------------------


def test_unsupported_format_raises() -> None:
    with pytest.raises(UnsupportedFormatError):
        parse_document(b"irrelevant", "image.png")
