"""Validation of the two video inputs. Nothing here fetches anything over the network.

Both inputs are untrusted:

- A YouTube URL is never passed through as written. We match an 11-character video id ourselves and
  rebuild a canonical watch URL from it, so query strings, redirects, credentials and look-alike
  hosts cannot survive into the value Gemini is handed. Whether that video is public, private or
  deleted is not knowable without fetching it, which this server deliberately never does; Gemini
  reports that when it tries to watch it.
- An uploaded file is accepted only when its declared type and its leading bytes agree, and only
  for the video types Gemini documents. A `.mp4` name on a ZIP is rejected before anything is sent.
"""

import re
from collections.abc import Callable
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlparse

from app.core.errors import AppError, ErrorCode

# Hosts that serve YouTube watch pages. Compared against the parsed hostname, so
# "https://youtube.com@example.test/" does not match: its hostname is example.test.
_YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)

# Every YouTube video id is exactly 11 characters from this alphabet.
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Path shapes that identify a single video. Anything else - a channel, a playlist page, a search -
# has no single video to watch and is rejected.
_ID_BEARING_PREFIXES = ("shorts", "embed", "live", "v")

_NOT_YOUTUBE = "Only public YouTube video links are accepted."


def canonical_youtube_url(raw: str) -> str:
    """A canonical `https://www.youtube.com/watch?v=<id>` URL, or raise `AppError`.

    The result is built from a validated id, never from the caller's string.
    """
    return f"https://www.youtube.com/watch?v={youtube_video_id(raw)}"


def youtube_video_id(raw: str) -> str:
    """The video id in `raw`, or raise `AppError` when it is not a single-video YouTube link."""
    candidate = (raw or "").strip()
    if not candidate:
        raise AppError(ErrorCode.INVALID_VIDEO_URL, "Enter a YouTube video link.")

    try:
        parsed = urlparse(candidate)
    except ValueError as exc:  # malformed IPv6 literal, bad port
        raise AppError(
            ErrorCode.INVALID_VIDEO_URL, f"{_NOT_YOUTUBE} This link is not valid."
        ) from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise AppError(
            ErrorCode.INVALID_VIDEO_URL, f"{_NOT_YOUTUBE} The link must start with https://."
        )
    # Credentials in a URL are never legitimate here and are a classic way to disguise the host.
    if parsed.username or parsed.password:
        raise AppError(ErrorCode.INVALID_VIDEO_URL, _NOT_YOUTUBE)

    hostname = (parsed.hostname or "").lower()
    if hostname not in _YOUTUBE_HOSTS:
        raise AppError(ErrorCode.INVALID_VIDEO_URL, _NOT_YOUTUBE)

    video_id = _id_from_path_or_query(hostname, parsed.path, parsed.query)
    if video_id is None or not _VIDEO_ID.fullmatch(video_id):
        raise AppError(
            ErrorCode.INVALID_VIDEO_URL,
            f"{_NOT_YOUTUBE} This link does not point to a single video.",
        )
    return video_id


def _id_from_path_or_query(hostname: str, path: str, query: str) -> str | None:
    parts = [part for part in PurePosixPath(path).parts if part not in {"/", ""}]
    if hostname in {"youtu.be", "www.youtu.be"}:
        # The short form carries the id as the whole path: youtu.be/<id>
        return parts[0] if len(parts) == 1 else None
    if parts == ["watch"]:
        values = parse_qs(query).get("v", [])
        return values[0] if len(values) == 1 else None
    if len(parts) == 2 and parts[0] in _ID_BEARING_PREFIXES:
        return parts[1]
    return None


# ---- Uploaded files ----------------------------------------------------------------------------


def _is_iso_bmff(head: bytes) -> bool:
    """MP4, MOV and 3GPP all use the ISO base media container: a `ftyp` box at offset 4."""
    return len(head) >= 12 and head[4:8] == b"ftyp"


def _is_ebml(head: bytes) -> bool:
    return head.startswith(b"\x1a\x45\xdf\xa3")


def _is_riff_avi(head: bytes) -> bool:
    return head.startswith(b"RIFF") and head[8:12] == b"AVI "


def _is_mpeg_program_stream(head: bytes) -> bool:
    # Pack header or sequence header; both start an MPEG-1/2 stream.
    return head.startswith((b"\x00\x00\x01\xba", b"\x00\x00\x01\xb3"))


def _is_flv(head: bytes) -> bool:
    return head.startswith(b"FLV")


def _is_asf(head: bytes) -> bool:
    """WMV files are ASF containers, which begin with a fixed 16-byte GUID."""
    return head.startswith(b"\x30\x26\xb2\x75\x8e\x66\xcf\x11")


# The video types Gemini documents, each with the container signature it must actually have.
# Keys are exactly the MIME types sent to the Files API; nothing outside this set is ever uploaded.
SUPPORTED_VIDEO_MIME_TYPES: dict[str, Callable[[bytes], bool]] = {
    "video/mp4": _is_iso_bmff,
    "video/mpeg": _is_mpeg_program_stream,
    "video/mpg": _is_mpeg_program_stream,
    "video/mov": _is_iso_bmff,
    "video/avi": _is_riff_avi,
    "video/x-flv": _is_flv,
    "video/webm": _is_ebml,
    "video/wmv": _is_asf,
    "video/3gpp": _is_iso_bmff,
}

# Types browsers and tools send for the same containers, mapped onto the names Gemini uses.
_MIME_ALIASES = {
    "video/quicktime": "video/mov",
    "video/x-msvideo": "video/avi",
    "video/msvideo": "video/avi",
    "video/x-ms-wmv": "video/wmv",
    "video/x-ms-asf": "video/wmv",
    "video/flv": "video/x-flv",
    "video/3gp": "video/3gpp",
}

# Used only when the client declares nothing useful (octet-stream or an empty type).
_EXTENSION_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpg",
    ".mov": "video/mov",
    ".avi": "video/avi",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".wmv": "video/wmv",
    ".3gp": "video/3gpp",
}

_UNTYPED = frozenset({"", "application/octet-stream", "binary/octet-stream"})

# Enough for every signature above; the longest one reads up to offset 12.
SIGNATURE_BYTES = 16


# The extension to give the temporary file we stream an upload into. The Files API is told the
# MIME type explicitly, so this only has to be plausible, never authoritative.
_PREFERRED_EXTENSION = {
    "video/mp4": ".mp4",
    "video/mpeg": ".mpeg",
    "video/mpg": ".mpg",
    "video/mov": ".mov",
    "video/avi": ".avi",
    "video/x-flv": ".flv",
    "video/webm": ".webm",
    "video/wmv": ".wmv",
    "video/3gpp": ".3gp",
}


def supported_video_types() -> list[str]:
    return sorted(SUPPORTED_VIDEO_MIME_TYPES)


def extension_for(mime_type: str) -> str:
    return _PREFERRED_EXTENSION.get(mime_type, ".bin")


def resolve_video_mime_type(*, content_type: str | None, filename: str | None) -> str:
    """The Gemini MIME type for this upload, or raise `AppError` when it is not a supported video.

    A declared video type wins. When the client declares nothing - a plain file upload often
    arrives as octet-stream - the filename extension is used instead. The bytes are never used to
    pick the type; they are checked separately against whichever type this returns.
    """
    declared = (content_type or "").split(";")[0].strip().lower()
    resolved = _MIME_ALIASES.get(declared, declared)
    if resolved in SUPPORTED_VIDEO_MIME_TYPES:
        return resolved
    if declared in _UNTYPED:
        suffix = PurePosixPath((filename or "").replace("\\", "/")).suffix.lower()
        from_name = _EXTENSION_TYPES.get(suffix)
        if from_name is not None:
            return from_name
    raise AppError(ErrorCode.INVALID_FILE_TYPE, unsupported_video_message())


def ensure_video_signature(head: bytes, mime_type: str) -> None:
    """Raise unless `head` really is a container of `mime_type`."""
    matches = SUPPORTED_VIDEO_MIME_TYPES.get(mime_type)
    if matches is None or not matches(head):
        raise AppError(
            ErrorCode.INVALID_FILE_TYPE,
            "This file is not a video, or does not match the type it claims to be.",
        )


def unsupported_video_message() -> str:
    return "Only these video types are accepted: " + ", ".join(supported_video_types()) + "."
