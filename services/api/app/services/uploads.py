"""Safe handling of uploaded PDF files.

- The file is streamed to disk in pieces with a hard size limit, so it never sits in memory whole.
- It is stored under a server-generated name inside the data directory and deleted when processing
  ends.
- The client's filename is used only as display text, after removing directories and control
  characters.
- Only files that start with the PDF signature are accepted, whatever their name or declared type.
"""

import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import UploadFile

from app.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_PDF_SIGNATURE = b"%PDF-"
_SIGNATURE_WINDOW = 1024  # PDF readers accept the header anywhere in the first 1024 bytes
_READ_SIZE = 1024 * 1024
_ACCEPTED_CONTENT_TYPES = frozenset(
    {"application/pdf", "application/x-pdf", "application/octet-stream", ""}
)
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_MAX_DISPLAY_NAME_LENGTH = 200
_ONLY_PDF = "Only PDF files are accepted."


@dataclass(frozen=True)
class StoredUpload:
    upload_id: str
    path: Path
    display_name: str
    size_bytes: int


@asynccontextmanager
async def stored_pdf_upload(
    upload: UploadFile, *, directory: Path, max_mb: int
) -> AsyncIterator[StoredUpload]:
    """Save `upload` under a generated name for the duration of the `async with` block."""
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ACCEPTED_CONTENT_TYPES:
        raise AppError(ErrorCode.INVALID_FILE_TYPE, _ONLY_PDF)

    directory.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex
    path = directory / f"{upload_id}.pdf"
    try:
        size = await _save_with_limit(upload, path, max_mb=max_mb)
        yield StoredUpload(
            upload_id=upload_id,
            path=path,
            display_name=display_filename(upload.filename),
            size_bytes=size,
        )
    finally:
        _delete(path, upload_id)


def display_filename(filename: str | None) -> str:
    """The last path component of `filename` without control characters, or a generic name."""
    name = PureWindowsPath(PurePosixPath(filename or "").name).name
    name = _CONTROL_CHARACTERS.sub("", name).strip()
    return name[:_MAX_DISPLAY_NAME_LENGTH] or "document.pdf"


async def _save_with_limit(upload: UploadFile, path: Path, *, max_mb: int) -> int:
    max_bytes = max_mb * 1024 * 1024
    size = 0
    with path.open("wb") as destination:
        while chunk := await upload.read(_READ_SIZE):
            if size == 0 and _PDF_SIGNATURE not in chunk[:_SIGNATURE_WINDOW]:
                raise AppError(ErrorCode.INVALID_FILE_TYPE, f"{_ONLY_PDF} This file is not a PDF.")
            size += len(chunk)
            if size > max_bytes:
                raise AppError(
                    ErrorCode.FILE_TOO_LARGE, f"The file is larger than the {max_mb} MB limit."
                )
            destination.write(chunk)
    if size == 0:
        raise AppError(ErrorCode.INVALID_FILE_TYPE, "The uploaded file is empty.")
    return size


def _delete(path: Path, upload_id: str) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Clean-up must not replace the request's real outcome. The file stays in the uploads
        # folder and the warning makes that visible.
        logger.warning("upload could not be deleted", extra={"upload_id": upload_id}, exc_info=True)
