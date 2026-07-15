"""Format-dispatched document parsing: plain text decode, PDF (pdfminer.six
primary + PyMuPDF rescue), Word (python-docx) -- DEC-036, corrected for PDF
by DEC-143, 2026-07-15.

**PDF**: Unstructured.io was DEC-036's original primary PDF parser, but its
PDF module (`unstructured.partition.pdf`) has an unconditional, module-level
import of `unstructured_inference`, which -- with its own dependency
`effdet` -- pulls in a full torch/OCR stack (torch, torchvision,
transformers, onnxruntime, opencv-python, pycocotools, accelerate)
regardless of which parse strategy is requested. `pdfminer.six`'s own
`extract_text()` is used directly instead -- lightweight (only
charset-normalizer + cryptography), no ML/OCR dependency. PyMuPDF remains
the rescue path, unchanged from DEC-036.

**Word**: `python-docx` directly, exactly as DEC-036 originally specified
(Word was never routed through Unstructured).

See `specs/13-decision-log.md` DEC-143 for the full rationale.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import docx
import pymupdf
from pdfminer.high_level import extract_text as pdfminer_extract_text

SUPPORTED_EXTENSIONS = (".md", ".txt", ".pdf", ".docx")


class UnsupportedFormatError(ValueError):
    """Raised for any upload whose extension isn't in SUPPORTED_EXTENSIONS.
    The caller (eventually TASK-033's HTTP layer) maps this to a 415."""


class DocumentDecodeError(ValueError):
    """Raised when a document's bytes can't be parsed into text. Its
    message currently interpolates the raw underlying library exception
    text verbatim -- fine today, since no HTTP boundary exists yet
    (nothing in this diff crosses one), but whoever wires TASK-033's
    `POST /v1/ingest` route must redact this message before it reaches an
    HTTP response (coding-standards.md's error-handling boundary rule
    against leaking internal detail across a trust boundary; not yet a
    live violation, code-review finding, 2026-07-15 -- same shape as
    `JobStore.fail()`'s existing note in `ingest/job_store.py`)."""


@dataclass(frozen=True)
class ParseResult:
    text: str
    # None = fallback/rescue is not a concept for this format (.md/.txt/.docx).
    # True/False only apply to PDF (whether the PyMuPDF rescue path fired).
    used_fallback_parser: bool | None = None


def parse_document(file_bytes: bytes, filename: str) -> ParseResult:
    lowered = filename.lower()
    if lowered.endswith((".md", ".txt")):
        return _parse_plain_text(file_bytes)
    if lowered.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    if lowered.endswith(".docx"):
        return _parse_docx(file_bytes)
    raise UnsupportedFormatError(f"Unsupported format: {filename!r}. Supported: {SUPPORTED_EXTENSIONS}")


def _parse_plain_text(file_bytes: bytes) -> ParseResult:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentDecodeError(f"Upload is not valid UTF-8 text: {exc}") from exc
    return ParseResult(text=text)


def _parse_pdf(file_bytes: bytes) -> ParseResult:
    # Broad `except Exception` is deliberate here, not a swallowed error:
    # pdfminer.six can raise many different exception types for malformed
    # PDF structure (PDFSyntaxError, PDFEncryptionError, PSEOF, plain
    # ValueError/TypeError on corrupt streams) and any of them should
    # trigger the PyMuPDF rescue path, per DEC-036's two-tier design. If
    # the rescue path also fails, that failure is wrapped and re-raised
    # below -- nothing vanishes silently.
    try:
        text = pdfminer_extract_text(io.BytesIO(file_bytes))
        return ParseResult(text=text, used_fallback_parser=False)
    except Exception as primary_exc:
        try:
            text = _parse_pdf_with_pymupdf(file_bytes)
        except Exception as rescue_exc:
            raise DocumentDecodeError(
                f"PDF parse failed on both the primary parser ({primary_exc}) "
                f"and the PyMuPDF rescue path ({rescue_exc})"
            ) from rescue_exc
        return ParseResult(text=text, used_fallback_parser=True)


def _parse_pdf_with_pymupdf(file_bytes: bytes) -> str:
    with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
        return "\n".join(page.get_text() for page in document)


def _parse_docx(file_bytes: bytes) -> ParseResult:
    # Broad `except Exception` is deliberate, same reasoning as _parse_pdf
    # above: python-docx can raise several different exception types for a
    # malformed .docx (BadZipFile, XML parse errors, KeyError on a missing
    # required part) -- all of them are equally "not a valid Word document"
    # from this function's caller's point of view, wrapped into one domain
    # error rather than leaking a library-specific exception type.
    try:
        document = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise DocumentDecodeError(f"DOCX parse failed: {exc}") from exc
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return ParseResult(text=text)
