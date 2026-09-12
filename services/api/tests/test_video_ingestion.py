"""Validating the two video inputs, with no network and no provider involved."""

import pytest

from app.core.errors import AppError, ErrorCode
from app.ingestion.video import (
    SUPPORTED_VIDEO_MIME_TYPES,
    canonical_youtube_url,
    ensure_video_signature,
    extension_for,
    resolve_video_mime_type,
    supported_video_types,
)
from tests.video_helpers import (
    AVI,
    CANONICAL_YOUTUBE_URL,
    FLV,
    MOV,
    MP4,
    MPEG,
    NOT_A_VIDEO,
    THREE_GPP,
    WEBM,
    WMV,
)

# ---- YouTube links -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "  https://youtu.be/dQw4w9WgXcQ  ",
    ],
    ids=[
        "watch",
        "no-www",
        "mobile",
        "music",
        "short-form",
        "shorts",
        "embed",
        "live",
        "old-v-path",
        "http-upgraded",
        "surrounding-whitespace",
    ],
)
def test_every_accepted_link_shape_becomes_one_canonical_url(url: str) -> None:
    assert canonical_youtube_url(url) == CANONICAL_YOUTUBE_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890&index=4",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://youtu.be/dQw4w9WgXcQ?si=trackingtoken",
    ],
    ids=["playlist-context", "start-time", "share-tracking"],
)
def test_extra_query_parameters_are_dropped_not_forwarded(url: str) -> None:
    """The URL handed to the provider is rebuilt from the id, so nothing else rides along."""
    assert canonical_youtube_url(url) == CANONICAL_YOUTUBE_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/123456789",
        "https://example.test/watch?v=dQw4w9WgXcQ",
        # The hostname here is example.test; "youtube.com" is only the userinfo.
        "https://www.youtube.com@example.test/watch?v=dQw4w9WgXcQ",
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com.example.test/watch?v=dQw4w9WgXcQ",
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "not a url at all",
        "",
        "   ",
    ],
    ids=[
        "other-video-site",
        "wrong-host",
        "host-disguised-as-userinfo",
        "look-alike-host",
        "subdomain-suffix-attack",
        "ftp-scheme",
        "file-scheme",
        "javascript-scheme",
        "not-a-url",
        "empty",
        "whitespace-only",
    ],
)
def test_links_that_are_not_youtube_videos_are_rejected(url: str) -> None:
    with pytest.raises(AppError) as caught:
        canonical_youtube_url(url)

    assert caught.value.code == ErrorCode.INVALID_VIDEO_URL
    assert caught.value.status_code == 422


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/playlist?list=PL1234567890",
        "https://www.youtube.com/@someteacher",
        "https://www.youtube.com/results?search_query=photosynthesis",
        "https://www.youtube.com/watch?v=tooshort",
        "https://www.youtube.com/watch?v=waaaaaaaaaytoolong",
        "https://www.youtube.com/watch?v=bad!chars??",
        "https://youtu.be/",
        "https://youtu.be/dQw4w9WgXcQ/extra",
    ],
    ids=[
        "home-page",
        "watch-without-id",
        "playlist",
        "channel",
        "search",
        "id-too-short",
        "id-too-long",
        "id-bad-characters",
        "short-form-without-id",
        "short-form-with-extra-path",
    ],
)
def test_youtube_links_without_a_single_video_are_rejected(url: str) -> None:
    """A private or deleted video cannot be told from a live one without fetching it, which this

    service never does - so the only thing checkable offline is that a link names one video.
    """
    with pytest.raises(AppError) as caught:
        canonical_youtube_url(url)

    assert caught.value.code == ErrorCode.INVALID_VIDEO_URL


def test_rejection_message_never_echoes_the_submitted_link() -> None:
    """The message is shown to a user and written by us, so it cannot carry their URL back out."""
    hostile = "https://evil.test/watch?v=dQw4w9WgXcQ&token=secret-value"

    with pytest.raises(AppError) as caught:
        canonical_youtube_url(hostile)

    assert "evil.test" not in caught.value.message
    assert "secret-value" not in caught.value.message


# ---- Uploaded files ----------------------------------------------------------------------------


def test_the_supported_types_are_exactly_the_ones_gemini_documents() -> None:
    assert supported_video_types() == [
        "video/3gpp",
        "video/avi",
        "video/mov",
        "video/mp4",
        "video/mpeg",
        "video/mpg",
        "video/webm",
        "video/wmv",
        "video/x-flv",
    ]


@pytest.mark.parametrize("mime_type", sorted(SUPPORTED_VIDEO_MIME_TYPES))
def test_every_supported_type_is_accepted_when_declared(mime_type: str) -> None:
    assert resolve_video_mime_type(content_type=mime_type, filename="lecture") == mime_type


@pytest.mark.parametrize(
    ("declared", "expected"),
    [
        ("video/quicktime", "video/mov"),
        ("video/x-msvideo", "video/avi"),
        ("video/msvideo", "video/avi"),
        ("video/x-ms-wmv", "video/wmv"),
        ("video/x-ms-asf", "video/wmv"),
        ("video/flv", "video/x-flv"),
        ("video/3gp", "video/3gpp"),
        ("VIDEO/MP4", "video/mp4"),
        ("video/mp4; codecs=avc1", "video/mp4"),
    ],
    ids=[
        "quicktime",
        "x-msvideo",
        "msvideo",
        "x-ms-wmv",
        "x-ms-asf",
        "flv",
        "3gp",
        "uppercase",
        "with-parameters",
    ],
)
def test_browser_type_names_are_mapped_onto_the_documented_ones(
    declared: str, expected: str
) -> None:
    assert resolve_video_mime_type(content_type=declared, filename="lecture.mp4") == expected


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("lecture.mp4", "video/mp4"),
        ("lecture.M4V", "video/mp4"),
        ("lecture.webm", "video/webm"),
        ("lecture.mov", "video/mov"),
        ("lecture.avi", "video/avi"),
        ("lecture.3gp", "video/3gpp"),
        ("C:\\Users\\me\\lecture.mp4", "video/mp4"),
    ],
    ids=["mp4", "uppercase-ext", "webm", "mov", "avi", "3gp", "windows-path"],
)
def test_the_extension_is_used_only_when_the_client_declares_nothing(
    filename: str, expected: str
) -> None:
    assert (
        resolve_video_mime_type(content_type="application/octet-stream", filename=filename)
        == expected
    )


@pytest.mark.parametrize(
    ("content_type", "filename"),
    [
        ("text/plain", "notes.txt"),
        ("application/pdf", "notes.pdf"),
        ("video/x-matroska", "lecture.mkv"),
        ("audio/mpeg", "lecture.mp3"),
        ("image/png", "diagram.png"),
        ("application/octet-stream", "lecture.mkv"),
        ("application/octet-stream", "lecture"),
        ("application/octet-stream", None),
        ("", "lecture.exe"),
    ],
    ids=[
        "text",
        "pdf",
        "matroska-not-supported",
        "audio-only",
        "image",
        "unknown-extension",
        "no-extension",
        "no-filename",
        "executable",
    ],
)
def test_types_gemini_does_not_document_are_rejected(
    content_type: str, filename: str | None
) -> None:
    with pytest.raises(AppError) as caught:
        resolve_video_mime_type(content_type=content_type, filename=filename)

    assert caught.value.code == ErrorCode.INVALID_FILE_TYPE
    assert caught.value.status_code == 415


@pytest.mark.parametrize(
    ("head", "mime_type"),
    [
        (MP4, "video/mp4"),
        (MOV, "video/mov"),
        (THREE_GPP, "video/3gpp"),
        (WEBM, "video/webm"),
        (AVI, "video/avi"),
        (MPEG, "video/mpeg"),
        (MPEG, "video/mpg"),
        (FLV, "video/x-flv"),
        (WMV, "video/wmv"),
    ],
    ids=["mp4", "mov", "3gpp", "webm", "avi", "mpeg", "mpg", "flv", "wmv"],
)
def test_a_real_container_passes_its_own_signature_check(head: bytes, mime_type: str) -> None:
    ensure_video_signature(head, mime_type)


@pytest.mark.parametrize(
    ("head", "mime_type"),
    [
        (NOT_A_VIDEO, "video/mp4"),
        (b"", "video/mp4"),
        (b"%PDF-1.7 not a video", "video/mp4"),
        (WEBM, "video/mp4"),
        (MP4, "video/webm"),
        (AVI, "video/wmv"),
        (b"RIFF\x00\x00\x00\x00WAVE", "video/avi"),
    ],
    ids=[
        "zip-named-mp4",
        "empty",
        "pdf-named-mp4",
        "webm-declared-as-mp4",
        "mp4-declared-as-webm",
        "avi-declared-as-wmv",
        "wav-declared-as-avi",
    ],
)
def test_bytes_that_disagree_with_the_declared_type_are_rejected(
    head: bytes, mime_type: str
) -> None:
    with pytest.raises(AppError) as caught:
        ensure_video_signature(head, mime_type)

    assert caught.value.code == ErrorCode.INVALID_FILE_TYPE


def test_an_unknown_type_can_never_pass_the_signature_check() -> None:
    with pytest.raises(AppError):
        ensure_video_signature(MP4, "video/x-matroska")


@pytest.mark.parametrize("mime_type", sorted(SUPPORTED_VIDEO_MIME_TYPES))
def test_every_supported_type_has_a_temporary_file_extension(mime_type: str) -> None:
    assert extension_for(mime_type).startswith(".")


def test_an_unknown_type_gets_a_neutral_extension() -> None:
    assert extension_for("video/x-matroska") == ".bin"
