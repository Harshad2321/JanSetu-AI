"""
JanSetu AI — Phase 6 Test Suite: Planning, Simulator, Recovery, and Independent Verification.

Automated verification of P6.1–P6.6:
1. Both TEMPORARY_RELIEF and PERMANENT_RESOLUTION plans are created with distinct IDs and types.
2. Plan versions persist across revisions without overwriting historical plans.
3. SUCCESS scenario produces simulated=True with valid completion evidence reference.
4. All 5 failure scenarios (CREW_UNAVAILABLE, MATERIAL_UNAVAILABLE, WEATHER_BLOCK,
   RELIEF_EXPIRED, COMPLETE_MISSING_EVIDENCE) return their documented failure reasons.
5. Crew unavailability leads to a materially different feasible plan or escalation.
6. Material unavailability leads to a materially different compatible plan or escalation.
7. Weather constraints cannot be bypassed; rain-sensitive alternatives are filtered out.
8. Unsafe (safety_certified=False) and unauthorized (authorized=False) alternatives are rejected.
9. Failed plan history and execution attempts are preserved in database and Twin.
10. Repeated recovery failures exhaust retries (MAX_RECOVERY_RETRIES=2) and escalate to HUMAN_REVIEW.
11. Missing supervisor sign-off produces HUMAN_REVIEW_REQUIRED.
12. Incomplete actions produce REJECTED_INCOMPLETE_ACTION.
13. Missing completion evidence produces REJECTED_INSUFFICIENT_EVIDENCE.
14. Critic and Independent Verification remain separate agents with distinct outputs.
15. A passing VerificationResult is strictly required for VERIFIED_CLOSED in state machine.
16. A planner claim, simulator success, or matched intake photo cannot bypass closure verification.
17. Civic Incident Twin displays all plan versions, failed attempts, recovery outcomes, and verifications.
18. Multi-record operations roll back on error via transaction_scope.
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.base import BaseCivicAgent, CivicAgentProtocol
from app.agents.critic import critic_node
from app.agents.recovery import (
    AdaptiveRecoveryAgent,
    MAX_RECOVERY_RETRIES,
    derive_constraints_from_failure,
    evaluate_alternatives,
    recovery_node,
)
from app.agents.resolution import (
    ResolutionPlanningAgent,
    generate_dual_response_plans,
    resolution_planning_node,
)
from app.agents.verification import (
    IndependentVerificationAgent,
    verification_node,
    verify_incident,
)
from app.db.models import (
    Base,
    ExecutionAttemptModel,
    IncidentModel,
    PlanModel,
    VerificationResultModel,
)
from app.db.repository import (
    get_execution_attempts_by_incident,
    get_incident_by_id,
    get_latest_plan,
    get_plans_by_incident,
    get_verification_results_by_incident,
    persist_execution_attempt_record,
    persist_plan_record,
    persist_verification_record,
    save_incident,
    transaction_scope,
)
from app.graph.state_machine import TransitionError, validate_transition
from app.schemas.incident import (
    AdaptiveRecoveryOutput,
    ClosureEvidence,
    ExecutionAttempt,
    IncidentCategory,
    IncidentLocation,
    IndependentVerificationOutput,
    OperationalStatus,
    PlanStatus,
    PlanType,
    ResolutionPlan,
    ResponsePlan,
    ResponsePlanningOutput,
    ValidationDecision,
    VerificationOutcome,
    VerificationResult,
)
from app.simulation.simulator import (
    ExecutionSimulator,
    SimulationScenario,
    SYNTHETIC_RESOURCES,
    get_simulator,
)
from app.twin.twin_service import get_incident_twin


@pytest.fixture
def db_session():
    """In-memory SQLite session with schema initialized."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# 1. P6.1 — Response Planning (Dual Plans & Persistence)
# ============================================================================

def test_p6_1_dual_plans_created_with_distinct_ids_and_types():
    """Agent 4 produces Plan A (TEMPORARY_RELIEF) and Plan B (PERMANENT_RESOLUTION)."""
    agent = ResolutionPlanningAgent()
    incident_input = {
        "incident_id": "INC-DUAL-01",
        "category": "pothole",
        "priority_band": "High",
    }

    output = agent.run(incident_input)
    assert isinstance(output, ResponsePlanningOutput)
    assert output.temporary_plan.plan_type in (PlanType.TEMPORARY_RELIEF, "TEMPORARY_RELIEF")
    assert output.permanent_plan.plan_type in (PlanType.PERMANENT_RESOLUTION, "PERMANENT_RESOLUTION")
    assert output.temporary_plan.plan_id != output.permanent_plan.plan_id
    assert output.temporary_plan.incident_id == "INC-DUAL-01"
    assert output.permanent_plan.incident_id == "INC-DUAL-01"
    assert output.temporary_plan.is_synthetic is True
    assert output.permanent_plan.is_synthetic is True
    assert len(output.temporary_plan.actions) > 0
    assert len(output.permanent_plan.actions) > 0
    assert len(output.permanent_plan.closure_criteria) > 0


def test_p6_1_plan_persistence_and_version_preservation(db_session):
    """Saving revised plan versions preserves historical versions in SQLite."""
    inc = IncidentModel(
        incident_id="INC-HIST-01",
        complaint="Deep road crater",
        category="pothole",
        operational_status="PLANNING",
    )
    save_incident(db_session, inc)

    # Version 1
    plan_v1 = ResponsePlan(
        plan_id="plan_pothole_v1",
        incident_id="INC-HIST-01",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        version=1,
        actions=["Lay hot-mix asphalt"],
        resource_requirements=["Hot-mix batch", "Paving roller"],
        closure_criteria=["Surface flush"],
    )
    persist_plan_record(db_session, plan_v1)

    # Version 2 (Revised plan)
    plan_v2 = ResponsePlan(
        plan_id="plan_pothole_v2",
        incident_id="INC-HIST-01",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        version=2,
        actions=["Install steel trench plate", "Cold-mix asphalt patch"],
        resource_requirements=["Steel plate 20mm", "Cold-mix polymer"],
        closure_criteria=["Surface flush", "Traffic restored"],
    )
    persist_plan_record(db_session, plan_v2)

    all_plans = get_plans_by_incident(db_session, "INC-HIST-01")
    assert len(all_plans) == 2
    assert all_plans[0].version == 1
    assert all_plans[1].version == 2
    assert all_plans[0].plan_id == "plan_pothole_v1"
    assert all_plans[1].plan_id == "plan_pothole_v2"

    latest = get_latest_plan(db_session, "INC-HIST-01")
    assert latest is not None
    assert latest.version == 2


# ============================================================================
# 2. P6.2 — Deterministic Execution Simulator
# ============================================================================

def test_p6_2_success_scenario_deterministic():
    """SUCCESS scenario returns simulated=True, outcome=SUCCESS and evidence reference."""
    sim = get_simulator()
    plan = ResponsePlan(
        plan_id="plan_sim_01",
        incident_id="INC-SIM-01",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        version=1,
        actions=["Repair road cavity"],
        resource_requirements=["Primary Crew"],
        closure_criteria=["Cavity flush"],
    )

    attempt = sim.simulate_execution(plan=plan, scenario=SimulationScenario.SUCCESS, seed=100)
    assert isinstance(attempt, ExecutionAttempt)
    assert attempt.simulated is True
    assert attempt.outcome == "SUCCESS"
    assert attempt.failure_reason is None
    assert attempt.evidence_reference is not None
    assert "INC-SIM-01" in attempt.evidence_reference


def test_p6_2_all_failure_scenarios_return_documented_reasons():
    """All 5 failure modes return their explicit failure reasons and simulated=True."""
    sim = get_simulator()
    plan = ResponsePlan(
        plan_id="plan_sim_fail",
        incident_id="INC-SIM-FAIL",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        version=1,
        actions=["Standard restoration"],
        resource_requirements=["Standard Crew"],
        closure_criteria=["Finished"],
    )

    # 1. CREW_UNAVAILABLE
    att_crew = sim.simulate_execution(plan=plan, scenario=SimulationScenario.CREW_UNAVAILABLE, seed=42)
    assert att_crew.outcome == "FAILED"
    assert "crew unavailable" in att_crew.failure_reason.lower()
    assert att_crew.simulated is True

    # 2. MATERIAL_UNAVAILABLE
    att_mat = sim.simulate_execution(plan=plan, scenario=SimulationScenario.MATERIAL_UNAVAILABLE, seed=42)
    assert att_mat.outcome == "FAILED"
    assert "material unavailable" in att_mat.failure_reason.lower() or "deficit" in att_mat.failure_reason.lower()
    assert att_mat.simulated is True

    # 3. WEATHER_BLOCK
    att_weath = sim.simulate_execution(plan=plan, scenario=SimulationScenario.WEATHER_BLOCK, seed=42)
    assert att_weath.outcome == "FAILED"
    assert "weather" in att_weath.failure_reason.lower() or "monsoon" in att_weath.failure_reason.lower()
    assert att_weath.simulated is True

    # 4. RELIEF_EXPIRED
    att_exp = sim.simulate_execution(plan=plan, scenario=SimulationScenario.RELIEF_EXPIRED, seed=42)
    assert att_exp.outcome == "FAILED"
    assert "expired" in att_exp.failure_reason.lower()
    assert att_exp.simulated is True

    # 5. COMPLETE_MISSING_EVIDENCE
    att_miss = sim.simulate_execution(plan=plan, scenario=SimulationScenario.COMPLETE_MISSING_EVIDENCE, seed=42)
    assert att_miss.outcome == "SUCCESS"  # field work done
    assert "not captured" in att_miss.failure_reason.lower() or "missing" in att_miss.failure_reason.lower()
    assert att_miss.evidence_reference is None  # no evidence


# ============================================================================
# 3. P6.3 — Adaptive Recovery (Agent 5)
# ============================================================================

def test_p6_3_crew_unavailability_selects_feasible_contractor_alternative():
    """Crew shortage constraint triggers contractor standby team selection."""
    agent = AdaptiveRecoveryAgent()
    res = agent.run({
        "incident_id": "INC-REC-01",
        "category": "pothole",
        "failure_reason": "Primary municipal crew unavailable: staffing deficit",
        "retry_count": 0,
    })

    assert isinstance(res, AdaptiveRecoveryOutput)
    assert res.recovery_attempted is True
    assert res.escalated_to_human is False
    assert "no_primary_municipal_crew" in res.constraints
    assert res.revised_plan is not None
    assert res.revised_plan.version == 2
    # Selected resource is different
    assert any("Contractor" in r for r in res.revised_plan.resource_requirements)


def test_p6_3_material_unavailability_selects_cold_mix_or_steel_plates():
    """Material exhaustion constraint selects compatible cold-mix polymer or steel plates."""
    agent = AdaptiveRecoveryAgent()
    res = agent.run({
        "incident_id": "INC-REC-02",
        "category": "pothole",
        "failure_reason": "Specified material unavailable: hot-mix asphalt batch deficit",
        "retry_count": 0,
    })

    assert res.escalated_to_human is False
    assert "no_hot_mix_asphalt" in res.constraints
    assert res.revised_plan is not None
    # Material selected is not hot-mix
    resources_str = " ".join(res.revised_plan.resource_requirements)
    assert "Cold-Mix" in resources_str or "Steel" in resources_str


def test_p6_3_weather_block_filters_out_weather_sensitive_options():
    """Monsoon/rain constraint rejects weather-sensitive materials and options."""
    constraints = derive_constraints_from_failure("Adverse weather block: monsoon rainfall exceeds safe threshold")
    assert "weather_safe_only" in constraints

    best, rejected, eligible = evaluate_alternatives(constraints, category="pothole")
    assert best is not None
    assert best.weather_safe is True
    # Verify that hot-mix asphalt was rejected due to weather
    hot_mix_rejections = [r for r in rejected if "hot-mix" in r["name"].lower()]
    assert len(hot_mix_rejections) > 0


def test_p6_3_rejects_unsafe_and_unauthorized_alternatives():
    """Uncertified labor and unauthorized private fleets are explicitly rejected."""
    _, rejected, eligible = evaluate_alternatives(["generic_contingency_required"], category="all")
    rejected_names = [r["name"].lower() for r in rejected]

    # Uncertified labor must be rejected
    assert any("uncertified" in name for name in rejected_names)
    # Unauthorized fleet must be rejected
    assert any("unauthorized" in name for name in rejected_names)
    # Neither should ever be in eligible
    for el in eligible:
        assert el.safety_certified is True
        assert el.authorized is True


def test_p6_3_retry_limit_exhaustion_escalates_to_human_review():
    """Exceeding MAX_RECOVERY_RETRIES triggers HUMAN_REVIEW escalation."""
    agent = AdaptiveRecoveryAgent()
    # At retry_count = 2, next attempt is 3 > 2
    res = agent.run({
        "incident_id": "INC-REC-MAX",
        "failure_reason": "Repeated contractor machine breakdown",
        "retry_count": MAX_RECOVERY_RETRIES,
    })

    assert res.escalated_to_human is True
    assert res.status == OperationalStatus.HUMAN_REVIEW.value
    assert res.revised_plan is None
    assert "Retry limit" in res.rationale


# ============================================================================
# 4. P6.4 — Independent Verification (Agent 6)
# ============================================================================

def test_p6_4_missing_signoff_yields_human_review_required():
    """Mandatory supervisor signoff missing results in HUMAN_REVIEW_REQUIRED."""
    res = verify_incident(
        incident_id="INC-VER-SIGNOFF",
        requires_human_signoff=True,
    )
    assert res.passed is False
    assert res.result == VerificationOutcome.HUMAN_REVIEW_REQUIRED
    assert any("sign-off" in r.lower() for r in res.rejection_reasons)


def test_p6_4_incomplete_action_rejected():
    """Failed intervention simulation produces REJECTED_INCOMPLETE_ACTION."""
    res = verify_incident(
        incident_id="INC-VER-FAIL",
        execution_outcome="FAILED",
    )
    assert res.passed is False
    assert res.result == VerificationOutcome.REJECTED_INCOMPLETE_ACTION
    assert any("did not complete successfully" in r for r in res.rejection_reasons)


def test_p6_4_missing_evidence_rejected():
    """Simulated success without completion evidence produces REJECTED_INSUFFICIENT_EVIDENCE."""
    res = verify_incident(
        incident_id="INC-VER-NO-EVID",
        execution_outcome="SUCCESS",
        evidence=None,
    )
    assert res.passed is False
    assert res.result == VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE


def test_p6_4_full_criteria_met_passes_verification():
    """When all criteria are met and marked ready, verification passes."""
    plan = ResponsePlan(
        plan_id="plan_ver_pass",
        incident_id="INC-VER-PASS",
        plan_type=PlanType.PERMANENT_RESOLUTION,
        closure_criteria=["Cavity flush", "Compaction verified"],
    )
    evidence = ClosureEvidence(
        incident_id="INC-VER-PASS",
        closure_criteria_met=["Cavity flush", "Compaction verified"],
        is_ready_for_closure=True,
    )

    res = verify_incident(
        incident_id="INC-VER-PASS",
        plan=plan,
        evidence=evidence,
        execution_outcome="SUCCESS",
    )
    assert res.passed is True
    assert res.result == VerificationOutcome.VERIFIED
    assert len(res.rejection_reasons) == 0


def test_p6_4_critic_and_independent_verification_separation():
    """Critic and Independent Verification are distinct agents with separate roles and schemas."""
    # Critic validates plan before execution
    critic_state = critic_node({
        "current_plan": ResolutionPlan(
            mitigation_steps=["Safety cones"],
            permanent_repair_steps=["Asphalt patch"],
            required_resources=["Roller"],
            assigned_roles=["Paving team"],
            closure_criteria=["Flush surface"],
        ),
        "retry_count": 0,
    })
    critic_res = critic_state["validation"]
    assert isinstance(critic_res, ValidationDecision)
    assert critic_res.status in ("APPROVE", "REJECT", "ESCALATE")

    # Independent Verification evaluates outcome after execution
    ver_agent = IndependentVerificationAgent()
    assert isinstance(ver_agent, BaseCivicAgent)
    assert isinstance(ver_agent, CivicAgentProtocol)
    assert ver_agent.agent_name == "Independent Verification Agent"


def test_p6_4_verified_closed_strictly_requires_passing_verification_result():
    """State machine rejects VERIFIED_CLOSED unless verification_result.passed is True."""
    # 1. Reject transition if verification_result is None
    with pytest.raises(TransitionError, match="requires a passing VerificationResult"):
        validate_transition(
            OperationalStatus.VERIFYING_CLOSURE.value,
            OperationalStatus.VERIFIED_CLOSED.value,
            verification_result=None,
        )

    # 2. Reject transition if verification_result.passed is False
    failing_ver = VerificationResult(
        verification_id="ver_fail",
        incident_id="INC-TEST",
        criteria=["Test criteria"],
        evidence_reviewed=[],
        result=VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE,
        passed=False,
    )
    with pytest.raises(TransitionError, match="passing VerificationResult"):
        validate_transition(
            OperationalStatus.VERIFYING_CLOSURE.value,
            OperationalStatus.VERIFIED_CLOSED.value,
            verification_result=failing_ver,
        )

    # 3. Allow transition when verification_result.passed is True
    passing_ver = VerificationResult(
        verification_id="ver_pass",
        incident_id="INC-TEST",
        criteria=["Test criteria"],
        evidence_reviewed=["Test criteria"],
        result=VerificationOutcome.VERIFIED,
        passed=True,
    )
    validated = validate_transition(
        OperationalStatus.VERIFYING_CLOSURE.value,
        OperationalStatus.VERIFIED_CLOSED.value,
        verification_result=passing_ver,
        incident_id="INC-TEST",
    )
    assert validated == OperationalStatus.VERIFIED_CLOSED.value


# ============================================================================
# 5. P6.6 — Twin & Transaction Safety
# ============================================================================

def test_p6_6_twin_displays_plans_attempts_and_verifications(db_session):
    """Civic Incident Twin loads all historical plans, attempts, and verifications."""
    inc = IncidentModel(
        incident_id="INC-TWIN-01",
        complaint="Submerged road and broken manhole",
        category="waterlogging",
        operational_status="AWAITING_VERIFICATION",
    )
    save_incident(db_session, inc)

    # Save 2 plans
    p1 = ResponsePlan(
        plan_id="p1", incident_id="INC-TWIN-01", plan_type=PlanType.TEMPORARY_RELIEF, version=1
    )
    p2 = ResponsePlan(
        plan_id="p2", incident_id="INC-TWIN-01", plan_type=PlanType.PERMANENT_RESOLUTION, version=1
    )
    persist_plan_record(db_session, p1)
    persist_plan_record(db_session, p2)

    # Save 1 failed attempt and 1 success attempt
    att1 = ExecutionAttempt(
        attempt_id="att1", incident_id="INC-TWIN-01", plan_id="p1", resource="Crew", outcome="FAILED", failure_reason="Crew unavailable", simulated=True
    )
    att2 = ExecutionAttempt(
        attempt_id="att2", incident_id="INC-TWIN-01", plan_id="p2", resource="Contractor", outcome="SUCCESS", simulated=True
    )
    persist_execution_attempt_record(db_session, att1)
    persist_execution_attempt_record(db_session, att2)

    # Save verification result
    ver = VerificationResult(
        verification_id="ver1", incident_id="INC-TWIN-01", criteria=["Water drained"], evidence_reviewed=["Water drained"], result=VerificationOutcome.VERIFIED, passed=True
    )
    persist_verification_record(db_session, ver)

    twin = get_incident_twin(db_session, "INC-TWIN-01")
    assert twin is not None
    assert len(twin.plans) == 2
    assert len(twin.execution_attempts) == 2
    assert len(twin.failures) == 1
    assert twin.failures[0].failure_reason == "Crew unavailable"
    assert len(twin.verification_results) == 1
    assert twin.verification_results[0].passed is True


def test_p6_6_transaction_rollback_preserves_database_integrity(db_session):
    """Failure inside transaction_scope rolls back changes completely."""
    inc = IncidentModel(
        incident_id="INC-TX-01",
        complaint="Garbage overflowing",
        category="garbage",
        operational_status="NEW",
    )
    save_incident(db_session, inc)

    with pytest.raises(RuntimeError):
        with transaction_scope(db_session):
            plan = PlanModel(
                plan_id="plan_tx_fail",
                incident_id="INC-TX-01",
                plan_type="TEMPORARY_RELIEF",
                version=1,
            )
            db_session.add(plan)
            db_session.flush()
            # Force simulated error
            raise RuntimeError("Database connection dropped or unexpected constraint violation")

    # Verify plan was NOT saved due to rollback
    plans = get_plans_by_incident(db_session, "INC-TX-01")
    assert len(plans) == 0
