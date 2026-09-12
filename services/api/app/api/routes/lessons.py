"""Lesson endpoints: create a lesson from an uploaded PDF, and fetch a stored lesson."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.core.errors import AppError, ErrorCode
from app.schemas.lessons_api import LessonRecord
from app.services.lesson_store import LessonStore
from app.services.pdf_lessons import PdfLessonService
from app.utils.ids import ensure_safe_id

router = APIRouter(prefix="/lessons", tags=["lessons"])


def get_pdf_lesson_service(request: Request) -> PdfLessonService:
    service: PdfLessonService = request.app.state.pdf_lesson_service
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
