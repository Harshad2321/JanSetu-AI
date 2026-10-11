"""
JanSetu AI — Incident Database Repository.

Encapsulates all database queries and aggregations:
- Incident creation and retrieval
- Filtering by operational and evidence statuses
- Dashboard summary metric aggregation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import IncidentModel


def create_incident(db: Session, incident: IncidentModel) -> IncidentModel:
    """Persist a newly recorded incident."""
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def get_incident_by_id(db: Session, incident_id: str) -> Optional[IncidentModel]:
    """Retrieve single incident by its unique reference ID."""
    return db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()


def list_incidents(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    evidence_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[IncidentModel], int]:
    """List incidents matching optional filter criteria, sorted by creation date descending."""
    query = db.query(IncidentModel)

    if status:
        query = query.filter(IncidentModel.operational_status == status)
    if category:
        query = query.filter(IncidentModel.category == category)
    if evidence_status:
        query = query.filter(IncidentModel.evidence_status == evidence_status)

    total = query.count()
    items = query.order_by(IncidentModel.created_at.desc()).offset(offset).limit(limit).all()
    return items, total


def save_incident(db: Session, incident: IncidentModel) -> IncidentModel:
    """Save changes to an existing incident record."""
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """
    Compute operational dashboard metrics:
    - Total incidents
    - Breakdown by operational status
    - Breakdown by evidence status
    - Breakdown by category
    - Breakdown by priority band
    """
    total = db.query(func.count(IncidentModel.incident_id)).scalar() or 0

    # Operational status breakdown
    op_counts = (
        db.query(IncidentModel.operational_status, func.count(IncidentModel.incident_id))
        .group_by(IncidentModel.operational_status)
        .all()
    )
    operational_statuses = {str(status): int(count) for status, count in op_counts}

    # Evidence status breakdown
    ev_counts = (
        db.query(IncidentModel.evidence_status, func.count(IncidentModel.incident_id))
        .group_by(IncidentModel.evidence_status)
        .all()
    )
    evidence_statuses = {str(status): int(count) for status, count in ev_counts}

    # Category breakdown
    cat_counts = (
        db.query(IncidentModel.category, func.count(IncidentModel.incident_id))
        .group_by(IncidentModel.category)
        .all()
    )
    categories = {str(cat): int(count) for cat, count in cat_counts}

    # Priority band breakdown from stored priority JSON column
    all_incidents = db.query(IncidentModel.priority).filter(IncidentModel.priority.isnot(None)).all()
    priority_bands: Dict[str, int] = {}
    for (p_data,) in all_incidents:
        if isinstance(p_data, dict):
            band = p_data.get("priority_band", "Unassigned")
            priority_bands[band] = priority_bands.get(band, 0) + 1

    return {
        "total_incidents": total,
        "operational_statuses": operational_statuses,
        "evidence_statuses": evidence_statuses,
        "categories": categories,
        "priority_bands": priority_bands,
    }
