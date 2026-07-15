"""Shared in-memory fixture builders for tests/ingest/ -- real PDF/DOCX
bytes built with PyMuPDF/python-docx themselves rather than committed as
binary fixture files (used by test_parsing.py and test_pipeline.py)."""

from __future__ import annotations

import io

import docx
import pymupdf


def build_pdf_bytes(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def build_docx_bytes(text: str) -> bytes:
    document = docx.Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
