"""PDF text extraction. The only module that imports PyMuPDF (AGPL-3.0).

Supports text-based PDFs. Scanned, image-only PDFs have no text layer and are rejected with a clear
message until OCR is added.
"""

from pathlib import Path

import pymupdf

from app.core.errors import AppError, ErrorCode
from app.ingestion.text_cleaning import clean_pages
from app.models.content import ExtractedDocument, ExtractedPage

# Fewer letters and digits than this across the whole file means there is no usable text layer.
MIN_TEXT_CHARACTERS = 50
_TEXT_BLOCK_TYPE = 0


def extract_pdf(path: Path, *, max_pages: int) -> ExtractedDocument:
    """Extract and clean the text of each page. Raises AppError for files that cannot be used."""
    try:
        # Opened from bytes, not from the path: when a damaged file fails to open, PyMuPDF can keep
        # the file handle, which on Windows stops the upload from being deleted afterwards. The
        # file was already size-limited when it was saved.
        document = pymupdf.open(stream=path.read_bytes(), filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise AppError(
            ErrorCode.PDF_EXTRACTION_FAILED,
            "This file could not be read as a PDF. It may be damaged.",
        ) from exc

    with document:
        if document.needs_pass:
            raise AppError(
                ErrorCode.PDF_EXTRACTION_FAILED,
                "This PDF is password-protected. Upload a copy without a password.",
            )
        if document.page_count == 0:
            raise AppError(ErrorCode.PDF_EXTRACTION_FAILED, "This PDF has no pages.")
        if document.page_count > max_pages:
            raise AppError(
                ErrorCode.PDF_TOO_MANY_PAGES,
                f"This PDF has {document.page_count} pages. The limit is {max_pages} pages.",
            )
        try:
            raw_pages = [_page_text(page) for page in document]
        except (RuntimeError, ValueError) as exc:
            raise AppError(
                ErrorCode.PDF_EXTRACTION_FAILED, "Text could not be extracted from this PDF."
            ) from exc

    pages = [
        ExtractedPage(page_number=number, text=text)
        for number, text in enumerate(clean_pages(raw_pages), start=1)
    ]
    if sum(char.isalnum() for page in pages for char in page.text) < MIN_TEXT_CHARACTERS:
        raise AppError(
            ErrorCode.PDF_HAS_NO_EXTRACTABLE_TEXT,
            "This PDF does not contain extractable text. OCR support is planned.",
        )
    return ExtractedDocument(pages=pages, total_pages=len(pages))


def _page_text(page: pymupdf.Page) -> str:
    # Blocks roughly match paragraphs; blank lines between them keep that structure for chunking.
    blocks = page.get_text("blocks")
    return "\n\n".join(block[4].strip() for block in blocks if block[6] == _TEXT_BLOCK_TYPE)
