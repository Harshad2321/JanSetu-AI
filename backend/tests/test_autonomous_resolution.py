"""
JanSetu AI — Autonomous Incident Resolution & Invariant Regression Suite.

Tests the 10 critical operational paths:
1. Routine pothole report submitted via API automatically reaches SIMULATED_RESOLVED.
2. Routine garbage report automatically reaches verified resolution.
3. Routine waterlogging report automatically reaches verified resolution.
4. Report mentioning previous accidents proceeds autonomously with elevated priority score (no false emergency halt).
5. Genuine active emergency triggers mandatory escalation and routes to HUMAN_REVIEW.
6. Vision-provider offline with honest partial processing (NLP_ONLY) proceeds autonomously.
7. Injected execution failure triggers Adaptive Recovery and succeeds after replan.
8. Retry exhaustion (2/2) routes to HUMAN_REVIEW.
9. Missing evidence prevents verified closure (CLOSURE_BLOCKED).
10. Repeated workflow execution requests avoid duplicate execution.
"""

from __future__ import annotations

import io
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes.incidents import get_db
from app.db.session import Base
from app.main import app
from app.schemas.incident import OperationalStatus
from tests.conftest import make_test_image


@pytest.fixture
def auto_client(tmp_path):
    """Isolated database session and test client for autonomous workflow tests."""
    db_file = tmp_path / "test_autonomous.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_01_routine_pothole_autonomous_resolution(auto_client):
    """1. Routine pothole report submitted via API automatically resolves."""
    payload = {
        "complaint": "Deep crater pothole in the center lane of Ring Road near Lajpat Nagar metro station.",
        "category": "pothole",
        "latitude": 28.5678,
        "longitude": 77.2432,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    # Autonomous execution verified
    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert data["current_plan"] is not None
    assert len(data["current_plan"]["mitigation_steps"]) > 0
    assert len(data["current_plan"]["permanent_repair_steps"]) > 0
    assert data["validation"]["status"] == "APPROVE"
    assert data["closure_evidence"]["is_ready_for_closure"] is True

    # Check twin history
    twin_resp = auto_client.get(f"/api/v1/incidents/{data['incident_id']}/twin")
    assert twin_resp.status_code == 200
    twin = twin_resp.json()
    assert len(twin["plans"]) >= 1
    assert len(twin["execution_attempts"]) >= 1
    assert twin["execution_attempts"][0]["outcome"] == "SUCCESS"
    assert len(twin["verification_results"]) >= 1
    assert twin["verification_results"][0]["passed"] is True


def test_02_routine_garbage_autonomous_resolution(auto_client):
    """2. Routine garbage report automatically reaches verified resolution."""
    payload = {
        "complaint": "Overflowing municipal garbage bin spilling waste onto the pedestrian walkway for two days.",
        "category": "garbage",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert data["current_plan"] is not None
    assert data["closure_evidence"]["is_ready_for_closure"] is True


def test_03_routine_waterlogging_autonomous_resolution(auto_client):
    """3. Routine waterlogging report automatically reaches verified resolution."""
    payload = {
        "complaint": "Severe waterlogging near metro underpass blocking two lanes of traffic.",
        "category": "waterlogging",
        "latitude": 28.5355,
        "longitude": 77.3910,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    data = resp.json()

    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert data["priority"]["priority_score"] > 0
    assert data["closure_evidence"]["is_ready_for_closure"] is True


def test_04_historical_accident_mention_proceeds_autonomously(auto_client):
    """4. Report mentioning previous accidents proceeds without active emergency halt."""
    payload = {
        "complaint": "There have been accidents reported here previously due to road defects, and two bikes skidded last week.",
        "category": "pothole",
        "latitude": 28.6200,
        "longitude": 77.2100,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Must NOT halt at HUMAN_REVIEW/ESCALATED
    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert data["current_plan"] is not None
    # Priority is elevated because of historical hazard mention
    assert data["priority"]["priority_score"] >= 60


def test_05_active_emergency_triggers_mandatory_escalation(auto_client):
    """5. Genuine mandatory life-safety escalation routes to HUMAN_REVIEW."""
    payload = {
        "complaint": "Active head-on collision right now with multiple casualties and driver trapped bleeding in vehicle!",
        "category": "pothole",
        "latitude": 28.6200,
        "longitude": 77.2100,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    data = resp.json()

    # Must halt at HUMAN_REVIEW / AWAITING_HUMAN_REVIEW
    assert data["operational_status"] in (
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.AWAITING_HUMAN_REVIEW.value,
        OperationalStatus.ESCALATED.value,
    )
    # Plan must not be formulated for active emergency
    assert data["current_plan"] is None
    # Audit trail explains the escalation
    audit_results = [e["result"] for e in data["audit_timeline"]]
    assert any("Mandatory Escalation" in r or "E03" in r for r in audit_results)


def test_06_vision_offline_honest_partial_processing(auto_client):
    """6. Vision-provider offline uses honest partial processing (NLP_ONLY) and resolves."""
    img_bytes = make_test_image(format_name="JPEG")
    files = {"image": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "complaint": "Pothole on the service road causing vehicular slow down.",
        "category": "pothole",
        "latitude": 28.5500,
        "longitude": 77.2500,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }

    # Force Groq client call to simulate offline / API error
    with patch("app.core.groq_vision.get_groq_client", return_value=None):
        resp = auto_client.post("/api/v1/incidents/", data=data, files=files)
        assert resp.status_code == 201
        res = resp.json()

        # Telemetry honestly describes fallback
        assert res["evidence_analysis"] is not None
        assert "Vision model provider offline" in res["evidence_analysis"]["visible_evidence"]
        # Workflow continues autonomously with NLP_ONLY
        assert res["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
        assert res["current_plan"] is not None


def test_07_injected_failure_adaptive_recovery(auto_client):
    """7. Injected failure triggers Adaptive Recovery and succeeds after replan."""
    payload = {
        "complaint": "Large pothole requiring immediate asphalt compaction.",
        "category": "pothole",
        "latitude": 28.5800,
        "longitude": 77.2200,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    # Initial creation auto-resolves
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    inc_id = resp.json()["incident_id"]

    # Now inject scenario 'crew_unavailable' via simulation endpoint
    sim_resp = auto_client.post(f"/api/v1/incidents/{inc_id}/simulate?scenario=crew_unavailable")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    # Recovery successfully replanned and resolved
    assert sim_data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    # Twin execution records show the recovery attempt
    twin_resp = auto_client.get(f"/api/v1/incidents/{inc_id}/twin")
    twin = twin_resp.json()
    assert len(twin["plans"]) >= 2
    # Failed attempt followed by success
    outcomes = [att["outcome"] for att in twin["execution_attempts"]]
    assert "FAILED" in outcomes or "FAILURE" in outcomes
    assert "SUCCESS" in outcomes


def test_08_retry_exhaustion_routes_to_human_review(auto_client):
    """8. Retry exhaustion stops at bounded limit and routes to human review."""
    payload = {
        "complaint": "Deep road trench blocking residential entrance.",
        "category": "pothole",
        "latitude": 28.5900,
        "longitude": 77.2300,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    inc_id = resp.json()["incident_id"]

    # Inject scenario retry_exhaustion
    sim_resp = auto_client.post(f"/api/v1/incidents/{inc_id}/simulate?scenario=retry_exhaustion")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    assert sim_data["operational_status"] in (
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.AWAITING_HUMAN_REVIEW.value,
        OperationalStatus.ESCALATED.value,
    )
    # Check bounded retries
    detail = auto_client.get(f"/api/v1/incidents/{inc_id}").json()
    assert detail["retry_count"] <= 2


def test_09_missing_evidence_blocks_closure(auto_client):
    """9. Missing evidence prevents verified closure (CLOSURE_BLOCKED)."""
    payload = {
        "complaint": "Garbage dump near public park.",
        "category": "garbage",
        "latitude": 28.5200,
        "longitude": 77.2100,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    inc_id = resp.json()["incident_id"]

    # Inject scenario insufficient_closure_evidence
    sim_resp = auto_client.post(f"/api/v1/incidents/{inc_id}/simulate?scenario=insufficient_closure_evidence")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()

    assert sim_data["operational_status"] == OperationalStatus.CLOSURE_BLOCKED.value
    # Independent verification Invariant 1 gate did NOT grant closure
    detail = auto_client.get(f"/api/v1/incidents/{inc_id}").json()
    assert detail["closure_evidence"]["is_ready_for_closure"] is False


def test_10_repeated_workflow_execution_prevents_duplicate(auto_client):
    """10. Repeated requests avoid duplicate workflow executions."""
    payload = {
        "complaint": "Pothole on outer lane.",
        "category": "pothole",
        "latitude": 28.5100,
        "longitude": 77.2000,
        "location_source": "DEVICE_GPS",
        "is_user_confirmed": True,
    }
    resp = auto_client.post("/api/v1/incidents/", data=payload)
    assert resp.status_code == 201
    inc_id = resp.json()["incident_id"]

    # Incident is already SIMULATED_RESOLVED
    # Calling /run again should return existing status cleanly
    run_resp = auto_client.post(f"/api/v1/incidents/{inc_id}/run")
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value

    # Verify execution attempts were not duplicated
    twin_resp = auto_client.get(f"/api/v1/incidents/{inc_id}/twin")
    twin = twin_resp.json()
    assert len(twin["execution_attempts"]) == 1
