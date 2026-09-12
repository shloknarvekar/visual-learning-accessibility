"""Turns an AI-written `LessonDraft` into a strict, validated `Lesson`.

The model's output is treated as untrusted input:
- citations are kept only where the source can prove them. What that means differs per input type
  and lives in `grounding`; this module never learns which input it is assembling.
- chart numbers must be supported by what the section cites
- sections and quiz questions that do not fit the lesson format are left out with a warning, never
  repaired or guessed
- ids, option letters and the schema version are assigned here, not by the model

There is one assembly path for every input type. The two entry points below differ only in which
`Grounding` they hand to the same assembler.
"""

from dataclasses import dataclass, field
from typing import Any, get_args

from pydantic import TypeAdapter, ValidationError

from app.ai.drafts import DraftQuizQuestion, DraftSection, DraftSourceReference, LessonDraft
from app.ai.grounding import Grounding, PageGrounding, VideoGrounding
from app.models.content import ExtractedDocument
from app.schemas.lesson import Lesson, QuizQuestion, Section, Source, SourceReference, Subject

MIN_QUIZ_QUESTIONS = 3
MAX_QUIZ_QUESTIONS = 5
_OPTION_IDS = "abcdefgh"
_SECTION_ADAPTER: TypeAdapter[Section] = TypeAdapter(Section)

# get_args(Subject) rather than retyping the list, so this can never drift from the contract type.
_ALLOWED_SUBJECTS: frozenset[str] = frozenset(get_args(Subject))
FALLBACK_SUBJECT: Subject = "general"


def _normalize_subject(raw: str) -> Subject:
    """The model's subject guess, or `general` when it does not confidently match one we know.

    Matched case- and whitespace-insensitively since a model may return "Biology" or " biology ";
    anything else - empty, unrecognized, or an outright guess we don't recognize - falls back
    rather than being interpreted further, per the rule that an unconfident subject is `general`.
    """
    candidate = raw.strip().lower()
    return candidate if candidate in _ALLOWED_SUBJECTS else FALLBACK_SUBJECT  # type: ignore[return-value]


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
    """Assemble a lesson whose claims are checked against a paged document's own text."""
    return _assemble(draft, lesson_id=lesson_id, source=source, grounding=PageGrounding(document))


def assemble_lesson_from_video(
    draft: LessonDraft, *, lesson_id: str, source: Source
) -> AssembledLesson:
    """Assemble a lesson from a watched video, where timestamps are the provable locator."""
    return _assemble(draft, lesson_id=lesson_id, source=source, grounding=VideoGrounding())


def _assemble(
    draft: LessonDraft, *, lesson_id: str, source: Source, grounding: Grounding
) -> AssembledLesson:
    assembler = _Assembler(grounding)
    sections, section_ids = assembler.build_sections(draft.sections)
    quiz = assembler.build_quiz(draft.quiz, section_ids)
    try:
        lesson = Lesson(
            id=lesson_id,
            title=draft.title.strip(),
            overview=draft.overview.strip(),
            source=source,
            subject=_normalize_subject(draft.subject),
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


class _Assembler:
    def __init__(self, grounding: Grounding) -> None:
        self._grounding = grounding
        self._notes: list[str] = []

    def warnings(self) -> list[str]:
        return self._notes + self._grounding.notes()

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
        values = [point.value for series in draft.series for point in series.points]
        rejection = self._grounding.chart_rejection(values, references)
        if rejection is not None:
            raise _RejectedError(rejection)
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
            reference = self._grounding.reference(draft)
            if reference is not None and reference not in resolved:
                resolved.append(reference)
        return resolved

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
