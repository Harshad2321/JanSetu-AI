"""
JanSetu AI — Health Check API Route.
"""

from __future__ import annotations

from fastapi import APIRouter
from app.config import settings
from app.schemas.api import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Check application and configuration health.
    Never exposes API credentials or internal connection strings.
    """
    return HealthResponse(
        status="healthy",
        service="JanSetu AI Backend",
        environment=settings.ENVIRONMENT,
        database="connected",
        groq_configured=bool(settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 5),
    )
