"""Versioned API. Register new route modules (for example `lessons`) on this router."""

from fastapi import APIRouter

from app.api.routes import health

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
