"""Liveness endpoint. Touches no external services, so it stays fast and free."""

from fastapi import APIRouter, Request

from app import __version__
from app.schemas.health import HealthResponse

SERVICE_NAME = "api"

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=__version__,
        ai_mode=request.app.state.ai_mode,
    )
