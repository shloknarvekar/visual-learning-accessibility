"""Turning a watched video into the same validated Lesson the document pipeline produces."""

import asyncio

import pytest

from app.ai.drafts import LessonDraft
from app.ai.lesson_assembly import LessonAssemblyError
from app.ai.lesson_generator import VideoLessonGenerationRequest
from app.ai.prompts.lesson_generation import LESSON_FROM_VIDEO_INSTRUCTIONS, VIDEO_REQUEST_TEXT
from app.ai.provider import AIInputNotSupportedError, AIRateLimitError
from app.ai.video_lesson_generator import VideoLessonGenerator
from app.models.media import VideoSource
from app.schemas.lesson import Source
from tests.video_helpers import FakeTextOnlyProvider, FakeVideoProvider, video_draft

YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

YOUTUBE_VIDEO = VideoSource(kind="youtube", uri=YOUTUBE_URL, processing="static")
UPLOADED_VIDEO = VideoSource(
    kind="upload",
    uri="https://files.example/v/abc123",
    processing="agentic",
    mime_type="video/mp4",
)


def request_for(video: VideoSource = YOUTUBE_VIDEO) -> VideoLessonGenerationRequest:
    source = (
        Source(source_type="youtube", title="YouTube video", url=YOUTUBE_URL)
        if video.kind == "youtube"
        else Source(source_type="video", title="lecture", filename="lecture.mp4")
    )
    return VideoLessonGenerationRequest(
        lesson_id="video-1", source=source, video=video, identity="identity-1"
    )


# ---- The request sent to the provider ----------------------------------------------------------


def test_the_video_is_passed_through_untouched_with_the_video_instructions() -> None:
    provider = FakeVideoProvider([video_draft()])
    generator = VideoLessonGenerator(provider)

    asyncio.run(generator.generate(request_for(UPLOADED_VIDEO)))

    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["video"] is UPLOADED_VIDEO
    assert call["instructions"] == LESSON_FROM_VIDEO_INSTRUCTIONS
    assert call["input_text"] == VIDEO_REQUEST_TEXT
    assert call["output_model"] is LessonDraft


def test_the_video_instructions_ask_for_times_and_not_pages() -> None:
    assert "start_time_seconds" in LESSON_FROM_VIDEO_INSTRUCTIONS
    assert "page_number to 0" in LESSON_FROM_VIDEO_INSTRUCTIONS
    assert "<page number=" not in LESSON_FROM_VIDEO_INSTRUCTIONS


def test_one_video_is_one_request_because_the_provider_does_the_chunking() -> None:
    provider = FakeVideoProvider([video_draft()])

    generated = asyncio.run(VideoLessonGenerator(provider).generate(request_for()))

    assert generated.ai_request_count == 1


# ---- The lesson that comes back ----------------------------------------------------------------


def test_the_lesson_carries_timestamps_rather_than_page_numbers() -> None:
    provider = FakeVideoProvider([video_draft(start=12.0, end=30.0)])

    generated = asyncio.run(VideoLessonGenerator(provider).generate(request_for()))

    references = [
        reference
        for section in generated.lesson.sections
        for reference in section.source_references
    ]
    assert references, "every section in the draft cited a time"
    assert all(reference.page_number is None for reference in references)
    assert all(reference.start_time_seconds == 12.0 for reference in references)
    assert all(reference.end_time_seconds == 30.0 for reference in references)


def test_the_lesson_reports_the_provider_that_actually_watched_it() -> None:
    provider = FakeVideoProvider([video_draft()], name="gemini")

    generated = asyncio.run(VideoLessonGenerator(provider).generate(request_for()))

    assert (generated.provider, generated.model, generated.generation_status) == (
        "gemini",
        "fake-video-model",
        "live",
    )


def test_the_source_says_where_the_lesson_came_from() -> None:
    provider = FakeVideoProvider([video_draft()])

    generated = asyncio.run(VideoLessonGenerator(provider).generate(request_for(UPLOADED_VIDEO)))

    assert generated.lesson.source.source_type == "video"
    assert generated.lesson.source.filename == "lecture.mp4"


def test_unverified_quotes_are_reported_as_a_warning_on_the_lesson() -> None:
    provider = FakeVideoProvider([video_draft(excerpt="plants make glucose from light")])

    generated = asyncio.run(VideoLessonGenerator(provider).generate(request_for()))

    assert any("not checked word for word" in warning for warning in generated.warnings)


def test_a_draft_that_cannot_become_a_lesson_is_reported_not_patched() -> None:
    unusable = LessonDraft(title="", overview="", sections=[], quiz=[])
    generator = VideoLessonGenerator(FakeVideoProvider([unusable]))

    with pytest.raises(LessonAssemblyError):
        asyncio.run(generator.generate(request_for()))


def test_a_provider_failure_is_left_for_the_router_to_handle() -> None:
    generator = VideoLessonGenerator(FakeVideoProvider([AIRateLimitError("quota")]))

    with pytest.raises(AIRateLimitError):
        asyncio.run(generator.generate(request_for()))


# ---- Capability --------------------------------------------------------------------------------


def test_a_text_only_provider_is_refused_before_a_request_is_built() -> None:
    """The point of declaring capability: no video is ever sent to a chat-completions endpoint."""
    provider = FakeTextOnlyProvider(name="groq")
    generator = VideoLessonGenerator(provider)  # type: ignore[arg-type]

    with pytest.raises(AIInputNotSupportedError) as caught:
        asyncio.run(generator.generate(request_for()))

    assert "groq" in str(caught.value)
    assert provider.calls == [], "the provider must not be called at all"
