"""Values that belong to the request being handled, readable anywhere without passing them along."""

from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
