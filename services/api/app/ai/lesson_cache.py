"""Cache of lessons that a live provider already produced, keyed by document content.

When every provider is unavailable, a document that was generated successfully before can be served
from here instead of falling back to demo content. Entries are validated `Lesson` JSON, so a cached
lesson goes through the same Pydantic validation as a fresh one.
"""

import hashlib
import logging
from pathlib import Path
from typing import Protocol

from app.models.content import ExtractedDocument
from app.schemas.lesson import Lesson

logger = logging.getLogger(__name__)


def document_cache_key(document: ExtractedDocument) -> str:
    """Stable key for a document's extracted text. Same text, same key."""
    text = "\n\n".join(page.text for page in document.pages)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LessonCache(Protocol):
    def get(self, key: str) -> Lesson | None: ...

    def put(self, key: str, lesson: Lesson) -> None: ...


class NullLessonCache:
    """Used when caching is turned off."""

    def get(self, key: str) -> Lesson | None:
        return None

    def put(self, key: str, lesson: Lesson) -> None:
        return None


class FileLessonCache:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def get(self, key: str) -> Lesson | None:
        path = self._path_for(key)
        if not path.is_file():
            return None
        try:
            return Lesson.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A damaged entry must never break a request; treat it as a miss.
            logger.warning("cached lesson could not be read", extra={"cache_key": key})
            return None

    def put(self, key: str, lesson: Lesson) -> None:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            path = self._path_for(key)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(lesson.model_dump_json(exclude_none=True), encoding="utf-8")
            temporary.replace(path)
        except OSError:
            # Caching is an optimisation; failing to write it must not fail the request.
            logger.warning("lesson could not be cached", extra={"cache_key": key})

    def _path_for(self, key: str) -> Path:
        # Keys are hex digests produced here, so they are always safe as file names.
        return self._directory / f"{key}.json"
