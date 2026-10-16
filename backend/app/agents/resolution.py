"""
JanSetu AI — Response Planning Agent (Phase 6, P6.1).

Responsible for:
- Formulating two distinct, versioned plans for a civic incident:
  * Plan A: TEMPORARY_RELIEF (immediate risk containment / interim protection)
  * Plan B: PERMANENT_RESOLUTION (long-term structural remediation)
- Sizing actions, resources, dependencies, and measurable completion criteria
- Implementing CivicAgentProtocol[ResponsePlanningOutput] and inheriting BaseCivicAgent
- Persisting plan versions in response_plans table without overwriting prior history
- Maintaining backwards compatibility with LangGraph resolution_planning_node
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import BaseCivicAgent
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    OperationalStatus,
    PlanStatus,
    PlanType,
    ResolutionPlan,
    ResponsePlan,
    ResponsePlanningOutput,
)

logger = logging.getLogger("jansetu.resolution")


def generate_dual_response_plans(
    incident_id: str,
    category: str,
    priority_band: str,
    critic_feedback: Optional[str] = None,
    version: int = 1,
) -> Tuple[ResponsePlan, ResponsePlan, ResolutionPlan]:
    """
    Generate two distinct, versioned Pydantic response plans:
    1. Plan A: TEMPORARY_RELIEF
    2. Plan B: PERMANENT_RESOLUTION
    Also returns a backwards-compatible ResolutionPlan for legacy graph nodes.
    """
    cat = (category or "uncertain_other").lower().strip()
    band = (priority_band or "Medium").capitalize()
    created_now = datetime.now(timezone.utc)

    temp_id = f"plan_temp_{incident_id}_{uuid.uuid4().hex[:6]}"
    perm_id = f"plan_perm_{incident_id}_{uuid.uuid4().hex[:6]}"

    if "waterlog" in cat:
        # Plan A: Temporary Relief
        temp_actions = [
            "Deploy high-visibility flood warning signage and amber warning beacons 100m upstream",
            "Position sandbag perimeter around vulnerable pedestrian accessways and shops",
            "Deploy portable high-flow dewatering pump to relieve immediate carriageway pooling",
        ]
        temp_deps = ["Traffic police coordination for safety corridor setup"]
        temp_resources = [
            "4x Flood warning signage stands",
            "50x High-density sandbags",
            "1x Portable 3-inch diesel suction pump unit",
        ]
        temp_cost = 4500.0
        temp_hours = 1.5
        temp_criteria = [
            "Pedestrian footpath cleared of standing stormwater",
            "Warning signage deployed and visible from 100m",
        ]

        # Plan B: Permanent Resolution
        perm_actions = [
            "Deploy high-capacity suction tanker to drain submerged arterial underpass",
            "High-pressure hydraulic jetting of clogged stormwater catch basins and culvert pipes",
            "Structural CCTV inspection of drainage lateral outfall to locate silt damming",
            "Rebuild damaged masonry catch basin grating to prevent recurrence",
        ]
        perm_deps = [
            "Stormwater Division Chief authorization",
            "Temporary lane diversion permit from traffic authorities",
        ]
        perm_resources = [
            "1x Suction pump truck (5000L)",
            "1x High-pressure jetter unit",
            "Drainage maintenance crew (4 technicians)",
            "Replacement cast-iron stormwater grate (heavy duty)",
        ]
        perm_cost = 24000.0
        perm_hours = 4.5
        perm_criteria = [
            "Water drained completely from all travel lanes",
            "Catch basins running free of debris",
            "Outfall flow rate restored to municipal baseline",
        ]
        perm_roles = ["Stormwater Drainage Team", "Traffic Police Liaison"]

    elif "garbage" in cat:
        # Plan A: Temporary Relief
        temp_actions = [
            "Erect high-visibility geotextile perimeter mesh to arrest windblown debris dispersion",
            "Apply powdered hydrated lime and surface odor neutralizer across perimeter",
            "Post municipal littering warning signage and monitor zone",
        ]
        temp_deps = []
        temp_resources = [
            "Geotextile containment barrier (25m)",
            "Hydrated lime deodorizer kit (50kg)",
            "2x Warning notice boards",
        ]
        temp_cost = 2000.0
        temp_hours = 1.0
        temp_criteria = [
            "Waste perimeter physically contained within mesh boundary",
            "Odor neutralizer applied to public walkway",
        ]

        # Plan B: Permanent Resolution
        perm_actions = [
            "Mechanical loading of accumulated solid waste into compactor truck",
            "Bulk haulage of solid waste to designated municipal processing facility",
            "High-pressure detergent wash and disinfectant spray of underlying sidewalk",
            "Install permanent secondary steel waste dumpster with rodent-proof lid",
        ]
        perm_deps = ["Municipal solid waste processing station intake acceptance slot"]
        perm_resources = [
            "1x Municipal compactor truck",
            "Sanitary clearing crew (4 workers)",
            "Surface disinfectant kit and power washer",
            "1x 1100L heavy-duty wheeled steel refuse bin",
        ]
        perm_cost = 14500.0
        perm_hours = 3.5
        perm_criteria = [
            "Solid waste completely cleared from pedestrian right-of-way",
            "Pavement disinfected",
            "New refuse bin installed and operational",
        ]
        perm_roles = ["Municipal Solid Waste Division", "Public Health Inspector"]

    else:  # Pothole or default road defect
        # Plan A: Temporary Relief
        temp_actions = [
            "Deploy advance traffic safety cones and retroreflective chevron barricades 50m upstream",
            "Clean loose cavity debris and tamp high-performance cold-mix asphalt patch flush with road surface",
            "Secure heavy structural steel trench plate across cavity if depth exceeds 15cm",
        ]
        temp_deps = ["Traffic police lane closure notification"]
        temp_resources = [
            "4x Reflective traffic safety cones",
            "2x Type-II road barricades",
            "High-performance cold-mix polymer asphalt (100kg)",
            "Heavy structural steel road plate (20mm)",
        ]
        temp_cost = 3500.0
        temp_hours = 1.0
        temp_criteria = [
            "Cavity secured with flush temporary surface or steel plate",
            "Advance warning cones deployed",
            "Smooth vehicular passage restored",
        ]

        # Plan B: Permanent Resolution
        perm_actions = [
            "Saw-cut and square cavity edges to sound asphalt base",
            "Vacuum road cavity, remove degraded sub-base aggregate, and apply hot cationic tack coat",
            "Lay hot-mix dense bituminous macadam and compact in lifts with tandem vibratory roller",
            "Seal joints with hot-poured rubberized bitumen joint sealant",
        ]
        perm_deps = [
            "Municipal Road Maintenance Division Chief sign-off",
            "Hot-mix asphalt batching plant dispatch slot",
            "Traffic control permit for partial carriageway closure",
        ]
        perm_resources = [
            "1x Tandem vibratory road paving roller",
            "Hot-mix asphalt batch (500kg)",
            "Paving crew (4 technicians)",
            "Joint sealant applicator",
        ]
        perm_cost = 18500.0
        perm_hours = 5.0
        perm_criteria = [
            "Pothole filled flush with surrounding wearing course",
            "Compaction verified",
            "Traffic flow restored",
        ]
        perm_roles = ["Road Maintenance Division", "Traffic Control Marshal"]

    # Incorporate Critic feedback if replanning
    if critic_feedback:
        crit_note = f"Critic Amendment: {critic_feedback}"
        perm_actions.append(crit_note)
        if "traffic" in critic_feedback.lower():
            perm_resources.append("Traffic Safety Officer vehicle")
            if "Traffic Safety Officer" not in perm_roles:
                perm_roles.append("Traffic Safety Officer")
        if "safety" in critic_feedback.lower() or "structural" in critic_feedback.lower():
            perm_resources.append("Enhanced structural safety barricades")

    # Construct Plan A: TEMPORARY_RELIEF
    temp_plan = ResponsePlan(
        plan_id=temp_id,
        incident_id=incident_id,
        plan_type=PlanType.TEMPORARY_RELIEF,
        version=version,
        status=PlanStatus.PROPOSED,
        actions=temp_actions,
        dependencies=temp_deps,
        resource_requirements=temp_resources,
        approval_requirements=[],
        requires_approval=False,
        estimated_cost=temp_cost,
        estimated_duration_hours=temp_hours,
        closure_criteria=temp_criteria,
        created_at=created_now,
        is_synthetic=True,
    )

    # Construct Plan B: PERMANENT_RESOLUTION
    perm_plan = ResponsePlan(
        plan_id=perm_id,
        incident_id=incident_id,
        plan_type=PlanType.PERMANENT_RESOLUTION,
        version=version,
        status=PlanStatus.PROPOSED,
        actions=perm_actions,
        dependencies=perm_deps,
        resource_requirements=perm_resources,
        approval_requirements=["Municipal Engineering Division Chief Approval"],
        requires_approval=True,
        estimated_cost=perm_cost,
        estimated_duration_hours=perm_hours,
        closure_criteria=perm_criteria,
        created_at=created_now,
        is_synthetic=True,
    )

    # Legacy-compatible composite ResolutionPlan
    legacy_plan = ResolutionPlan(
        mitigation_steps=temp_actions,
        permanent_repair_steps=perm_actions,
        required_resources=perm_resources,
        assigned_roles=perm_roles,
        closure_criteria=perm_criteria,
        estimated_duration_hours=perm_hours,
    )

    return temp_plan, perm_plan, legacy_plan


def generate_domain_plan(
    category: str,
    priority_band: str,
    critic_feedback: str | None = None,
) -> ResolutionPlan:
    """Legacy helper maintained for compatibility."""
    _, _, legacy_plan = generate_dual_response_plans(
        incident_id="INC-LEGACY",
        category=category,
        priority_band=priority_band,
        critic_feedback=critic_feedback,
    )
    return legacy_plan


class ResolutionPlanningAgent(BaseCivicAgent[ResponsePlanningOutput]):
    """Agent 4: Response Planning Specialist."""

    agent_name: str = "Resolution Planning Agent"
    agent_role: str = "Planner"

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResponsePlanningOutput:
        """
        Formulate both Plan A (TEMPORARY_RELIEF) and Plan B (PERMANENT_RESOLUTION).
        Returns validated ResponsePlanningOutput.
        """
        data = self.extract_incident_dict(incident)
        ctx = context or {}

        incident_id = data.get("incident_id") or ctx.get("incident_id") or f"inc_{uuid.uuid4().hex[:8]}"

        # Category and Priority determination
        facts = data.get("extracted_facts") or ctx.get("extracted_facts")
        if facts is not None:
            category = getattr(facts, "category", None) or facts.get("category", "uncertain_other")
        else:
            category = data.get("selected_category") or data.get("category") or ctx.get("selected_category", "uncertain_other")

        priority = data.get("priority") or ctx.get("priority")
        if priority is not None:
            band = getattr(priority, "priority_band", None) or priority.get("priority_band", "Medium")
        else:
            band = "Medium"

        validation = data.get("validation") or ctx.get("validation")
        feedback = None
        if validation is not None:
            val_status = getattr(validation, "status", None) or validation.get("status")
            if str(val_status).upper() in ("REJECT", "REJECTED"):
                feedback = getattr(validation, "feedback", None) or validation.get("feedback")

        plan_version = int(data.get("retry_count", 0)) + 1

        # Generate both versioned plans
        temp_plan, perm_plan, legacy_plan = generate_dual_response_plans(
            incident_id=incident_id,
            category=category,
            priority_band=band,
            critic_feedback=feedback,
            version=plan_version,
        )

        # Selected primary plan: Permanent Resolution is primary target; Temporary Relief deployed concurrently for high/critical
        selected_plan = perm_plan

        # Optional persistence if db is provided in context
        db = ctx.get("db")
        if db is not None:
            from app.db.repository import persist_plan_record
            try:
                persist_plan_record(db, temp_plan)
                persist_plan_record(db, perm_plan)
            except Exception as exc:
                logger.warning("Could not persist plans during agent run: %s", exc)

        temp_type = temp_plan.plan_type.value if hasattr(temp_plan.plan_type, "value") else str(temp_plan.plan_type)
        perm_type = perm_plan.plan_type.value if hasattr(perm_plan.plan_type, "value") else str(perm_plan.plan_type)
        rationale = (
            f"Formulated Plan A ({temp_type}) for immediate risk mitigation and "
            f"Plan B ({perm_type}) for complete restoration. "
            f"Incident Category: {category}, Priority Tier: {band}."
        )

        return ResponsePlanningOutput(
            incident_id=incident_id,
            temporary_plan=temp_plan,
            permanent_plan=perm_plan,
            selected_plan=selected_plan,
            resolution_plan=legacy_plan,
            status=OperationalStatus.PLANNING.value,
            rationale=rationale,
        )


def resolution_planning_node(state: IncidentState) -> Dict[str, Any]:
    """
    Resolution Planning Agent node for LangGraph workflow.
    Waits for both GeoCivic and Priority Intelligence branches to complete.
    
    Returns:
    - current_plan: ResolutionPlan (backwards compatible)
    - response_planning_output: ResponsePlanningOutput
    - temporary_plan: ResponsePlan dict
    - permanent_plan: ResponsePlan dict
    - selected_plan: ResponsePlan dict
    - status: VALIDATING
    - audit_timeline: list of AuditEvent
    """
    agent = ResolutionPlanningAgent()
    now_iso = datetime.now(timezone.utc).isoformat()
    cid = state.get("correlation_id") or f"corr_{state.get('incident_id', 'unknown')}"

    # Route to human review if escalated (danger/risk) or in an escalation status
    if state.get("is_escalated") or state.get("status") in (
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.ESCALATED.value,
    ):
        reasons = state.get("escalation_reasons") or ["Mandatory priority danger escalation"]
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent=agent.agent_name,
            action="Planning Bypassed — Mandatory Escalation",
            result=f"Incident routed to Human Review: {', '.join(reasons)}",
            correlation_id=cid,
            event_type="escalation",
            outcome="HUMAN_REVIEW",
        )
        return {
            "status": OperationalStatus.HUMAN_REVIEW.value,
            "current_plan": None,
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    output = agent.run(state)

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent=agent.agent_name,
        action="Formulated Dual Response Plans",
        result=(
            f"Temp: {output.temporary_plan.plan_id} (Est: {output.temporary_plan.estimated_duration_hours}h) | "
            f"Perm: {output.permanent_plan.plan_id} (Est: {output.permanent_plan.estimated_duration_hours}h)"
        ),
        correlation_id=cid,
        event_type="planning",
    )

    logger.info("Resolution Planning complete: temp=%s, perm=%s", output.temporary_plan.plan_id, output.permanent_plan.plan_id)

    return {
        "current_plan": output.resolution_plan,
        "response_planning_output": output.model_dump(),
        "temporary_plan": output.temporary_plan.model_dump(),
        "permanent_plan": output.permanent_plan.model_dump(),
        "selected_plan": output.selected_plan.model_dump(),
        "status": OperationalStatus.VALIDATING.value,
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }
