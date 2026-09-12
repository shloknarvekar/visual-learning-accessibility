from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import AIProviderName


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    ai_mode: AIProviderName = Field(
        description="`mock` when no AI provider is configured: lessons come from example data."
    )
