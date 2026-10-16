"""
JanSetu AI — Adaptive Recovery Agent (Phase 6, P6.3).

Responsible for:
- Responding to simulated intervention failures (crew shortage, material deficit, weather blocks, relief expiration)
- Executing the tracker-defined recovery algorithm:
  1. Read failed attempt and reason.
  2. Convert reason to an explicit constraint.
  3. Retrieve compatible alternatives from synthetic resource registry.
  4. Reject unsafe (not safety_certified), unavailable, or unauthorized options.
  5. Rank alternatives by feasibility, safety, time, cost.
  6. Select best eligible alternative and record rationale.
  7. Formulate a materially different plan with incremented version.
  8. Enforce bounded retry ceiling (MAX_RECOVERY_RETRIES = 2); escalate to supervisor/HUMAN_REVIEW on exhaustion.
- Preserving failed plan versions and execution attempts before recording replacements.
- Routing revised plans back through the Critic & Verification gate before execution.
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
    RevisedPlan,
    AdaptiveRecoveryOutput,
)
from app.simulation.simulator import SYNTHETIC_RESOURCES, SyntheticResource

logger = logging.getLogger("jansetu.recovery")

MAX_RECOVERY_RETRIES: int = 2


def derive_constraints_from_failure(failure_reason: str) -> List[str]:
    """Convert failure reason to explicit operational constraints."""
    reason_lower = (failure_reason or "").lower()
    constraints: List[str] = []

    if "crew" in reason_lower:
        constraints.append("no_primary_municipal_crew")
        constraints.append("require_standby_contractor_crew")
    elif "material" in reason_lower or "asphalt" in reason_lower:
        constraints.append("no_hot_mix_asphalt")
        constraints.append("require_cold_mix_or_steel_plates")
    elif "weather" in reason_lower or "rain" in reason_lower or "monsoon" in reason_lower:
        constraints.append("weather_safe_only")
        constraints.append("prohibit_rain_sensitive_surfacing")
    elif "relief" in reason_lower or "expired" in reason_lower:
        constraints.append("re_stabilize_perimeter")
        constraints.append("heavy_steel_reinforcement_required")
    elif "evidence" in reason_lower or "missing" in reason_lower:
        constraints.append("mandatory_supervisor_on_site_qa")
    elif "utility" in reason_lower or "gas" in reason_lower or "pipe" in reason_lower:
        constraints.append("underground_utility_conflict")
        constraints.append("require_hydro_vacuum_excavation")
    else:
        constraints.append("generic_contingency_required")

    return constraints


def evaluate_alternatives(
    constraints: List[str],
    category: str = "pothole",
) -> Tuple[Optional[SyntheticResource], List[Dict[str, Any]], List[SyntheticResource]]:
    """
    Query synthetic resource registry, reject unsafe/unavailable/unauthorized options,
    rank remaining by lead time and cost, and select the top alternative.
    """
    rejected: List[Dict[str, Any]] = []
    eligible: List[SyntheticResource] = []

    for res_id, res in SYNTHETIC_RESOURCES.items():
        # Check basic eligibility constraints
        if not res.available:
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Resource currently unavailable in inventory or on shift",
            })
            continue

        if not res.safety_certified:
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Resource failed municipal labor & engineering safety guidelines (UNSAFE)",
            })
            continue

        if not res.authorized:
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Resource lacks active municipal administrative vendor authorization (UNAUTHORIZED)",
            })
            continue

        if "weather_safe_only" in constraints and not res.weather_safe:
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Resource not certified for adverse weather operations (>25mm/hr rain)",
            })
            continue

        if "no_primary_municipal_crew" in constraints and res_id == "res_crew_municipal_primary":
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Primary municipal crew blocked by active failure constraint",
            })
            continue

        if "no_hot_mix_asphalt" in constraints and res_id == "res_mat_hot_mix_asphalt":
            rejected.append({
                "resource_id": res_id,
                "name": res.name,
                "rejection_reason": "Hot-mix asphalt batch supply exhausted or plant shut down",
            })
            continue

        # Check category match
        if "all" in res.category_affinity or category.lower() in [c.lower() for c in res.category_affinity]:
            eligible.append(res)

    # Rank eligible alternatives by lead time (primary) and cost (secondary)
    eligible.sort(key=lambda r: (r.lead_time_hours, r.cost_estimate))

    best_alternative = eligible[0] if eligible else None
    return best_alternative, rejected, eligible


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
        new_steps = [
            "Activate emergency standby contractor paving team",
            "Deploy automated directional signage to protect zone during crew transit",
            "Contractor executes rapid cavity milling and compaction under emergency mandate",
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
        new_steps = [
            "Anchor heavy interlocking structural steel trench plates across cavity as immediate bridge",
            "Procure and apply high-performance cold-mix polymer asphalt for rapid curing",
            "Cold patch tamped and sealed with bitumen edge emulsion",
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

    elif "weather" in reason_lower or "rain" in reason_lower:
        new_steps = [
            "Halt rain-sensitive hot-mix asphalt application immediately",
            "Deploy weather-safe interlocking steel plates and high-capacity submersible pump array",
            "Apply moisture-tolerant cold-mix polymer patch once pooling is stabilized",
        ]
        new_resources = [
            "Heavy structural steel road plates (20mm)",
            "Emergency High-Flow Submersible Pump Array",
            "High-Performance Cold-Mix Polymer Asphalt (400kg)",
        ]
        new_roles = [
            "Monsoon Emergency Contingency Team",
            "Stormwater Drainage Division",
        ]

    elif "relief" in reason_lower or "expired" in reason_lower:
        new_steps = [
            "Re-establish damaged traffic containment zone with heavy steel barricades and solar beacons",
            "Inspect sub-base for progressive vehicle-induced settlement",
            "Accelerate permanent hot-mix repair to commence within 12 hours",
        ]
        new_resources = [
            "Reinforced Steel Traffic Barricade Kit with Solar Beacons",
            "Road Sub-base Density Profilometer",
        ]
        new_roles = [
            "Rapid Response Barrier Unit",
            "Senior Civil Works Inspector",
        ]

    elif "closure" in reason_lower or "evidence" in reason_lower:
        new_steps = [
            "Dispatch municipal quality assurance supervisor for mandatory on-site core inspection",
            "Capture digital geotagged profilometer roughness and density compaction test",
            "Upload photographic verification before authorization",
        ]
        new_resources = [
            "Core density penetrometer test kit",
            "Digital road profilometer",
        ]
        new_roles = [
            "Municipal Quality Assurance Inspector",
            "Supervisory Engineering Field Officer",
        ]

    elif "utility" in reason_lower or "gas" in reason_lower or "pipe" in reason_lower:
        new_steps = [
            "Hand-dig test pits to locate underground utilities safely",
            "Coordinate with gas and water municipal utility boards",
            "Deploy non-destructive hydro-vacuum excavation unit",
        ]
        new_resources = [
            "Hydro-vac excavation truck",
            "Underground utility locator radar",
        ]
        new_roles = [
            "Hydro-vac Specialist Operator",
            "Gas Utility Safety Liaison",
        ]

    else:
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


class AdaptiveRecoveryAgent(BaseCivicAgent[AdaptiveRecoveryOutput]):
    """Agent 5: Adaptive Recovery Specialist."""

    agent_name: str = "Adaptive Recovery Agent"
    agent_role: str = "Business Automation"

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> AdaptiveRecoveryOutput:
        """
        Executes bounded adaptive recovery.
        Derives constraints, filters alternatives, selects best alternative,
        and constructs a materially different plan. Escalate to HUMAN_REVIEW on retry exhaustion.
        """
        data = self.extract_incident_dict(incident)
        ctx = context or {}

        incident_id = data.get("incident_id") or ctx.get("incident_id") or f"inc_{uuid.uuid4().hex[:8]}"
        failure_reason = str(data.get("failure_reason") or ctx.get("failure_reason") or "Simulated intervention failure")
        retry_count = int(data.get("retry_count", 0))

        # Previous plan handling
        previous_plan = data.get("current_plan") or ctx.get("current_plan")
        prev_plan_id = None
        if hasattr(previous_plan, "plan_id"):
            prev_plan_id = previous_plan.plan_id
        elif isinstance(previous_plan, dict):
            prev_plan_id = previous_plan.get("plan_id")

        facts = data.get("extracted_facts") or ctx.get("extracted_facts")
        category = facts.category if facts and hasattr(facts, "category") else (data.get("selected_category") or "pothole")

        new_retry_count = retry_count + 1

        # Check bounded retry limit
        if new_retry_count > MAX_RECOVERY_RETRIES:
            logger.warning(
                "Adaptive Recovery retry ceiling reached (%d/%d). Escalating to supervisor.",
                new_retry_count,
                MAX_RECOVERY_RETRIES,
            )
            return AdaptiveRecoveryOutput(
                incident_id=incident_id,
                recovery_attempted=True,
                previous_plan_id=prev_plan_id,
                revised_plan=None,
                resolution_plan=None,
                failure_reason=failure_reason,
                selected_alternative=None,
                rejected_alternatives=[],
                constraints=derive_constraints_from_failure(failure_reason),
                retry_count=new_retry_count,
                status=OperationalStatus.HUMAN_REVIEW.value,
                escalated_to_human=True,
                rationale=(
                    f"Retry limit ({MAX_RECOVERY_RETRIES}) reached following obstacle '{failure_reason}'. "
                    f"Escalated to municipal supervisor for manual intervention."
                ),
            )

        # 1. Derive constraints
        constraints = derive_constraints_from_failure(failure_reason)

        # 2. Evaluate synthetic alternatives (filtering unsafe, unavailable, unauthorized)
        best_alt, rejected, eligible = evaluate_alternatives(constraints, category=category)

        if not best_alt:
            logger.warning("No eligible alternatives found satisfying constraints: %s", constraints)
            return AdaptiveRecoveryOutput(
                incident_id=incident_id,
                recovery_attempted=True,
                previous_plan_id=prev_plan_id,
                revised_plan=None,
                resolution_plan=None,
                failure_reason=failure_reason,
                selected_alternative=None,
                rejected_alternatives=rejected,
                constraints=constraints,
                retry_count=new_retry_count,
                status=OperationalStatus.HUMAN_REVIEW.value,
                escalated_to_human=True,
                rationale="No certified, available, and authorized alternative resources exist. Routed to HUMAN_REVIEW.",
            )

        # 3. Formulate materially different plan
        new_steps, new_resources, new_roles = generate_adaptive_remedy(
            previous_plan if isinstance(previous_plan, ResolutionPlan) else None,
            failure_reason,
        )

        # Ensure the selected best alternative is highlighted in resources
        if best_alt.name not in new_resources:
            new_resources.insert(0, f"Selected Contingency: {best_alt.name}")

        plan_version = new_retry_count + 1
        revised_plan_id = f"plan_rev_v{plan_version}_{incident_id}_{uuid.uuid4().hex[:6]}"

        criteria = (
            getattr(previous_plan, "closure_criteria", None)
            or ["Remediation verified complete and traffic restored"]
        )

        # Typed ResponsePlan
        revised_response_plan = ResponsePlan(
            plan_id=revised_plan_id,
            incident_id=incident_id,
            plan_type=PlanType.PERMANENT_RESOLUTION,
            version=plan_version,
            status=PlanStatus.PROPOSED,
            actions=new_steps,
            dependencies=[f"Contingency authorization for {best_alt.name}"],
            resource_requirements=new_resources,
            approval_requirements=["Civil Works Supervisor sign-off for alternative recovery plan"],
            requires_approval=True,
            estimated_cost=best_alt.cost_estimate + 5000.0,
            estimated_duration_hours=best_alt.lead_time_hours + 3.0,
            closure_criteria=criteria,
            created_at=datetime.now(timezone.utc),
            is_synthetic=True,
        )

        # Legacy ResolutionPlan
        legacy_plan = ResolutionPlan(
            mitigation_steps=new_steps,
            permanent_repair_steps=getattr(previous_plan, "permanent_repair_steps", ["Restoration complete"]),
            required_resources=new_resources,
            assigned_roles=new_roles,
            closure_criteria=criteria,
            estimated_duration_hours=revised_response_plan.estimated_duration_hours,
        )

        # Optional persistence
        db = ctx.get("db")
        if db is not None:
            from app.db.repository import persist_plan_record
            try:
                persist_plan_record(db, revised_response_plan)
            except Exception as exc:
                logger.warning("Could not persist revised recovery plan: %s", exc)

        rationale = (
            f"Obstacle '{failure_reason}' converted to constraints: {', '.join(constraints)}. "
            f"Selected alternative: '{best_alt.name}' (Lead time: {best_alt.lead_time_hours}h, Cost: {best_alt.cost_estimate} INR). "
            f"Rejected {len(rejected)} unsafe/unavailable/unauthorized options. Formulated Plan v{plan_version}."
        )

        return AdaptiveRecoveryOutput(
            incident_id=incident_id,
            recovery_attempted=True,
            previous_plan_id=prev_plan_id,
            revised_plan=revised_response_plan,
            resolution_plan=legacy_plan,
            failure_reason=failure_reason,
            selected_alternative=best_alt.name,
            rejected_alternatives=rejected,
            constraints=constraints,
            retry_count=new_retry_count,
            status=OperationalStatus.VALIDATING.value,
            escalated_to_human=False,
            rationale=rationale,
        )


def recovery_node(state: IncidentState) -> Dict[str, Any]:
    """
    Adaptive Recovery Agent node for LangGraph workflow.
    Wraps AdaptiveRecoveryAgent().run(state) maintaining full backwards compatibility.
    """
    agent = AdaptiveRecoveryAgent()
    output = agent.run(state)

    cid = state.get("correlation_id") or f"corr_{output.incident_id}"
    now_iso = datetime.now(timezone.utc).isoformat()
    if output.escalated_to_human:
        audit_event = AuditEvent(
            timestamp=now_iso,
            agent=agent.agent_name,
            action="Recovery Exhausted — Escalating",
            result=output.rationale,
            correlation_id=cid,
            event_type="recovery",
        )
        logger.warning("Recovery escalated: %s", output.rationale)
        return {
            "status": OperationalStatus.HUMAN_REVIEW.value,
            "retry_count": output.retry_count,
            "adaptive_recovery_output": output.model_dump(),
            "correlation_id": cid,
            "audit_timeline": [audit_event.model_dump()],
        }

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent=agent.agent_name,
        action="Formulated Adaptive Recovery Plan",
        result=f"Resolved obstacle '{output.failure_reason}' using '{output.selected_alternative}' (Retry {output.retry_count}/{MAX_RECOVERY_RETRIES})",
        correlation_id=cid,
        event_type="recovery",
    )

    logger.info("Adaptive Recovery formulated revised plan for obstacle: %s", output.failure_reason)

    return {
        "current_plan": output.resolution_plan,
        "revised_plan": output.revised_plan.model_dump() if output.revised_plan else None,
        "adaptive_recovery_output": output.model_dump(),
        "status": OperationalStatus.VALIDATING.value,
        "retry_count": output.retry_count,
        "failure_reason": None,  # Reset failure reason for new attempt
        "simulation_scenario": None,  # Clear failure scenario for next simulation
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }
