"""FastAPI application factory.

Run locally from services/api:  uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai.factory import create_lesson_generator, resolve_ai_mode
from app.api.router import api_v1_router
from app.api.routes import health
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    REQUEST_ID_HEADER,
    register_request_logging,
    register_upload_size_limit,
)
from app.services.lesson_store import FileLessonStore
from app.services.pdf_lessons import PdfLessonService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.is_production)

    app = FastAPI(
        title="Visual Learning API",
        version=__version__,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.ai_mode = resolve_ai_mode(settings)
    if app.state.ai_mode != settings.ai_provider:
        logger.warning(
            "AI provider is not configured; serving deterministic mock lessons",
            extra={"ai_provider": settings.ai_provider},
        )
    app.state.lesson_store = FileLessonStore(settings.data_dir)
    app.state.pdf_lesson_service = PdfLessonService.from_settings(
        settings,
        generator=create_lesson_generator(settings),
        store=app.state.lesson_store,
    )

    register_exception_handlers(app)
    # Middleware registered later wraps middleware registered earlier.
    register_upload_size_limit(app, max_upload_mb=settings.max_upload_mb)
    register_request_logging(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    app.include_router(health.router)  # unversioned /health for deploy platforms and uptime checks
    app.include_router(api_v1_router)
    return app


app = create_app()
