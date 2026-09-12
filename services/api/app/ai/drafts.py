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


# No timestamp was given. Negative rather than None so the draft schema stays inside the JSON
# Schema subset structured output supports, for the same reason the fields below default to "".
NO_TIMESTAMP = -1.0


class DraftSourceReference(BaseModel):
    """Where content came from. Which locator applies depends on the input type.

    Both locators are offered to every provider because one `LessonDraft` serves every input type.
    The prompt says which to fill, and grounding keeps only the locator the input can prove: pages
    for documents, timestamps for video.
    """

    page_number: int = Field(
        description='Documents: number from the <page number="..."> tag that contains the '
        "supporting text. Video: use 0 and give timestamps instead."
    )
    start_time_seconds: float = Field(
        default=NO_TIMESTAMP,
        description="Video: seconds from the start of the video where this content begins. "
        "Documents: leave unset.",
    )
    end_time_seconds: float = Field(
        default=NO_TIMESTAMP,
        description="Video: seconds where this content ends; never before start_time_seconds. "
        "Documents: leave unset.",
    )
    excerpt: str = Field(
        default="",
        description="A short quote (at most 25 words) copied exactly from the source, or empty.",
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
    subject: str = Field(
        default="",
        description="The single academic subject this material best fits: biology, mathematics, "
        "physics, chemistry, history, computer_science, geography, or general if none of those "
        "clearly fit. Leave empty if unsure.",
    )
    sections: list[DraftSection]
    quiz: list[DraftQuizQuestion]
