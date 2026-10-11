"""
JanSetu AI — SQLAlchemy Incident Persistence Model.

Stores:
- Core citizen complaints and validated location data
- Decoupled operational status and evidence verification status
- Structured JSON outputs for extracted facts, evidence analysis, geo context,
  priority assessments, resolution plans, Critic decisions, and closure evidence
- Detailed agent traces and immutable audit event history
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

from app.db.session import Base
from app.schemas.api import IncidentResponse
from app.schemas.incident import (
    AgentExecutionTrace,
    AuditEvent,
    ClosureEvidence,
    EvidenceOutcome,
    GeoAnalysis,
    IncidentCategory,
    IncidentExtraction,
    IncidentLocation,
    OperationalStatus,
    PhotoEvidenceAnalysis,
    PriorityAssessment,
    ResolutionPlan,
    ValidationDecision,
)


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


def to_jsonable(obj: Any) -> Any:
    """Recursively convert Pydantic models, datetimes, and enums to JSON-safe primitives."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):
        return obj.value
    return obj


class IncidentModel(Base):
    """Database model for persisting municipal civic incidents and their workflow state."""
    __tablename__ = "incidents"

    incident_id = Column(String(64), primary_key=True, index=True)
    complaint = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, default="uncertain_other", index=True)
    location_data = Column(JSON, nullable=True)
    has_photograph = Column(Boolean, default=False, nullable=False)
    photo_storage_path = Column(String(512), nullable=True)
    photo_mime_type = Column(String(64), nullable=True)

    # Strictly decoupled statuses
    operational_status = Column(
        String(64),
        nullable=False,
        default=OperationalStatus.NEW.value,
        index=True,
    )
    evidence_status = Column(
        String(64),
        nullable=False,
        default=EvidenceOutcome.NOT_PROVIDED.value,
        index=True,
    )

    # Specialist Agent Outputs (JSON columns)
    extracted_facts = Column(JSON, nullable=True)
    evidence_analysis = Column(JSON, nullable=True)
    geo_context = Column(JSON, nullable=True)
    priority = Column(JSON, nullable=True)
    current_plan = Column(JSON, nullable=True)
    validation = Column(JSON, nullable=True)
    closure_evidence = Column(JSON, nullable=True)

    # Simulation and recovery telemetry
    simulation_result = Column(String(64), nullable=True)
    failure_reason = Column(String(512), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    agent_traces = Column(JSON, default=list, nullable=False)
    audit_timeline = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    def to_pydantic_location(self) -> IncidentLocation:
        """Hydrate IncidentLocation model safely from stored JSON."""
        if not self.location_data:
            return IncidentLocation()
        return IncidentLocation(**self.location_data)

    def to_response(self) -> IncidentResponse:
        """Convert database record to typed API IncidentResponse."""
        return IncidentResponse(
            incident_id=self.incident_id,
            complaint=self.complaint,
            category=IncidentCategory(self.category),
            location=self.to_pydantic_location(),
            has_photograph=bool(self.has_photograph),
            operational_status=OperationalStatus(self.operational_status),
            evidence_status=EvidenceOutcome(self.evidence_status),
            extracted_facts=(
                IncidentExtraction(**self.extracted_facts)
                if self.extracted_facts
                else None
            ),
            evidence_analysis=(
                PhotoEvidenceAnalysis(**self.evidence_analysis)
                if self.evidence_analysis
                else None
            ),
            geo_context=(
                GeoAnalysis(**self.geo_context)
                if self.geo_context
                else None
            ),
            priority=(
                PriorityAssessment(**self.priority)
                if self.priority
                else None
            ),
            current_plan=(
                ResolutionPlan(**self.current_plan)
                if self.current_plan
                else None
            ),
            validation=(
                ValidationDecision(**self.validation)
                if self.validation
                else None
            ),
            closure_evidence=(
                ClosureEvidence(**self.closure_evidence)
                if self.closure_evidence
                else None
            ),
            simulation_result=self.simulation_result,
            failure_reason=self.failure_reason,
            retry_count=self.retry_count or 0,
            agent_traces=[
                AgentExecutionTrace(**t) for t in (self.agent_traces or [])
            ],
            audit_timeline=[
                AuditEvent(**a) for a in (self.audit_timeline or [])
            ],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update_from_state(self, state: Dict[str, Any]) -> None:
        """Safely synchronize LangGraph execution state back to the database record."""
        if "status" in state and state["status"]:
            status_val = state["status"]
            self.operational_status = (
                status_val.value if hasattr(status_val, "value") else str(status_val)
            )

        if "evidence_status" in state and state["evidence_status"]:
            ev_val = state["evidence_status"]
            self.evidence_status = (
                ev_val.value if hasattr(ev_val, "value") else str(ev_val)
            )

        if "extracted_facts" in state and state["extracted_facts"]:
            self.extracted_facts = to_jsonable(state["extracted_facts"])

        if "evidence_analysis" in state and state["evidence_analysis"]:
            self.evidence_analysis = to_jsonable(state["evidence_analysis"])

        if "geo_context" in state and state["geo_context"]:
            self.geo_context = to_jsonable(state["geo_context"])

        if "priority" in state and state["priority"]:
            self.priority = to_jsonable(state["priority"])

        if "current_plan" in state and state["current_plan"]:
            self.current_plan = to_jsonable(state["current_plan"])

        if "validation" in state and state["validation"]:
            self.validation = to_jsonable(state["validation"])

        if "closure_evidence" in state and state["closure_evidence"]:
            self.closure_evidence = to_jsonable(state["closure_evidence"])

        if "simulation_result" in state:
            self.simulation_result = state.get("simulation_result")


        if "failure_reason" in state:
            self.failure_reason = state.get("failure_reason")

        if "retry_count" in state:
            self.retry_count = state.get("retry_count", 0)

        if "audit_timeline" in state and state["audit_timeline"]:
            existing_events = self.audit_timeline or []
            new_events = [to_jsonable(e) for e in state["audit_timeline"]]
            seen = {(e.get("timestamp"), e.get("action")) for e in existing_events if isinstance(e, dict)}
            combined = list(existing_events)
            for event in new_events:
                if isinstance(event, dict):
                    key = (event.get("timestamp"), event.get("action"))
                    if key not in seen:
                        combined.append(event)
                        seen.add(key)
                else:
                    combined.append(event)
            self.audit_timeline = combined

        self.updated_at = utc_now()
