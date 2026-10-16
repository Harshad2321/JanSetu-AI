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
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

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
    verification_result = Column(JSON, nullable=True)

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

        if "verification_result" in state and state["verification_result"]:
            self.verification_result = to_jsonable(state["verification_result"])

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


class ModelPredictionModel(Base):
    """Persisted model predictions from NLP, vision, and fusion stages."""
    __tablename__ = "model_predictions"

    prediction_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    task_type = Column(String(64), nullable=False)
    predicted_label = Column(String(128), nullable=False)
    scores = Column(JSON, default=dict, nullable=False)
    model_version = Column(String(128), nullable=True)
    available = Column(Boolean, default=True, nullable=False)
    fallback_provenance = Column(String(64), default="direct", nullable=False)
    is_synthetic = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("IncidentModel", back_populates="predictions")


class PlanModel(Base):
    """Persisted plan versions, including temporary relief and permanent repair variants."""
    __tablename__ = "response_plans"

    plan_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    plan_type = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(64), nullable=False, default="DRAFT")
    actions = Column(JSON, default=list, nullable=False)
    dependencies = Column(JSON, default=list, nullable=False)
    resource_requirements = Column(JSON, default=list, nullable=False)
    approval_requirements = Column(JSON, default=list, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    is_synthetic = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("IncidentModel", back_populates="plans")


class ExecutionAttemptModel(Base):
    """Persisted execution-record history for simulated intervention attempts."""
    __tablename__ = "execution_attempts"

    attempt_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    plan_id = Column(String(128), nullable=True)
    resource = Column(String(128), default="simulated_runtime", nullable=False)
    outcome = Column(String(64), nullable=False)
    failure_reason = Column(Text, nullable=True)
    evidence_reference = Column(String(512), nullable=True)
    simulated = Column(Boolean, default=True, nullable=False)
    attempted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("IncidentModel", back_populates="execution_attempts")


class VerificationResultModel(Base):
    """Persisted independent verification result tied to the incident being closed."""
    __tablename__ = "verification_results"

    verification_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    criteria = Column(JSON, default=list, nullable=False)
    evidence_reviewed = Column(JSON, default=list, nullable=False)
    result = Column(String(64), nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    rejection_reasons = Column(JSON, default=list, nullable=False)
    reviewer = Column(String(128), default="independent_verification_agent", nullable=False)
    reviewed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    correlation_id = Column(String(128), nullable=True)

    incident = relationship("IncidentModel", back_populates="verification_results")


class AuditEventModel(Base):
    """Persistent chronological audit timeline for each incident."""
    __tablename__ = "audit_events"

    event_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    timestamp = Column(String(64), nullable=False)
    agent = Column(String(128), nullable=False)
    action = Column(String(256), nullable=False)
    result = Column(Text, nullable=False)
    outcome = Column(String(64), nullable=True)
    event_type = Column(String(64), nullable=True)
    correlation_id = Column(String(128), nullable=True)

    incident = relationship("IncidentModel", back_populates="audit_events")


class HumanCorrectionModel(Base):
    """Persistent human corrections and review decisions for normalized fields."""
    __tablename__ = "human_corrections"

    correction_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    source_record = Column(String(128), nullable=False)
    corrected_field = Column(String(128), nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    reviewer = Column(String(128), default="human_operator", nullable=False)
    review_status = Column(String(32), default="PENDING", nullable=False)
    corrected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("IncidentModel", back_populates="human_corrections")


class DuplicateCandidateModel(Base):
    """Candidate duplicate records remain unconfirmed until human review."""
    __tablename__ = "duplicate_candidates"

    candidate_id = Column(String(128), primary_key=True, index=True)
    incident_id = Column(String(64), ForeignKey("incidents.incident_id"), nullable=False, index=True)
    other_incident_id = Column(String(64), nullable=False)
    distance_meters = Column(Float, nullable=True)
    similarity_score = Column(Float, nullable=True)
    rationale = Column(Text, nullable=True)
    review_status = Column(String(32), default="UNCONFIRMED", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("IncidentModel", back_populates="duplicate_candidates")


# Back-population wiring for IncidentModel relationships.
IncidentModel.predictions = relationship("ModelPredictionModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.plans = relationship("PlanModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.execution_attempts = relationship("ExecutionAttemptModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.verification_results = relationship("VerificationResultModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.audit_events = relationship("AuditEventModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.human_corrections = relationship("HumanCorrectionModel", back_populates="incident", cascade="all, delete-orphan")
IncidentModel.duplicate_candidates = relationship("DuplicateCandidateModel", back_populates="incident", cascade="all, delete-orphan")
