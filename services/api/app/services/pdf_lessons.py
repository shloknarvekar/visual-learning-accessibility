"""Creates lessons from uploaded PDFs: upload -> extract -> chunk -> generate -> validate -> store.

Only the first three steps are specific to a PDF. Everything from generation onwards is shared with
every other input type and lives in `lesson_pipeline`.

Each step is timed and logged against a document id. Document text and filenames are never logged.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePath
from typing import Self

from fastapi import UploadFile

from app.ai.lesson_generator import LessonGenerationRequest, LessonGenerator
from app.core.config import Settings
from app.core.errors import AppError
from app.ingestion.pdf import extract_pdf
from app.models.content import ExtractedDocument
from app.schemas.lesson import Source
from app.schemas.lessons_api import LessonMetadata, LessonRecord, ProcessingTimings
from app.services.chunking import chunk_document
from app.services.lesson_pipeline import elapsed_ms, generate_lesson, notice_for, validate_lesson
from app.services.lesson_store import LessonStore
from app.services.uploads import stored_pdf_upload

logger = logging.getLogger(__name__)

# What to call the material when telling a reader this lesson is not about it.
MATERIAL = "the uploaded PDF"
MATERIAL_NOUN = "document"


@dataclass(frozen=True)
class PdfLessonLimits:
    max_upload_mb: int
    max_pages: int
    chunk_max_chars: int


class PdfLessonService:
    def __init__(
        self,
        *,
        generator: LessonGenerator,
        store: LessonStore,
        uploads_dir: Path,
        limits: PdfLessonLimits,
    ) -> None:
        self._generator = generator
        self._store = store
        self._uploads_dir = uploads_dir
        self._limits = limits

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        generator: LessonGenerator,
        store: LessonStore,
    ) -> Self:
        return cls(
            generator=generator,
            store=store,
            uploads_dir=settings.data_dir / "uploads",
            limits=PdfLessonLimits(
                max_upload_mb=settings.max_upload_mb,
                max_pages=settings.pdf_max_pages,
                chunk_max_chars=settings.chunk_max_chars,
            ),
        )

    async def create_lesson(self, upload: UploadFile) -> LessonRecord:
        started = time.perf_counter()
        async with stored_pdf_upload(
            upload, directory=self._uploads_dir, max_mb=self._limits.max_upload_mb
        ) as stored:
            document_id = stored.upload_id
            logger.info(
                "pdf upload received",
                extra={"document_id": document_id, "size_bytes": stored.size_bytes},
            )
            step = time.perf_counter()
            document = await self._extract(stored.path, document_id)
            extraction_ms = elapsed_ms(step)
        # The uploaded file has been deleted; the remaining steps only use the extracted text.

        step = time.perf_counter()
        chunks = chunk_document(document, max_chars=self._limits.chunk_max_chars)
        chunking_ms = elapsed_ms(step)
        logger.info(
            "document chunked",
            extra={
                "document_id": document_id,
                "chunk_count": len(chunks),
                "duration_ms": chunking_ms,
            },
        )

        source = Source(
            source_type="pdf",
            title=PurePath(stored.display_name).stem or "Uploaded PDF",
            filename=stored.display_name,
        )
        step = time.perf_counter()
        generated = await generate_lesson(
            self._generator,
            LessonGenerationRequest(
                lesson_id=document_id, source=source, document=document, chunks=chunks
            ),
        )
        generation_ms = elapsed_ms(step)

        step = time.perf_counter()
        lesson = validate_lesson(generated.lesson, document_id)
        validation_ms = elapsed_ms(step)

        record = LessonRecord(
            lesson_id=document_id,
            lesson=lesson,
            metadata=LessonMetadata(
                provider=generated.provider,
                generation_status=generated.generation_status,
                is_mock=generated.provider == "demo",
                notice=notice_for(generated, material=MATERIAL, noun=MATERIAL_NOUN),
                model=generated.model,
                source_filename=stored.display_name,
                page_count=document.total_pages,
                chunk_count=len(chunks),
                character_count=document.character_count,
                ai_request_count=generated.ai_request_count,
                warnings=_extraction_warnings(document) + generated.warnings,
                timings=ProcessingTimings(
                    extraction_ms=extraction_ms,
                    chunking_ms=chunking_ms,
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
                "document_id": document_id,
                "provider": generated.provider,
                "generation_status": generated.generation_status,
                "total_ms": elapsed_ms(started),
            },
        )
        return record

    async def _extract(self, path: Path, document_id: str) -> ExtractedDocument:
        started = time.perf_counter()
        try:
            document = await asyncio.to_thread(extract_pdf, path, max_pages=self._limits.max_pages)
        except AppError as exc:
            logger.warning(
                "pdf extraction failed",
                extra={
                    "document_id": document_id,
                    "error_code": exc.code,
                    "duration_ms": elapsed_ms(started),
                },
            )
            raise
        logger.info(
            "pdf text extracted",
            extra={
                "document_id": document_id,
                "page_count": document.total_pages,
                "character_count": document.character_count,
                "duration_ms": elapsed_ms(started),
            },
        )
        return document


def _extraction_warnings(document: ExtractedDocument) -> list[str]:
    empty_pages = document.empty_page_numbers
    if not empty_pages:
        return []
    pages = ", ".join(map(str, empty_pages))
    return [
        f"{len(empty_pages)} page(s) had no extractable text (pages {pages}). "
        "Scanned pages need OCR, which is planned."
    ]
