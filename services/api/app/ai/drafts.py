"""Output models the AI fills in. Internal: never returned by the API.

They are deliberately flat and permissive (plain strings, lists, empty defaults) so they fit the
JSON Schema subset that structured output supports. `lesson_assembly` turns a `LessonDraft` into a
strict, validated `Lesson` and checks every page reference against the extracted text.
"""

from typing import Literal

from pydantic import BaseModel, Field

SectionType = Literal[
    "concept",
    "explanation",
    "process",
    "comparison",
    "timeline",
    "example",
    "concept_map",
    "diagram",
    "chart",
]


class DraftSourceReference(BaseModel):
    page_number: int = Field(
        description='Number from the <page number="..."> tag that contains the supporting text.'
    )
    excerpt: str = Field(
        default="",
        description="A short quote (at most 25 words) copied exactly from that page, or empty.",
    )


# ---- Stage A: study notes for one chunk --------------------------------------------------------


class NoteItem(BaseModel):
    kind: Literal[
        "concept",
        "definition",
        "fact",
        "formula",
        "relationship",
        "process",
        "example",
        "comparison",
        "data",
    ]
    title: str = Field(description="The concept, process or topic this note is about.")
    content: str = Field(description="The information, stated faithfully and briefly.")
    steps: list[str] = Field(default_factory=list, description="Ordered steps; process only.")
    source_references: list[DraftSourceReference] = Field(default_factory=list)


class ChunkNotes(BaseModel):
    topics: list[str] = Field(default_factory=list, description="Main topics in this part.")
    notes: list[NoteItem] = Field(default_factory=list)


# ---- Stage B: the lesson -----------------------------------------------------------------------


class DraftStep(BaseModel):
    title: str
    description: str


class DraftComparisonRow(BaseModel):
    criterion: str
    values: list[str] = Field(description="One value per compared item, in the order of items.")


class DraftTimelineEvent(BaseModel):
    time_label: str
    title: str
    description: str


class DraftNode(BaseModel):
    id: str = Field(description="Short identifier, unique in this section, used by edges.")
    label: str
    description: str = ""


class DraftEdge(BaseModel):
    from_id: str
    to_id: str
    label: str = Field(default="", description="The relationship, read as '<from> <label> <to>'.")


class DraftChartPoint(BaseModel):
    label: str
    value: float


class DraftChartSeries(BaseModel):
    name: str
    points: list[DraftChartPoint]


class DraftSection(BaseModel):
    """One lesson section. Fill in only the fields for its type and leave the others empty."""

    type: SectionType
    title: str
    source_references: list[DraftSourceReference] = Field(default_factory=list)
    term: str = Field(default="", description="concept: the key term.")
    definition: str = Field(default="", description="concept: a literal definition.")
    body: str = Field(default="", description="explanation: a short, clear explanation.")
    key_points: list[str] = Field(
        default_factory=list, description="concept, explanation: short key points."
    )
    steps: list[DraftStep] = Field(default_factory=list, description="process: ordered steps.")
    items: list[str] = Field(
        default_factory=list, description="comparison: the things being compared."
    )
    rows: list[DraftComparisonRow] = Field(
        default_factory=list, description="comparison: one row per criterion."
    )
    events: list[DraftTimelineEvent] = Field(
        default_factory=list, description="timeline: events in time order."
    )
    scenario: str = Field(default="", description="example: a concrete situation from the source.")
    explanation: str = Field(default="", description="example: what the situation shows.")
    summary: str = Field(
        default="",
        description="concept_map, diagram, chart: what the visual shows, in 1-2 sentences.",
    )
    diagram_type: str = Field(default="", description="diagram: flowchart, cycle or hierarchy.")
    nodes: list[DraftNode] = Field(default_factory=list, description="concept_map, diagram: boxes.")
    edges: list[DraftEdge] = Field(
        default_factory=list, description="concept_map, diagram: arrows between node ids."
    )
    chart_type: str = Field(default="", description="chart: bar, line or pie.")
    x_axis_label: str = ""
    y_axis_label: str = ""
    unit: str = ""
    series: list[DraftChartSeries] = Field(
        default_factory=list, description="chart: numbers copied exactly from the source."
    )


class DraftQuizQuestion(BaseModel):
    prompt: str
    options: list[str] = Field(description="Three or four answer options.")
    correct_option_index: int = Field(description="Position of the correct option, starting at 0.")
    explanation: str = Field(description="Why the correct answer is correct, based on the source.")
    section_numbers: list[int] = Field(
        default_factory=list, description="Positions (starting at 1) of the sections it checks."
    )
    source_references: list[DraftSourceReference] = Field(default_factory=list)


class LessonDraft(BaseModel):
    title: str
    overview: str = Field(description="Two to four plain sentences on what the lesson covers.")
    sections: list[DraftSection]
    quiz: list[DraftQuizQuestion]
