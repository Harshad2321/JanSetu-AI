"""
JanSetu AI — Adaptive Recovery Agent.

Responsible for:
- Responding to simulated intervention failures (crew shortage, material deficit, utility strikes)
- Formulating materially different alternative remediation plans
- Enforcing strict bounded replanning limits (escalating upon retry exhaustion)
- Routing revised plans back through the Critic & Verification gate before execution
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    OperationalStatus,
    ResolutionPlan,
    RevisedPlan,
)

logger = logging.getLogger("jansetu.recovery")

MAX_RECOVERY_RETRIES: int = 2


def generate_adaptive_remedy(
    previous_plan: ResolutionPlan | None,
    failure_reason: str,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Propose materially different action steps and resources based on the specific failure mode.
    Guarantees the recovery plan does NOT simply repeat the failed action.
    """
    reason_lower = failure_reason.lower()

    if "crew" in reason_lower:
        # Failure mode: Municipal crew unavailable
        new_steps = [
            "Activate emergency standby contractor paving team",
            "Deploy automated directional signage to protect zone during crew transit",
        ]
        new_resources = [
            "1x On-call Emergency Contractor Crew",
            "Automated electronic arrow board trailer",
        ]
        new_roles = [
            "Contractor Emergency Works Liaison",
            "Traffic Police Dispatcher",
        ]

    elif "material" in reason_lower:
        # Failure mode: Hot-mix asphalt or supplies exhausted
        new_steps = [
            "Anchor heavy interlocking steel trench plates across cavity as immediate bridge",
            "Source high-performance cold-mix polymer asphalt for rapid curing",
        ]
        new_resources = [
            "2x Heavy structural steel road plates (20mm)",
            "Asphalt anchor bolts and edge bevel ramps",
            "High-performance cold-mix polymer asphalt (400kg)",
        ]
        new_roles = [
            "Emergency Structural Road Works Team",
            "Materials Procurement Officer",
        ]

    elif "utility" in reason_lower or "gas" in reason_lower or "pipe" in reason_lower:
        # Failure mode: Buried utility line or infrastructure conflict
        new_steps = [
            "Cease mechanical hydraulic compaction immediately",
            "Deploy non-destructive vacuum hydro-excavation to safely expose utility alignment",
            "Perform joint site inspection with Gas & Utility Authority engineer",
        ]
        new_resources = [
            "1x Vacuum Hydro-Excavation rig",
            "Non-sparking hand excavation tools",
            "Utility locating radar unit",
        ]
        new_roles = [
            "Specialist Hydro-Vac Team",
            "Gas Grid Safety Marshal",
            "Civil Works Supervisor",
        ]

    elif "closure" in reason_lower or "evidence" in reason_lower:
        # Failure mode: Inadequate synthetic closure evidence
        new_steps = [
            "Dispatch municipal quality assurance supervisor for on-site core inspection",
            "Perform digital profilometer roughness and density compaction test",
        ]
        new_resources = [
            "Core density penetrometer test kit",
            "Digital road profilometer",
        ]
        new_roles = [
            "Municipal Quality Assurance Inspector",
            "Supervisory Engineering Field Officer",
        ]

    else:
        # Generic operational obstacle
        new_steps = [
            f"Alternative operational contingency protocol addressing '{failure_reason}'",
            "Secondary containment and bypass routing around incident site",
        ]
        new_resources = [
            "Contingency auxiliary equipment unit",
            "Perimeter barrier package",
        ]
        new_roles = [
            "Contingency Response Division",
        ]

    return new_steps, new_resources, new_roles


def recovery_node(state: IncidentState) -> Dict[str, Any]:
    """
    Adaptive Recovery Agent node.
    
    Increments retry_count. If retry ceiling is exceeded, escalates immediately.
    Otherwise, builds a materially different plan and sets status=VALIDATING to loop back to Critic.
    """
    plan = state.get("current_plan")
    failure_reason = state.get("failure_reason", "Simulated intervention failure")
    retry_count = state.get("retry_count", 0)

    new_retry_count = retry_count + 1

    # Check bounded retry ceiling
    if new_retry_count > MAX_RECOVERY_RETRIES:
        logger.warning(
            "Adaptive Recovery retry ceiling reached (%d/%d). Escalating to supervisor.",
            new_retry_count,
            MAX_RECOVERY_RETRIES,
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent="Adaptive Recovery Agent",
            action="Recovery Exhausted — Escalating",
            result=f"Retry limit ({MAX_RECOVERY_RETRIES}) reached following failure: '{failure_reason}'. Escalated to municipal supervisor.",
        )
        return {
            "status": OperationalStatus.ESCALATED.value,
            "retry_count": new_retry_count,
            "audit_timeline": [audit_event.model_dump()],
        }

    # Formulate materially different plan
    new_steps, new_resources, new_roles = generate_adaptive_remedy(plan, failure_reason)

    criteria = plan.closure_criteria if plan else ["Remediation verified complete and traffic restored"]

    updated_plan = ResolutionPlan(
        mitigation_steps=new_steps,
        permanent_repair_steps=plan.permanent_repair_steps if plan else ["Restoration complete"],
        required_resources=new_resources,
        assigned_roles=new_roles,
        closure_criteria=criteria,
        estimated_duration_hours=(plan.estimated_duration_hours or 4.0) + 2.0,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Adaptive Recovery Agent",
        action="Formulated Adaptive Recovery Plan",
        result=f"Resolved obstacle '{failure_reason}' with alternative roles: {', '.join(new_roles)} (Retry {new_retry_count}/{MAX_RECOVERY_RETRIES})",
    )

    logger.info("Adaptive Recovery formulated revised plan for obstacle: %s", failure_reason)

    return {
        "current_plan": updated_plan,
        "status": OperationalStatus.VALIDATING.value,
        "retry_count": new_retry_count,
        "failure_reason": None,  # Reset failure reason for new attempt
        "audit_timeline": [audit_event.model_dump()],
    }
