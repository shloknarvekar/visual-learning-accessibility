"""Normalised media input passed between ingestion and the AI layer.

Internal: not part of the public API contract. Ingestion turns either video input - a public
YouTube URL or an uploaded file - into the same `VideoSource`, so the AI layer never learns which
endpoint the request arrived on and there is one video path to test.
"""

from dataclasses import dataclass
from typing import Literal

# How the model should watch the video. Both values are documented Gemini processing modes; no
# other value is ever sent.
#   static   samples frames at a fixed rate in one pass - cheaper, right for short clips
#   agentic  lets the model navigate the video itself - what long recordings need
VideoProcessing = Literal["static", "agentic"]

VideoKind = Literal["youtube", "upload"]


@dataclass(frozen=True)
class VideoSource:
    """A video the model can watch, identified only by a URI Gemini is allowed to read.

    This API server never fetches `uri` itself. For `youtube` it is a canonical watch URL that
    only Gemini resolves; for `upload` it is a Gemini Files API URI for bytes we already sent.
    """

    kind: VideoKind
    uri: str
    processing: VideoProcessing
    # Set for uploads, which carry bytes of a known type. None for YouTube, where we never see the
    # media and must not guess.
    mime_type: str | None = None
