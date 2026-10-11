"""
JanSetu AI — Dashboard Aggregates & Metrics API Route.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repository import get_dashboard_summary
from app.db.session import get_db
from app.schemas.api import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    """
    Retrieve operational aggregates:
    - Total recorded incidents
    - Breakdown by operational lifecycle status
    - Breakdown by photographic evidence outcome
    - Breakdown by incident category
    - Breakdown by priority tier
    """
    summary = get_dashboard_summary(db)
    return DashboardSummaryResponse(**summary)
