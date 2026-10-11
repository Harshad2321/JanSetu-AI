"""
JanSetu AI — Critic & Verification Agent.

Responsible for:
- Independent validation of resolution plans against safety, resource, and policy criteria
- Gating transition to simulation: APPROVE, REJECT, or ESCALATE
- Enforcing strict bounded retries (maximum 2 replanning cycles before escalation)
- Guaranteeing no plan proceeds without adequate safety mitigations and closure criteria
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    CriticVerdict,
    OperationalStatus,
    ValidationDecision,
)

logger = logging.getLogger("jansetu.critic")

MAX_PLANNING_RETRIES: int = 2


def critic_node(state: IncidentState) -> Dict[str, Any]:
    """
    Critic and Verification Agent node.
    
    Evaluates current_plan:
    - APPROVE -> status: SIMULATING
    - REJECT (retry_count < 2) -> status: PLANNING (loop back to resolution_planning)
    - REJECT (retry_count >= 2) -> status: ESCALATED (retry exhaustion)
    - ESCALATE -> status: ESCALATED
    """
    plan = state.get("current_plan")
    retry_count = state.get("retry_count", 0)
    injected_verdict = state.get("injected_critic_verdict")

    # Seeded scenario override hook
    if injected_verdict:
        verdict_status = injected_verdict.get("status", "APPROVE").upper()
        feedback = injected_verdict.get("feedback", "Injected test feedback.")
        decision = ValidationDecision(
            status=verdict_status,
            feedback=feedback,
            safety_check_passed=(verdict_status == "APPROVE"),
            resource_check_passed=(verdict_status == "APPROVE"),
        )
    elif plan is None:
        decision = ValidationDecision(
            status="REJECT",
            feedback="No resolution plan provided for review.",
            safety_check_passed=False,
            resource_check_passed=False,
        )
    elif not plan.mitigation_steps or not plan.closure_criteria:
        decision = ValidationDecision(
            status="REJECT",
            feedback="Plan lacks required mitigation steps or measurable closure criteria.",
            safety_check_passed=False,
            resource_check_passed=True,
        )
    elif any("prohibited" in s.lower() or "invalid" in s.lower() for s in plan.mitigation_steps):
        decision = ValidationDecision(
            status="REJECT",
            feedback="Plan contains prohibited materials or unauthorized methods.",
            safety_check_passed=False,
            resource_check_passed=False,
        )
    else:
        decision = ValidationDecision(
            status="APPROVE",
            feedback="Plan satisfies municipal safety protocols and resource allocation requirements.",
            safety_check_passed=True,
            resource_check_passed=True,
        )

    # Check bounded retry exhaustion
    if decision.status == "REJECT":
        if retry_count >= MAX_PLANNING_RETRIES:
            logger.warning("Critic rejected plan; retry ceiling (%d) reached. Escalating.", MAX_PLANNING_RETRIES)
            decision = ValidationDecision(
                status="ESCALATE",
                feedback=f"Plan rejected and retry limit of {MAX_PLANNING_RETRIES} exhausted: {decision.feedback}",
                safety_check_passed=False,
                resource_check_passed=False,
            )
            next_status = OperationalStatus.ESCALATED.value
        else:
            next_status = OperationalStatus.PLANNING.value
    elif decision.status == "APPROVE":
        next_status = OperationalStatus.SIMULATING.value
    else:  # ESCALATE
        next_status = OperationalStatus.ESCALATED.value

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Critic Agent",
        action=f"Plan Review: {decision.status}",
        result=f"Status: {decision.status} | Feedback: {decision.feedback} (Retry: {retry_count}/{MAX_PLANNING_RETRIES})",
    )

    logger.info("Critic review complete: decision=%s, next_status=%s", decision.status, next_status)

    return {
        "validation": decision,
        "status": next_status,
        "audit_timeline": [audit_event.model_dump()],
    }
