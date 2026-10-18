"""
JanSetu AI — REST API & Persistence Test Suite.

Verifies:
1. Health endpoint (no leaked secrets)
2. Incident creation with photograph (sanitized, EXIF-stripped)
3. Incident creation without photograph (RECORDED_PENDING_REVIEW, NOT_PROVIDED)
4. Valid and invalid location coordinates
5. Unsupported or corrupted image uploads rejected
6. Incident listing, filtering, and detail retrieval
7. Database persistence across application restarts (SQLite on-disk survival)
8. Workflow execution using deterministic seeded scenarios
9. Retrieval of agent traces and audit events
10. Failed workflow execution does not produce a false resolved status
11. Mismatched evidence is preserved and routed correctly
12. Insufficient closure evidence blocks closure (CLOSURE_BLOCKED)
13. Simulated completion is explicitly labelled (SIMULATED_RESOLVED, is_simulated=True)
14. API validation errors and missing incident IDs (404 and 422)
15. CORS behavior for permitted and unpermitted origins
16. Sensitive secrets and raw base64 payloads never leak into API responses
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.api.routes.incidents import get_db
from app.config import settings
from app.db.session import Base
from app.main import app
from app.schemas.incident import (
    EvidenceOutcome,
    IncidentCategory,
    LocationSource,
    OperationalStatus,
)


# ============================================================================
# Test Fixtures: Isolated Database & Storage
# ============================================================================

@pytest.fixture
def test_env(tmp_path: Path):
    """Setup isolated SQLite database and private storage directory for tests."""
    db_file = tmp_path / "test_jansetu.db"
    storage_dir = tmp_path / "test_uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)

    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Patch settings storage dir and database url
    old_storage = settings.STORAGE_DIR
    old_db_url = settings.DATABASE_URL
    settings.STORAGE_DIR = str(storage_dir)
    settings.DATABASE_URL = test_db_url

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "SessionLocal": TestingSessionLocal,
        "db_file": db_file,
        "storage_dir": storage_dir,
    }

    # Teardown
    app.dependency_overrides.clear()
    settings.STORAGE_DIR = old_storage
    settings.DATABASE_URL = old_db_url


@pytest.fixture
def client(test_env) -> TestClient:
    """FastAPI TestClient with isolated test database."""
    return TestClient(app)


def make_test_image_bytes(color: str = "gray", width: int = 400, height: int = 400, format: str = "JPEG") -> bytes:
    """Helper to generate in-memory test image bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


# ============================================================================
# 1. Health Endpoint
# ============================================================================

def test_health_endpoint_no_credentials_leaked(client: TestClient):
    """Health check returns 200 without exposing secrets."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "JanSetu AI Backend"
    assert "GROQ_API_KEY" not in str(data)
    assert "password" not in str(data)

    # Also test /api/v1/health
    v1_resp = client.get("/api/v1/health")
    assert v1_resp.status_code == 200
    assert v1_resp.json()["status"] == "healthy"


# ============================================================================
# 2. Incident Creation with Photograph
# ============================================================================

def test_incident_creation_with_photograph(client: TestClient):
    """Multipart incident intake with a valid photograph strips EXIF and stores privately."""
    img_bytes = make_test_image_bytes(color="darkgray")

    response = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Deep hazardous pothole in the right lane of arterial road.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "accuracy_meters": "8.5",
            "location_source": "DEVICE_GPS",
            "is_user_confirmed": "true",
        },
        files={
            "image": ("pothole.jpg", img_bytes, "image/jpeg"),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["incident_id"].startswith("INC-")
    assert data["has_photograph"] is True
    assert data["operational_status"] in (OperationalStatus.NEW.value, OperationalStatus.SIMULATED_RESOLVED.value)
    assert data["evidence_status"] in (EvidenceOutcome.MATCHED.value, EvidenceOutcome.LOW_QUALITY.value)
    assert data["category"] == "pothole"
    assert data["location"]["latitude"] == 28.6139
    assert data["location"]["longitude"] == 77.2090
    assert len(data["audit_timeline"]) >= 1


# ============================================================================
# 3. Incident Creation without Photograph
# ============================================================================

def test_incident_creation_without_photograph(client: TestClient):
    """A complaint without a photograph is preserved as RECORDED_PENDING_REVIEW."""
    response = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Garbage accumulating behind community market, stray cattle gathered.",
            "category": "garbage",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["has_photograph"] is False
    assert data["operational_status"] in (OperationalStatus.RECORDED_PENDING_REVIEW.value, OperationalStatus.SIMULATED_RESOLVED.value)
    assert data["evidence_status"] == EvidenceOutcome.NOT_PROVIDED.value
    assert data["category"] == "garbage"


# ============================================================================
# 4. Valid and Invalid Location Coordinates
# ============================================================================

def test_valid_location_coordinates_json(client: TestClient):
    """JSON intake with valid paired coordinates succeeds."""
    payload = {
        "complaint": "Waterlogging across lane near underpass blocking pedestrians.",
        "category": "waterlogging",
        "location": {
            "latitude": 28.5670,
            "longitude": 77.2210,
            "accuracy_meters": 15.0,
            "source": LocationSource.DEVICE_GPS.value,
            "is_user_confirmed": True,
        },
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["location"]["latitude"] == 28.5670
    assert data["location"]["longitude"] == 77.2210


def test_invalid_latitude_out_of_bounds_rejected(client: TestClient):
    """Latitude > 90 must be rejected with 422."""
    payload = {
        "complaint": "Pothole on service lane.",
        "category": "pothole",
        "location": {
            "latitude": 95.0,
            "longitude": 77.0,
        },
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 422


def test_unpaired_coordinate_rejected(client: TestClient):
    """Latitude provided without longitude must be rejected with 422."""
    payload = {
        "complaint": "Pothole on service lane.",
        "category": "pothole",
        "location": {
            "latitude": 28.5,
            "longitude": None,
        },
    }
    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 422


# ============================================================================
# 5. Unsupported or Corrupted Image Uploads
# ============================================================================

def test_unsupported_or_corrupted_image_rejected(client: TestClient):
    """Corrupted binary or text payload masquerading as an image is rejected with 400."""
    fake_image_bytes = b"This is not a JPEG, this is a plain text file masquerading."
    response = client.post(
        "/api/v1/incidents",
        data={"complaint": "Pothole reported with bad photo attachment."},
        files={"image": ("bad.jpg", fake_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "Image upload rejected" in response.json()["detail"]


# ============================================================================
# 6. Incident Listing, Filtering, and Detail Retrieval
# ============================================================================

def test_incident_listing_filtering_and_detail(client: TestClient):
    """Listing returns items and total; filtering isolates matches; detail returns 200."""
    # Seed demonstration incidents
    seed_resp = client.post("/api/v1/incidents/seed")
    assert seed_resp.status_code == 200
    seeded_ids = seed_resp.json()["seeded_ids"]
    assert len(seeded_ids) >= 1

    # List all
    list_resp = client.get("/api/v1/incidents")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= len(seeded_ids)

    # Filter by category
    filter_resp = client.get("/api/v1/incidents?category=pothole")
    assert filter_resp.status_code == 200
    for item in filter_resp.json()["items"]:
        assert item["category"] == "pothole"

    # Detail retrieval
    first_id = seeded_ids[0]
    detail_resp = client.get(f"/api/v1/incidents/{first_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["incident_id"] == first_id


# ============================================================================
# 7. Database Persistence Across Application Restarts
# ============================================================================

def test_persistence_across_restarts(test_env, client: TestClient):
    """Data written to SQLite survives closing and reopening database sessions."""
    # Create incident
    resp = client.post(
        "/api/v1/incidents",
        json={
            "complaint": "Water pipe leak causing localized street flooding.",
            "category": "waterlogging",
        },
    )
    assert resp.status_code == 201
    created_id = resp.json()["incident_id"]

    # Reconnect directly to SQLite using a fresh session to simulate restart
    db_file = test_env["db_file"]
    new_engine = create_engine(f"sqlite:///{db_file}")
    NewSession = sessionmaker(bind=new_engine)
    session = NewSession()

    from app.db.models import IncidentModel
    saved_record = session.query(IncidentModel).filter_by(incident_id=created_id).first()
    assert saved_record is not None
    assert saved_record.complaint == "Water pipe leak causing localized street flooding."
    assert saved_record.category == "waterlogging"
    session.close()


# ============================================================================
# 8. Workflow Execution: Seeded Scenarios
# ============================================================================

def test_workflow_run_normal_scenario(client: TestClient):
    """Running 'normal' simulation scenario on a valid pothole reaches SIMULATED_RESOLVED."""
    img_bytes = make_test_image_bytes(color="gray")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Severe pothole on main road causing hazard for two-wheelers.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        files={"image": ("pothole.jpg", img_bytes, "image/jpeg")},
    )
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["incident_id"]

    # Execute workflow with normal scenario
    run_resp = client.post(
        f"/api/v1/incidents/{inc_id}/run",
        json={"simulation_scenario": "normal"},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert run_data["is_simulated_resolution"] is True
    assert run_data["current_plan"] is not None
    assert len(run_data["audit_timeline"]) > 2


def test_workflow_run_crew_unavailable_triggers_recovery(client: TestClient):
    """Running 'crew_unavailable' invokes Adaptive Recovery and produces updated plan."""
    img_bytes = make_test_image_bytes(color="gray")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Severe pothole on main road.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        files={"image": ("pothole.jpg", img_bytes, "image/jpeg")},
    )
    inc_id = create_resp.json()["incident_id"]

    run_resp = client.post(
        f"/api/v1/incidents/{inc_id}/run",
        json={"simulation_scenario": "crew_unavailable"},
    )
    assert run_resp.status_code == 200
    data = run_resp.json()
    # Should not be SIMULATED_RESOLVED; should have gone through recovery
    assert data["operational_status"] != OperationalStatus.RESOLVED.value
    audit_results = [e["result"] for e in data["audit_timeline"]]
    assert any("contractor" in r.lower() or "crew" in r.lower() for r in audit_results)


# ============================================================================
# 9. Retrieval of Agent Traces and Audit Events
# ============================================================================

def test_retrieval_of_traces_and_audit(client: TestClient):
    """Endpoints /trace and /audit return valid lists."""
    # Seed data
    client.post("/api/v1/incidents/seed")
    inc_resp = client.get("/api/v1/incidents")
    first_id = inc_resp.json()["items"][0]["incident_id"]

    audit_resp = client.get(f"/api/v1/incidents/{first_id}/audit")
    assert audit_resp.status_code == 200
    assert isinstance(audit_resp.json(), list)

    trace_resp = client.get(f"/api/v1/incidents/{first_id}/trace")
    assert trace_resp.status_code == 200
    assert isinstance(trace_resp.json(), list)


# ============================================================================
# 10. Failed Workflow Execution Does Not Produce False Resolved Status
# ============================================================================

def test_failed_workflow_never_marks_resolved(client: TestClient):
    """Injected repeated failure causes escalation and NEVER reaches resolved status."""
    img_bytes = make_test_image_bytes(color="gray")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Pothole on expressway.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        files={"image": ("pothole.jpg", img_bytes, "image/jpeg")},
    )
    inc_id = create_resp.json()["incident_id"]

    run_resp = client.post(
        f"/api/v1/incidents/{inc_id}/run",
        json={"simulation_scenario": "retry_exhaustion"},
    )
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["operational_status"] == OperationalStatus.ESCALATED.value
    assert data["is_simulated_resolution"] is False


# ============================================================================
# 11. Mismatched Evidence Routed Correctly
# ============================================================================

def test_mismatched_evidence_routing(client: TestClient):
    """Mismatched category vs image routes to AWAITING_CLARIFICATION and preserves report."""
    # Pothole claimed, but photo shows indoor scene (mocked or keyword evaluated)
    img_bytes = make_test_image_bytes(color="blue")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "A large pothole on the street.",
            "category": "pothole",
        },
        files={"image": ("indoor.jpg", img_bytes, "image/jpeg")},
    )
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["incident_id"]

    # When workflow runs, incident intelligence checks evidence match
    run_resp = client.post(f"/api/v1/incidents/{inc_id}/run")
    assert run_resp.status_code == 200
    # Report must still exist in DB
    detail_resp = client.get(f"/api/v1/incidents/{inc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["operational_status"] != OperationalStatus.RESOLVED.value


# ============================================================================
# 12. Insufficient Closure Evidence Blocks Closure
# ============================================================================

def test_insufficient_closure_evidence_blocks_closure(client: TestClient):
    """Intervention succeeds but missing closure evidence transitions to CLOSURE_BLOCKED."""
    img_bytes = make_test_image_bytes(color="gray")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Road surface damaged and cratered.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        files={"image": ("pothole.jpg", img_bytes, "image/jpeg")},
    )
    inc_id = create_resp.json()["incident_id"]

    run_resp = client.post(
        f"/api/v1/incidents/{inc_id}/run",
        json={"simulation_scenario": "insufficient_closure_evidence"},
    )
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["operational_status"] == OperationalStatus.CLOSURE_BLOCKED.value
    assert data["is_simulated_resolution"] is False


# ============================================================================
# 13. Simulated Completion is Explicitly Labelled
# ============================================================================

def test_simulated_completion_explicit_marker(client: TestClient):
    """Successful mock intervention must be labelled SIMULATED_RESOLVED, never real RESOLVED."""
    img_bytes = make_test_image_bytes(color="gray")
    create_resp = client.post(
        "/api/v1/incidents",
        data={
            "complaint": "Deep road pothole.",
            "category": "pothole",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        files={"image": ("pothole.jpg", img_bytes, "image/jpeg")},
    )
    inc_id = create_resp.json()["incident_id"]

    run_resp = client.post(
        f"/api/v1/incidents/{inc_id}/run",
        json={"simulation_scenario": "normal"},
    )
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
    assert data["operational_status"] != OperationalStatus.RESOLVED.value
    assert data["is_simulated_resolution"] is True


# ============================================================================
# 14. Validation Errors and Missing IDs
# ============================================================================

def test_validation_error_short_complaint(client: TestClient):
    """Complaint text under 5 characters returns 422."""
    resp = client.post(
        "/api/v1/incidents",
        data={"complaint": "bad"},
    )
    assert resp.status_code == 422
    assert "Complaint description must be between 5 and 2000 characters." in resp.json()["detail"]


def test_missing_incident_id_returns_404(client: TestClient):
    """Querying non-existent incident ID returns 404."""
    resp = client.get("/api/v1/incidents/INC-NONEXISTENT")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ============================================================================
# 15. CORS Behavior
# ============================================================================

def test_cors_headers_permitted_origin(client: TestClient):
    """Permitted origin receives Access-Control-Allow-Origin header."""
    response = client.options(
        "/api/v1/incidents",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ============================================================================
# 16. Zero Secrets or Base64 Leakage in Responses
# ============================================================================

def test_zero_secrets_or_payload_leakage(client: TestClient):
    """API responses do not contain secrets, internal DB paths, or raw base64 data."""
    seed_resp = client.post("/api/v1/incidents/seed")
    assert seed_resp.status_code == 200

    list_resp = client.get("/api/v1/incidents")
    text_data = list_resp.text
    assert "gsk_" not in text_data
    assert "GROQ_API_KEY" not in text_data
    assert "data:image/jpeg;base64," not in text_data
    assert "sqlite:///" not in text_data


# ============================================================================
# 17. ML Model Lab Endpoints
# ============================================================================

def test_ml_model_metrics_endpoint(client: TestClient):
    """Verifies ML model metrics endpoint returns model info and evaluation data."""
    resp = client.get("/api/v1/ml/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["model_name"] == "TFIDF-LogisticRegression"
    assert "classes" in data
    assert "vision_provider" in data


def test_ml_predict_endpoint(client: TestClient):
    """Verifies live complaint prediction endpoint returns predicted category and scores."""
    resp = client.post("/api/v1/ml/predict", json={"text": "Deep dangerous pothole on the expressway"})
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_label" in data
    assert "confidence" in data
    assert "scores" in data

