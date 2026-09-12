"""Putting an uploaded video where the model can watch it, and taking it away again.

Gemini reads video from a URI, not from the request body, so an uploaded file has to reach the
Files API before it can be watched. That store is remote and lives in our account, so an upload here
is never left behind: `upload` is a context manager that deletes the remote file on the way out,
whether the lesson succeeded, failed, or the video never finished processing.

The bytes are streamed from a path by the SDK; this module never holds a whole video in memory, and
never sends the learner's own filename to the provider.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import Any, Protocol, Self

import httpx
from google import genai
from google.genai.types import UploadFileConfig

from app.ai.provider import AIConfigurationError, AIProviderError
from app.core.config import Settings
from app.models.media import VideoProcessing, VideoSource

logger = logging.getLogger(__name__)

# Sending a large file is slower than asking a question about one, so this is generous. It still
# bounds the request: without it a stalled upload would hold a worker open indefinitely.
UPLOAD_TIMEOUT_SECONDS = 300.0

# After the bytes arrive the service decodes the video before it can be watched. This is how long
# we wait for that, and how often we ask.
PROCESSING_TIMEOUT_SECONDS = 180.0
POLL_INTERVAL_SECONDS = 2.0


class VideoUploader(Protocol):
    def upload(
        self,
        path: Path,
        *,
        mime_type: str,
        display_name: str,
        processing: VideoProcessing,
    ) -> AbstractAsyncContextManager[VideoSource]:
        """Make `path` watchable for the duration of the block, then remove it again."""
        ...


class NullVideoUploader:
    """Used when there is no provider to upload to, which is mock mode.

    An uploaded video still has to be accepted, validated and cleaned up the same way, so the only
    step that is skipped is the one with nothing on the other end. The `VideoSource` it yields
    carries no URI because nothing will watch it: the only generator reachable in that state is
    `MockLessonGenerator`, which ignores the video and returns fixed example content. This keeps a
    video upload working with no API key at all, exactly like a PDF upload does.
    """

    @asynccontextmanager
    async def upload(
        self,
        path: Path,
        *,
        mime_type: str,
        display_name: str,
        processing: VideoProcessing,
    ) -> AsyncIterator[VideoSource]:
        yield VideoSource(kind="upload", uri="", processing=processing, mime_type=mime_type)


def _state_of(file: Any) -> str:
    """The file's state as a plain name, however the SDK happens to represent the enum."""
    state = getattr(file, "state", None)
    return str(getattr(state, "name", state) or "").upper()


class GeminiFilesUploader:
    """`VideoUploader` backed by the Gemini Files API."""

    def __init__(
        self,
        *,
        client: genai.Client,
        processing_timeout: float = PROCESSING_TIMEOUT_SECONDS,
        poll_interval: float = POLL_INTERVAL_SECONDS,
        upload_timeout: float = UPLOAD_TIMEOUT_SECONDS,
    ) -> None:
        self._client = client
        self._processing_timeout = processing_timeout
        self._poll_interval = poll_interval
        self._upload_timeout = upload_timeout

    @classmethod
    def from_settings(
        cls, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> Self:
        if settings.gemini_api_key is None:
            raise AIConfigurationError("Set GEMINI_API_KEY to send videos to Gemini.")
        http_options: dict[str, Any] = {}
        if transport is not None:
            http_options["async_client_args"] = {"transport": transport}
        client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=http_options or None,
        )
        return cls(client=client)

    @asynccontextmanager
    async def upload(
        self,
        path: Path,
        *,
        mime_type: str,
        display_name: str,
        processing: VideoProcessing,
    ) -> AsyncIterator[VideoSource]:
        file = await self._send(path, mime_type=mime_type, display_name=display_name)
        name = getattr(file, "name", None)
        try:
            ready = await self._wait_until_watchable(file)
            uri = getattr(ready, "uri", None)
            if not uri:
                raise AIProviderError("Gemini accepted the video but returned no URI for it.")
            yield VideoSource(kind="upload", uri=uri, processing=processing, mime_type=mime_type)
        finally:
            # Runs for a failed lesson and a failed upload alike: the remote copy is ours to clean
            # up either way, and leaving it behind would quietly fill the account's file store.
            await self._delete(name)

    async def _send(self, path: Path, *, mime_type: str, display_name: str) -> Any:
        try:
            async with asyncio.timeout(self._upload_timeout):
                return await self._client.aio.files.upload(
                    file=path,
                    config=UploadFileConfig(mime_type=mime_type, display_name=display_name),
                )
        except TimeoutError as exc:
            raise AIProviderError(
                f"Sending the video to Gemini exceeded its {self._upload_timeout:g}s deadline."
            ) from exc
        except Exception as exc:
            # Error text from the SDK can echo request details, so only the type is reported.
            raise AIProviderError(
                f"Gemini rejected the video upload: {type(exc).__name__}."
            ) from exc

    async def _wait_until_watchable(self, file: Any) -> Any:
        """Poll until the service finishes decoding the video, or give up."""
        current = file
        name = getattr(current, "name", None)
        deadline = time.monotonic() + self._processing_timeout
        while _state_of(current) == "PROCESSING":
            if time.monotonic() >= deadline:
                raise AIProviderError(
                    f"Gemini was still processing the video after {self._processing_timeout:g}s."
                )
            await asyncio.sleep(self._poll_interval)
            try:
                current = await self._client.aio.files.get(name=name)
            except Exception as exc:
                raise AIProviderError(
                    f"Could not check the uploaded video's state: {type(exc).__name__}."
                ) from exc

        state = _state_of(current)
        if state != "ACTIVE":
            raise AIProviderError(
                f"Gemini could not process the video (state {state or 'unknown'})."
            )
        return current

    async def _delete(self, name: str | None) -> None:
        if not name:
            return
        try:
            await self._client.aio.files.delete(name=name)
        except Exception:
            # Clean-up must never replace the request's real outcome. The remote file expires on
            # its own; the warning makes a leak visible without failing a lesson that worked.
            logger.warning("uploaded video could not be deleted from the provider", exc_info=True)
