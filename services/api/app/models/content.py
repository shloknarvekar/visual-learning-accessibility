"""Data passed between pipeline stages. Internal: not part of the public API contract."""

from pydantic import BaseModel, Field, computed_field

from app.schemas.lesson import Id


class ExtractedPage(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class ExtractedDocument(BaseModel):
    """Cleaned text, page by page. Pages without text are kept so page numbers stay exact."""

    pages: list[ExtractedPage]
    total_pages: int = Field(ge=1)

    @computed_field
    @property
    def character_count(self) -> int:
        return sum(len(page.text) for page in self.pages)

    @property
    def empty_page_numbers(self) -> list[int]:
        return [page.page_number for page in self.pages if not page.text.strip()]


class PagePassage(BaseModel):
    """Consecutive text from a single page inside a chunk."""

    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)


class ContentChunk(BaseModel):
    """A slice of the document small enough for one model request, keeping page boundaries."""

    chunk_id: Id
    passages: list[PagePassage] = Field(min_length=1)

    @computed_field
    @property
    def page_start(self) -> int:
        return self.passages[0].page_number

    @computed_field
    @property
    def page_end(self) -> int:
        return self.passages[-1].page_number

    @computed_field
    @property
    def text(self) -> str:
        return "\n\n".join(passage.text for passage in self.passages)
