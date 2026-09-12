"""Builds small PDFs in memory, so tests need no binary fixtures."""

import pymupdf

_TEXT_AREA = pymupdf.Rect(56, 56, 540, 790)


def make_pdf(pages: list[str]) -> bytes:
    """One page per string. An empty string produces a blank page."""
    with pymupdf.open() as document:
        for text in pages:
            page = document.new_page()
            if text and page.insert_textbox(_TEXT_AREA, text, fontsize=10) < 0:
                raise ValueError("test text does not fit on one page")
        return document.tobytes()


def make_image_only_pdf() -> bytes:
    """A page with a drawing and no text layer, like a scanned document."""
    with pymupdf.open() as document:
        page = document.new_page()
        page.draw_rect(pymupdf.Rect(50, 50, 300, 300), color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
        return document.tobytes()


def make_password_protected_pdf() -> bytes:
    with pymupdf.open() as document:
        document.new_page().insert_textbox(
            _TEXT_AREA, "Notes about photosynthesis and chlorophyll pigments.", fontsize=10
        )
        return document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user"
        )
