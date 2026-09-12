from typing import Any

import pytest

from app.ai.drafts import (
    DraftChartPoint,
    DraftChartSeries,
    DraftEdge,
    DraftNode,
    DraftQuizQuestion,
    DraftSection,
    DraftSourceReference,
    DraftStep,
    LessonDraft,
)
from app.ai.lesson_assembly import AssembledLesson, LessonAssemblyError, assemble_lesson
from app.models.content import ExtractedDocument, ExtractedPage
from app.schemas.lesson import Lesson, Source, SourceReference

PAGES = [
    "Photosynthesis is the process plants use to make glucose from light, water and carbon "
    "dioxide.",
    "Chlorophyll absorbs red and blue light. The light-dependent reactions happen in the thylakoid "
    "membranes.",
    "In the experiment, 12 bubbles formed per minute at 10 cm and 30 bubbles formed per minute at "
    "5 cm.",
]
DOCUMENT = ExtractedDocument(
    pages=[ExtractedPage(page_number=n, text=text) for n, text in enumerate(PAGES, start=1)],
    total_pages=len(PAGES),
)
SOURCE = Source(source_type="pdf", title="Biology notes", filename="notes.pdf")


def ref(page: int, excerpt: str = "") -> DraftSourceReference:
    return DraftSourceReference(page_number=page, excerpt=excerpt)


def concept(refs: list[DraftSourceReference] | None = None) -> DraftSection:
    return DraftSection(
        type="concept",
        title="Photosynthesis",
        term="Photosynthesis",
        definition="How plants make glucose using light.",
        source_references=[ref(1, "the process plants use to make glucose")]
        if refs is None
        else refs,
    )


def process() -> DraftSection:
    return DraftSection(
        type="process",
        title="Light-dependent reactions",
        steps=[
            DraftStep(title="Absorb light", description="Chlorophyll absorbs red and blue light."),
            DraftStep(title="React", description="Reactions happen in the thylakoid membranes."),
        ],
        source_references=[ref(2, "Chlorophyll absorbs red and blue light.")],
    )


def chart(
    values: tuple[float, float] = (12, 30), refs: list[DraftSourceReference] | None = None
) -> DraftSection:
    return DraftSection(
        type="chart",
        title="Bubbles per minute",
        chart_type="bar",
        summary="More bubbles form when the lamp is closer.",
        y_axis_label="Bubbles per minute",
        series=[
            DraftChartSeries(
                name="Bubbles",
                points=[
                    DraftChartPoint(label="10 cm", value=values[0]),
                    DraftChartPoint(label="5 cm", value=values[1]),
                ],
            )
        ],
        source_references=[ref(3)] if refs is None else refs,
    )


def question(
    number: int, *, correct: int = 0, sections: tuple[int, ...] = (1,)
) -> DraftQuizQuestion:
    return DraftQuizQuestion(
        prompt=f"Question {number}?",
        options=["Glucose", "Salt", "Iron"],
        correct_option_index=correct,
        explanation="Page 1 says plants make glucose.",
        section_numbers=list(sections),
    )


def assemble(
    sections: list[DraftSection], quiz: list[DraftQuizQuestion] | None = None
) -> AssembledLesson:
    draft = LessonDraft(
        title="Photosynthesis",
        overview="How plants make food from light.",
        sections=sections,
        quiz=[question(n) for n in (1, 2, 3)] if quiz is None else quiz,
    )
    return assemble_lesson(draft, lesson_id="lesson-1", source=SOURCE, document=DOCUMENT)


def test_valid_draft_becomes_a_valid_lesson() -> None:
    result = assemble([concept(), process(), chart()])
    lesson = result.lesson
    sections: list[Any] = lesson.sections

    assert result.warnings == []
    assert [section.id for section in sections] == ["sec-1", "sec-2", "sec-3"]
    assert [section.type for section in sections] == ["concept", "process", "chart"]
    assert sections[1].content.steps[0].id == "sec-2-step-1"
    assert sections[0].source_references == [
        SourceReference(page_number=1, excerpt="the process plants use to make glucose")
    ]
    assert lesson.quiz[0].correct_option_id == "a"
    assert lesson.quiz[0].section_ids == ["sec-1"]
    assert Lesson.model_validate(lesson.model_dump(mode="json", exclude_none=True)) == lesson


def test_quote_citing_the_wrong_page_is_moved_to_its_real_page() -> None:
    result = assemble([concept(refs=[ref(1, "Chlorophyll absorbs red and blue light.")])])

    assert result.lesson.sections[0].source_references == [
        SourceReference(page_number=2, excerpt="Chlorophyll absorbs red and blue light.")
    ]
    assert any("moved to the right page" in warning for warning in result.warnings)


def test_quote_not_in_the_pdf_is_removed_but_a_valid_page_is_kept() -> None:
    result = assemble([concept(refs=[ref(1, "Plants only breathe oxygen at night.")])])

    assert result.lesson.sections[0].source_references == [SourceReference(page_number=1)]
    assert any("could not be found in the PDF" in warning for warning in result.warnings)


def test_reference_to_a_page_that_does_not_exist_is_removed() -> None:
    result = assemble([concept(refs=[ref(9)])])

    assert result.lesson.sections[0].source_references == []
    assert any("pages that do not exist" in warning for warning in result.warnings)


def test_section_that_does_not_fit_the_format_is_left_out_and_ids_stay_sequential() -> None:
    empty_process = DraftSection(type="process", title="Missing steps")
    quiz = [question(1, sections=(1, 3)), question(2), question(3)]

    result = assemble([concept(), empty_process, chart()], quiz=quiz)
    sections: list[Any] = result.lesson.sections

    assert [(section.id, section.type) for section in sections] == [
        ("sec-1", "concept"),
        ("sec-2", "chart"),
    ]
    assert result.lesson.quiz[0].section_ids == ["sec-1", "sec-2"]
    assert any('Left out section 2 (process, "Missing steps")' in w for w in result.warnings)


@pytest.mark.parametrize(
    "section", [chart(values=(12, 99)), chart(refs=[])], ids=["invented-number", "no-page"]
)
def test_chart_that_cannot_be_traced_to_the_source_is_left_out(section: DraftSection) -> None:
    result = assemble([concept(), section])

    assert [section.type for section in result.lesson.sections] == ["concept"]
    assert any("(chart," in warning for warning in result.warnings)


def test_connections_to_missing_boxes_are_removed() -> None:
    concept_map = DraftSection(
        type="concept_map",
        title="How it connects",
        summary="Light helps plants make glucose.",
        nodes=[DraftNode(id="light", label="Light"), DraftNode(id="glucose", label="Glucose")],
        edges=[
            DraftEdge(from_id="light", to_id="glucose", label="helps make"),
            DraftEdge(from_id="light", to_id="oxygen", label="releases"),
        ],
        source_references=[ref(1)],
    )

    result = assemble([concept_map])
    content: Any = result.lesson.sections[0].content

    assert [(edge.from_id, edge.to_id) for edge in content.edges] == [
        ("sec-1-node-1", "sec-1-node-2")
    ]
    assert any("missing boxes" in warning for warning in result.warnings)


def test_invalid_quiz_questions_are_left_out_and_extra_questions_are_trimmed() -> None:
    quiz = [question(1, correct=7)] + [question(n) for n in range(2, 9)]

    result = assemble([concept()], quiz=quiz)

    assert [q.id for q in result.lesson.quiz] == ["q-1", "q-2", "q-3", "q-4", "q-5"]
    assert result.lesson.quiz[0].prompt == "Question 2?"
    assert any("quiz question 1" in warning for warning in result.warnings)
    assert any("first 5 quiz questions" in warning for warning in result.warnings)


def test_draft_without_any_usable_section_is_rejected() -> None:
    with pytest.raises(LessonAssemblyError):
        assemble([DraftSection(type="concept", title="Empty")], quiz=[])


@pytest.mark.parametrize(
    "section",
    [
        DraftSection.model_validate(
            {
                "type": "diagram",
                "title": "Unsupported diagram",
                "diagram_type": "spiral",
                "summary": "A spiral.",
                "nodes": [{"id": "a", "label": "Light"}],
                "source_references": [{"page_number": 1}],
            }
        ),
        DraftSection.model_validate(
            {
                "type": "comparison",
                "title": "Uneven table",
                "items": ["Light-dependent reactions", "Calvin cycle"],
                "rows": [{"criterion": "Location", "values": ["Thylakoid membranes"]}],
                "source_references": [{"page_number": 2}],
            }
        ),
        DraftSection(type="timeline", title="Timeline without events"),
    ],
    ids=["unsupported-diagram-type", "comparison-row-too-short", "empty-timeline"],
)
def test_structurally_invalid_visual_is_left_out_with_a_warning(section: DraftSection) -> None:
    result = assemble([concept(), section])

    assert [kept.type for kept in result.lesson.sections] == ["concept"]
    assert any(f'"{section.title}"' in warning for warning in result.warnings)


def test_question_with_a_single_option_is_left_out() -> None:
    single_option = DraftQuizQuestion(
        prompt="Only one?", options=["Yes"], correct_option_index=0, explanation="There is one."
    )

    result = assemble([concept()], quiz=[single_option, question(1), question(2), question(3)])

    assert [q.prompt for q in result.lesson.quiz] == ["Question 1?", "Question 2?", "Question 3?"]
    assert any("quiz question 1" in warning for warning in result.warnings)
