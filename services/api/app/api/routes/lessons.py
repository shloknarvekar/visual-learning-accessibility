"""Lesson endpoints: create a lesson from a PDF, a video file or a YouTube link, and fetch one.

There is one endpoint per input type rather than a single normalised one, because the three do not
share a request: a PDF and a video arrive as multipart uploads with different size limits and
different accepted types, while a YouTube lesson is a small JSON body with no upload at all.
Collapsing them would mean one endpoint whose valid shape depends on a discriminator field, which
is harder to validate, harder to document and harder to call.

What they do share is the response. All three return the same `LessonRecord`, so a client renders
one shape and reads `lesson.source.source_type` when it needs to know where the lesson came from.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.core.errors import AppError, ErrorCode
from app.schemas.lessons_api import LessonRecord, YouTubeLessonRequest
from app.services.lesson_store import LessonStore
from app.services.pdf_lessons import PdfLessonService
from app.services.video_lessons import VideoLessonService
from app.utils.ids import ensure_safe_id

router = APIRouter(prefix="/lessons", tags=["lessons"])


def get_pdf_lesson_service(request: Request) -> PdfLessonService:
    service: PdfLessonService = request.app.state.pdf_lesson_service
    return service


def get_video_lesson_service(request: Request) -> VideoLessonService:
    service: VideoLessonService = request.app.state.video_lesson_service
    return service


def get_lesson_store(request: Request) -> LessonStore:
    store: LessonStore = request.app.state.lesson_store
    return store


@router.post(
    "/pdf",
    status_code=status.HTTP_201_CREATED,
    response_model=LessonRecord,
    response_model_exclude_none=True,
    summary="Create a lesson from a PDF",
)
async def create_lesson_from_pdf(
    file: Annotated[UploadFile, File(description="A text-based PDF file.")],
    service: Annotated[PdfLessonService, Depends(get_pdf_lesson_service)],
) -> LessonRecord:
    return await service.create_lesson(file)


@router.post(
    "/video",
    status_code=status.HTTP_201_CREATED,
    response_model=LessonRecord,
    response_model_exclude_none=True,
    summary="Create a lesson from an uploaded video",
)
async def create_lesson_from_video(
    file: Annotated[
        UploadFile,
        File(description="A video file. See the API reference for the accepted types and size."),
    ],
    service: Annotated[VideoLessonService, Depends(get_video_lesson_service)],
) -> LessonRecord:
    return await service.create_lesson_from_upload(file)


@router.post(
    "/youtube",
    status_code=status.HTTP_201_CREATED,
    response_model=LessonRecord,
    response_model_exclude_none=True,
    summary="Create a lesson from a public YouTube video",
)
async def create_lesson_from_youtube(
    body: YouTubeLessonRequest,
    service: Annotated[VideoLessonService, Depends(get_video_lesson_service)],
) -> LessonRecord:
    return await service.create_lesson_from_youtube(body.url)


@router.get(
    "/{lesson_id}",
    response_model=LessonRecord,
    response_model_exclude_none=True,
    summary="Get a stored lesson",
)
async def get_lesson(
    lesson_id: str, store: Annotated[LessonStore, Depends(get_lesson_store)]
) -> LessonRecord:
    try:
        ensure_safe_id(lesson_id)
    except ValueError:
        record = None  # an id that is not valid cannot belong to a stored lesson
    else:
        record = store.get(lesson_id)
    if record is None:
        raise AppError(ErrorCode.LESSON_NOT_FOUND, "No lesson exists with this id.")
    return record
