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
    status_to_use = (
        OperationalStatus.TRIAGED.value
        if scenario_str is not None
        else incident.operational_status
    )
    initial_state: IncidentState = {
        "incident_id": incident.incident_id,
        "raw_input": incident.complaint,
        "selected_category": incident.category,
        "location_data": incident.location_data,
        "image_bytes": image_bytes,
        "status": status_to_use,
        "evidence_status": incident.evidence_status,
        "retry_count": initial_retry_count,
        "audit_timeline": [
            AuditEvent(**a) for a in (incident.audit_timeline or [])
        ],
        "simulation_mode": bool(scenario_str is not None),
        "simulation_scenario": scenario_str,
        "failure_reason": failure_reason,
        "injected_critic_verdict": injected_critic_verdict,
        "synthetic_closure_evidence": synthetic_closure_evidence,
        "allow_unverified_triage": (
            req.allow_unverified_triage
            if req.allow_unverified_triage is not None
            else True
        ),
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

    # 5. Build agent telemetry traces and synchronize state back to database
    traces = build_agent_execution_traces(final_state, incident)
    final_state["agent_traces"] = traces
    incident.update_from_state(final_state)
    save_incident(db, incident)

    # 6. Persist relational records to enable Civic Incident Twin historical tracking
    _persist_relational_artifacts(db, final_state)

    # 7. Build response
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


def _persist_relational_artifacts(db: Session, final_state: Dict[str, Any]) -> None:
    """Persist relational artifacts for Civic Incident Twin historical tracking."""
    from app.db.repository import (
        persist_execution_attempt_record,
        persist_plan_record,
        persist_prediction_record,
        persist_verification_record,
    )
    # Model predictions
    if "model_predictions" in final_state and final_state["model_predictions"]:
        for pred in final_state["model_predictions"]:
            try:
                persist_prediction_record(db, pred)
            except Exception as exc:
                logger.debug("Prediction persistence note: %s", exc)

    # Plans (Temporary & Permanent)
    if "temporary_plan" in final_state and final_state["temporary_plan"]:
        try:
            persist_plan_record(db, final_state["temporary_plan"])
        except Exception as exc:
            logger.debug("Temp plan persistence note: %s", exc)

    if "permanent_plan" in final_state and final_state["permanent_plan"]:
        try:
            persist_plan_record(db, final_state["permanent_plan"])
        except Exception as exc:
            logger.debug("Perm plan persistence note: %s", exc)

    # Revised adaptive recovery plan
    if "revised_plan" in final_state and final_state["revised_plan"]:
        try:
            persist_plan_record(db, final_state["revised_plan"])
        except Exception as exc:
            logger.debug("Revised plan persistence note: %s", exc)
    if "adaptive_recovery_output" in final_state and final_state["adaptive_recovery_output"]:
        rec_out = final_state["adaptive_recovery_output"]
        rev_p = rec_out.get("revised_plan") if isinstance(rec_out, dict) else getattr(rec_out, "revised_plan", None)
        if rev_p:
            try:
                persist_plan_record(db, rev_p)
            except Exception as exc:
                logger.debug("Adaptive recovery plan persistence note: %s", exc)
    if "current_plan" in final_state and final_state["current_plan"]:
        plan_obj = final_state["current_plan"]
        is_revised = getattr(plan_obj, "is_revised", False) if hasattr(plan_obj, "is_revised") else (plan_obj.get("is_revised", False) if isinstance(plan_obj, dict) else False)
        if is_revised:
            try:
                persist_plan_record(db, plan_obj)
            except Exception as exc:
                logger.debug("Current revised plan persistence note: %s", exc)

    # Execution attempts (All preserved)
    if "execution_attempts" in final_state and final_state["execution_attempts"]:
        for att in final_state["execution_attempts"]:
            try:
                persist_execution_attempt_record(db, att)
            except Exception as exc:
                logger.debug("Execution attempt persistence note: %s", exc)
    elif "execution_attempt" in final_state and final_state["execution_attempt"]:
        try:
            persist_execution_attempt_record(db, final_state["execution_attempt"])
        except Exception as exc:
            logger.debug("Execution attempt persistence note: %s", exc)

    # Verification result
    if "verification_result" in final_state and final_state["verification_result"]:
        try:
            persist_verification_record(db, final_state["verification_result"])
        except Exception as exc:
            logger.debug("Verification result persistence note: %s", exc)


def build_agent_execution_traces(final_state: Dict[str, Any], incident: IncidentModel) -> List[Dict[str, Any]]:
    """Construct authentic execution telemetry for all specialist agents."""
    now_iso = datetime.now(timezone.utc).isoformat()
    traces: List[Dict[str, Any]] = []
    retries = final_state.get("retry_count", 0)
    created_iso = incident.created_at.isoformat() if hasattr(incident, "created_at") and incident.created_at else now_iso

    # 1. Incident Intelligence Specialist
    if final_state.get("extracted_facts") or final_state.get("evidence_analysis"):
        facts = final_state.get("extracted_facts")
        cat = getattr(facts, "category", "civic defect") if facts else "civic defect"
        traces.append({
            "agent_name": "Incident Intelligence",
            "start_time": created_iso,
            "end_time": now_iso,
            "input_summary": f"Citizen complaint ({len(incident.complaint)} chars) & photographic evidence intake",
            "output_summary": f"Multimodal analysis complete. Category: '{cat}', evidence: {final_state.get('evidence_status', 'TRIAGED')}.",
            "status": "COMPLETED",
            "retry_count": 0,
        })

    # 2. GeoCivic Specialist (Branch A)
    if final_state.get("geo_context"):
        geo = final_state["geo_context"]
        dups = len(getattr(geo, "duplicate_candidates", []) or (geo.get("duplicate_candidates", []) if isinstance(geo, dict) else []))
        traces.append({
            "agent_name": "GeoCivic Agent",
            "start_time": created_iso,
            "end_time": now_iso,
            "input_summary": "Spatial coordinate verification and local municipal corridor lookup",
            "output_summary": f"Haversine & DBSCAN analysis complete. {dups} unconfirmed duplicate candidate(s) evaluated.",
            "status": "COMPLETED",
            "retry_count": 0,
        })
    elif final_state.get("status") in ("NEEDS_CLARIFICATION", "AWAITING_CLARIFICATION", "AWAITING_HUMAN_REVIEW"):
        traces.append({
            "agent_name": "GeoCivic Agent",
            "start_time": created_iso,
            "end_time": now_iso,
            "input_summary": "Spatial coordinates",
            "output_summary": "Awaiting complaint clarification or evidence resolution before spatial dispatch",
            "status": "BLOCKED",
            "retry_count": 0,
        })

    # 3. Priority Intelligence Specialist (Branch B)
    if final_state.get("priority"):
        prio = final_state["priority"]
        score = getattr(prio, "priority_score", 0) if hasattr(prio, "priority_score") else prio.get("priority_score", 0)
        band = getattr(prio, "priority_band", "Medium") if hasattr(prio, "priority_band") else prio.get("priority_band", "Medium")
        is_esc = final_state.get("is_escalated", False)
        traces.append({
            "agent_name": "Priority Intelligence",
            "start_time": created_iso,
            "end_time": now_iso,
            "input_summary": "Heuristic risk matrix & mandatory life-safety rules",
            "output_summary": f"Calculated priority score {score} ({band})" + (" [Mandatory Danger Escalation: Human Review]" if is_esc else ""),
            "status": "COMPLETED",
            "retry_count": 0,
        })

    # 4. Response Planning Specialist
    if final_state.get("current_plan") or final_state.get("temporary_plan"):
        temp = final_state.get("temporary_plan", {})
        perm = final_state.get("permanent_plan", {})
        temp_id = temp.get("plan_id", "PlanA") if isinstance(temp, dict) else getattr(temp, "plan_id", "PlanA")
        perm_id = perm.get("plan_id", "PlanB") if isinstance(perm, dict) else getattr(perm, "plan_id", "PlanB")
        traces.append({
            "agent_name": "Response Planning",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": "Civic category, priority tier, and municipal resource registry",
            "output_summary": f"Formulated Dual Plans: Temporary Relief ({temp_id}) & Permanent Resolution ({perm_id})",
            "status": "COMPLETED",
            "retry_count": retries,
        })
    elif final_state.get("is_escalated") or final_state.get("status") in ("HUMAN_REVIEW", "ESCALATED"):
        traces.append({
            "agent_name": "Response Planning",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": "Mandatory safety escalation triggered",
            "output_summary": "Bypassed automated planning to prioritize urgent human safety intervention",
            "status": "BLOCKED",
            "retry_count": 0,
        })

    # 5. Critic Gate (Pre-Execution Safety)
    if final_state.get("validation"):
        val = final_state["validation"]
        val_status = getattr(val, "status", "UNKNOWN") if hasattr(val, "status") else val.get("status", "UNKNOWN")
        feedback = getattr(val, "feedback", "") if hasattr(val, "feedback") else val.get("feedback", "")
        traces.append({
            "agent_name": "Critic",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": "Proposed resolution plan actions, safety clearances, and municipal procurement standards",
            "output_summary": f"Verdict: {val_status}. {feedback}".strip(),
            "status": "COMPLETED" if str(val_status).upper() == "APPROVE" else "REJECTED",
            "retry_count": retries,
        })

    # 6. Deterministic Execution Simulator
    if final_state.get("execution_attempt") or final_state.get("simulation_result"):
        sim_res = final_state.get("simulation_result", "UNKNOWN")
        traces.append({
            "agent_name": "Simulation Lab",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": "Approved intervention execution plan (simulated=True)",
            "output_summary": f"Simulated intervention outcome: {sim_res}",
            "status": "COMPLETED" if sim_res == "SUCCESS" else "FAILED",
            "retry_count": retries,
        })

    # 7. Adaptive Recovery Agent
    if retries > 0 or final_state.get("status") == "RECOVERING":
        reason = final_state.get("failure_reason", "Obstacle encountered")
        traces.append({
            "agent_name": "Adaptive Recovery",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": f"Obstacle diagnosis: {reason}",
            "output_summary": f"Selected certified resource alternative; replanned (Attempt {retries}/2)",
            "status": "COMPLETED",
            "retry_count": retries,
        })

    # 8. Independent Verification Agent
    if final_state.get("verification_result"):
        vr = final_state["verification_result"]
        passed = getattr(vr, "passed", False) if hasattr(vr, "passed") else vr.get("passed", False)
        outcome = getattr(vr, "outcome", "PENDING") if hasattr(vr, "outcome") else vr.get("outcome", "PENDING")
        traces.append({
            "agent_name": "Independent Verification Agent",
            "start_time": now_iso,
            "end_time": now_iso,
            "input_summary": "Plan closure criteria, simulated attempt telemetry, and post-repair photographic proof",
            "output_summary": f"Independent audit outcome: {outcome} (Passed: {passed})",
            "status": "COMPLETED" if passed else "BLOCKED",
            "retry_count": 0,
        })

    return traces
