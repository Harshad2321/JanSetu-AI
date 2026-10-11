"""
JanSetu AI — Explicit Demonstration Incident Seeding Utility.

Provides on-demand seeding of representative municipal incidents for demonstration
and UI development.

Rules:
- Never executed automatically on application startup.
- Only invoked via explicit administrative or API seed requests.
- Checks for existing incident IDs to avoid duplication.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from app.db.models import IncidentModel
from app.db.repository import get_incident_by_id
from app.schemas.incident import (
    AuditEvent,
    EvidenceOutcome,
    IncidentCategory,
    LocationSource,
    OperationalStatus,
    PriorityBand,
)

logger = logging.getLogger("jansetu.seed")


def seed_demonstration_incidents(db: Session) -> List[str]:
    """
    Seed structured demonstration incidents if they do not already exist.
    Returns list of seeded incident IDs.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    demonstration_records = [
        {
            "incident_id": "INC-DEMO-01",
            "complaint": "Severe deep pothole on Ring Road near Mayur Vihar flyover causing traffic congestion and bike skids.",
            "category": IncidentCategory.POTHOLE.value,
            "location_data": {
                "latitude": 28.6139,
                "longitude": 77.2090,
                "accuracy_meters": 8.5,
                "source": LocationSource.DEVICE_GPS.value,
                "address_text": "Ring Road, near Mayur Vihar Phase 1 Flyover, Delhi",
                "is_user_confirmed": True,
            },
            "has_photograph": True,
            "operational_status": OperationalStatus.TRIAGED.value,
            "evidence_status": EvidenceOutcome.MATCHED.value,
            "priority": {
                "priority_score": 82,
                "priority_band": PriorityBand.CRITICAL.value,
                "explanation": "Critical arterial road pothole with acute vehicular accident hazard.",
            },
            "audit_timeline": [
                AuditEvent(
                    timestamp=now_iso,
                    agent="Intake Portal",
                    action="Incident Submitted",
                    result="Recorded with citizen GPS location and matched photograph.",
                ).model_dump(),
                AuditEvent(
                    timestamp=now_iso,
                    agent="Priority Intelligence",
                    action="Priority Evaluated",
                    result="Score: 82 (Critical) assigned due to arterial exposure and skid risks.",
                ).model_dump(),
            ],
        },
        {
            "incident_id": "INC-DEMO-02",
            "complaint": "Heavy waterlogging under South Ext metro underpass after morning rain, 2 feet water accumulated.",
            "category": IncidentCategory.WATERLOGGING.value,
            "location_data": {
                "latitude": 28.5670,
                "longitude": 77.2210,
                "accuracy_meters": 12.0,
                "source": LocationSource.DEVICE_GPS.value,
                "address_text": "South Extension Underpass, Ring Road, Delhi",
                "is_user_confirmed": True,
            },
            "has_photograph": True,
            "operational_status": OperationalStatus.PLANNING.value,
            "evidence_status": EvidenceOutcome.MATCHED.value,
            "priority": {
                "priority_score": 88,
                "priority_band": PriorityBand.CRITICAL.value,
                "explanation": "Submerged metro underpass blocking arterial traffic flow.",
            },
            "audit_timeline": [
                AuditEvent(
                    timestamp=now_iso,
                    agent="Intake Portal",
                    action="Incident Submitted",
                    result="Waterlogging report confirmed with visual photograph.",
                ).model_dump(),
            ],
        },
        {
            "incident_id": "INC-DEMO-03",
            "complaint": "Garbage accumulation behind Community Center block C. Strong foul odor, stray cattle gathering.",
            "category": IncidentCategory.GARBAGE.value,
            "location_data": {
                "latitude": 28.6300,
                "longitude": 77.2150,
                "accuracy_meters": 15.0,
                "source": LocationSource.MANUAL_ENTRY.value,
                "address_text": "Behind Block C Community Centre, Delhi",
                "is_user_confirmed": False,
            },
            "has_photograph": False,
            "operational_status": OperationalStatus.RECORDED_PENDING_REVIEW.value,
            "evidence_status": EvidenceOutcome.NOT_PROVIDED.value,
            "priority": {
                "priority_score": 45,
                "priority_band": PriorityBand.MEDIUM.value,
                "explanation": "Residential sanitation backlog queued for standard municipal inspection.",
            },
            "audit_timeline": [
                AuditEvent(
                    timestamp=now_iso,
                    agent="Intake Portal",
                    action="Complaint Recorded Without Photo",
                    result="Accepted and queued as RECORDED_PENDING_REVIEW.",
                ).model_dump(),
            ],
        },
        {
            "incident_id": "INC-DEMO-04",
            "complaint": "Reported garbage dump on street corner, but uploaded image shows an unrelated indoor indoor scene.",
            "category": IncidentCategory.GARBAGE.value,
            "location_data": {
                "latitude": 28.6250,
                "longitude": 77.2180,
                "accuracy_meters": 20.0,
                "source": LocationSource.USER_PIN_ADJUSTED.value,
                "address_text": "Connaught Place Outer Circle, Delhi",
                "is_user_confirmed": True,
            },
            "has_photograph": True,
            "operational_status": OperationalStatus.AWAITING_CLARIFICATION.value,
            "evidence_status": EvidenceOutcome.MISMATCH.value,
            "audit_timeline": [
                AuditEvent(
                    timestamp=now_iso,
                    agent="Incident Intelligence",
                    action="Evidence Mismatch Flagged",
                    result="Complaint preserved; citizen prompted for clarification.",
                ).model_dump(),
            ],
        },
    ]

    seeded_ids: List[str] = []
    for record in demonstration_records:
        existing = get_incident_by_id(db, record["incident_id"])
        if not existing:
            incident = IncidentModel(
                incident_id=record["incident_id"],
                complaint=record["complaint"],
                category=record["category"],
                location_data=record["location_data"],
                has_photograph=record["has_photograph"],
                operational_status=record["operational_status"],
                evidence_status=record["evidence_status"],
                priority=record.get("priority"),
                audit_timeline=record.get("audit_timeline", []),
                created_at=now,
                updated_at=now,
            )
            db.add(incident)
            seeded_ids.append(record["incident_id"])

    if seeded_ids:
        db.commit()
        logger.info("Successfully seeded %d demonstration incidents: %s", len(seeded_ids), seeded_ids)
    else:
        logger.info("Demonstration incidents already exist; skipping seeding.")

    return seeded_ids
