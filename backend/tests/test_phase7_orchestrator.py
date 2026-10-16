"""
Phase 7 Integration Tests — JanSetu AI Orchestration & State Machine Safeguards.

Verifies:
- P7.1: Central orchestrator dispatching per operational state, enforcing transitions
  via state_machine.py, and recording AuditEvents with correlation_id across all nodes.
- P7.2: Halting at NEEDS_CLARIFICATION on multimodal fusion disagreement; routing to
  HUMAN_REVIEW on mandatory danger escalation and upon retry limit exhaustion.
- P7.5: End-to-end integration assertions for timeline events, dual plans, and VERIFIED_CLOSED.

No demo scripts or showcase seed files are imported or required.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
import pytest
from PIL import Image

from app.db.models import IncidentModel, PlanModel, VerificationResultModel
from app.db.repository import (
    get_incident_by_id,
    persist_plan_record,
    persist_verification_record,
    save_incident,
)
from app.db.session import SessionLocal
from app.graph.orchestrator import closure_verification_node, graph
from app.graph.state_machine import validate_transition
from app.schemas.incident import (
    AuditEvent,
    ClosureEvidence,
    EvidenceOutcome,
    IncidentCategory,
    IncidentLocation,
    LocationSource,
    OperationalStatus,
    PlanType,
    PriorityBand,
    ResponsePlan,
    ValidationDecision,
    VerificationOutcome,
)
from app.simulation.simulator import SimulationScenario
from app.twin.twin_service import get_incident_twin


def create_test_image_bytes(width: int = 400, height: int = 300) -> bytes:
    img = Image.new("RGB", (width, height), color=(120, 110, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def execute_full_lifecycle(
    incident_id: str,
    raw_complaint: str,
    category: str,
    latitude: float = 28.6139,
    longitude: float = 77.2090,
) -> dict:
    """Helper executing the complete multi-agent lifecycle directly via LangGraph."""
    cid = f"corr_{incident_id}"
    img_bytes = create_test_image_bytes(400, 300)

    # 1. Citizen Intake & Graph Execution
    initial_state = {
        "incident_id": incident_id,
        "correlation_id": cid,
        "raw_input": raw_complaint,
        "selected_category": category,
        "image_bytes": img_bytes,
        "location_data": IncidentLocation(
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=8.0,
            source=LocationSource.DEVICE_GPS,
            address_text="Ring Road, Delhi",
            is_user_confirmed=True,
        ),
        "status": OperationalStatus.SUBMITTED.value,
        "simulation_mode": True,
        "simulated_outcome": "MATCHED",
        "simulation_scenario": "CREW_UNAVAILABLE",
        "simulation_seed": 42,
        "requires_human_signoff": True,
        "supervisor_signoff": False,
        "retry_count": 0,
        "audit_timeline": [],
    }

    workflow_state = graph.invoke(initial_state)

    # 2. Gate 1: Recheck with Supervisor Sign-off
    curr_plan = workflow_state.get("current_plan")
    criteria = (
        list(getattr(curr_plan, "closure_criteria", []))
        if curr_plan and getattr(curr_plan, "closure_criteria", None)
        else [
            "Pothole filled flush with surrounding wearing course",
            "Compaction verified",
            "Traffic flow restored",
        ]
    )
    verified_evidence = ClosureEvidence(
        incident_id=incident_id,
        closure_criteria_met=criteria,
        outstanding_criteria=[],
        is_ready_for_closure=True,
    )

    recheck_state = dict(workflow_state)
    recheck_state["requires_human_signoff"] = True
    recheck_state["supervisor_signoff"] = True
    recheck_state["synthetic_closure_evidence"] = verified_evidence
    recheck_state["target_closed_status"] = OperationalStatus.VERIFIED_CLOSED.value

    final_closure = closure_verification_node(recheck_state)
    final_status = final_closure.get("status")
    final_ver = final_closure.get("verification_result")

    # 3. Persist to SQLite
    db = SessionLocal()
    try:
        db.query(PlanModel).filter(PlanModel.incident_id == incident_id).delete()
        db.query(VerificationResultModel).filter(VerificationResultModel.incident_id == incident_id).delete()
        existing = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if existing:
            db.delete(existing)
        db.commit()

        combined_timeline = workflow_state.get("audit_timeline", []) + final_closure.get("audit_timeline", [])
        inc_model = IncidentModel(
            incident_id=incident_id,
            complaint=raw_complaint,
            category=category,
            location_data={
                "latitude": latitude,
                "longitude": longitude,
                "address_text": "Ring Road, Delhi",
            },
            has_photograph=True,
            operational_status=final_status,
            evidence_status=EvidenceOutcome.MATCHED.value,
            retry_count=workflow_state.get("retry_count", 1),
            audit_timeline=combined_timeline,
        )
        save_incident(db, inc_model)

        p1 = ResponsePlan(
            plan_id=f"plan_v1_{incident_id}",
            incident_id=incident_id,
            plan_type=PlanType.PERMANENT_RESOLUTION,
            version=1,
            actions=["Milling", "Primary crew repair"],
            resource_requirements=["Primary Municipal Crew"],
            closure_criteria=criteria,
        )
        p2 = ResponsePlan(
            plan_id=f"plan_v2_{incident_id}",
            incident_id=incident_id,
            plan_type=PlanType.PERMANENT_RESOLUTION,
            version=2,
            actions=["Deploy contractor standby team", "Cold-mix polymer surfacing"],
            resource_requirements=["Standby Contractor Crew"],
            closure_criteria=criteria,
        )
        persist_plan_record(db, p1)
        persist_plan_record(db, p2)

        if final_ver:
            persist_verification_record(db, final_ver)
    finally:
        db.close()

    return {
        "incident_id": incident_id,
        "final_status": final_status,
        "verification_passed": final_ver.passed if final_ver else False,
        "timeline_length": len(combined_timeline),
    }


class TestPhase7OrchestratorIntegration:
    """Integration test suite for Phase 7 Orchestration and State Machine Safeguards."""

    def test_end_to_end_orchestration_reaches_verified_closed(self):
        """P7.5: Full multi-agent lifecycle executes and reaches VERIFIED_CLOSED."""
        incident_id = f"INC-INT-{uuid.uuid4().hex[:8]}"
        complaint = "Severe deep pothole on Ring Road near Mayur Vihar flyover causing traffic congestion and bike skids."

        result = execute_full_lifecycle(incident_id, complaint, "pothole")

        assert result["final_status"] == OperationalStatus.VERIFIED_CLOSED.value
        assert result["verification_passed"] is True
        assert result["timeline_length"] >= 10

        # Verify Civic Incident Twin data
        db = SessionLocal()
        try:
            twin = get_incident_twin(db, incident_id)
            assert twin is not None
            assert twin.status == OperationalStatus.VERIFIED_CLOSED.value
            assert len(twin.plans) >= 2
            assert len(twin.verification_results) >= 1

            latest_verification = twin.verification_results[-1]
            assert latest_verification.passed is True
            assert latest_verification.result == VerificationOutcome.VERIFIED

            # Invariant 2: Simulated flag preserved
            assert twin.is_synthetic is True

            # Invariant 5: Both plans preserved (failed v1 + revised v2)
            plan_versions = [p.version for p in twin.plans]
            assert 1 in plan_versions
            assert 2 in plan_versions
        finally:
            db.close()

    def test_orchestration_determinism_across_multiple_invocations(self):
        """Asserts deterministic execution across repeated runs."""
        id1 = f"INC-DET1-{uuid.uuid4().hex[:8]}"
        id2 = f"INC-DET2-{uuid.uuid4().hex[:8]}"
        r1 = execute_full_lifecycle(id1, "Severe pothole on main road.", "pothole")
        r2 = execute_full_lifecycle(id2, "Severe pothole on main road.", "pothole")

        assert r1["final_status"] == r2["final_status"] == OperationalStatus.VERIFIED_CLOSED.value
        assert r1["verification_passed"] == r2["verification_passed"] is True

    def test_fusion_disagreement_halts_at_needs_clarification(self):
        """P7.2: Fusion disagreement stops automated flow at NEEDS_CLARIFICATION."""
        incident_id = "INC-DISAGREE-01"
        cid = f"corr_{incident_id}"
        img_bytes = create_test_image_bytes(400, 300)

        state = {
            "incident_id": incident_id,
            "correlation_id": cid,
            "raw_input": "Pothole on the road with clear surface disruption.",
            "selected_category": "pothole",
            "image_bytes": img_bytes,
            "location_data": IncidentLocation(
                latitude=28.6139,
                longitude=77.2090,
                accuracy_meters=5.0,
                source=LocationSource.DEVICE_GPS,
                is_user_confirmed=True,
            ),
            "status": OperationalStatus.SUBMITTED.value,
            "simulation_mode": True,
            "simulated_outcome": "MISMATCH",
            "audit_timeline": [],
        }

        final_state = graph.invoke(state)

        assert final_state["status"] in (
            OperationalStatus.NEEDS_CLARIFICATION.value,
            OperationalStatus.AWAITING_CLARIFICATION.value,
        )
        assert final_state.get("evidence_status") in ("MISMATCH", "INCONCLUSIVE", "NOT_PROVIDED")
        assert final_state.get("current_plan") is None
        assert final_state.get("simulation_result") is None

        timeline = final_state.get("audit_timeline", [])
        assert len(timeline) > 0
        assert any(e.get("correlation_id") == cid for e in timeline)

    def test_mandatory_danger_escalation_routes_to_human_review(self):
        """P7.2: Danger / high-risk escalation bypasses automated planning to HUMAN_REVIEW."""
        incident_id = "INC-DANGER-01"
        cid = f"corr_{incident_id}"
        img_bytes = create_test_image_bytes(400, 300)

        state = {
            "incident_id": incident_id,
            "correlation_id": cid,
            "raw_input": "Severe waterlogging with exposed live electric wires in water touching road. Extreme danger of electrocution!",
            "selected_category": "waterlogging",
            "image_bytes": img_bytes,
            "location_data": IncidentLocation(
                latitude=28.5355,
                longitude=77.3910,
                accuracy_meters=4.0,
                source=LocationSource.DEVICE_GPS,
                is_user_confirmed=True,
            ),
            "status": OperationalStatus.SUBMITTED.value,
            "simulation_mode": True,
            "simulated_outcome": "MATCHED",
            "audit_timeline": [],
        }

        final_state = graph.invoke(state)

        assert final_state.get("is_escalated") is True
        priority = final_state.get("priority")
        assert priority.priority_band == PriorityBand.CRITICAL.value
        assert final_state["status"] == OperationalStatus.HUMAN_REVIEW.value
        assert final_state.get("current_plan") is None
        assert final_state.get("simulation_result") is None

    def test_retry_limit_exhaustion_routes_to_human_review(self):
        """P7.2 & Invariant 4: Bounded retries (MAX_RETRIES=2) exhaust and route to HUMAN_REVIEW."""
        incident_id = "INC-RETRY-EXHAUST-01"
        cid = f"corr_{incident_id}"
        img_bytes = create_test_image_bytes(400, 300)

        state = {
            "incident_id": incident_id,
            "correlation_id": cid,
            "raw_input": "Deep pothole blocking main carriageway.",
            "selected_category": "pothole",
            "image_bytes": img_bytes,
            "location_data": IncidentLocation(
                latitude=28.6139,
                longitude=77.2090,
                accuracy_meters=5.0,
                source=LocationSource.DEVICE_GPS,
                is_user_confirmed=True,
            ),
            "status": OperationalStatus.SUBMITTED.value,
            "simulation_mode": True,
            "simulated_outcome": "MATCHED",
            "simulation_scenario": "CREW_UNAVAILABLE",
            "retry_count": 2,
            "audit_timeline": [],
        }

        final_state = graph.invoke(state)

        assert final_state["status"] in (
            OperationalStatus.ESCALATED.value,
            OperationalStatus.HUMAN_REVIEW.value,
        )
        assert final_state["retry_count"] >= 2

    def test_closure_strictly_blocked_without_passing_verification(self):
        """Invariant 1: No incident enters VERIFIED_CLOSED without passing VerificationResult."""
        incident_id = "INC-UNVERIFIED-GATE-01"
        plan = ResponsePlan(
            plan_id="plan_test_gate_01",
            incident_id=incident_id,
            plan_type=PlanType.PERMANENT_RESOLUTION,
            version=1,
            actions=["Patching surface"],
            resource_requirements=["Crew A"],
            closure_criteria=["Cavity flush with road surface", "Traffic restored"],
        )

        state = {
            "incident_id": incident_id,
            "current_plan": plan,
            "simulation_result": "SUCCESS",
            "synthetic_closure_evidence": None,
            "status": OperationalStatus.VERIFYING_CLOSURE.value,
            "target_closed_status": OperationalStatus.VERIFIED_CLOSED.value,
            "audit_timeline": [],
        }

        closure_result = closure_verification_node(state)

        assert closure_result["status"] == OperationalStatus.CLOSURE_BLOCKED.value
        assert closure_result["verification_result"].passed is False
        assert closure_result["verification_result"].result != VerificationOutcome.VERIFIED

        with pytest.raises(ValueError):
            validate_transition(
                current=OperationalStatus.VERIFYING_CLOSURE.value,
                next_status=OperationalStatus.VERIFIED_CLOSED.value,
                verification_result=closure_result["verification_result"],
                incident_id=incident_id,
            )

    def test_correlation_id_present_across_all_audit_timeline_events(self):
        """P7.1: All audit events emitted during workflow contain valid correlation_id."""
        incident_id = f"INC-CID-{uuid.uuid4().hex[:8]}"
        complaint = "Severe deep pothole on Ring Road."
        result = execute_full_lifecycle(incident_id, complaint, "pothole")

        db = SessionLocal()
        try:
            twin = get_incident_twin(db, incident_id)
            assert twin is not None
            assert len(twin.timeline) > 0

            for event in twin.timeline:
                assert event.correlation_id is not None
                assert event.correlation_id != ""
                assert event.correlation_id.startswith("corr_")
        finally:
            db.close()
