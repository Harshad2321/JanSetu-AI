"""JanSetu AI — Phase 3 Foundation Tests.

Validates:
1. Pydantic v2 schemas and invariants for all core records.
2. State machine allowed transitions and rejection of invalid transitions.
3. Deterministic closure gate: VERIFIED_CLOSED requires a passing VerificationResult.
4. Independent Verification Agent distinct from Critic.
5. SQLite persistence across sessions (simulated restart).
6. Plan version preservation (failed and previous plans remain in history).
7. Execution attempt preservation (failures preserved; simulated=True enforced).
8. Database transaction rollback on multi-record failure.
9. Duplicate candidates marked UNCONFIRMED without auto-merging or deleting.
10. Civic Incident Twin read-oriented history service.
"""

from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.critic import critic_node
from app.agents.verification import verify_incident, verification_node
from app.db.models import (
    Base,
    DuplicateCandidateModel,
    ExecutionAttemptModel,
    IncidentModel,
    ModelPredictionModel,
    PlanModel,
    VerificationResultModel,
)
from app.db.repository import (
    create_incident,
    get_execution_attempts_by_incident,
    get_incident_by_id,
    get_plans_by_incident,
    get_predictions_by_incident,
    get_verification_results_by_incident,
    save_duplicate_candidate,
    save_execution_attempt,
    save_plan,
    save_prediction,
    save_verification_result,
    transaction_scope,
)
from app.graph.state_machine import (
    TransitionError,
    is_allowed_transition,
    transition_status,
    validate_transition,
)
from app.schemas.incident import (
    AuditEvent,
    ClosureEvidence,
    DuplicateReviewStatus,
    EvidenceOutcome,
    ExecutionAttempt,
    HumanCorrection,
    Incident,
    IncidentCategory,
    IncidentLocation,
    ModelPrediction,
    OperationalStatus,
    PlanStatus,
    PlanType,
    ResolutionPlan,
    ResponsePlan,
    VerificationOutcome,
    VerificationResult,
)
from app.twin import get_incident_twin


@pytest.fixture
def memory_db():
    """Create an isolated, in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ============================================================================
# 1. State Machine & Transition Tests
# ============================================================================

def test_invalid_state_transitions_rejected():
    """Invalid state transitions must raise TransitionError."""
    # Cannot jump from SUBMITTED directly to VERIFIED_CLOSED
    with pytest.raises(TransitionError, match="Invalid state transition"):
        validate_transition(OperationalStatus.SUBMITTED, OperationalStatus.VERIFIED_CLOSED)

    # Cannot jump from PLANNING directly to VERIFIED_CLOSED
    with pytest.raises(TransitionError, match="Invalid state transition"):
        validate_transition(OperationalStatus.PLANNING, OperationalStatus.VERIFIED_CLOSED)

    # Cannot jump from CLASSIFIED directly to IN_PROGRESS_SIMULATED
    with pytest.raises(TransitionError, match="Invalid state transition"):
        validate_transition(OperationalStatus.CLASSIFIED, OperationalStatus.IN_PROGRESS_SIMULATED)

    # Terminal states reject transitions
    with pytest.raises(TransitionError, match="Invalid state transition"):
        validate_transition(OperationalStatus.VERIFIED_CLOSED, OperationalStatus.PLANNING)

    with pytest.raises(TransitionError, match="Invalid state transition"):
        validate_transition(OperationalStatus.HUMAN_REVIEW, OperationalStatus.PLANNING)


def test_allowed_tracker_transitions():
    """Verify core transitions from Tracker Section 4."""
    assert is_allowed_transition(OperationalStatus.SUBMITTED, OperationalStatus.CLASSIFIED)
    assert is_allowed_transition(OperationalStatus.SUBMITTED, OperationalStatus.NEEDS_CLARIFICATION)
    assert is_allowed_transition(OperationalStatus.NEEDS_CLARIFICATION, OperationalStatus.HUMAN_REVIEW)
    assert is_allowed_transition(OperationalStatus.CLASSIFIED, OperationalStatus.TRIAGED)
    assert is_allowed_transition(OperationalStatus.TRIAGED, OperationalStatus.PLANNING)
    assert is_allowed_transition(OperationalStatus.TRIAGED, OperationalStatus.HUMAN_REVIEW)
    assert is_allowed_transition(OperationalStatus.IN_PROGRESS_SIMULATED, OperationalStatus.AWAITING_VERIFICATION)
    assert is_allowed_transition(OperationalStatus.IN_PROGRESS_SIMULATED, OperationalStatus.PLAN_FAILED)
    assert is_allowed_transition(OperationalStatus.PLAN_FAILED, OperationalStatus.REPLANNING)
    assert is_allowed_transition(OperationalStatus.REPLANNING, OperationalStatus.PLANNING)
    assert is_allowed_transition(OperationalStatus.REOPENED, OperationalStatus.TRIAGED)


# ============================================================================
# 2. Deterministic Closure Gate & Verification Invariant Tests
# ============================================================================

def test_closure_without_verification_rejected():
    """Attempting to transition to VERIFIED_CLOSED without a VerificationResult is blocked."""
    with pytest.raises(TransitionError, match="VERIFIED_CLOSED requires a passing VerificationResult"):
        validate_transition(
            OperationalStatus.AWAITING_VERIFICATION,
            OperationalStatus.VERIFIED_CLOSED,
            verification_result=None,
        )


def test_closure_with_failed_verification_rejected():
    """Attempting to transition to VERIFIED_CLOSED with passed=False is blocked."""
    failed_verification = VerificationResult(
        verification_id="VER-TEST-FAIL",
        incident_id="INC-TEST-001",
        criteria=["Post-repair photo archived"],
        evidence_reviewed=[],
        result=VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE,
        passed=False,
        rejection_reasons=["No verification photo uploaded."],
        reviewer="independent_verification_agent",
    )

    with pytest.raises(TransitionError, match="VERIFIED_CLOSED requires a passing VerificationResult"):
        validate_transition(
            OperationalStatus.AWAITING_VERIFICATION,
            OperationalStatus.VERIFIED_CLOSED,
            verification_result=failed_verification,
            incident_id="INC-TEST-001",
        )


def test_closure_with_mismatched_incident_id_rejected():
    """VerificationResult must match the incident being closed."""
    passing_verification = VerificationResult(
        verification_id="VER-TEST-PASS",
        incident_id="INC-DIFFERENT-999",
        criteria=["Fill flush"],
        evidence_reviewed=["Fill flush"],
        result=VerificationOutcome.VERIFIED,
        passed=True,
    )

    with pytest.raises(TransitionError, match="incident_id does not match"):
        validate_transition(
            OperationalStatus.AWAITING_VERIFICATION,
            OperationalStatus.VERIFIED_CLOSED,
            verification_result=passing_verification,
            incident_id="INC-TEST-001",
        )


def test_closure_with_valid_verification_succeeds():
    """Transition to VERIFIED_CLOSED succeeds only when passing VerificationResult matches."""
    passing_verification = VerificationResult(
        verification_id="VER-TEST-PASS",
        incident_id="INC-TEST-001",
        criteria=["Pothole filled flush with road grade", "Post-repair photo archived"],
        evidence_reviewed=["Pothole filled flush with road grade", "Post-repair photo archived"],
        result=VerificationOutcome.VERIFIED,
        passed=True,
        rejection_reasons=[],
    )

    next_state = transition_status(
        OperationalStatus.AWAITING_VERIFICATION,
        OperationalStatus.VERIFIED_CLOSED,
        verification_result=passing_verification,
        incident_id="INC-TEST-001",
    )
    assert next_state == OperationalStatus.VERIFIED_CLOSED.value


def test_simulated_resolution_does_not_silently_convert_to_verified_closed():
    """SIMULATED_RESOLVED is a simulation marker, not a real verified closure."""
    # SIMULATED_RESOLVED is allowed only after closure verification gate
    with pytest.raises(TransitionError, match="Invalid state transition from SUBMITTED to SIMULATED_RESOLVED"):
        validate_transition(OperationalStatus.SUBMITTED, OperationalStatus.SIMULATED_RESOLVED)

    # Validating transition to SIMULATED_RESOLVED produces SIMULATED_RESOLVED, never VERIFIED_CLOSED
    res = validate_transition(OperationalStatus.AWAITING_VERIFICATION, OperationalStatus.SIMULATED_RESOLVED)
    assert res == OperationalStatus.SIMULATED_RESOLVED.value
    assert res != OperationalStatus.VERIFIED_CLOSED.value


# ============================================================================
# 3. Independent Verification Agent Distinct from Critic
# ============================================================================

def test_critic_evaluates_plan_before_execution():
    """Critic evaluates plan feasibility before execution, setting bounded retries."""
    state_valid_plan = {
        "current_plan": ResolutionPlan(
            mitigation_steps=["Deploy warning barriers"],
            permanent_repair_steps=["Fill pothole flush with asphalt"],
            required_resources=["1x Road Crew"],
            assigned_roles=["Public Works"],
            closure_criteria=["Pothole filled flush", "Photo archived"],
            estimated_duration_hours=4.0,
        ),
        "retry_count": 0,
    }
    critic_output = critic_node(state_valid_plan)
    assert critic_output["validation"].status == "APPROVE"
    assert critic_output["status"] == OperationalStatus.SIMULATING.value

    # Critic rejects prohibited methods
    state_bad_plan = {
        "current_plan": ResolutionPlan(
            mitigation_steps=["Use prohibited toxic solvent"],
            permanent_repair_steps=["Restoration"],
            required_resources=["1x Road Crew"],
            closure_criteria=["Inspection"],
        ),
        "retry_count": 0,
    }
    critic_reject = critic_node(state_bad_plan)
    assert critic_reject["validation"].status == "REJECT"
    assert critic_reject["status"] == OperationalStatus.PLANNING.value


def test_independent_verification_agent_evaluates_after_execution():
    """Independent verifier checks execution outcome and evidence, not plan feasibility."""
    plan = ResponsePlan(
        plan_id="PLAN-001",
        incident_id="INC-101",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        actions=["Fill void", "Compact surface"],
        dependencies=[],
        resource_requirements=["Hot-mix asphalt"],
        approval_requirements=[],
    )

    # 1. Missing evidence -> REJECTED_INSUFFICIENT_EVIDENCE
    result_missing = verify_incident(
        incident_id="INC-101",
        plan=plan,
        evidence=None,
        execution_outcome="SUCCESS",
    )
    assert not result_missing.passed
    assert result_missing.result == VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE

    # 2. Execution failed -> REJECTED_INCOMPLETE_ACTION
    result_exec_failed = verify_incident(
        incident_id="INC-101",
        plan=plan,
        evidence=None,
        execution_outcome="FAILURE",
    )
    assert not result_exec_failed.passed
    assert result_exec_failed.result == VerificationOutcome.REJECTED_INCOMPLETE_ACTION

    # 3. Complete evidence with met criteria -> VERIFIED
    evidence_good = ClosureEvidence(
        incident_id="INC-101",
        closure_criteria_met=["Pothole filled flush with adjacent road grade", "Post-repair photo archived"],
        outstanding_criteria=[],
        is_ready_for_closure=True,
    )
    result_passed = verify_incident(
        incident_id="INC-101",
        plan=ResponsePlan(
            plan_id="PLAN-001",
            incident_id="INC-101",
            plan_type=PlanType.PERMANENT_RESOLUTION,
            actions=["Fill void"],
            dependencies=[],
            approval_requirements=[],
        ),
        evidence=evidence_good,
        execution_outcome="SUCCESS",
    )
    assert result_passed.passed
    assert result_passed.result == VerificationOutcome.VERIFIED


# ============================================================================
# 4. Persistence & Process Restart Invariant Tests
# ============================================================================

def test_incident_persists_across_sessions(tmp_path):
    """Incident data must survive database re-opening (simulating process restart)."""
    db_file = tmp_path / "test_jansetu.db"
    db_url = f"sqlite:///{db_file}"

    # Session 1: Create and persist incident
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    db1 = Session1()

    inc = IncidentModel(
        incident_id="INC-RESTART-01",
        complaint="Deep pothole outside Metro Station Pillar 12",
        category="pothole",
        location_data={"latitude": 28.6139, "longitude": 77.2090, "source": "DEVICE_GPS"},
        has_photograph=True,
        operational_status=OperationalStatus.CLASSIFIED.value,
        evidence_status=EvidenceOutcome.MATCHED.value,
    )
    create_incident(db1, inc)
    db1.close()
    engine1.dispose()

    # Session 2: Connect again with a fresh engine and session
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    # Non-destructive create_all
    Base.metadata.create_all(bind=engine2)
    Session2 = sessionmaker(bind=engine2)
    db2 = Session2()

    loaded = get_incident_by_id(db2, "INC-RESTART-01")
    assert loaded is not None
    assert loaded.incident_id == "INC-RESTART-01"
    assert loaded.complaint == "Deep pothole outside Metro Station Pillar 12"
    assert loaded.category == "pothole"
    assert loaded.location_data["latitude"] == 28.6139
    assert loaded.operational_status == OperationalStatus.CLASSIFIED.value
    db2.close()
    engine2.dispose()


# ============================================================================
# 5. Plan History & Execution Attempt Preservation Tests
# ============================================================================

def test_plan_history_preservation(memory_db):
    """When a plan is reworked, previous plan versions remain in database history."""
    incident_id = "INC-PLAN-HIST-01"
    inc = IncidentModel(
        incident_id=incident_id,
        complaint="Waterlogging in underpass",
        category="waterlogging",
    )
    create_incident(memory_db, inc)

    # Version 1: Temporary relief
    plan_v1 = PlanModel(
        plan_id=f"PLAN-{incident_id}-V1",
        incident_id=incident_id,
        plan_type=PlanType.TEMPORARY_RELIEF.value,
        version=1,
        status=PlanStatus.FAILED.value,
        actions=["Deploy portable suction pump"],
        dependencies=[],
        resource_requirements=["1x Portable Pump"],
        approval_requirements=[],
        estimated_duration_hours=2.0,
    )
    save_plan(memory_db, plan_v1)

    # Version 2: Permanent resolution
    plan_v2 = PlanModel(
        plan_id=f"PLAN-{incident_id}-V2",
        incident_id=incident_id,
        plan_type=PlanType.PERMANENT_RESOLUTION.value,
        version=2,
        status=PlanStatus.APPROVED.value,
        actions=["Excavate drainage culvert and install high-capacity pump"],
        dependencies=["Municipal water division approval"],
        resource_requirements=["High-capacity drainage pump", "Excavator team"],
        approval_requirements=["Chief Engineer Sign-off"],
        estimated_duration_hours=24.0,
    )
    save_plan(memory_db, plan_v2)

    # Query all plans: both versions must be preserved!
    all_plans = get_plans_by_incident(memory_db, incident_id)
    assert len(all_plans) == 2
    assert all_plans[0].version == 1
    assert all_plans[0].plan_type == PlanType.TEMPORARY_RELIEF.value
    assert all_plans[0].status == PlanStatus.FAILED.value
    assert all_plans[1].version == 2
    assert all_plans[1].plan_type == PlanType.PERMANENT_RESOLUTION.value
    assert all_plans[1].status == PlanStatus.APPROVED.value


def test_execution_attempt_history_preservation(memory_db):
    """Every execution attempt (failure or success) is logged and requires simulated=True."""
    incident_id = "INC-ATTEMPT-HIST-01"
    inc = IncidentModel(incident_id=incident_id, complaint="Pothole repair", category="pothole")
    create_incident(memory_db, inc)

    # Attempt 1: Failed
    att1 = ExecutionAttemptModel(
        attempt_id=f"ATT-{incident_id}-1",
        incident_id=incident_id,
        plan_id=f"PLAN-{incident_id}-V1",
        resource="municipal_crew_alpha",
        outcome="FAILURE",
        failure_reason="crew_unavailable: scheduled crew diverted to emergency water main break",
        simulated=True,
    )
    save_execution_attempt(memory_db, att1)

    # Attempt 2: Succeeded with alternative resource
    att2 = ExecutionAttemptModel(
        attempt_id=f"ATT-{incident_id}-2",
        incident_id=incident_id,
        plan_id=f"PLAN-{incident_id}-V2",
        resource="standby_contractor_beta",
        outcome="SUCCESS",
        evidence_reference="PHOTO-POST-REPAIR-9981.jpg",
        simulated=True,
    )
    save_execution_attempt(memory_db, att2)

    attempts = get_execution_attempts_by_incident(memory_db, incident_id)
    assert len(attempts) == 2
    assert attempts[0].outcome == "FAILURE"
    assert "crew_unavailable" in attempts[0].failure_reason
    assert attempts[1].outcome == "SUCCESS"
    assert attempts[1].resource == "standby_contractor_beta"


def test_execution_attempt_enforces_simulated_true():
    """ExecutionAttempt schema strictly rejects simulated=False to prevent false repair claims."""
    with pytest.raises(ValueError, match="must be simulated=True"):
        ExecutionAttempt(
            attempt_id="ATT-REAL-CLAIM",
            incident_id="INC-001",
            outcome="SUCCESS",
            simulated=False,
        )


# ============================================================================
# 6. Database Transaction Rollback Tests
# ============================================================================

def test_transaction_rollback_on_failure(memory_db):
    """Multi-record database transactions roll back completely when any step fails."""
    incident_id = "INC-TX-TEST-01"

    with pytest.raises(RuntimeError, match="Simulated mid-transaction failure"):
        with transaction_scope(memory_db):
            inc = IncidentModel(
                incident_id=incident_id,
                complaint="Valid complaint within transaction",
                category="pothole",
            )
            memory_db.add(inc)

            # Insert a plan
            plan = PlanModel(
                plan_id=f"PLAN-{incident_id}-V1",
                incident_id=incident_id,
                plan_type=PlanType.TEMPORARY_RELIEF.value,
                version=1,
            )
            memory_db.add(plan)

            # Simulated crash before committing transaction
            raise RuntimeError("Simulated mid-transaction failure")

    # Verify rollback: neither incident nor plan should exist in the database
    assert get_incident_by_id(memory_db, incident_id) is None
    assert get_plans_by_incident(memory_db, incident_id) == []


# ============================================================================
# 7. Duplicate Candidate Semantics Tests
# ============================================================================

def test_duplicate_candidate_marked_unconfirmed_without_auto_merge(memory_db):
    """Proximity or similarity marks candidates UNCONFIRMED; never merges or drops reports."""
    # Parent incident
    inc_parent = IncidentModel(
        incident_id="INC-PARENT-01",
        complaint="Massive pothole on Connaught Place outer circle",
        category="pothole",
    )
    create_incident(memory_db, inc_parent)

    # Second reporting citizen
    inc_child = IncidentModel(
        incident_id="INC-CHILD-02",
        complaint="Dangerous road crater at CP outer circle near block B",
        category="pothole",
    )
    create_incident(memory_db, inc_child)

    # GeoCivic identifies duplicate candidate
    candidate = DuplicateCandidateModel(
        candidate_id="CAND-01",
        incident_id="INC-CHILD-02",
        other_incident_id="INC-PARENT-01",
        distance_meters=22.5,
        similarity_score=0.88,
        rationale="Within 25 meters on Connaught Place corridor with high TF-IDF similarity",
        review_status=DuplicateReviewStatus.UNCONFIRMED.value,
    )
    save_duplicate_candidate(memory_db, candidate)

    # Both incidents must remain active and distinct
    parent_loaded = get_incident_by_id(memory_db, "INC-PARENT-01")
    child_loaded = get_incident_by_id(memory_db, "INC-CHILD-02")
    assert parent_loaded is not None
    assert child_loaded is not None
    assert parent_loaded.incident_id != child_loaded.incident_id

    # Duplicate review status is UNCONFIRMED
    assert candidate.review_status == DuplicateReviewStatus.UNCONFIRMED.value


# ============================================================================
# 8. Civic Incident Twin History Service Tests
# ============================================================================

def test_civic_incident_twin_complete_history(memory_db):
    """Civic Incident Twin must expose complete unmodified history and timelines."""
    incident_id = "INC-TWIN-01"
    inc = IncidentModel(
        incident_id=incident_id,
        complaint="Original citizen complaint text with typographical errors and clues",
        category="garbage",
        location_data={"latitude": 28.7045, "longitude": 77.1028, "source": "MANUAL_ENTRY"},
        operational_status=OperationalStatus.TRIAGED.value,
        evidence_status=EvidenceOutcome.MATCHED.value,
    )
    create_incident(memory_db, inc)

    # 1. Model prediction
    pred = ModelPredictionModel(
        prediction_id=f"PRED-{incident_id}-1",
        incident_id=incident_id,
        task_type="vision_classification",
        predicted_label="garbage",
        scores={"garbage": 0.94, "pothole": 0.04, "waterlogging": 0.02},
        model_version="groq/qwen3.8-27b",
        available=True,
        fallback_provenance="direct",
        is_synthetic=True,
    )
    save_prediction(memory_db, pred)

    # 2. Plan versions
    p1 = PlanModel(
        plan_id=f"PLAN-{incident_id}-V1",
        incident_id=incident_id,
        plan_type=PlanType.TEMPORARY_RELIEF.value,
        version=1,
        status=PlanStatus.FAILED.value,
        actions=["Initial containment"],
        dependencies=[],
        resource_requirements=["Crew 1"],
        approval_requirements=[],
    )
    save_plan(memory_db, p1)

    p2 = PlanModel(
        plan_id=f"PLAN-{incident_id}-V2",
        incident_id=incident_id,
        plan_type=PlanType.PERMANENT_RESOLUTION.value,
        version=2,
        status=PlanStatus.APPROVED.value,
        actions=["Deploy compactor truck", "Sanitize public walkway"],
        dependencies=[],
        resource_requirements=["Compactor truck", "Sanitization team"],
        approval_requirements=["Sanitation Inspector"],
    )
    save_plan(memory_db, p2)

    # 3. Execution attempt (failure)
    att = ExecutionAttemptModel(
        attempt_id=f"ATT-{incident_id}-1",
        incident_id=incident_id,
        plan_id=f"PLAN-{incident_id}-V1",
        resource="sanitation_truck_3",
        outcome="FAILURE",
        failure_reason="vehicle_breakdown",
        simulated=True,
    )
    save_execution_attempt(memory_db, att)

    # 4. Verification result
    ver = VerificationResultModel(
        verification_id=f"VER-{incident_id}-1",
        incident_id=incident_id,
        criteria=["Waste cleared", "Sanitization verified"],
        evidence_reviewed=["Site photo archived"],
        result=VerificationOutcome.VERIFIED.value,
        passed=True,
        reviewer="independent_verification_agent",
    )
    save_verification_result(memory_db, ver)

    # Query Civic Incident Twin
    twin = get_incident_twin(memory_db, incident_id)
    assert twin is not None
    assert twin.incident_id == incident_id
    assert twin.original_input == "Original citizen complaint text with typographical errors and clues"
    assert twin.category == "garbage"
    assert twin.is_synthetic is True

    # Predictions verified
    assert len(twin.predictions) == 1
    assert twin.predictions[0].predicted_label == "garbage"
    assert twin.predictions[0].available is True

    # Plan version history verified
    assert len(twin.plans) == 2
    assert twin.plans[0].version == 1
    assert twin.plans[1].version == 2

    # Execution attempt & failures verified
    assert len(twin.execution_attempts) == 1
    assert len(twin.failures) == 1
    assert twin.failures[0].failure_reason == "vehicle_breakdown"

    # Verification result verified
    assert len(twin.verification_results) == 1
    assert twin.verification_results[0].passed is True
