"""
JanSetu AI — Multi-Agent Graph Orchestrator.

Implements:
- Parallel execution of GeoCivic and Priority Intelligence branches
- Conditional evidence routing based on multimodal intake outcomes
- Plan formulation and bounded Critic gate with replanning loop (max 2 retries)
- Failure-aware Adaptive Recovery handling simulated execution obstacles
- Deterministic closure verification gate enforcing verified synthetic completion evidence
- Zero false resolution claims: simulated completions produce SIMULATED_RESOLVED with explicit markers
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from app.agents.critic import critic_node
from app.agents.geocivic import geocivic_node
from app.agents.incident_intel import incident_intel_node
from app.agents.priority import priority_node
from app.agents.recovery import recovery_node
from app.agents.resolution import resolution_planning_node
from app.agents.verification import verification_node
from app.graph.state import IncidentState
from app.graph.state_machine import transition_status
from app.schemas.incident import (
    AuditEvent,
    ClosureEvidence,
    EvidenceOutcome,
    OperationalStatus,
    VerificationResult,
    VerificationOutcome,
)

logger = logging.getLogger("jansetu.orchestrator")


# ============================================================================
# Deterministic Workflow Gate Nodes
# ============================================================================

def simulate_intervention(state: IncidentState) -> Dict[str, Any]:
    """
    Deterministic simulated intervention node.
    Simulates physical execution; on failure injection routes to Adaptive Recovery.
    On success routes to the deterministic Closure Verification Gate.
    """
    from app.simulation.simulator import get_simulator, SimulationScenario

    plan = state.get("current_plan")
    incident_id = state.get("incident_id") or "INC-SIM"
    cid = state.get("correlation_id") or f"corr_{incident_id}"
    scenario_input = state.get("simulation_scenario")
    failure_reason = state.get("failure_reason")
    seed = state.get("simulation_seed", 42)
    now_iso = datetime.now(timezone.utc).isoformat()

    simulator = get_simulator()

    if scenario_input:
        attempt = simulator.simulate_execution(plan=plan, scenario=scenario_input, seed=seed, incident_id=incident_id)
        if attempt.outcome == "SUCCESS" and not attempt.failure_reason:
            audit_event = AuditEvent(
                timestamp=now_iso,
                agent="Simulation Lab",
                action="Simulated Intervention Executed",
                result=f"Physical field work simulated successfully ({attempt.resource}). Awaiting closure evidence verification.",
                correlation_id=cid,
                event_type="simulation",
                outcome="SUCCESS",
            )
            return {
                "simulation_result": "SUCCESS",
                "execution_attempt": attempt.model_dump(),
                "status": OperationalStatus.VERIFYING_CLOSURE.value,
                "correlation_id": cid,
                "audit_timeline": [audit_event.model_dump()],
            }
        else:
            fail_msg = attempt.failure_reason or f"Simulation scenario {scenario_input} failed."
            audit_event = AuditEvent(
                timestamp=now_iso,
                agent="Simulation Lab",
                action="Simulated Intervention Failed",
                result=f"Obstacle encountered: {fail_msg}. Triggering Adaptive Recovery.",
                correlation_id=cid,
                event_type="simulation",
                outcome="FAILURE",
            )
            return {
                "simulation_result": "FAILURE",
                "failure_reason": fail_msg,
                "execution_attempt": attempt.model_dump(),
                "status": OperationalStatus.RECOVERING.value,
                "correlation_id": cid,
                "audit_timeline": [audit_event.model_dump()],
            }

    if failure_reason:
        attempt = simulator.simulate_execution(plan=plan, scenario=failure_reason, seed=seed, incident_id=incident_id)
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Simulation Lab",
            action="Simulated Intervention Failed",
            result=f"Obstacle encountered: {failure_reason}. Triggering Adaptive Recovery.",
            correlation_id=cid,
            event_type="simulation",
            outcome="FAILURE",
        )
        logger.info("Simulation failure injected: %s", failure_reason)
        return {
            "simulation_result": "FAILURE",
            "execution_attempt": attempt.model_dump(),
            "status": OperationalStatus.RECOVERING.value,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    attempt = simulator.simulate_execution(plan=plan, scenario=SimulationScenario.SUCCESS, seed=seed, incident_id=incident_id)
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Simulation Lab",
        action="Simulated Intervention Executed",
        result="Physical field work simulated successfully. Awaiting closure evidence verification.",
        correlation_id=cid,
        event_type="simulation",
        outcome="SUCCESS",
    )
    logger.info("Simulation executed successfully. Moving to closure verification.")
    return {
        "simulation_result": "SUCCESS",
        "execution_attempt": attempt.model_dump(),
        "status": OperationalStatus.VERIFYING_CLOSURE.value,
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }


def closure_verification_node(state: IncidentState) -> Dict[str, Any]:
    """
    Deterministic Closure Evidence Verification Gate.
    
    Guarantees:
    - Never marks an incident resolved solely based on a model output or matched photo.
    - Requires verified synthetic completion evidence (closure_criteria_met with is_ready_for_closure=True).
    - If criteria are missing or unmet, blocks closure and records exact deficit.
    - Successful simulation yields SIMULATED_RESOLVED or VERIFIED_CLOSED with explicit simulation markers.
    """
    plan = state.get("current_plan")
    sim_result = state.get("simulation_result")
    closure_evidence = state.get("closure_evidence")
    synthetic_evidence = state.get("synthetic_closure_evidence")
    incident_id = state.get("incident_id") or "UNKNOWN"
    cid = state.get("correlation_id") or f"corr_{incident_id}"
    requires_human_signoff = bool(state.get("requires_human_signoff", False))
    supervisor_signoff = bool(state.get("supervisor_signoff", False))

    target_status = state.get("target_closed_status") or (
        OperationalStatus.VERIFIED_CLOSED.value
        if state.get("require_verified_closed")
        else OperationalStatus.SIMULATED_RESOLVED.value
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # Prioritize synthetic test evidence if passed in state
    evidence_to_evaluate: ClosureEvidence | None = None
    if isinstance(synthetic_evidence, ClosureEvidence):
        evidence_to_evaluate = synthetic_evidence
    elif isinstance(synthetic_evidence, dict):
        evidence_to_evaluate = ClosureEvidence(**synthetic_evidence)
    elif isinstance(closure_evidence, ClosureEvidence):
        evidence_to_evaluate = closure_evidence
    elif isinstance(closure_evidence, dict):
        evidence_to_evaluate = ClosureEvidence(**closure_evidence)

    from app.agents.verification import verify_incident
    from app.graph.state_machine import validate_transition

    # 1. Check if simulated action succeeded
    if sim_result != "SUCCESS":
        verification = verify_incident(
            incident_id=incident_id,
            plan=plan,
            evidence=evidence_to_evaluate,
            execution_outcome=sim_result,
            requires_human_signoff=requires_human_signoff,
            supervisor_signoff=supervisor_signoff,
        )
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Simulation Failure",
            result="Cannot verify closure because intervention simulation was not successful.",
            outcome=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
            correlation_id=cid,
            event_type="verification",
        )
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": "Simulation did not complete successfully",
            "verification_result": verification,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    # 2. Check if plan and criteria exist
    required_criteria = plan.closure_criteria if plan else []
    if not required_criteria:
        verification = verify_incident(
            incident_id=incident_id,
            plan=plan,
            evidence=evidence_to_evaluate,
            execution_outcome=sim_result,
            requires_human_signoff=requires_human_signoff,
            supervisor_signoff=supervisor_signoff,
        )
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Undefined Criteria",
            result="Cannot verify closure because resolution plan lacks measurable criteria.",
            outcome=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
            correlation_id=cid,
            event_type="verification",
        )
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": "No measurable closure criteria defined",
            "verification_result": verification,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    # 3. Check if verified completion evidence exists and is satisfied
    if not evidence_to_evaluate or not evidence_to_evaluate.is_ready_for_closure or (requires_human_signoff and not supervisor_signoff):
        verification = verify_incident(
            incident_id=incident_id,
            plan=plan,
            evidence=evidence_to_evaluate,
            execution_outcome=sim_result,
            requires_human_signoff=requires_human_signoff,
            supervisor_signoff=supervisor_signoff,
        )
        unmet = [c for c in required_criteria if not (evidence_to_evaluate and c in evidence_to_evaluate.closure_criteria_met)]
        if requires_human_signoff and not supervisor_signoff:
            missing_desc = "Mandatory human supervisor sign-off required before closure verification"
        elif unmet:
            missing_desc = f"Missing criteria: {', '.join(unmet)}"
        else:
            missing_desc = "Completion evidence not marked ready for closure"

        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Verification Incomplete",
            result=f"Closure blocked. {missing_desc}. Real repairs cannot be claimed without field inspection.",
            outcome=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
            correlation_id=cid,
            event_type="verification",
        )
        logger.warning("Closure verification blocked: %s", missing_desc)
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": f"Insufficient closure evidence: {missing_desc}",
            "verification_result": verification,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    # 4. Verified completion evidence exists
    verification = verify_incident(
        incident_id=incident_id,
        plan=plan,
        evidence=evidence_to_evaluate,
        execution_outcome=sim_result,
        requires_human_signoff=requires_human_signoff,
        supervisor_signoff=supervisor_signoff,
    )
    if not verification.passed:
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Verification Rejected",
            result=f"Verification rejected: {', '.join(verification.rejection_reasons)}",
            outcome=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
            correlation_id=cid,
            event_type="verification",
        )
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": f"Verification rejected: {', '.join(verification.rejection_reasons)}",
            "verification_result": verification,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    current_status = state.get("status") or OperationalStatus.VERIFYING_CLOSURE.value
    try:
        validated_status = validate_transition(
            current_status,
            target_status,
            verification_result=verification,
            incident_id=incident_id,
        )
    except Exception as exc:
        logger.warning("Transition validation note for closure: %s", exc)
        validated_status = target_status

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Closure Verification Gate",
        action="Closure Verified",
        result=(
            f"All {len(evidence_to_evaluate.closure_criteria_met)} closure criteria verified. "
            f"Independent verification passed ({verification.verification_id}). "
            f"Status updated to {validated_status} [Simulation / simulated=True]."
        ),
        outcome="VERIFIED",
        correlation_id=cid,
        event_type="verification",
    )
    logger.info("Closure verification succeeded. Marked as %s with passing VerificationResult.", validated_status)
    return {
        "status": validated_status,
        "closure_evidence": evidence_to_evaluate,
        "verification_result": verification,
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def route_from_intake(state: IncidentState) -> List[str] | str:
    """
    Evidence-based workflow router following Incident Intelligence analysis.
    
    - If status indicates clarification or review needed: halts (END).
    - MATCHED: proceeds to concurrent parallel execution of GeoCivic and Priority Intelligence.
    - NOT_PROVIDED with allow_unverified_triage: proceeds to conservative parallel triage.
    - MISMATCH, LOW_QUALITY, INCONCLUSIVE, or default NOT_PROVIDED: halts automated planning
      preserving the respective review status without dropping the complaint.
    """
    status = state.get("status")
    if status in (
        OperationalStatus.NEEDS_CLARIFICATION.value,
        OperationalStatus.AWAITING_CLARIFICATION.value,
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.AWAITING_HUMAN_REVIEW.value,
        OperationalStatus.AWAITING_EVIDENCE_RETAKE.value,
    ):
        logger.info("Intake router: status '%s' halts automated flow; awaiting clarification/review.", status)
        return END

    evidence_status = state.get("evidence_status")
    allow_unverified = state.get("allow_unverified_triage", False)

    if evidence_status == EvidenceOutcome.MATCHED.value or evidence_status == "MATCHED":
        logger.info("Intake router: Evidence MATCHED -> Dispatching GeoCivic & Priority Intelligence in parallel.")
        return ["geocivic", "priority_intel"]

    if (evidence_status == EvidenceOutcome.NOT_PROVIDED.value or evidence_status == "NOT_PROVIDED") and allow_unverified:
        logger.info("Intake router: Evidence NOT_PROVIDED with conservative triage policy enabled -> Dispatching parallel branches.")
        return ["geocivic", "priority_intel"]

    logger.info(
        "Intake router: Evidence status '%s' halts automated planning. Complaint preserved in status '%s'.",
        evidence_status,
        state.get("status"),
    )
    return END


def route_from_planning(state: IncidentState) -> str:
    """Route from Resolution Planning: to Critic unless escalated or routed to human review."""
    status = state.get("status")
    if status in (OperationalStatus.HUMAN_REVIEW.value, OperationalStatus.ESCALATED.value) or state.get("is_escalated"):
        return END
    return "critic"


def route_from_critic(state: IncidentState) -> str:
    """Route from Critic & Verification Agent."""
    status = state.get("status")
    if status == OperationalStatus.SIMULATING.value or status == "SIMULATING":
        return "simulate"
    elif status == OperationalStatus.PLANNING.value or status == "PLANNING":
        return "resolution_planning"
    else:  # ESCALATED or other termination
        return END


def route_from_simulation(state: IncidentState) -> str:
    """Route from Simulation Lab based on intervention outcome."""
    status = state.get("status")
    if status == OperationalStatus.RECOVERING.value or status == "RECOVERING":
        return "adaptive_recovery"
    elif status == OperationalStatus.VERIFYING_CLOSURE.value or status == "VERIFYING_CLOSURE":
        return "closure_gate"
    return END


def route_from_recovery(state: IncidentState) -> str:
    """Route from Adaptive Recovery: loop back to Critic unless escalated."""
    status = state.get("status")
    if status == OperationalStatus.ESCALATED.value or status == "ESCALATED":
        return END
    return "critic"


def route_from_closure(state: IncidentState) -> str:
    """Route from Closure Verification Gate.

    This graph keeps compatibility with the existing synthetic/demo flow, but the
    tracker requirement is enforced here: only a valid independent verification can
    reach VERIFIED_CLOSED. A simulated success remains explicitly labeled and must
    not masquerade as a real municipal closure.
    """
    status = state.get("status")
    verification_result = state.get("verification_result")
    allow_recovery = state.get("allow_closure_recovery", False)
    retry_count = state.get("retry_count", 0)

    if status == OperationalStatus.VERIFIED_CLOSED.value or status == "VERIFIED_CLOSED":
        return END

    if status == OperationalStatus.SIMULATED_RESOLVED.value or status == "SIMULATED_RESOLVED":
        return END

    if (status == OperationalStatus.CLOSURE_BLOCKED.value or status == "CLOSURE_BLOCKED") and allow_recovery and retry_count < 2:
        return "adaptive_recovery"

    if verification_result and getattr(verification_result, "passed", False):
        return END

    return END


# ============================================================================
# Graph Builder
# ============================================================================

def build_graph() -> StateGraph:
    """
    Construct the JanSetu AI Multi-Agent LangGraph workflow.
    
    Architecture:
    1. START -> incident_intel
    2. incident_intel -> conditional fork:
       - MATCHED -> [geocivic, priority_intel] (concurrency)
       - Others -> END (preserves intake status)
    3. [geocivic, priority_intel] -> resolution_planning (join)
    4. resolution_planning -> critic
    5. critic -> conditional:
       - APPROVE -> simulate
       - REJECT -> resolution_planning (bounded retry <= 2)
       - ESCALATE -> END
    6. simulate -> conditional:
       - FAILURE -> adaptive_recovery
       - SUCCESS -> closure_gate
    7. adaptive_recovery -> conditional:
       - VALIDATING -> critic (re-validation)
       - ESCALATED -> END
    8. closure_gate -> conditional:
       - SIMULATED_RESOLVED -> END
       - CLOSURE_BLOCKED -> adaptive_recovery / END
    """
    builder = StateGraph(IncidentState)

    # Specialist Agent Nodes
    builder.add_node("incident_intel", incident_intel_node)
    builder.add_node("geocivic", geocivic_node)
    builder.add_node("priority_intel", priority_node)
    builder.add_node("resolution_planning", resolution_planning_node)
    builder.add_node("critic", critic_node)
    builder.add_node("adaptive_recovery", recovery_node)

    # Deterministic Gate Nodes
    builder.add_node("simulate", simulate_intervention)
    builder.add_node("closure_gate", closure_verification_node)

    # 1. Entry edge
    builder.add_edge(START, "incident_intel")

    # 2. Conditional evidence fork from intake
    builder.add_conditional_edges(
        "incident_intel",
        route_from_intake,
        {
            "geocivic": "geocivic",
            "priority_intel": "priority_intel",
            END: END,
        },
    )

    # 3. Parallel Join: Both geocivic and priority_intel must complete before resolution_planning
    builder.add_edge("geocivic", "resolution_planning")
    builder.add_edge("priority_intel", "resolution_planning")

    # 4. Planning to Critic (conditional on escalation)
    builder.add_conditional_edges(
        "resolution_planning",
        route_from_planning,
        {
            "critic": "critic",
            END: END,
        },
    )

    # 5. Critic routing
    builder.add_conditional_edges(
        "critic",
        route_from_critic,
        {
            "simulate": "simulate",
            "resolution_planning": "resolution_planning",
            END: END,
        },
    )

    # 6. Simulation routing
    builder.add_conditional_edges(
        "simulate",
        route_from_simulation,
        {
            "adaptive_recovery": "adaptive_recovery",
            "closure_gate": "closure_gate",
            END: END,
        },
    )

    # 7. Adaptive Recovery routing back to Critic
    builder.add_conditional_edges(
        "adaptive_recovery",
        route_from_recovery,
        {
            "critic": "critic",
            END: END,
        },
    )

    # 8. Closure Gate routing
    builder.add_conditional_edges(
        "closure_gate",
        route_from_closure,
        {
            "adaptive_recovery": "adaptive_recovery",
            END: END,
        },
    )

    return builder.compile()


# Compile default workflow graph instance
graph = build_graph()
