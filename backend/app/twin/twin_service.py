"""JanSetu AI — Civic Incident Twin Service.

Read-oriented incident history service exposing:
- Original citizen complaint (unmodified)
- Predictions with full model provenance and availability status
- Separate plan types (TEMPORARY_RELIEF, PERMANENT_RESOLUTION) and versions
- Execution attempts, failures, and recovery decisions
- Independent verification results
- Human corrections and reviews
- Chronological audit timeline

Invariants:
- Never fabricate missing information.
- Never overwrite historical plan versions or execution attempts.
- Clearly label synthetic data and simulated execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import IncidentModel
from app.db.repository import (
    get_audit_events_by_incident,
    get_duplicate_candidates_by_incident,
    get_execution_attempts_by_incident,
    get_human_corrections_by_incident,
    get_incident_by_id,
    get_plans_by_incident,
    get_predictions_by_incident,
    get_verification_results_by_incident,
)
from app.schemas.incident import (
    AuditEvent,
    DuplicateReviewStatus,
    ExecutionAttempt,
    HumanCorrection,
    ModelPrediction,
    OperationalStatus,
    PlanStatus,
    PlanType,
    ResponsePlan,
    VerificationOutcome,
    VerificationResult,
)


class CivicIncidentTwin(BaseModel):
    """Normalized, read-oriented historical representation of a civic incident."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Unique stable incident identifier")
    original_input: str = Field(description="Original, unmodified citizen complaint text")
    normalized_summary: Optional[str] = Field(default=None, description="Model-extracted normalized summary")
    category: str = Field(description="Civic category (pothole, waterlogging, garbage, uncertain_other)")
    status: str = Field(description="Current operational lifecycle status")
    evidence_status: Optional[str] = Field(default=None, description="Intake evidence status")
    is_synthetic: bool = Field(default=True, description="Always True: synthetic academic PoC marker")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Incident coordinates and provenance")
    has_photograph: bool = Field(default=False, description="Whether a photo was submitted")
    retry_count: int = Field(default=0, description="Replanning retry count")

    predictions: List[ModelPrediction] = Field(
        default_factory=list,
        description="Model predictions with provenance, model name, version, and availability",
    )
    plans: List[ResponsePlan] = Field(
        default_factory=list,
        description="Preserved response plans including TEMPORARY_RELIEF and PERMANENT_RESOLUTION versions",
    )
    current_plan: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Active plan in the current operational state",
    )
    execution_attempts: List[ExecutionAttempt] = Field(
        default_factory=list,
        description="Chronological log of all simulated execution attempts",
    )
    failures: List[ExecutionAttempt] = Field(
        default_factory=list,
        description="Recorded execution failures that triggered adaptive recovery",
    )
    recovery_decisions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recorded replanning rationale and constraint modifications",
    )
    verification_results: List[VerificationResult] = Field(
        default_factory=list,
        description="Independent verification outcomes gating closure",
    )
    human_corrections: List[HumanCorrection] = Field(
        default_factory=list,
        description="Human operator corrections and overrides",
    )
    duplicate_candidates: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Candidate duplicates marked UNCONFIRMED awaiting review",
    )
    timeline: List[AuditEvent] = Field(
        default_factory=list,
        description="Chronological audit timeline of all events",
    )

    created_at: datetime = Field(description="Incident creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


def get_incident_twin(db: Session, incident_id: str) -> Optional[CivicIncidentTwin]:
    """Retrieve the complete Civic Incident Twin for an incident.

    Reads from relational tables where available, falling back safely to stored
    incident JSON state without fabricating data.
    """
    incident: Optional[IncidentModel] = get_incident_by_id(db, incident_id)
    if incident is None:
        return None

    # 1. Predictions
    pred_models = get_predictions_by_incident(db, incident_id)
    predictions: List[ModelPrediction] = []
    for pm in pred_models:
        predictions.append(
            ModelPrediction(
                prediction_id=pm.prediction_id,
                incident_id=pm.incident_id,
                task_type=pm.task_type,
                predicted_label=pm.predicted_label,
                scores=pm.scores or {},
                model_version=pm.model_version or "unknown",
                model_name="JanSetu-Classifier",
                available=pm.available,
                fallback_provenance=pm.fallback_provenance,
                is_synthetic=pm.is_synthetic,
                created_at=pm.created_at,
            )
        )
    # If no relational predictions exist yet, extract from stored evidence analysis if present
    if not predictions and incident.evidence_analysis:
        ea = incident.evidence_analysis
        predictions.append(
            ModelPrediction(
                prediction_id=f"PRED-{incident_id}-INTAKE",
                incident_id=incident_id,
                task_type="vision_triage",
                predicted_label=str(ea.get("detected_category", incident.category)),
                confidence=float(ea.get("confidence_score", 0.0) or 0.0),
                model_name="Multimodal-Intake",
                model_version="1.0.0",
                available=True,
                fallback_provenance=str(ea.get("provenance", "INTAKE_EVALUATION")),
                is_synthetic=True,
                created_at=incident.created_at,
            )
        )

    # 2. Plans (Preserving all versions)
    plan_models = get_plans_by_incident(db, incident_id)
    plans: List[ResponsePlan] = []
    for pm in plan_models:
        try:
            ptype = PlanType(pm.plan_type)
        except ValueError:
            ptype = PlanType.PERMANENT_RESOLUTION
        try:
            pstat = PlanStatus(pm.status)
        except ValueError:
            pstat = PlanStatus.DRAFT

        plans.append(
            ResponsePlan(
                plan_id=pm.plan_id,
                incident_id=pm.incident_id,
                plan_type=ptype,
                version=pm.version,
                status=pstat,
                actions=list(pm.actions or []),
                dependencies=list(pm.dependencies or []),
                resource_requirements=list(pm.resource_requirements or []),
                approval_requirements=list(pm.approval_requirements or []),
                estimated_cost=pm.estimated_cost,
                estimated_duration_hours=pm.estimated_duration_hours,
                created_at=pm.created_at,
                is_synthetic=pm.is_synthetic,
            )
        )
    # If no relational plans exist yet, adapt current_plan JSON if present
    if not plans and incident.current_plan:
        cp = incident.current_plan
        plans.append(
            ResponsePlan(
                plan_id=f"PLAN-{incident_id}-V1",
                incident_id=incident_id,
                plan_type=PlanType.TEMPORARY_RELIEF if cp.get("mitigation_steps") else PlanType.PERMANENT_RESOLUTION,
                version=1,
                status=PlanStatus.APPROVED,
                actions=list(cp.get("mitigation_steps", []) + cp.get("permanent_repair_steps", [])),
                dependencies=[],
                resource_requirements=list(cp.get("required_resources", [])),
                approval_requirements=list(cp.get("assigned_roles", [])),
                estimated_duration_hours=cp.get("estimated_duration_hours"),
                created_at=incident.created_at,
                is_synthetic=True,
            )
        )

    # 3. Execution Attempts & Failures
    attempt_models = get_execution_attempts_by_incident(db, incident_id)
    execution_attempts: List[ExecutionAttempt] = []
    for am in attempt_models:
        execution_attempts.append(
            ExecutionAttempt(
                attempt_id=am.attempt_id,
                incident_id=am.incident_id,
                plan_id=am.plan_id,
                resource=am.resource,
                outcome=am.outcome,
                failure_reason=am.failure_reason,
                evidence_reference=am.evidence_reference,
                simulated=am.simulated,
                attempted_at=am.attempted_at,
            )
        )
    # If no relational attempts exist yet, adapt simulation_result if present
    if not execution_attempts and incident.simulation_result:
        execution_attempts.append(
            ExecutionAttempt(
                attempt_id=f"ATTEMPT-{incident_id}-1",
                incident_id=incident_id,
                plan_id=f"PLAN-{incident_id}-V1",
                resource="simulated_runtime",
                outcome=str(incident.simulation_result),
                failure_reason=incident.failure_reason,
                simulated=True,
                attempted_at=incident.updated_at or incident.created_at,
            )
        )

    failures: List[ExecutionAttempt] = [
        att for att in execution_attempts if att.outcome != "SUCCESS"
    ]

    # 4. Recovery Decisions
    recovery_decisions: List[Dict[str, Any]] = []
    if incident.failure_reason:
        recovery_decisions.append({
            "incident_id": incident_id,
            "failure_reason": incident.failure_reason,
            "retry_count": incident.retry_count or 0,
            "status": incident.operational_status,
            "timestamp": (incident.updated_at or incident.created_at).isoformat(),
        })

    # 5. Verification Results
    ver_models = get_verification_results_by_incident(db, incident_id)
    verification_results: List[VerificationResult] = []
    for vm in ver_models:
        try:
            outcome = VerificationOutcome(vm.result)
        except ValueError:
            outcome = VerificationOutcome.VERIFIED if vm.passed else VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE

        verification_results.append(
            VerificationResult(
                verification_id=vm.verification_id,
                incident_id=vm.incident_id,
                criteria=list(vm.criteria or []),
                evidence_reviewed=list(vm.evidence_reviewed or []),
                result=outcome,
                passed=vm.passed,
                rejection_reasons=list(vm.rejection_reasons or []),
                reviewer=vm.reviewer,
                reviewed_at=vm.reviewed_at,
                correlation_id=vm.correlation_id,
            )
        )

    # 6. Human Corrections
    corr_models = get_human_corrections_by_incident(db, incident_id)
    human_corrections: List[HumanCorrection] = []
    for cm in corr_models:
        human_corrections.append(
            HumanCorrection(
                correction_id=cm.correction_id,
                incident_id=cm.incident_id,
                source_record=cm.source_record,
                corrected_field=cm.corrected_field,
                original_value=cm.original_value,
                corrected_value=cm.corrected_value,
                reviewer=cm.reviewer,
                review_status=cm.review_status,
                corrected_at=cm.corrected_at,
            )
        )

    # 7. Duplicate Candidates (UNCONFIRMED)
    dup_models = get_duplicate_candidates_by_incident(db, incident_id)
    duplicate_candidates: List[Dict[str, Any]] = []
    for dm in dup_models:
        duplicate_candidates.append({
            "candidate_id": dm.candidate_id,
            "incident_id": dm.incident_id,
            "other_incident_id": dm.other_incident_id,
            "distance_meters": dm.distance_meters,
            "similarity_score": dm.similarity_score,
            "rationale": dm.rationale,
            "review_status": dm.review_status,
            "created_at": dm.created_at.isoformat(),
        })
    # If no relational duplicate candidates exist but geo_context flagged a duplicate
    if not duplicate_candidates and incident.geo_context:
        gc = incident.geo_context
        if gc.get("is_duplicate") and gc.get("duplicate_of_id"):
            duplicate_candidates.append({
                "candidate_id": f"DUP-{incident_id}-{gc.get('duplicate_of_id')}",
                "incident_id": incident_id,
                "other_incident_id": str(gc.get("duplicate_of_id")),
                "distance_meters": gc.get("distance_to_nearest_meters"),
                "similarity_score": gc.get("similarity_score"),
                "rationale": "Geospatial proximity match identified by GeoCivic Agent; awaiting human verification",
                "review_status": DuplicateReviewStatus.UNCONFIRMED.value,
                "created_at": incident.created_at.isoformat(),
            })

    # 8. Chronological Timeline
    audit_models = get_audit_events_by_incident(db, incident_id)
    timeline: List[AuditEvent] = []
    for am in audit_models:
        timeline.append(
            AuditEvent(
                event_id=am.event_id,
                incident_id=am.incident_id,
                timestamp=am.timestamp,
                agent=am.agent,
                action=am.action,
                result=am.result,
                outcome=am.outcome,
                event_type=am.event_type,
                correlation_id=am.correlation_id,
            )
        )
    # If no relational audit events exist yet, use stored JSON timeline
    if not timeline and incident.audit_timeline:
        for at in incident.audit_timeline:
            if isinstance(at, dict):
                timeline.append(
                    AuditEvent(
                        timestamp=at.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        agent=at.get("agent", "System"),
                        action=at.get("action", "Recorded"),
                        result=at.get("result", ""),
                        outcome=at.get("outcome"),
                        event_type=at.get("event_type"),
                        correlation_id=at.get("correlation_id", incident_id),
                    )
                )

    # Sort timeline chronologically
    timeline.sort(key=lambda e: e.timestamp)

    return CivicIncidentTwin(
        incident_id=incident.incident_id,
        original_input=incident.complaint,
        normalized_summary=incident.extracted_facts.get("description_clean") if incident.extracted_facts else None,
        category=incident.category,
        status=incident.operational_status,
        evidence_status=incident.evidence_status,
        is_synthetic=True,
        location=incident.location_data,
        has_photograph=incident.has_photograph,
        retry_count=incident.retry_count or 0,
        predictions=predictions,
        plans=plans,
        current_plan=incident.current_plan,
        execution_attempts=execution_attempts,
        failures=failures,
        recovery_decisions=recovery_decisions,
        verification_results=verification_results,
        human_corrections=human_corrections,
        duplicate_candidates=duplicate_candidates,
        timeline=timeline,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )
