"""Sending an uploaded video to the Files API, waiting for it, and always removing it again.

The SDK client is replaced by a stub, so these tests exercise our own upload, polling, error and
clean-up logic without a network or an API key.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.ai.provider import AIProviderError
from app.ai.video_upload import GeminiFilesUploader, NullVideoUploader
from tests.video_helpers import MP4

REMOTE_NAME = "files/abc123"
REMOTE_URI = "https://files.example/v/abc123"


class _FakeFile:
    def __init__(self, *, name: str = REMOTE_NAME, state: str, uri: str | None = REMOTE_URI):
        self.name = name
        self.state = state
        self.uri = uri


class _FakeFiles:
    """Stands in for `client.aio.files`, returning prepared states in order."""

    def __init__(
        self,
        *,
        results: list[Any],
        upload_error: Exception | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self._results = list(results)
        self._upload_error = upload_error
        self._delete_error = delete_error
        self.uploaded: list[dict[str, Any]] = []
        self.polled: list[str] = []
        self.deleted: list[str] = []

    async def upload(self, *, file: Any, config: Any) -> _FakeFile:
        path = Path(file)
        self.uploaded.append(
            {
                "path": path,
                "existed": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "mime_type": config.mime_type,
                "display_name": config.display_name,
            }
        )
        if self._upload_error is not None:
            raise self._upload_error
        return self._next()

    async def get(self, *, name: str) -> _FakeFile:
        self.polled.append(name)
        return self._next()

    async def delete(self, *, name: str) -> None:
        self.deleted.append(name)
        if self._delete_error is not None:
            raise self._delete_error

    def _next(self) -> _FakeFile:
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _FakeClient:
    def __init__(self, files: _FakeFiles) -> None:
        self.aio = type("_Aio", (), {"files": files})()


def uploader_for(files: _FakeFiles, **kwargs: Any) -> GeminiFilesUploader:
    return GeminiFilesUploader(
        client=_FakeClient(files),  # type: ignore[arg-type]
        poll_interval=0,
        **kwargs,
    )


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "lecture.mp4"
    path.write_bytes(MP4)
    return path


async def _collect(uploader: Any, path: Path) -> Any:
    async with uploader.upload(
        path, mime_type="video/mp4", display_name="lesson-1", processing="static"
    ) as source:
        return source


# ---- The happy path ----------------------------------------------------------------------------


def test_a_ready_video_becomes_a_watchable_source(video: Path) -> None:
    files = _FakeFiles(results=[_FakeFile(state="ACTIVE")])

    source = asyncio.run(_collect(uploader_for(files), video))

    assert (source.kind, source.uri, source.mime_type, source.processing) == (
        "upload",
        REMOTE_URI,
        "video/mp4",
        "static",
    )


def test_the_file_is_sent_from_disk_with_the_type_and_name_we_chose(video: Path) -> None:
    """Streamed from a path, so a large video never has to be held in memory here."""
    files = _FakeFiles(results=[_FakeFile(state="ACTIVE")])

    asyncio.run(_collect(uploader_for(files), video))

    assert files.uploaded == [
        {
            "path": video,
            "existed": True,
            "size": len(MP4),
            "mime_type": "video/mp4",
            "display_name": "lesson-1",
        }
    ]


def test_a_video_still_processing_is_waited_for(video: Path) -> None:
    files = _FakeFiles(
        results=[
            _FakeFile(state="PROCESSING"),
            _FakeFile(state="PROCESSING"),
            _FakeFile(state="ACTIVE"),
        ]
    )

    source = asyncio.run(_collect(uploader_for(files), video))

    assert source.uri == REMOTE_URI
    assert files.polled == [REMOTE_NAME, REMOTE_NAME]


# ---- Clean-up ----------------------------------------------------------------------------------


def test_the_remote_copy_is_deleted_after_a_successful_lesson(video: Path) -> None:
    files = _FakeFiles(results=[_FakeFile(state="ACTIVE")])

    asyncio.run(_collect(uploader_for(files), video))

    assert files.deleted == [REMOTE_NAME]


def test_the_remote_copy_is_deleted_when_the_work_inside_fails(video: Path) -> None:
    files = _FakeFiles(results=[_FakeFile(state="ACTIVE")])
    uploader = uploader_for(files)

    async def fail_while_watching() -> None:
        async with uploader.upload(
            video, mime_type="video/mp4", display_name="lesson-1", processing="static"
        ):
            raise RuntimeError("the model failed")

    with pytest.raises(RuntimeError):
        asyncio.run(fail_while_watching())

    assert files.deleted == [REMOTE_NAME], "a failed lesson must not leave a video behind"


@pytest.mark.parametrize(
    "results",
    [
        [_FakeFile(state="FAILED")],
        [_FakeFile(state="ACTIVE", uri=None)],
        [_FakeFile(state="PROCESSING"), _FakeFile(state="FAILED")],
    ],
    ids=["rejected-outright", "no-uri-returned", "failed-while-processing"],
)
def test_a_video_the_service_cannot_use_is_reported_and_cleaned_up(
    video: Path, results: list[Any]
) -> None:
    files = _FakeFiles(results=results)

    with pytest.raises(AIProviderError):
        asyncio.run(_collect(uploader_for(files), video))

    assert files.deleted == [REMOTE_NAME]


def test_a_video_stuck_processing_gives_up_and_cleans_up(video: Path) -> None:
    files = _FakeFiles(results=[_FakeFile(state="PROCESSING")] * 50)

    with pytest.raises(AIProviderError, match="still processing"):
        asyncio.run(_collect(uploader_for(files, processing_timeout=0), video))

    assert files.deleted == [REMOTE_NAME]


def test_a_failure_to_delete_does_not_fail_a_lesson_that_worked(video: Path) -> None:
    files = _FakeFiles(
        results=[_FakeFile(state="ACTIVE")], delete_error=RuntimeError("permission denied")
    )

    source = asyncio.run(_collect(uploader_for(files), video))

    assert source.uri == REMOTE_URI


# ---- Failures before anything exists remotely --------------------------------------------------


def test_a_rejected_upload_is_reported_and_nothing_is_deleted(video: Path) -> None:
    files = _FakeFiles(results=[], upload_error=RuntimeError("connection reset"))

    with pytest.raises(AIProviderError):
        asyncio.run(_collect(uploader_for(files), video))

    assert files.deleted == [], "there is no remote file to delete yet"


def test_a_polling_failure_is_reported(video: Path) -> None:
    files = _FakeFiles(results=[_FakeFile(state="PROCESSING"), RuntimeError("gone")])

    with pytest.raises(AIProviderError, match="state"):
        asyncio.run(_collect(uploader_for(files), video))


def test_failure_messages_never_carry_the_path_or_the_provider_s_own_words(video: Path) -> None:
    """Only the exception type is reported: SDK messages can echo request details back out."""
    files = _FakeFiles(results=[], upload_error=RuntimeError("Bearer sk-secret-value"))

    with pytest.raises(AIProviderError) as caught:
        asyncio.run(_collect(uploader_for(files), video))

    assert "sk-secret-value" not in str(caught.value)
    assert str(video) not in str(caught.value)
    assert "RuntimeError" in str(caught.value)


# ---- Mock mode ---------------------------------------------------------------------------------


def test_the_inert_uploader_makes_no_calls_and_yields_nothing_to_watch(video: Path) -> None:
    """With no provider configured there is nowhere to upload to, but the request still works."""
    source = asyncio.run(_collect(NullVideoUploader(), video))

    assert (source.kind, source.uri, source.mime_type) == ("upload", "", "video/mp4")
