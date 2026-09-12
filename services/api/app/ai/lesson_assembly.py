"""Turns an AI-written `LessonDraft` into a strict, validated `Lesson`.

The model's output is treated as untrusted input:
- page numbers must exist in the document, and quotes must appear on the page they cite (a quote
  found on another page is moved there; a quote found nowhere is removed)
- chart numbers must appear on the pages the chart cites
- sections and quiz questions that do not fit the lesson format are left out with a warning, never
  repaired or guessed
- ids, option letters and the schema version are assigned here, not by the model
"""

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.ai.drafts import DraftQuizQuestion, DraftSection, DraftSourceReference, LessonDraft
from app.models.content import ExtractedDocument
from app.schemas.lesson import Lesson, QuizQuestion, Section, Source, SourceReference

MIN_QUIZ_QUESTIONS = 3
MAX_QUIZ_QUESTIONS = 5
MIN_EXCERPT_CHARS = 12  # shorter quotes match too many places to prove anything
MAX_EXCERPT_CHARS = 300
_OPTION_IDS = "abcdefgh"
_WHITESPACE = re.compile(r"\s+")
_SECTION_ADAPTER: TypeAdapter[Section] = TypeAdapter(Section)


class LessonAssemblyError(Exception):
    """No valid lesson can be built from the draft (the message is for logs, not for users)."""


class _RejectedError(Exception):
    """One section or question failed a check. The message says why, in plain words."""


@dataclass
class AssembledLesson:
    lesson: Lesson
    warnings: list[str] = field(default_factory=list)


def assemble_lesson(
    draft: LessonDraft, *, lesson_id: str, source: Source, document: ExtractedDocument
) -> AssembledLesson:
    assembler = _Assembler(document)
    sections, section_ids = assembler.build_sections(draft.sections)
    quiz = assembler.build_quiz(draft.quiz, section_ids)
    try:
        lesson = Lesson(
            id=lesson_id,
            title=draft.title.strip(),
            overview=draft.overview.strip(),
            source=source,
            sections=sections,
            quiz=quiz,
        )
    except ValidationError as exc:
        locations = sorted({".".join(map(str, error["loc"])) or "lesson" for error in exc.errors()})
        raise LessonAssemblyError(f"lesson validation failed at: {', '.join(locations)}") from exc
    return AssembledLesson(lesson=lesson, warnings=assembler.warnings())


def _points(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _optional(value: str) -> str | None:
    return value.strip() or None


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().casefold()


def _shorten(excerpt: str) -> str:
    if len(excerpt) <= MAX_EXCERPT_CHARS:
        return excerpt
    cut = excerpt.rfind(" ", 0, MAX_EXCERPT_CHARS)
    return excerpt[: cut if cut > 0 else MAX_EXCERPT_CHARS]


def _number_in_text(value: float, text: str) -> bool:
    forms = {f"{value:g}", f"{value:.1f}", f"{value:.2f}"}
    if value.is_integer():
        forms |= {str(int(value)), f"{int(value):,}"}
    return any(re.search(rf"(?<![\d.]){re.escape(form)}(?!\d)", text) for form in forms)


class _Assembler:
    def __init__(self, document: ExtractedDocument) -> None:
        self._page_count = document.total_pages
        self._page_text = {page.page_number: _normalise(page.text) for page in document.pages}
        self._notes: list[str] = []
        self._moved_quotes = 0
        self._removed_quotes = 0
        self._removed_pages = 0

    def warnings(self) -> list[str]:
        counts = [
            (self._moved_quotes, "quote(s) cited the wrong page and were moved to the right page"),
            (self._removed_quotes, "quote(s) could not be found in the PDF and were removed"),
            (self._removed_pages, "reference(s) to pages that do not exist were removed"),
        ]
        return self._notes + [f"{count} {message}." for count, message in counts if count]

    # ---- Sections ------------------------------------------------------------------------------

    def build_sections(self, drafts: list[DraftSection]) -> tuple[list[Section], dict[int, str]]:
        """Valid sections with sequential ids, and a map from draft position to section id."""
        sections: list[Section] = []
        section_ids: dict[int, str] = {}
        for position, draft in enumerate(drafts, start=1):
            section_id = f"sec-{len(sections) + 1}"
            try:
                section = self._section(draft, section_id)
            except _RejectedError as exc:
                self._left_out(position, draft, str(exc))
            except ValidationError:
                self._left_out(position, draft, "it did not match the lesson format")
            else:
                sections.append(section)
                section_ids[position] = section_id
        return sections, section_ids

    def _left_out(self, position: int, draft: DraftSection, reason: str) -> None:
        title = draft.title.strip() or "untitled"
        self._notes.append(
            f'Left out section {position} ({draft.type}, "{title}") because {reason}.'
        )

    def _section(self, draft: DraftSection, section_id: str) -> Section:
        references = self.references(draft.source_references)
        build_content = getattr(self, f"_{draft.type}_content")
        return _SECTION_ADAPTER.validate_python(
            {
                "id": section_id,
                "type": draft.type,
                "title": draft.title.strip(),
                "source_references": [ref.model_dump(exclude_none=True) for ref in references],
                "content": build_content(draft, section_id, references),
            }
        )

    def _concept_content(self, draft: DraftSection, *_: Any) -> dict[str, Any]:
        return {
            "term": draft.term.strip(),
            "definition": draft.definition.strip(),
            "key_points": _points(draft.key_points),
        }

    def _explanation_content(self, draft: DraftSection, *_: Any) -> dict[str, Any]:
        return {"body": draft.body.strip(), "key_points": _points(draft.key_points)}

    def _process_content(self, draft: DraftSection, section_id: str, *_: Any) -> dict[str, Any]:
        steps = [
            {
                "id": f"{section_id}-step-{number}",
                "title": step.title.strip(),
                "description": step.description.strip(),
            }
            for number, step in enumerate(draft.steps, start=1)
        ]
        return {"steps": steps}

    def _comparison_content(self, draft: DraftSection, *_: Any) -> dict[str, Any]:
        rows = [
            {"criterion": row.criterion.strip(), "values": [value.strip() for value in row.values]}
            for row in draft.rows
        ]
        return {"items": [item.strip() for item in draft.items], "rows": rows}

    def _timeline_content(self, draft: DraftSection, section_id: str, *_: Any) -> dict[str, Any]:
        events = [
            {
                "id": f"{section_id}-event-{number}",
                "time_label": event.time_label.strip(),
                "title": event.title.strip(),
                "description": event.description.strip(),
            }
            for number, event in enumerate(draft.events, start=1)
        ]
        return {"events": events}

    def _example_content(self, draft: DraftSection, *_: Any) -> dict[str, Any]:
        return {"scenario": draft.scenario.strip(), "explanation": draft.explanation.strip()}

    def _concept_map_content(self, draft: DraftSection, section_id: str, *_: Any) -> dict[str, Any]:
        return self._graph(draft, section_id)

    def _diagram_content(self, draft: DraftSection, section_id: str, *_: Any) -> dict[str, Any]:
        return {
            "diagram_type": draft.diagram_type.strip().lower(),
            **self._graph(draft, section_id),
        }

    def _chart_content(
        self, draft: DraftSection, _section_id: str, references: list[SourceReference]
    ) -> dict[str, Any]:
        cited_text = " ".join(self._page_text[ref.page_number] for ref in references)
        if not cited_text:
            raise _RejectedError("a chart must cite the page its numbers come from")
        values = [point.value for series in draft.series for point in series.points]
        if not all(_number_in_text(value, cited_text) for value in values):
            raise _RejectedError("some of its numbers do not appear on the pages it cites")
        return {
            "chart_type": draft.chart_type.strip().lower(),
            "summary": draft.summary.strip(),
            "x_axis_label": _optional(draft.x_axis_label),
            "y_axis_label": _optional(draft.y_axis_label),
            "unit": _optional(draft.unit),
            "series": [
                {
                    "name": series.name.strip(),
                    "points": [
                        {"label": point.label.strip(), "value": point.value}
                        for point in series.points
                    ],
                }
                for series in draft.series
            ],
        }

    def _graph(self, draft: DraftSection, section_id: str) -> dict[str, Any]:
        node_ids: dict[str, str] = {}
        nodes = []
        for number, node in enumerate(draft.nodes, start=1):
            key = node.id.strip()
            if key in node_ids:
                continue
            node_ids[key] = f"{section_id}-node-{number}"
            nodes.append(
                {
                    "id": node_ids[key],
                    "label": node.label.strip(),
                    "description": _optional(node.description),
                }
            )
        edges = []
        for edge in draft.edges:
            from_id, to_id = node_ids.get(edge.from_id.strip()), node_ids.get(edge.to_id.strip())
            if from_id and to_id:
                edges.append({"from_id": from_id, "to_id": to_id, "label": _optional(edge.label)})
        if missing := len(draft.edges) - len(edges):
            self._notes.append(
                f'Removed {missing} connection(s) in "{draft.title.strip()}" that pointed to '
                "missing boxes."
            )
        return {"summary": draft.summary.strip(), "nodes": nodes, "edges": edges}

    # ---- Provenance ----------------------------------------------------------------------------

    def references(self, drafts: list[DraftSourceReference]) -> list[SourceReference]:
        resolved: list[SourceReference] = []
        for draft in drafts:
            reference = self._reference(draft)
            if reference is not None and reference not in resolved:
                resolved.append(reference)
        return resolved

    def _reference(self, draft: DraftSourceReference) -> SourceReference | None:
        excerpt = _WHITESPACE.sub(" ", draft.excerpt).strip()
        if len(excerpt) >= MIN_EXCERPT_CHARS:
            page = self._page_with_quote(excerpt, preferred=draft.page_number)
            if page is not None:
                if page != draft.page_number:
                    self._moved_quotes += 1
                return SourceReference(page_number=page, excerpt=_shorten(excerpt))
        if excerpt:
            self._removed_quotes += 1
        if 1 <= draft.page_number <= self._page_count:
            return SourceReference(page_number=draft.page_number)
        self._removed_pages += 1
        return None

    def _page_with_quote(self, excerpt: str, *, preferred: int) -> int | None:
        needle = _normalise(excerpt)
        if needle in self._page_text.get(preferred, ""):
            return preferred
        return next((number for number, text in self._page_text.items() if needle in text), None)

    # ---- Quiz ----------------------------------------------------------------------------------

    def build_quiz(
        self, drafts: list[DraftQuizQuestion], section_ids: dict[int, str]
    ) -> list[QuizQuestion]:
        questions: list[QuizQuestion] = []
        for position, draft in enumerate(drafts, start=1):
            if len(questions) == MAX_QUIZ_QUESTIONS:
                self._notes.append(
                    f"Kept the first {MAX_QUIZ_QUESTIONS} quiz questions and left out "
                    f"{len(drafts) - position + 1}."
                )
                break
            try:
                questions.append(self._question(draft, f"q-{len(questions) + 1}", section_ids))
            except _RejectedError as exc:
                self._notes.append(f"Left out quiz question {position} because {exc}.")
            except ValidationError:
                self._notes.append(
                    f"Left out quiz question {position} because it did not match the quiz format."
                )
        if len(questions) < MIN_QUIZ_QUESTIONS:
            self._notes.append(f"Only {len(questions)} quiz question(s) could be generated.")
        return questions

    def _question(
        self, draft: DraftQuizQuestion, question_id: str, section_ids: dict[int, str]
    ) -> QuizQuestion:
        options = [option.strip() for option in draft.options]
        if len(options) > len(_OPTION_IDS):
            raise _RejectedError("it has too many options")
        if not 0 <= draft.correct_option_index < len(options):
            raise _RejectedError("its correct answer is not one of its options")
        references = self.references(draft.source_references)
        return QuizQuestion.model_validate(
            {
                "id": question_id,
                "type": "multiple_choice",
                "prompt": draft.prompt.strip(),
                "options": [
                    {"id": _OPTION_IDS[index], "text": text} for index, text in enumerate(options)
                ],
                "correct_option_id": _OPTION_IDS[draft.correct_option_index],
                "explanation": draft.explanation.strip(),
                "section_ids": [
                    section_ids[number]
                    for number in dict.fromkeys(draft.section_numbers)
                    if number in section_ids
                ],
                "source_references": [ref.model_dump(exclude_none=True) for ref in references],
            }
        )
