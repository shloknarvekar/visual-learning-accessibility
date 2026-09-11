"""FastAPI application factory.

Run locally from services/api:  uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai.factory import resolve_ai_mode
from app.api.router import api_v1_router
from app.api.routes import health
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, register_request_logging

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

    register_exception_handlers(app)
    register_request_logging(app)
    # Registered last so it is the outermost middleware and also covers error responses.
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
