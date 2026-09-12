"""Versioned API. Register new route modules on this router."""

from fastapi import APIRouter

from app.api.routes import health, lessons

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(lessons.router)
