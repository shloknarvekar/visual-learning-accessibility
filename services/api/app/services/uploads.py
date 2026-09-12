"""Safe handling of uploaded files.

The same rules apply to every upload, whatever it is:

- It is streamed to disk in pieces under a hard size limit, so it never sits in memory whole. This
  matters most for video, where holding a whole file in memory is how a small server falls over.
- It is stored under a server-generated name inside the data directory and deleted when processing
  ends, whether that ended well or badly.
- The client's filename is used only as display text, after removing directories and control
  characters. It never reaches the filesystem.
- Its first bytes must match what it claims to be. A name and a declared type are both caller
  controlled; the container signature is the part that is not.

A content hash is computed while streaming, so the same file sent twice is recognisable later
without reading it again.
"""

import hashlib
import logging
import re
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from fastapi import UploadFile

from app.core.errors import AppError, ErrorCode
from app.ingestion.video import (
    SIGNATURE_BYTES,
    ensure_video_signature,
    extension_for,
    resolve_video_mime_type,
)

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
    content_hash: str


@dataclass(frozen=True)
class StoredVideoUpload(StoredUpload):
    mime_type: str


@asynccontextmanager
async def stored_pdf_upload(
    upload: UploadFile, *, directory: Path, max_mb: int
) -> AsyncIterator[StoredUpload]:
    """Save `upload` under a generated name for the duration of the `async with` block."""
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ACCEPTED_CONTENT_TYPES:
        raise AppError(ErrorCode.INVALID_FILE_TYPE, _ONLY_PDF)

    def check_head(head: bytes) -> None:
        if _PDF_SIGNATURE not in head[:_SIGNATURE_WINDOW]:
            raise AppError(ErrorCode.INVALID_FILE_TYPE, f"{_ONLY_PDF} This file is not a PDF.")

    directory.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex
    path = directory / f"{upload_id}.pdf"
    try:
        size, digest = await _save_with_limit(upload, path, max_mb=max_mb, check_head=check_head)
        yield StoredUpload(
            upload_id=upload_id,
            path=path,
            display_name=display_filename(upload.filename),
            size_bytes=size,
            content_hash=digest,
        )
    finally:
        _delete(path, upload_id)


@asynccontextmanager
async def stored_video_upload(
    upload: UploadFile, *, directory: Path, max_mb: int
) -> AsyncIterator[StoredVideoUpload]:
    """Save a video upload under a generated name for the duration of the `async with` block.

    The type is resolved before a byte is written and the signature is checked on the first chunk,
    so an unsupported or mislabelled file is rejected without a whole video reaching the disk.
    """
    mime_type = resolve_video_mime_type(content_type=upload.content_type, filename=upload.filename)

    def check_head(head: bytes) -> None:
        ensure_video_signature(head[:SIGNATURE_BYTES], mime_type)

    directory.mkdir(parents=True, exist_ok=True)
    upload_id = uuid.uuid4().hex
    path = directory / f"{upload_id}{extension_for(mime_type)}"
    try:
        size, digest = await _save_with_limit(upload, path, max_mb=max_mb, check_head=check_head)
        yield StoredVideoUpload(
            upload_id=upload_id,
            path=path,
            display_name=display_filename(upload.filename, fallback="video"),
            size_bytes=size,
            content_hash=digest,
            mime_type=mime_type,
        )
    finally:
        _delete(path, upload_id)


def display_filename(filename: str | None, *, fallback: str = "document.pdf") -> str:
    """The last path component of `filename` without control characters, or a generic name."""
    name = PureWindowsPath(PurePosixPath(filename or "").name).name
    name = _CONTROL_CHARACTERS.sub("", name).strip()
    return name[:_MAX_DISPLAY_NAME_LENGTH] or fallback


async def _save_with_limit(
    upload: UploadFile,
    path: Path,
    *,
    max_mb: int,
    check_head: Callable[[bytes], None],
) -> tuple[int, str]:
    max_bytes = max_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    with path.open("wb") as destination:
        while chunk := await upload.read(_READ_SIZE):
            if size == 0:
                check_head(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise AppError(
                    ErrorCode.FILE_TOO_LARGE, f"The file is larger than the {max_mb} MB limit."
                )
            digest.update(chunk)
            destination.write(chunk)
    if size == 0:
        raise AppError(ErrorCode.INVALID_FILE_TYPE, "The uploaded file is empty.")
    return size, digest.hexdigest()


def _delete(path: Path, upload_id: str) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Clean-up must not replace the request's real outcome. The file stays in the uploads
        # folder and the warning makes that visible.
        logger.warning("upload could not be deleted", extra={"upload_id": upload_id}, exc_info=True)
