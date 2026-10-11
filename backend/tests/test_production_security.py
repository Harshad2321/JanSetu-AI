"""
JanSetu AI — Production Security & Safe Exception Handling Tests.

Validates:
- Demo mode protection on unauthenticated simulation & seed endpoints
- 413 Payload Too Large on oversized photograph uploads
- Safe 500 generic error handler that conceals internal stack traces and paths
- Health check liveness and environment visibility without credential exposure
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.models import IncidentModel
from app.db.repository import create_incident
from app.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


def test_production_demo_mode_disabled_blocks_simulation(test_client, db_session):
    """Ensure simulation endpoint returns 403 when DEMO_MODE=False in production."""
    incident = IncidentModel(
        incident_id="INC-SEC-01",
        complaint="Civic incident for security testing.",
        category="pothole",
        operational_status="NEW",
    )
    create_incident(db_session, incident)

    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "DEMO_MODE", False):
        resp = test_client.post(
            "/api/v1/incidents/INC-SEC-01/simulate",
            json={"scenario": "normal"},
        )
        assert resp.status_code == 403
        assert "disabled in production" in resp.json()["detail"].lower()


def test_production_demo_mode_disabled_blocks_seeding(test_client):
    """Ensure seeding endpoint returns 403 when DEMO_MODE=False in production."""
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "DEMO_MODE", False):
        resp = test_client.post("/api/v1/incidents/seed")
        assert resp.status_code == 403
        assert "disabled in production" in resp.json()["detail"].lower()


def test_oversized_upload_rejected_with_413(test_client):
    """Ensure uploads exceeding MAX_UPLOAD_SIZE_MB receive HTTP 413."""
    # Create fake 15MB payload (exceeding 10MB limit)
    oversized_data = b"0" * (11 * 1024 * 1024)

    files = {
        "image": ("large.jpg", oversized_data, "image/jpeg")
    }
    data = {
        "complaint": "Complaint accompanied by excessively large photograph.",
        "category": "pothole",
    }

    resp = test_client.post("/api/v1/incidents", data=data, files=files)
    assert resp.status_code == 413
    assert "exceeds maximum allowed size" in resp.json()["detail"].lower()


def test_health_endpoints_do_not_leak_secrets(test_client):
    """Verify /health and root probes return operational status without leaking credentials."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    
    # Ensure no tokens or secret keys present in health payload
    resp_text = resp.text.lower()
    assert "gsk_" not in resp_text
    assert "secret" not in resp_text
    assert "password" not in resp_text
    assert "service_role" not in resp_text


def test_generic_exception_handler_masks_internals():
    """Verify unhandled 500 error returns generic safe message without stack traces."""
    client = TestClient(app, raise_server_exceptions=False)
    with patch("app.api.routes.incidents.list_incidents", side_effect=RuntimeError("Database socket /var/run/secret failed")):
        resp = client.get("/api/v1/incidents")
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"] == "Internal Server Error"
        assert "/var/run/secret" not in data["detail"]
        assert "RuntimeError" not in data["detail"]
