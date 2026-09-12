from app.models.content import ExtractedDocument, ExtractedPage
from app.services.chunking import chunk_document


def _document(*page_texts: str) -> ExtractedDocument:
    pages = [
        ExtractedPage(page_number=number, text=text)
        for number, text in enumerate(page_texts, start=1)
    ]
    return ExtractedDocument(pages=pages, total_pages=len(pages))


def _paragraphs(count: int) -> list[str]:
    return [
        f"Paragraph {number} explains one idea in a complete sentence." for number in range(count)
    ]


def test_short_document_becomes_one_chunk_covering_every_page() -> None:
    chunks = chunk_document(_document("Page one text.", "Page two text."), max_chars=1_000)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert (chunk.chunk_id, chunk.page_start, chunk.page_end) == ("chunk-001", 1, 2)
    assert chunk.text == "Page one text.\n\nPage two text."
    assert [passage.page_number for passage in chunk.passages] == [1, 2]


def test_chunks_stay_within_the_limit_and_keep_all_text_in_order() -> None:
    paragraphs = _paragraphs(40)
    document = _document("\n\n".join(paragraphs[:20]), "\n\n".join(paragraphs[20:]))

    chunks = chunk_document(document, max_chars=300)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 300 for chunk in chunks)
    assert "\n\n".join(chunk.text for chunk in chunks) == "\n\n".join(paragraphs)


def test_each_passage_is_text_from_the_page_it_names() -> None:
    paragraphs = _paragraphs(30)
    document = _document("\n\n".join(paragraphs[:15]), "\n\n".join(paragraphs[15:]))

    chunks = chunk_document(document, max_chars=250)

    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    for chunk in chunks:
        assert chunk.page_start <= chunk.page_end
        for passage in chunk.passages:
            assert passage.text in document.pages[passage.page_number - 1].text


def test_long_paragraph_splits_between_sentences() -> None:
    sentences = [f"Sentence number {number} ends here." for number in range(30)]

    chunks = chunk_document(_document(" ".join(sentences)), max_chars=120)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.text.startswith("Sentence number")
        assert chunk.text.endswith("ends here.")
    assert " ".join(chunk.text for chunk in chunks) == " ".join(sentences)


def test_sentence_longer_than_the_limit_splits_between_words() -> None:
    text = " ".join(["photosynthesis"] * 40)

    chunks = chunk_document(_document(text), max_chars=50)

    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert " ".join(chunk.text for chunk in chunks) == text


def test_word_longer_than_the_limit_is_sliced() -> None:
    chunks = chunk_document(_document("x" * 25), max_chars=10)

    assert [chunk.text for chunk in chunks] == ["x" * 10, "x" * 10, "x" * 5]


def test_blank_pages_are_skipped_without_breaking_page_ranges() -> None:
    document = _document("Real text on page one.", "", "More text on page three.")

    chunks = chunk_document(document, max_chars=1_000)

    assert [passage.page_number for passage in chunks[0].passages] == [1, 3]
    assert (chunks[0].page_start, chunks[0].page_end) == (1, 3)


def test_chunking_is_deterministic_with_sequential_ids() -> None:
    document = _document("\n\n".join(_paragraphs(25)))

    first = chunk_document(document, max_chars=200)
    second = chunk_document(document, max_chars=200)

    assert first == second
    assert [chunk.chunk_id for chunk in first] == [
        f"chunk-{number:03d}" for number in range(1, len(first) + 1)
    ]
