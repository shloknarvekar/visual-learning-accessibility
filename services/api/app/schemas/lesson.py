"""Pydantic mirror of the public Lesson contract.

Source of truth: packages/contracts/lesson.schema.json. Change both in the same commit;
tests/test_lesson_contract.py fails when they drift apart.

These models also enforce integrity rules JSON Schema cannot express (unique ids, references that
must resolve), so every Lesson the API returns renders without defensive checks in the frontend.

Serialise with `lesson.model_dump(mode="json", exclude_none=True)`: the contract omits absent
optional fields rather than sending null.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

from app.utils.ids import ID_PATTERN

Id = Annotated[str, StringConstraints(pattern=ID_PATTERN)]
PlainText = Annotated[str, StringConstraints(min_length=1)]
SourceType = Literal["youtube", "pdf", "video"]

# Keep in sync with $defs.Subject.enum in packages/contracts/lesson.schema.json.
# "general" is the fallback whenever the subject cannot be confidently determined.
Subject = Literal[
    "biology",
    "mathematics",
    "physics",
    "chemistry",
    "history",
    "computer_science",
    "geography",
    "general",
]


def _ensure_unique(ids: list[str], kind: str) -> None:
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise ValueError(f"duplicate {kind} ids: {duplicates}")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- Source and provenance ---------------------------------------------------------------------


class Source(ContractModel):
    source_type: SourceType
    title: PlainText
    url: HttpUrl | None = None
    filename: PlainText | None = None


class SourceReference(ContractModel):
    page_number: int | None = Field(default=None, ge=1)
    start_time_seconds: float | None = Field(default=None, ge=0)
    end_time_seconds: float | None = Field(default=None, ge=0)
    excerpt: PlainText | None = None

    @model_validator(mode="after")
    def _check_locators(self) -> Self:
        if not self.model_dump(exclude_none=True):
            raise ValueError("a source reference needs at least one locator")
        start, end = self.start_time_seconds, self.end_time_seconds
        if start is not None and end is not None and end < start:
            raise ValueError("end_time_seconds must not be before start_time_seconds")
        return self


# ---- Section content ---------------------------------------------------------------------------


class ConceptContent(ContractModel):
    term: PlainText
    definition: PlainText
    key_points: list[PlainText] = Field(default_factory=list)


class ExplanationContent(ContractModel):
    body: PlainText
    key_points: list[PlainText] = Field(default_factory=list)


class ProcessStep(ContractModel):
    id: Id
    title: PlainText
    description: PlainText


class ProcessContent(ContractModel):
    steps: list[ProcessStep] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        _ensure_unique([step.id for step in self.steps], "step")
        return self


class ComparisonRow(ContractModel):
    criterion: PlainText
    values: list[PlainText] = Field(min_length=2)


class ComparisonContent(ContractModel):
    items: list[PlainText] = Field(min_length=2)
    rows: list[ComparisonRow] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_row_widths(self) -> Self:
        for row in self.rows:
            if len(row.values) != len(self.items):
                raise ValueError(
                    f"row {row.criterion!r} has {len(row.values)} values "
                    f"for {len(self.items)} items"
                )
        return self


class TimelineEvent(ContractModel):
    id: Id
    time_label: PlainText
    title: PlainText
    description: PlainText


class TimelineContent(ContractModel):
    events: list[TimelineEvent] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> Self:
        _ensure_unique([event.id for event in self.events], "event")
        return self


class ExampleContent(ContractModel):
    scenario: PlainText
    explanation: PlainText


class GraphNode(ContractModel):
    id: Id
    label: PlainText
    description: PlainText | None = None


class GraphEdge(ContractModel):
    from_id: Id
    to_id: Id
    label: PlainText | None = None


class _GraphContent(ContractModel):
    summary: PlainText
    nodes: list[GraphNode] = Field(min_length=1)
    edges: list[GraphEdge]

    @model_validator(mode="after")
    def _check_graph(self) -> Self:
        node_ids = [node.id for node in self.nodes]
        _ensure_unique(node_ids, "node")
        known = set(node_ids)
        for edge in self.edges:
            unknown = sorted({edge.from_id, edge.to_id} - known)
            if unknown:
                raise ValueError(f"edge references unknown node ids: {unknown}")
        return self


class ConceptMapContent(_GraphContent):
    """Concepts and the labelled relationships between them."""


class DiagramContent(_GraphContent):
    diagram_type: Literal["flowchart", "cycle", "hierarchy"]


class ChartPoint(ContractModel):
    label: PlainText
    value: float


class ChartSeries(ContractModel):
    name: PlainText
    points: list[ChartPoint] = Field(min_length=1)


class ChartContent(ContractModel):
    chart_type: Literal["bar", "line", "pie"]
    summary: PlainText
    x_axis_label: PlainText | None = None
    y_axis_label: PlainText | None = None
    unit: PlainText | None = None
    series: list[ChartSeries] = Field(min_length=1)


# ---- Sections ----------------------------------------------------------------------------------


class _SectionBase(ContractModel):
    id: Id
    title: PlainText
    source_references: list[SourceReference] = Field(default_factory=list)


class ConceptSection(_SectionBase):
    type: Literal["concept"]
    content: ConceptContent


class ExplanationSection(_SectionBase):
    type: Literal["explanation"]
    content: ExplanationContent


class ProcessSection(_SectionBase):
    type: Literal["process"]
    content: ProcessContent


class ComparisonSection(_SectionBase):
    type: Literal["comparison"]
    content: ComparisonContent


class TimelineSection(_SectionBase):
    type: Literal["timeline"]
    content: TimelineContent


class ExampleSection(_SectionBase):
    type: Literal["example"]
    content: ExampleContent


class ConceptMapSection(_SectionBase):
    type: Literal["concept_map"]
    content: ConceptMapContent


class DiagramSection(_SectionBase):
    type: Literal["diagram"]
    content: DiagramContent


class ChartSection(_SectionBase):
    type: Literal["chart"]
    content: ChartContent


Section = Annotated[
    ConceptSection
    | ExplanationSection
    | ProcessSection
    | ComparisonSection
    | TimelineSection
    | ExampleSection
    | ConceptMapSection
    | DiagramSection
    | ChartSection,
    Field(discriminator="type"),
]


# ---- Quiz and lesson ---------------------------------------------------------------------------


class QuizOption(ContractModel):
    id: Id
    text: PlainText


class QuizQuestion(ContractModel):
    id: Id
    type: Literal["multiple_choice"]
    prompt: PlainText
    options: list[QuizOption] = Field(min_length=2)
    correct_option_id: Id
    explanation: PlainText
    section_ids: list[Id] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_options(self) -> Self:
        option_ids = [option.id for option in self.options]
        _ensure_unique(option_ids, "option")
        if self.correct_option_id not in option_ids:
            raise ValueError(f"correct_option_id {self.correct_option_id!r} is not an option id")
        return self


class Lesson(ContractModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: Id
    title: PlainText
    overview: PlainText
    source: Source
    subject: Subject
    sections: list[Section] = Field(min_length=1)
    quiz: list[QuizQuestion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        section_ids = [section.id for section in self.sections]
        _ensure_unique(section_ids, "section")
        _ensure_unique([question.id for question in self.quiz], "quiz question")
        known = set(section_ids)
        for question in self.quiz:
            unknown = sorted(set(question.section_ids) - known)
            if unknown:
                raise ValueError(
                    f"quiz question {question.id!r} references unknown sections: {unknown}"
                )
        return self
