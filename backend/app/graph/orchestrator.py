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
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    ClosureEvidence,
    EvidenceOutcome,
    OperationalStatus,
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
    failure_reason = state.get("failure_reason")
    now_iso = datetime.now(timezone.utc).isoformat()

    if failure_reason:
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Simulation Lab",
            action="Simulated Intervention Failed",
            result=f"Obstacle encountered: {failure_reason}. Triggering Adaptive Recovery.",
        )
        logger.info("Simulation failure injected: %s", failure_reason)
        return {
            "simulation_result": "FAILURE",
            "status": OperationalStatus.RECOVERING.value,
            "audit_timeline": [audit_event.model_dump()],
        }

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Simulation Lab",
        action="Simulated Intervention Executed",
        result="Physical field work simulated successfully. Awaiting closure evidence verification.",
    )
    logger.info("Simulation executed successfully. Moving to closure verification.")
    return {
        "simulation_result": "SUCCESS",
        "status": OperationalStatus.VERIFYING_CLOSURE.value,
        "audit_timeline": [audit_event.model_dump()],
    }


def closure_verification_node(state: IncidentState) -> Dict[str, Any]:
    """
    Deterministic Closure Evidence Verification Gate.
    
    Guarantees:
    - Never marks an incident resolved solely based on a model output or matched photo.
    - Requires verified synthetic completion evidence (closure_criteria_met with is_ready_for_closure=True).
    - If criteria are missing or unmet, blocks closure and records exact deficit.
    - Successful simulation yields SIMULATED_RESOLVED with explicit simulation markers.
    """
    plan = state.get("current_plan")
    sim_result = state.get("simulation_result")
    closure_evidence = state.get("closure_evidence")
    synthetic_evidence = state.get("synthetic_closure_evidence")

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

    # 1. Check if simulated action succeeded
    if sim_result != "SUCCESS":
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Simulation Failure",
            result="Cannot verify closure because intervention simulation was not successful.",
        )
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": "Simulation did not complete successfully",
            "audit_timeline": [audit_event.model_dump()],
        }

    # 2. Check if plan and criteria exist
    required_criteria = plan.closure_criteria if plan else []
    if not required_criteria:
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Undefined Criteria",
            result="Cannot verify closure because resolution plan lacks measurable criteria.",
        )
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": "No measurable closure criteria defined",
            "audit_timeline": [audit_event.model_dump()],
        }

    # 3. Check if verified completion evidence exists and is satisfied
    if not evidence_to_evaluate or not evidence_to_evaluate.is_ready_for_closure:
        unmet = [c for c in required_criteria if not (evidence_to_evaluate and c in evidence_to_evaluate.closure_criteria_met)]
        missing_desc = f"Missing criteria: {', '.join(unmet)}" if unmet else "No completion evidence verified"
        
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Closure Verification Gate",
            action="Closure Blocked: Incomplete Evidence",
            result=f"Closure blocked. {missing_desc}. Real repairs cannot be claimed without field inspection.",
        )
        logger.warning("Closure verification blocked: %s", missing_desc)
        return {
            "status": OperationalStatus.CLOSURE_BLOCKED.value,
            "failure_reason": f"Insufficient closure evidence: {missing_desc}",
            "audit_timeline": [audit_event.model_dump()],
        }

    # 4. Verified completion evidence exists
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Closure Verification Gate",
        action="Closure Verified (Simulation)",
        result=(
            f"All {len(evidence_to_evaluate.closure_criteria_met)} closure criteria verified. "
            f"Status updated to {OperationalStatus.SIMULATED_RESOLVED.value} [Simulation / Demo Only]."
        ),
    )
    logger.info("Closure verification succeeded. Marked as SIMULATED_RESOLVED.")
    return {
        "status": OperationalStatus.SIMULATED_RESOLVED.value,
        "closure_evidence": evidence_to_evaluate,
        "audit_timeline": [audit_event.model_dump()],
    }


# ============================================================================
# Conditional Routing Functions
# ============================================================================

def route_from_intake(state: IncidentState) -> List[str] | str:
    """
    Evidence-based workflow router following Incident Intelligence analysis.
    
    - MATCHED: proceeds to concurrent parallel execution of GeoCivic and Priority Intelligence.
    - NOT_PROVIDED with allow_unverified_triage: proceeds to conservative parallel triage.
    - MISMATCH, LOW_QUALITY, INCONCLUSIVE, or default NOT_PROVIDED: halts automated planning
      preserving the respective review status without dropping the complaint.
    """
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
    """Route from Closure Verification Gate."""
    status = state.get("status")
    allow_recovery = state.get("allow_closure_recovery", False)
    retry_count = state.get("retry_count", 0)

    # If closure is blocked and closure recovery is enabled within retry limits
    if (status == OperationalStatus.CLOSURE_BLOCKED.value or status == "CLOSURE_BLOCKED") and allow_recovery and retry_count < 2:
        return "adaptive_recovery"
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

    # 4. Planning to Critic
    builder.add_edge("resolution_planning", "critic")

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
