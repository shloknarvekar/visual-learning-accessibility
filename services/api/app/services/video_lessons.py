"""Creates lessons from video: a public YouTube link, or an uploaded file.

Both inputs become the same `VideoSource` and leave through the same shared pipeline, so the only
thing that differs is how the model is given something to watch:

    YouTube link  -> validated, rebuilt from its video id -> a URL only Gemini ever resolves
    uploaded file -> validated, streamed to disk -> Files API -> a URI, deleted afterwards

This service never downloads a video and never fetches a caller's URL. It does not log the URL, the
filename, or anything about the video's content; a lesson is identified in logs by its id alone.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Literal, Self

from fastapi import UploadFile

from app.ai.lesson_generator import LessonGenerator, VideoLessonGenerationRequest
from app.ai.provider import (
    AIInputNotSupportedError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
)
from app.ai.video_upload import VideoUploader
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.ingestion.video import canonical_youtube_url
from app.models.media import VideoProcessing, VideoSource
from app.schemas.lesson import Source
from app.schemas.lessons_api import LessonMetadata, LessonRecord, ProcessingTimings
from app.services.lesson_pipeline import (
    NO_CAPABLE_PROVIDER,
    elapsed_ms,
    generate_lesson,
    notice_for,
    translate_ai_error,
    validate_lesson,
)
from app.services.lesson_store import LessonStore
from app.services.uploads import stored_video_upload

logger = logging.getLogger(__name__)

MATERIAL_NOUN = "video"
YOUTUBE_MATERIAL = "this video"
UPLOAD_MATERIAL = "the uploaded video"

# A video carries no page or character counts. They are reported as zero rather than invented, and
# `page_count` is left off entirely - see `LessonMetadata`.
_NO_TEXT_CHUNKS = 0


@dataclass(frozen=True)
class VideoLessonLimits:
    max_upload_mb: int
    processing_mode: Literal["auto", "static", "agentic"]
    agentic_threshold_mb: int


class VideoLessonService:
    def __init__(
        self,
        *,
        generator: LessonGenerator | None,
        uploader: VideoUploader | None,
        store: LessonStore,
        uploads_dir: Path,
        limits: VideoLessonLimits,
    ) -> None:
        # These are None when nothing configured can watch a video. That is a capability fact, not
        # an outage, so it is reported as one before any work starts.
        self._generator = generator
        self._uploader = uploader
        self._store = store
        self._uploads_dir = uploads_dir
        self._limits = limits

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        generator: LessonGenerator | None,
        uploader: VideoUploader | None,
        store: LessonStore,
    ) -> Self:
        return cls(
            generator=generator,
            uploader=uploader,
            store=store,
            uploads_dir=settings.data_dir / "video-uploads",
            limits=VideoLessonLimits(
                max_upload_mb=settings.max_video_upload_mb,
                processing_mode=settings.video_processing_mode,
                agentic_threshold_mb=settings.video_agentic_threshold_mb,
            ),
        )

    async def create_lesson_from_youtube(self, url: str) -> LessonRecord:
        started = time.perf_counter()
        # Validated before the capability check so an obviously wrong link is answered as a bad
        # link, which the caller can fix, rather than as a missing provider, which they cannot.
        watch_url = canonical_youtube_url(url)
        generator = self._require_generator()

        lesson_id = uuid.uuid4().hex
        logger.info("youtube lesson requested", extra={"document_id": lesson_id})

        video = VideoSource(
            kind="youtube", uri=watch_url, processing=self._processing_for(size_bytes=None)
        )
        source = Source(source_type="youtube", title="YouTube video", url=watch_url)
        return await self._build(
            generator=generator,
            lesson_id=lesson_id,
            source=source,
            video=video,
            # The canonical URL is what makes this the same video next time, whoever typed it.
            identity=watch_url,
            material=YOUTUBE_MATERIAL,
            source_filename=None,
            ingestion_ms=elapsed_ms(started),
            started=started,
        )

    async def create_lesson_from_upload(self, upload: UploadFile) -> LessonRecord:
        started = time.perf_counter()
        generator = self._require_generator()
        uploader = self._uploader
        if uploader is None:
            raise AppError(ErrorCode.AI_INPUT_NOT_SUPPORTED, NO_CAPABLE_PROVIDER)

        async with stored_video_upload(
            upload, directory=self._uploads_dir, max_mb=self._limits.max_upload_mb
        ) as stored:
            lesson_id = stored.upload_id
            logger.info(
                "video upload received",
                extra={
                    "document_id": lesson_id,
                    "size_bytes": stored.size_bytes,
                    "mime_type": stored.mime_type,
                },
            )
            step = time.perf_counter()
            try:
                async with uploader.upload(
                    stored.path,
                    mime_type=stored.mime_type,
                    # A generated name, not the learner's filename: the provider has no need
                    # for it.
                    display_name=f"lesson-{lesson_id}",
                    processing=self._processing_for(size_bytes=stored.size_bytes),
                ) as video:
                    ingestion_ms = elapsed_ms(step)
                    source = Source(
                        source_type="video",
                        title=PurePath(stored.display_name).stem or "Uploaded video",
                        filename=stored.display_name,
                    )
                    # Generation stays inside both blocks: the model reads the remote copy
                    # while it answers, and neither copy is removed until there is nothing
                    # left to redo.
                    return await self._build(
                        generator=generator,
                        lesson_id=lesson_id,
                        source=source,
                        video=video,
                        # The file's own hash, so the same recording uploaded twice hits the
                        # cache; the Files API URI is new every time and would never match.
                        identity=stored.content_hash,
                        material=UPLOAD_MATERIAL,
                        source_filename=stored.display_name,
                        ingestion_ms=ingestion_ms,
                        started=started,
                    )
            except (
                AIRateLimitError,
                AIInvalidResponseError,
                AIInputNotSupportedError,
                AIProviderError,
            ) as exc:
                # Getting a video ready to watch is still an AI-service call (the Gemini Files
                # API), so a failure here is reported exactly like a failed generation call -
                # never as a bare 500. `generate_lesson` inside `_build` already translates its
                # own failures into `AppError`, which is not one of the types caught here, so
                # this cannot double-translate it.
                raise translate_ai_error(exc, lesson_id) from exc

    async def _build(
        self,
        *,
        generator: LessonGenerator,
        lesson_id: str,
        source: Source,
        video: VideoSource,
        identity: str,
        material: str,
        source_filename: str | None,
        ingestion_ms: int,
        started: float,
    ) -> LessonRecord:
        step = time.perf_counter()
        generated = await generate_lesson(
            generator,
            VideoLessonGenerationRequest(
                lesson_id=lesson_id, source=source, video=video, identity=identity
            ),
        )
        generation_ms = elapsed_ms(step)

        step = time.perf_counter()
        lesson = validate_lesson(generated.lesson, lesson_id)
        validation_ms = elapsed_ms(step)

        record = LessonRecord(
            lesson_id=lesson_id,
            lesson=lesson,
            metadata=LessonMetadata(
                provider=generated.provider,
                generation_status=generated.generation_status,
                is_mock=generated.provider == "demo",
                notice=notice_for(generated, material=material, noun=MATERIAL_NOUN),
                model=generated.model,
                source_filename=source_filename,
                page_count=None,  # a video has no pages; the field is omitted from the response
                chunk_count=_NO_TEXT_CHUNKS,
                character_count=_NO_TEXT_CHUNKS,
                ai_request_count=generated.ai_request_count,
                warnings=generated.warnings,
                timings=ProcessingTimings(
                    # "Extraction" for a video is making it watchable: sending it to the provider,
                    # or nothing at all for a link.
                    extraction_ms=ingestion_ms,
                    chunking_ms=0,  # the provider handles the whole recording itself
                    generation_ms=generation_ms,
                    validation_ms=validation_ms,
                    total_ms=elapsed_ms(started),
                ),
                created_at=datetime.now(UTC),
            ),
        )
        self._store.save(record)
        logger.info(
            "lesson stored",
            extra={
                "document_id": lesson_id,
                "provider": generated.provider,
                "generation_status": generated.generation_status,
                "source_type": source.source_type,
                "total_ms": elapsed_ms(started),
            },
        )
        return record

    def _require_generator(self) -> LessonGenerator:
        if self._generator is None:
            raise AppError(ErrorCode.AI_INPUT_NOT_SUPPORTED, NO_CAPABLE_PROVIDER)
        return self._generator

    def _processing_for(self, *, size_bytes: int | None) -> VideoProcessing:
        """How thoroughly the model should watch this video.

        Size is the only signal available without decoding the file, and for a link there is not
        even that: finding out how long a YouTube video is would mean fetching it, which this
        service does not do. A link therefore gets the cheaper single pass unless an operator has
        chosen otherwise.
        """
        mode = self._limits.processing_mode
        if mode != "auto":
            return mode
        if size_bytes is None:
            return "static"
        threshold_bytes = self._limits.agentic_threshold_mb * 1024 * 1024
        return "agentic" if size_bytes >= threshold_bytes else "static"
