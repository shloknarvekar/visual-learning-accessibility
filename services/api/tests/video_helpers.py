"""Test doubles and byte fixtures for the video pipeline. Nothing here touches the network.

The byte strings are real container headers with nothing behind them. That is deliberate: every
check this codebase makes on an uploaded video reads the first bytes only, so a valid header is
enough to exercise acceptance, and a header that disagrees with its declared type is exactly what
the rejection path is for.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.ai.drafts import DraftQuizQuestion, DraftSection, DraftSourceReference, LessonDraft
from app.ai.provider import TEXT_AND_VIDEO, TEXT_ONLY
from app.models.media import VideoProcessing, VideoSource

_PADDING = b"\x00" * 64

# ISO base media (mp4/mov/3gp): a size field, then the "ftyp" box.
MP4 = b"\x00\x00\x00\x18ftypmp42" + _PADDING
MOV = b"\x00\x00\x00\x14ftypqt  " + _PADDING
THREE_GPP = b"\x00\x00\x00\x18ftyp3gp5" + _PADDING
WEBM = b"\x1a\x45\xdf\xa3" + _PADDING
AVI = b"RIFF\x00\x00\x00\x00AVI " + _PADDING
MPEG = b"\x00\x00\x01\xba" + _PADDING
FLV = b"FLV\x01\x05" + _PADDING
WMV = b"\x30\x26\xb2\x75\x8e\x66\xcf\x11" + _PADDING

# Not a video by any reading: a ZIP header.
NOT_A_VIDEO = b"PK\x03\x04" + _PADDING

VALID_YOUTUBE_URL = "https://youtu.be/dQw4w9WgXcQ"
CANONICAL_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def video_draft(
    *,
    start: float = 12.0,
    end: float = 30.0,
    excerpt: str = "chlorophyll absorbs red and blue light",
    subject: str = "",
) -> LessonDraft:
    """A draft shaped the way the video prompt asks for: timestamps, and page_number left at 0."""

    def ref() -> DraftSourceReference:
        return DraftSourceReference(
            page_number=0, start_time_seconds=start, end_time_seconds=end, excerpt=excerpt
        )

    return LessonDraft(
        title="Photosynthesis",
        overview="How plants turn light into chemical energy.",
        subject=subject,
        sections=[
            DraftSection(
                type="concept",
                title="Photosynthesis",
                term="Photosynthesis",
                definition="How plants make glucose from light, water and carbon dioxide.",
                source_references=[ref()],
            ),
            DraftSection(
                type="explanation",
                title="Why leaves look green",
                body="Chlorophyll reflects green light.",
                source_references=[ref()],
            ),
        ],
        quiz=[
            DraftQuizQuestion(
                prompt=f"Question {number}?",
                options=["Glucose", "Salt", "Iron"],
                correct_option_index=0,
                explanation="The video says plants make glucose.",
                section_numbers=[1],
                source_references=[ref()],
            )
            for number in (1, 2, 3)
        ],
    )


class FakeVideoProvider:
    """A video-capable provider that returns, or raises, prepared responses in order."""

    def __init__(self, responses: list[BaseModel | Exception], *, name: str = "gemini") -> None:
        self._responses = list(responses)
        self.name = name
        self.model_name = "fake-video-model"
        self.modalities = TEXT_AND_VIDEO
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[BaseModel]
    ) -> Any:
        return self._next(output_model)

    async def generate_structured_from_video(
        self,
        *,
        instructions: str,
        input_text: str,
        video: VideoSource,
        output_model: type[BaseModel],
    ) -> Any:
        self.calls.append(
            {
                "instructions": instructions,
                "input_text": input_text,
                "video": video,
                "output_model": output_model,
            }
        )
        return self._next(output_model)

    def _next(self, output_model: type[BaseModel]) -> Any:
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        assert isinstance(response, output_model)
        return response


class FakeTextOnlyProvider:
    """A provider that declares text only, the way OpenRouter and Groq do."""

    def __init__(self, *, name: str = "groq") -> None:
        self.name = name
        self.model_name = "fake-text-model"
        self.modalities = TEXT_ONLY
        self.calls: list[dict[str, Any]] = []

    async def generate_structured(
        self, *, instructions: str, input_text: str, output_model: type[BaseModel]
    ) -> Any:
        raise AssertionError("a video test must never reach a text-only provider")


class FakeUploader:
    """Records what was uploaded and proves the upload was released afterwards."""

    def __init__(
        self, *, uri: str = "https://files.example/v/abc123", error: Exception | None = None
    ) -> None:
        self._uri = uri
        self._error = error
        self.uploads: list[dict[str, Any]] = []
        self.released = 0

    @asynccontextmanager
    async def upload(
        self,
        path: Path,
        *,
        mime_type: str,
        display_name: str,
        processing: VideoProcessing,
    ) -> AsyncIterator[VideoSource]:
        self.uploads.append(
            {
                "mime_type": mime_type,
                "display_name": display_name,
                "processing": processing,
                # Recorded at upload time: the local temporary file must still exist here, and must
                # be gone once the request is over.
                "path": path,
                "path_existed": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
        if self._error is not None:
            raise self._error
        try:
            yield VideoSource(
                kind="upload", uri=self._uri, processing=processing, mime_type=mime_type
            )
        finally:
            self.released += 1
