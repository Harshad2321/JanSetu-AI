"""
JanSetu AI — Incident Database Repository.

Encapsulates all database queries and aggregations:
- Incident creation and retrieval
- Filtering by operational and evidence statuses
- Dashboard summary metric aggregation
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas.incident import (
    DuplicateCandidateRecord,
    ExecutionAttempt,
    ModelPrediction,
    ResponsePlan,
    VerificationResult,
)

from app.db.models import (
    AuditEventModel,
    DuplicateCandidateModel,
    ExecutionAttemptModel,
    HumanCorrectionModel,
    IncidentModel,
    ModelPredictionModel,
    PlanModel,
    VerificationResultModel,
)


@contextmanager
def transaction_scope(db: Session) -> Generator[Session, None, None]:
    """Provide a transactional boundary around a series of database operations.

    Guarantees:
    - Automatically commits on clean exit.
    - Automatically rolls back on any exception and re-raises.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


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


# ============================================================================
# Response Plans (Version-Preserving)
# ============================================================================

def save_plan(db: Session, plan: PlanModel) -> PlanModel:
    """Persist a plan record, preserving version history."""
    existing = db.query(PlanModel).filter(PlanModel.plan_id == plan.plan_id).first()
    if existing:
        plan.plan_id = f"{plan.plan_id}-{uuid.uuid4().hex[:6]}"
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_plans_by_incident(db: Session, incident_id: str) -> List[PlanModel]:
    """Retrieve all historical and active plan versions for an incident."""
    return (
        db.query(PlanModel)
        .filter(PlanModel.incident_id == incident_id)
        .order_by(PlanModel.version.asc(), PlanModel.created_at.asc())
        .all()
    )


def get_latest_plan(
    db: Session,
    incident_id: str,
    plan_type: Optional[str] = None,
) -> Optional[PlanModel]:
    """Retrieve the latest plan version for an incident, optionally filtered by plan_type."""
    query = db.query(PlanModel).filter(PlanModel.incident_id == incident_id)
    if plan_type:
        query = query.filter(PlanModel.plan_type == plan_type)
    return query.order_by(PlanModel.version.desc(), PlanModel.created_at.desc()).first()


def persist_plan_record(
    db: Session,
    plan: Union[ResponsePlan, PlanModel, Dict[str, Any]],
) -> PlanModel:
    """Persist a response plan record, accepting either a Pydantic ResponsePlan, PlanModel, or dict."""
    if isinstance(plan, PlanModel):
        return save_plan(db, plan)

    if isinstance(plan, dict):
        try:
            plan = ResponsePlan(**plan)
        except Exception:
            pass

    if isinstance(plan, ResponsePlan):
        record = PlanModel(
            plan_id=plan.plan_id,
            incident_id=plan.incident_id,
            plan_type=plan.plan_type.value if hasattr(plan.plan_type, "value") else str(plan.plan_type),
            version=plan.version,
            status=plan.status.value if hasattr(plan.status, "value") else str(plan.status),
            actions=plan.actions,
            dependencies=plan.dependencies,
            resource_requirements=plan.resource_requirements or getattr(plan, "resources", None) or [],
            approval_requirements=plan.approval_requirements,
            estimated_cost=plan.estimated_cost or getattr(plan, "cost_estimate", None),
            estimated_duration_hours=plan.estimated_duration_hours or getattr(plan, "time_estimate", None),
            is_synthetic=plan.is_synthetic,
            created_at=plan.created_at,
        )
    elif isinstance(plan, dict):
        record = PlanModel(
            plan_id=plan.get("plan_id") or f"plan_{uuid.uuid4().hex[:8]}",
            incident_id=plan.get("incident_id") or "UNKNOWN",
            plan_type=str(plan.get("plan_type", "PERMANENT_RESOLUTION")),
            version=int(plan.get("version", 1)),
            status=str(plan.get("status", "PROPOSED")),
            actions=list(plan.get("actions") or plan.get("mitigation_steps") or []),
            dependencies=list(plan.get("dependencies") or []),
            resource_requirements=list(plan.get("resource_requirements") or plan.get("required_resources") or []),
            approval_requirements=list(plan.get("approval_requirements") or plan.get("assigned_roles") or []),
            estimated_cost=plan.get("estimated_cost") or plan.get("cost_estimate"),
            estimated_duration_hours=plan.get("estimated_duration_hours") or plan.get("time_estimate"),
            is_synthetic=bool(plan.get("is_synthetic", True)),
        )
    else:
        record = plan
    return save_plan(db, record)


# ============================================================================
# Execution Attempts (Preserving all attempts and failure history)
# ============================================================================

def save_execution_attempt(db: Session, attempt: ExecutionAttemptModel) -> ExecutionAttemptModel:
    """Persist an execution attempt record."""
    existing = db.query(ExecutionAttemptModel).filter(ExecutionAttemptModel.attempt_id == attempt.attempt_id).first()
    if existing:
        attempt.attempt_id = f"{attempt.attempt_id}-{uuid.uuid4().hex[:6]}"
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def persist_execution_attempt_record(
    db: Session,
    attempt: Union[ExecutionAttempt, ExecutionAttemptModel, Dict[str, Any]],
) -> ExecutionAttemptModel:
    """Persist an execution attempt record, accepting either Pydantic ExecutionAttempt, ORM model, or dict."""
    if isinstance(attempt, ExecutionAttemptModel):
        return save_execution_attempt(db, attempt)

    if isinstance(attempt, dict):
        try:
            attempt = ExecutionAttempt(**attempt)
        except Exception:
            pass

    if isinstance(attempt, ExecutionAttempt):
        record = ExecutionAttemptModel(
            attempt_id=attempt.attempt_id,
            incident_id=attempt.incident_id or "UNKNOWN",
            plan_id=attempt.plan_id,
            resource=attempt.resource,
            outcome=attempt.outcome,
            failure_reason=attempt.failure_reason,
            evidence_reference=attempt.evidence_reference or attempt.evidence_ref,
            simulated=attempt.simulated,
            attempted_at=attempt.attempted_at,
        )
    elif isinstance(attempt, dict):
        record = ExecutionAttemptModel(
            attempt_id=attempt.get("attempt_id") or f"att_{uuid.uuid4().hex[:8]}",
            incident_id=attempt.get("incident_id") or "UNKNOWN",
            plan_id=attempt.get("plan_id"),
            resource=attempt.get("resource", "simulated_crew"),
            outcome=attempt.get("outcome", "SUCCESS"),
            failure_reason=attempt.get("failure_reason"),
            evidence_reference=attempt.get("evidence_reference") or attempt.get("evidence_ref"),
            simulated=bool(attempt.get("simulated", True)),
        )
    else:
        record = attempt
    return save_execution_attempt(db, record)


def get_execution_attempts_by_incident(db: Session, incident_id: str) -> List[ExecutionAttemptModel]:
    """Retrieve all execution attempts for an incident in chronological order."""
    return (
        db.query(ExecutionAttemptModel)
        .filter(ExecutionAttemptModel.incident_id == incident_id)
        .order_by(ExecutionAttemptModel.attempted_at.asc())
        .all()
    )


# ============================================================================
# Model Predictions (Provenance & Availability tracking)
# ============================================================================

def save_prediction(db: Session, prediction: ModelPredictionModel) -> ModelPredictionModel:
    """Persist a model prediction record."""
    existing = db.query(ModelPredictionModel).filter(ModelPredictionModel.prediction_id == prediction.prediction_id).first()
    if existing:
        prediction.prediction_id = f"{prediction.prediction_id}-{uuid.uuid4().hex[:6]}"
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def persist_prediction_record(
    db: Session,
    prediction: Union[ModelPrediction, ModelPredictionModel, Dict[str, Any]],
) -> ModelPredictionModel:
    """
    Persist a model prediction record, accepting either a Pydantic ModelPrediction,
    ORM ModelPredictionModel, or dict.
    """
    if isinstance(prediction, dict):
        try:
            prediction = ModelPrediction(**prediction)
        except Exception:
            pass

    if isinstance(prediction, ModelPrediction):
        record = ModelPredictionModel(
            prediction_id=prediction.prediction_id,
            incident_id=prediction.incident_id,
            task_type=prediction.task_type,
            predicted_label=prediction.predicted_label,
            scores=prediction.scores,
            model_version=prediction.model_version,
            available=prediction.available,
            fallback_provenance=prediction.fallback_provenance,
            is_synthetic=prediction.is_synthetic,
            created_at=prediction.created_at,
        )
    else:
        record = prediction
    return save_prediction(db, record)


def get_predictions_by_incident(db: Session, incident_id: str) -> List[ModelPredictionModel]:
    """Retrieve all model predictions for an incident."""
    return (
        db.query(ModelPredictionModel)
        .filter(ModelPredictionModel.incident_id == incident_id)
        .order_by(ModelPredictionModel.created_at.asc())
        .all()
    )


# ============================================================================
# Independent Verification Results
# ============================================================================

def save_verification_result(db: Session, verification: VerificationResultModel) -> VerificationResultModel:
    """Persist an independent verification result."""
    existing = db.query(VerificationResultModel).filter(VerificationResultModel.verification_id == verification.verification_id).first()
    if existing:
        verification.verification_id = f"{verification.verification_id}-{uuid.uuid4().hex[:6]}"
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


def get_verification_results_by_incident(db: Session, incident_id: str) -> List[VerificationResultModel]:
    """Retrieve all verification results for an incident."""
    return (
        db.query(VerificationResultModel)
        .filter(VerificationResultModel.incident_id == incident_id)
        .order_by(VerificationResultModel.reviewed_at.asc())
        .all()
    )


def get_latest_verification_result(db: Session, incident_id: str) -> Optional[VerificationResultModel]:
    """Retrieve the most recent verification result for an incident."""
    return (
        db.query(VerificationResultModel)
        .filter(VerificationResultModel.incident_id == incident_id)
        .order_by(VerificationResultModel.reviewed_at.desc())
        .first()
    )


def persist_verification_record(
    db: Session,
    verification: Union[VerificationResult, VerificationResultModel, Dict[str, Any]],
) -> VerificationResultModel:
    """Persist an independent verification result, accepting either Pydantic VerificationResult, ORM model, or dict."""
    if isinstance(verification, dict):
        try:
            verification = VerificationResult(**verification)
        except Exception:
            pass

    if isinstance(verification, VerificationResult):
        record = VerificationResultModel(
            verification_id=verification.verification_id,
            incident_id=verification.incident_id,
            criteria=verification.criteria,
            evidence_reviewed=verification.evidence_reviewed,
            passed=verification.passed,
            result=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
            rejection_reasons=verification.rejection_reasons,
            reviewer=verification.reviewer,
            correlation_id=verification.correlation_id,
            reviewed_at=verification.reviewed_at,
        )
    else:
        record = verification
    return save_verification_result(db, record)


# ============================================================================
# Audit Timeline Events
# ============================================================================

def save_audit_event(db: Session, event: AuditEventModel) -> AuditEventModel:
    """Persist an immutable audit event."""
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_audit_events_by_incident(db: Session, incident_id: str) -> List[AuditEventModel]:
    """Retrieve all audit events for an incident in chronological order."""
    return (
        db.query(AuditEventModel)
        .filter(AuditEventModel.incident_id == incident_id)
        .order_by(AuditEventModel.timestamp.asc())
        .all()
    )


# ============================================================================
# Human Corrections & Reviews
# ============================================================================

def save_human_correction(db: Session, correction: HumanCorrectionModel) -> HumanCorrectionModel:
    """Persist a human correction record."""
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


def get_human_corrections_by_incident(db: Session, incident_id: str) -> List[HumanCorrectionModel]:
    """Retrieve all human corrections for an incident."""
    return (
        db.query(HumanCorrectionModel)
        .filter(HumanCorrectionModel.incident_id == incident_id)
        .order_by(HumanCorrectionModel.corrected_at.asc())
        .all()
    )


# ============================================================================
# Duplicate Candidates (Evidence-only, UNCONFIRMED, never auto-merge)
# ============================================================================

def save_duplicate_candidate(db: Session, candidate: DuplicateCandidateModel) -> DuplicateCandidateModel:
    """Persist an unconfirmed duplicate candidate record."""
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def get_duplicate_candidates_by_incident(db: Session, incident_id: str) -> List[DuplicateCandidateModel]:
    """Retrieve all duplicate candidates linked to an incident."""
    return (
        db.query(DuplicateCandidateModel)
        .filter(DuplicateCandidateModel.incident_id == incident_id)
        .order_by(DuplicateCandidateModel.created_at.asc())
        .all()
    )


# ============================================================================
# Operational Dashboard Summary
# ============================================================================

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


# ============================================================================
# Candidate Duplicates (Evidence-first review, no auto-merge)
# ============================================================================

def save_duplicate_candidate(
    db: Session,
    candidate: Union[DuplicateCandidateRecord, DuplicateCandidateModel],
) -> DuplicateCandidateModel:
    """Persist a candidate duplicate record (initially UNCONFIRMED)."""
    if isinstance(candidate, DuplicateCandidateRecord):
        record = DuplicateCandidateModel(
            candidate_id=candidate.candidate_id,
            incident_id=candidate.incident_id,
            other_incident_id=candidate.other_incident_id,
            distance_meters=candidate.distance_meters,
            similarity_score=candidate.text_similarity,
            rationale=candidate.rationale,
            review_status=candidate.review_status,
        )
    else:
        record = candidate
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_duplicate_candidates_by_incident(
    db: Session,
    incident_id: str,
) -> List[DuplicateCandidateModel]:
    """Retrieve all duplicate candidates for an incident."""
    return (
        db.query(DuplicateCandidateModel)
        .filter(DuplicateCandidateModel.incident_id == incident_id)
        .order_by(DuplicateCandidateModel.created_at.asc())
        .all()
    )
