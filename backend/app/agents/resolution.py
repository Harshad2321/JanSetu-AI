"""
JanSetu AI — Resolution Planning Agent.

Responsible for:
- Merging outputs from GeoCivic and Priority Intelligence
- Generating actionable remediation plans (mitigation, repair, resources, roles, closure criteria)
- Revising plans based on Critic feedback
- Ensuring strict closure criteria are defined before plan leaves this gate
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
)

logger = logging.getLogger("jansetu.resolution")


def generate_domain_plan(
    category: str,
    priority_band: str,
    critic_feedback: str | None = None,
) -> ResolutionPlan:
    """Generate structured remediation plan customized by hazard category and priority tier."""
    cat = category.lower()

    if "waterlog" in cat:
        mitigation = ["Deploy warning signage and high-visibility traffic cones 100m upstream"]
        repairs = ["Clear catch basin debris with high-pressure water jet", "Deploy mobile suction pump unit"]
        resources = ["1x Suction pump truck (5000L)", "4x Traffic safety cones", "High-pressure jetter"]
        roles = ["Stormwater Drainage Team", "Traffic Police Liaison"]
        criteria = ["Water drained completely from all travel lanes", "Catch basins running free of debris"]
        duration = 4.0
    elif "garbage" in cat:
        mitigation = ["Erect temporary mesh containment to prevent windblown litter dispersion"]
        repairs = ["Load and haul waste to designated processing station", "Sanitize public pavement"]
        resources = ["1x Compactor truck", "Sanitary crew (4 workers)", "Surface disinfectant kit"]
        roles = ["Municipal Solid Waste Division", "Public Health Inspector"]
        criteria = ["Solid waste completely cleared from pedestrian right-of-way", "Pavement disinfected"]
        duration = 3.0
    else:  # Pothole or other
        mitigation = ["Deploy advance traffic warning cones and safety barricades around cavity"]
        repairs = ["Square cavity edges, clean debris, apply tack coat, compact hot-mix asphalt"]
        resources = ["1x Road paving roller", "Hot-mix asphalt batch (500kg)", "4x Traffic safety cones"]
        roles = ["Road Maintenance Division", "Traffic Control Marshal"]
        criteria = ["Pothole filled flush with surrounding wearing course", "Compaction verified", "Traffic flow restored"]
        duration = 5.0

    # If Critic previously gave feedback (e.g. requested extra traffic or structural checks)
    if critic_feedback:
        mitigation.append(f"Critic Amendment: {critic_feedback}")
        if "traffic" in critic_feedback.lower() and "Traffic Safety Officer" not in roles:
            roles.append("Traffic Safety Officer")
        if "resource" in critic_feedback.lower() or "safety" in critic_feedback.lower():
            resources.append("Enhanced Safety Barricade Kit")

    return ResolutionPlan(
        mitigation_steps=mitigation,
        permanent_repair_steps=repairs,
        required_resources=resources,
        assigned_roles=roles,
        closure_criteria=criteria,
        estimated_duration_hours=duration,
    )


def resolution_planning_node(state: IncidentState) -> Dict[str, Any]:
    """
    Resolution Planning Agent node.
    Waits for both GeoCivic and Priority Intelligence to complete.
    
    Returns:
    - current_plan: ResolutionPlan
    - status: VALIDATING
    - audit_timeline: list of AuditEvent
    """
    facts = state.get("extracted_facts")
    geo = state.get("geo_context")
    priority = state.get("priority")
    validation = state.get("validation")

    category = facts.category if facts else state.get("selected_category", "uncertain_other")
    band = priority.priority_band if priority else "Medium"
    feedback = validation.feedback if validation and validation.status == "REJECT" else None

    # Generate domain plan
    plan = generate_domain_plan(category, band, feedback)

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Resolution Planning Agent",
        action="Formulated Resolution Plan" if not feedback else "Revised Resolution Plan (Critic Amendment)",
        result=f"Roles: {', '.join(plan.assigned_roles)} | Criteria: {len(plan.closure_criteria)} | Dur: {plan.estimated_duration_hours}h",
    )

    logger.info("Resolution Planning complete: roles=%s", plan.assigned_roles)

    return {
        "current_plan": plan,
        "status": OperationalStatus.VALIDATING.value,
        "audit_timeline": [audit_event.model_dump()],
    }
