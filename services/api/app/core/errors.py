"""Error handling. Every error response uses one JSON envelope, and internal details never leak:

    {"error": {"code": "PDF_HAS_NO_EXTRACTABLE_TEXT", "message": "...", "details": [...]}}

`code` is a stable identifier clients can switch on. `message` is plain language and may change.
"""

import logging
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    HTTP_ERROR = "HTTP_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    PDF_EXTRACTION_FAILED = "PDF_EXTRACTION_FAILED"
    PDF_HAS_NO_EXTRACTABLE_TEXT = "PDF_HAS_NO_EXTRACTABLE_TEXT"
    PDF_TOO_MANY_PAGES = "PDF_TOO_MANY_PAGES"
    DOCUMENT_TOO_LONG = "DOCUMENT_TOO_LONG"
    INVALID_VIDEO_URL = "INVALID_VIDEO_URL"
    VIDEO_PROCESSING_FAILED = "VIDEO_PROCESSING_FAILED"
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    # The configured providers cannot read this kind of input at all. Distinct from
    # AI_PROVIDER_UNAVAILABLE, which means a provider that *could* have answered did not: retrying
    # this request will never help until a video-capable provider is configured.
    AI_INPUT_NOT_SUPPORTED = "AI_INPUT_NOT_SUPPORTED"
    AI_RATE_LIMITED = "AI_RATE_LIMITED"
    AI_INVALID_RESPONSE = "AI_INVALID_RESPONSE"
    LESSON_VALIDATION_FAILED = "LESSON_VALIDATION_FAILED"
    LESSON_NOT_FOUND = "LESSON_NOT_FOUND"


_STATUS_CODES: dict[ErrorCode, int] = {
    ErrorCode.INVALID_FILE_TYPE: 415,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.PDF_EXTRACTION_FAILED: 422,
    ErrorCode.PDF_HAS_NO_EXTRACTABLE_TEXT: 422,
    ErrorCode.PDF_TOO_MANY_PAGES: 422,
    ErrorCode.DOCUMENT_TOO_LONG: 422,
    ErrorCode.INVALID_VIDEO_URL: 422,
    ErrorCode.VIDEO_PROCESSING_FAILED: 502,
    ErrorCode.AI_PROVIDER_UNAVAILABLE: 503,
    ErrorCode.AI_INPUT_NOT_SUPPORTED: 503,
    ErrorCode.AI_RATE_LIMITED: 429,
    ErrorCode.AI_INVALID_RESPONSE: 502,
    ErrorCode.LESSON_VALIDATION_FAILED: 502,
    ErrorCode.LESSON_NOT_FOUND: 404,
}


class AppError(Exception):
    """An expected failure whose message is safe to show to API clients."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = _STATUS_CODES.get(code, 400)


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    *,
    details: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(
            exc.status_code, ErrorCode.HTTP_ERROR, str(exc.detail), headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = jsonable_encoder(exc.errors())
        return error_response(
            422, ErrorCode.VALIDATION_ERROR, "The request is invalid.", details=details
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error", exc_info=exc, extra={"path": request.url.path})
        return error_response(500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred.")
