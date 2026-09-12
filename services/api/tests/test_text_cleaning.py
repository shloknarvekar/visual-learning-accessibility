from app.ingestion.text_cleaning import clean_pages


def clean_one(text: str) -> str:
    return clean_pages([text])[0]


def test_normalises_spaces_and_invisible_characters() -> None:
    text = "Light \t energy is\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}ab\N{SOFT HYPHEN}sorbed."

    assert clean_one(text) == "Light energy is absorbed."


def test_collapses_blank_lines_between_paragraphs() -> None:
    assert clean_one("First paragraph.\n\n\n\nSecond paragraph.") == (
        "First paragraph.\n\nSecond paragraph."
    )


def test_joins_lines_wrapped_mid_sentence() -> None:
    text = "Chlorophyll absorbs red\nand blue light.\nLeaves look green."

    assert clean_one(text) == "Chlorophyll absorbs red and blue light.\nLeaves look green."


def test_joins_hyphenated_line_break_and_keeps_the_hyphen() -> None:
    assert clean_one("the light-\ndependent reactions") == "the light-dependent reactions"


def test_keeps_list_lines_separate() -> None:
    text = "Steps:\n1. Absorb light\n2. Split water\n- Release oxygen"

    assert clean_one(text) == text


def test_removes_running_headers_and_page_footers() -> None:
    content = ["Plants need light.", "Water is split.", "Oxygen is released.", "Sugar is made."]
    pages = [
        f"Biology Notes\n{text}\nPage {number} of 4" for number, text in enumerate(content, start=1)
    ]

    assert clean_pages(pages) == content


def test_removes_printed_page_numbers_offset_from_the_pdf_page() -> None:
    content = ["Plants need light.", "Water is split.", "Oxygen is released."]
    pages = [f"{text}\n{146 + number}" for number, text in enumerate(content, start=1)]

    assert clean_pages(pages) == content


def test_removes_bare_page_number_matching_the_page() -> None:
    pages = ["Intro text.\n1", "More text.\n\N{EN DASH} 2 \N{EN DASH}"]

    assert clean_pages(pages) == ["Intro text.", "More text."]


def test_keeps_numbers_that_are_not_the_page_number() -> None:
    assert clean_one("The answer is:\n42") == "The answer is:\n42"


def test_keeps_numbered_headings_that_do_not_follow_page_numbers() -> None:
    sections = [(2, "A"), (5, "B"), (9, "C")]
    pages = [f"Section {section}\nDetail for part {part}." for section, part in sections]

    assert [page.split("\n")[0] for page in clean_pages(pages)] == [
        "Section 2",
        "Section 5",
        "Section 9",
    ]


def test_keeps_repeated_lines_in_the_middle_of_pages() -> None:
    pages = [
        f"Chapter summary\nPlants need light {part}.\nKey idea\nWater is split {part}.\n"
        f"Oxygen is released {part}."
        for part in "ABCD"
    ]

    cleaned = clean_pages(pages)

    assert all("Key idea" in page for page in cleaned)
    assert not any("Chapter summary" in page for page in cleaned)


def test_does_not_treat_short_documents_as_having_headers() -> None:
    pages = ["Photosynthesis\nFirst page.", "Photosynthesis\nSecond page."]

    assert clean_pages(pages) == pages
