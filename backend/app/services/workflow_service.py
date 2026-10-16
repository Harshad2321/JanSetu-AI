"""
JanSetu AI — Workflow Orchestration Service.

Bridges FastAPI REST endpoints and the real LangGraph multi-agent orchestrator:
- Hydrates state from persisted incident records and local image store
- Configures deterministic simulation scenarios safely
- Executes the compiled LangGraph workflow
- Persists resulting specialist outputs, traces, and audit timelines
- Enforces zero false resolution guarantees
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.db.models import IncidentModel
from app.db.repository import save_incident
from app.graph.orchestrator import graph
from app.graph.state import IncidentState
from app.schemas.api import (
    SupportedScenario,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.schemas.incident import (
    AgentExecutionTrace,
    AuditEvent,
    ClosureEvidence,
    OperationalStatus,
)
from app.services.image_storage import load_sanitized_image

logger = logging.getLogger("jansetu.workflow_service")


def execute_incident_workflow(
    db: Session,
    incident: IncidentModel,
    run_req: Optional[WorkflowRunRequest] = None,
) -> WorkflowRunResponse:
    """
    Execute the multi-agent LangGraph workflow for an incident.

    Guarantees:
    - Never simulates successful resolution inside the endpoint.
    - Only the deterministic closure gate can grant SIMULATED_RESOLVED.
    - Preserves audit timeline and agent traces across parallel branches.
    """
    req = run_req or WorkflowRunRequest()

    # 1. Load image bytes if available in private storage
    image_bytes = None
    if incident.has_photograph and incident.photo_storage_path:
        image_bytes = load_sanitized_image(incident.photo_storage_path)

    # 2. Configure scenario parameters
    scenario = req.simulation_scenario
    scenario_str = (
        scenario.value if hasattr(scenario, "value") else (str(scenario) if scenario else None)
    )
    failure_reason = req.failure_reason
    injected_critic_verdict = None
    synthetic_closure_evidence = None
    initial_retry_count = incident.retry_count or 0

    if scenario_str == SupportedScenario.CREW_UNAVAILABLE.value:
        failure_reason = "crew_unavailable"
    elif scenario_str == SupportedScenario.MATERIALS_UNAVAILABLE.value:
        failure_reason = "materials_unavailable"
    elif scenario_str == SupportedScenario.CRITIC_REJECTION.value:
        injected_critic_verdict = {
            "status": "REJECT",
            "feedback": "Injected safety rejection: proposed sealant lacks municipal standard certification.",
        }
    elif scenario_str == SupportedScenario.RETRY_EXHAUSTION.value:
        failure_reason = "repeated_intervention_failure"
        initial_retry_count = 2
    elif scenario_str == SupportedScenario.INSUFFICIENT_CLOSURE_EVIDENCE.value:
        failure_reason = None
        synthetic_closure_evidence = None  # Explicitly omitted to trigger closure gate block
    elif scenario_str == SupportedScenario.NORMAL.value:
        failure_reason = None
        synthetic_closure_evidence = {
            "incident_id": incident.incident_id,
            "closure_criteria_met": [
                "Pothole filled flush with adjacent road grade",
                "Compaction density verified via dynamic cone penetrometer",
                "Post-repair visual verification photo archived",
                "Temporary barricades and warning cones cleared",
                "No standing water observed after pump operation",
                "Drainage culvert cleared and flow restored",
                "Waste cleared and receptacle sanitized",
                "Site photograph archived in municipal registry",
                "Pothole filled flush with surrounding wearing course",
                "Compaction verified",
                "Traffic flow restored",
                "Water drained completely from all travel lanes",
                "Catch basins running free of debris",
                "Outfall flow rate restored to municipal baseline",
                "Solid waste completely cleared from pedestrian right-of-way",
                "Pavement disinfected",
                "New refuse bin installed and operational",
                "Cavity secured with flush temporary surface or steel plate",
                "Advance warning cones deployed",
                "Smooth vehicular passage restored",
                "Pedestrian footpath cleared of standing stormwater",
                "Warning signage deployed and visible from 100m",
                "Waste perimeter physically contained within mesh boundary",
                "Odor neutralizer applied to public walkway",
                "Remediation verified complete and traffic restored",
            ],
            "outstanding_criteria": [],
            "is_ready_for_closure": True,
            "inspector_notes": "Simulated field inspector verified all completion criteria met.",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    # 3. Assemble initial graph state
    initial_state: IncidentState = {
        "incident_id": incident.incident_id,
        "raw_input": incident.complaint,
        "selected_category": incident.category,
        "location_data": incident.location_data,
        "image_bytes": image_bytes,
        "status": incident.operational_status,
        "evidence_status": incident.evidence_status,
        "retry_count": initial_retry_count,
        "audit_timeline": [
            AuditEvent(**a) for a in (incident.audit_timeline or [])
        ],
        "simulation_mode": bool(scenario_str is not None),
        "failure_reason": failure_reason,
        "injected_critic_verdict": injected_critic_verdict,
        "synthetic_closure_evidence": synthetic_closure_evidence,
        "allow_unverified_triage": req.allow_unverified_triage or False,
        "allow_closure_recovery": req.allow_closure_recovery or False,
    }

    # 4. Invoke the real LangGraph workflow
    logger.info("Executing LangGraph workflow for incident: %s (Scenario: %s)", incident.incident_id, scenario)
    try:
        final_state: Dict[str, Any] = graph.invoke(initial_state)
    except Exception as exc:
        logger.error("LangGraph workflow error for incident %s: %s", incident.incident_id, str(exc), exc_info=True)
        # Log error in audit timeline and mark operational status as ESCALATED or error
        now_iso = datetime.now(timezone.utc).isoformat()
        error_event = AuditEvent(
            timestamp=now_iso,
            agent="Workflow Orchestrator",
            action="Workflow Execution Error",
            result=f"Graph execution failed: {str(exc)}. Routing to supervisor review.",
        )
        incident.operational_status = OperationalStatus.ESCALATED.value
        existing_timeline = incident.audit_timeline or []
        incident.audit_timeline = existing_timeline + [error_event.model_dump()]
        save_incident(db, incident)
        
        return WorkflowRunResponse(
            incident_id=incident.incident_id,
            operational_status=OperationalStatus.ESCALATED,
            evidence_status=incident.evidence_status,
            is_simulated_resolution=False,
            audit_timeline=[AuditEvent(**a) for a in incident.audit_timeline],
            message=f"Workflow failed safely: {str(exc)}",
        )

    # 5. Synchronize final state back to database
    incident.update_from_state(final_state)
    save_incident(db, incident)

    # 6. Build response
    op_status = OperationalStatus(incident.operational_status)
    is_sim_resolved = (op_status == OperationalStatus.SIMULATED_RESOLVED)

    return WorkflowRunResponse(
        incident_id=incident.incident_id,
        operational_status=op_status,
        evidence_status=incident.evidence_status,
        is_simulated_resolution=is_sim_resolved,
        simulation_scenario=scenario_str,
        current_plan=incident.to_response().current_plan,
        validation=incident.to_response().validation,
        closure_evidence=incident.to_response().closure_evidence,
        agent_traces=incident.to_response().agent_traces,
        audit_timeline=incident.to_response().audit_timeline,
        message=(
            "Simulated intervention completed successfully."
            if is_sim_resolved
            else f"Workflow executed. Current status: {incident.operational_status}"
        ),
    )
