from pathlib import Path

import pytest

from app.core.errors import AppError, ErrorCode
from app.ingestion.pdf import extract_pdf
from tests.pdf_helpers import make_image_only_pdf, make_password_protected_pdf, make_pdf

PAGE_ONE = "Photosynthesis converts light energy into chemical energy."
PAGE_TWO = "Chlorophyll absorbs red and blue light and reflects green light."


def _save(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "upload.pdf"
    path.write_bytes(data)
    return path


def _extraction_error(path: Path, *, max_pages: int = 10) -> AppError:
    with pytest.raises(AppError) as caught:
        extract_pdf(path, max_pages=max_pages)
    return caught.value


def test_extracts_text_with_page_numbers(tmp_path: Path) -> None:
    document = extract_pdf(_save(tmp_path, make_pdf([PAGE_ONE, PAGE_TWO])), max_pages=10)

    assert document.total_pages == 2
    assert [page.page_number for page in document.pages] == [1, 2]
    assert document.pages[0].text == PAGE_ONE
    assert document.pages[1].text == PAGE_TWO
    assert document.character_count == len(PAGE_ONE) + len(PAGE_TWO)


def test_unwraps_lines_and_keeps_paragraphs(tmp_path: Path) -> None:
    text = (
        "Plants make glucose\nfrom carbon dioxide and water.\n\nOxygen is released as a by-product."
    )

    document = extract_pdf(_save(tmp_path, make_pdf([text])), max_pages=10)

    assert document.pages[0].text == (
        "Plants make glucose from carbon dioxide and water.\n\nOxygen is released as a by-product."
    )


def test_keeps_blank_pages_so_page_numbers_stay_exact(tmp_path: Path) -> None:
    document = extract_pdf(_save(tmp_path, make_pdf([PAGE_ONE, "", PAGE_TWO])), max_pages=10)

    assert document.total_pages == 3
    assert document.empty_page_numbers == [2]
    assert document.pages[2].text == PAGE_TWO


@pytest.mark.parametrize(
    "data", [make_image_only_pdf(), make_pdf(["", ""])], ids=["image-only", "blank"]
)
def test_pdf_without_text_is_rejected_with_ocr_message(tmp_path: Path, data: bytes) -> None:
    error = _extraction_error(_save(tmp_path, data))

    assert error.code == ErrorCode.PDF_HAS_NO_EXTRACTABLE_TEXT
    assert error.message == "This PDF does not contain extractable text. OCR support is planned."


@pytest.mark.parametrize(
    "data",
    [b"%PDF-1.7\nnot really a pdf", b"", b"just a plain text file"],
    ids=["corrupt", "empty", "not-pdf"],
)
def test_unreadable_file_is_rejected(tmp_path: Path, data: bytes) -> None:
    assert _extraction_error(_save(tmp_path, data)).code == ErrorCode.PDF_EXTRACTION_FAILED


def test_password_protected_pdf_is_rejected(tmp_path: Path) -> None:
    error = _extraction_error(_save(tmp_path, make_password_protected_pdf()))

    assert error.code == ErrorCode.PDF_EXTRACTION_FAILED
    assert "password" in error.message


def test_pdf_over_the_page_limit_is_rejected(tmp_path: Path) -> None:
    path = _save(tmp_path, make_pdf([PAGE_ONE, PAGE_TWO, PAGE_ONE]))

    error = _extraction_error(path, max_pages=2)

    assert error.code == ErrorCode.PDF_TOO_MANY_PAGES
    assert "3 pages" in error.message
