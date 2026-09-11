"""Identifier rules shared by the contract models and code that turns ids into paths or URLs."""

import re

# Keep in sync with $defs.Id.pattern in packages/contracts/lesson.schema.json.
ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
_ID_REGEX = re.compile(ID_PATTERN)


def ensure_safe_id(value: str) -> str:
    """Return `value` if it matches ID_PATTERN; otherwise raise ValueError.

    Safe ids contain no path separators, dots, or whitespace, so they cannot escape a directory.
    """
    if not _ID_REGEX.fullmatch(value):
        raise ValueError("invalid id: use 1-64 letters, digits, '-' or '_'")
    return value
