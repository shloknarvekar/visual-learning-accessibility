"""Generates a lesson from a video the provider watches.

One request: the model watches the whole recording and returns the same `LessonDraft` the document
pipeline produces, which `lesson_assembly` then checks and turns into the same strict `Lesson`.

There is no chunking stage here, which is why this is so much smaller than `AILessonGenerator`
rather than a copy of it: splitting a video into pieces is the provider's job, expressed by the
processing mode on the `VideoSource`, not something this service can do without decoding media.
"""

import logging
import time

from app.ai.drafts import LessonDraft
from app.ai.lesson_assembly import assemble_lesson_from_video
from app.ai.lesson_generator import GeneratedLesson, VideoLessonGenerationRequest
from app.ai.prompts.lesson_generation import LESSON_FROM_VIDEO_INSTRUCTIONS, VIDEO_REQUEST_TEXT
from app.ai.provider import VideoCapableProvider, require

logger = logging.getLogger(__name__)


class VideoLessonGenerator:
    def __init__(self, provider: VideoCapableProvider) -> None:
        self._provider = provider

    async def generate(self, request: VideoLessonGenerationRequest) -> GeneratedLesson:
        # Checked before a request is built rather than after one fails, so a provider that cannot
        # watch video is reported as exactly that instead of as a confusing model error.
        require(self._provider, "video")

        started = time.perf_counter()
        draft = await self._provider.generate_structured_from_video(
            instructions=LESSON_FROM_VIDEO_INSTRUCTIONS,
            input_text=VIDEO_REQUEST_TEXT,
            video=request.video,
            output_model=LessonDraft,
        )
        logger.info(
            "lesson draft generated from video",
            extra={
                "document_id": request.lesson_id,
                # Never the URI: for YouTube it is the material the learner chose, and for an
                # upload it is a Files API address tied to our account.
                "video_kind": request.video.kind,
                "video_processing": request.video.processing,
                "ai_requests": 1,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )

        assembled = assemble_lesson_from_video(
            draft, lesson_id=request.lesson_id, source=request.source
        )
        return GeneratedLesson(
            lesson=assembled.lesson,
            warnings=assembled.warnings,
            model=self._provider.model_name,
            ai_request_count=1,
            provider=self._provider.name,  # type: ignore[arg-type]
            generation_status="live",
        )
