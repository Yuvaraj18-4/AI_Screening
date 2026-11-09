import io
from typing import NamedTuple

import docx
import pdfplumber

from app.core.logging import logger


class ExtractionResult(NamedTuple):
    text: str
    is_scan: bool
    parse_status: str  # "ok" | "needs_review" | "failed"
    parse_error: str | None


def is_valid_pdf_magic(content: bytes) -> bool:
    return content.startswith(b"%PDF-")


def is_valid_docx_magic(content: bytes) -> bool:
    # DOCX is a zip archive starting with PK\x03\x04
    return content.startswith(b"PK\x03\x04")


def extract_text_from_pdf(content: bytes) -> ExtractionResult:
    if not is_valid_pdf_magic(content):
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error="Invalid PDF header magic bytes",
        )

    try:
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) == 0:
                return ExtractionResult(
                    text="",
                    is_scan=False,
                    parse_status="failed",
                    parse_error="PDF has 0 pages",
                )

            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    pages_text.append(txt)

        full_text = "\n".join(pages_text).strip()

        # Check for image-only scan or empty text
        if len(full_text) < 50:
            return ExtractionResult(
                text=full_text,
                is_scan=True,
                parse_status="needs_review",
                parse_error="Scanned image-only PDF or insufficient text extracted",
            )

        return ExtractionResult(
            text=full_text,
            is_scan=False,
            parse_status="ok",
            parse_error=None,
        )

    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error=f"PDF extraction error: {exc}",
        )


def extract_text_from_docx(content: bytes) -> ExtractionResult:
    if not is_valid_docx_magic(content):
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error="Invalid DOCX header magic bytes",
        )

    try:
        doc = docx.Document(io.BytesIO(content))
        paragraphs: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]

        # Extract text from tables if any
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    paragraphs.append(" | ".join(row_cells))

        full_text = "\n".join(paragraphs).strip()

        if len(full_text) < 20:
            return ExtractionResult(
                text=full_text,
                is_scan=False,
                parse_status="needs_review",
                parse_error="DOCX contains minimal or empty text",
            )

        return ExtractionResult(
            text=full_text,
            is_scan=False,
            parse_status="ok",
            parse_error=None,
        )

    except Exception as exc:
        logger.warning("DOCX extraction failed: %s", exc)
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error=f"DOCX extraction error: {exc}",
        )


def extract_cv_text(filename: str, content: bytes) -> ExtractionResult:
    if not content:
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error="File is empty (0 bytes)",
        )

    fname = filename.lower()
    if fname.endswith(".pdf"):
        return extract_text_from_pdf(content)
    elif fname.endswith(".docx"):
        return extract_text_from_docx(content)
    else:
        return ExtractionResult(
            text="",
            is_scan=False,
            parse_status="failed",
            parse_error=f"Unsupported file format: {filename}. Only PDF and DOCX are supported.",
        )
