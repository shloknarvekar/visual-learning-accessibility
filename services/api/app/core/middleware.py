"""HTTP middleware: request ids, one structured log line per request, and an upload size limit."""

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from app.core import request_context
from app.core.errors import ErrorCode, error_response

REQUEST_ID_HEADER = "X-Request-ID"
# Room for the multipart boundaries and form headers that surround an uploaded file.
MULTIPART_OVERHEAD_BYTES = 64 * 1024

logger = logging.getLogger("app.request")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generated server-side, not accepted from the client, so ids are unique and log-safe.
        current_request_id = uuid.uuid4().hex
        token = request_context.request_id.set(current_request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = current_request_id
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            return response
        finally:
            request_context.request_id.reset(token)


def register_upload_size_limit(app: FastAPI, *, max_upload_mb: int) -> None:
    """Reject requests that declare a body over the upload limit, before the body is read.

    Uploads sent without a Content-Length header are still limited while they are saved.
    """
    max_body_bytes = max_upload_mb * 1024 * 1024 + MULTIPART_OVERHEAD_BYTES

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next: RequestResponseEndpoint) -> Response:
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > max_body_bytes:
            return error_response(
                413,
                ErrorCode.FILE_TOO_LARGE,
                f"The file is larger than the {max_upload_mb} MB limit.",
            )
        return await call_next(request)
