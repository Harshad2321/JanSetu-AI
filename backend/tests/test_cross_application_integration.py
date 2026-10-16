"""
JanSetu AI — REST API Client Integration Tests.

Verifies that HTTP client wrappers interact reliably with
the underlying FastAPI service contracts, preserve evidence/operational status
decoupling, enforce deterministic closure verification, and handle failures without
leaking credentials or raw payloads.
"""

import io
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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


class BackendConnectionError(Exception):
    """Raised when the FastAPI backend cannot be reached."""
    pass


class BackendAPIError(Exception):
    """Raised when the FastAPI backend returns an HTTP error."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class JanSetuAPIClient:
    """HTTP client wrapper for the JanSetu AI FastAPI REST service."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _handle_response(self, response: httpx.Response) -> Any:
        if not response.is_success:
            error_msg = f"Request failed with status {response.status_code}"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("detail") or err_data.get("error") or error_msg
            except Exception:
                error_msg = response.text or error_msg
            raise BackendAPIError(response.status_code, str(error_msg))
        return response.json()

    def get_health(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/health")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(
                f"Cannot connect to JanSetu backend at {self.base_url}. "
                f"Ensure FastAPI is running: {str(exc)}"
            )


@pytest.fixture
def cross_test_env(tmp_path: Path):
    """Isolated test environment with dedicated SQLite database and upload storage."""
    db_file = tmp_path / "cross_test.db"
    storage_dir = tmp_path / "cross_uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)

    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    old_storage = settings.STORAGE_DIR
    old_db_url = settings.DATABASE_URL
    settings.STORAGE_DIR = str(storage_dir)
    settings.DATABASE_URL = test_db_url

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "storage_dir": storage_dir,
    }

    app.dependency_overrides.clear()
    settings.STORAGE_DIR = old_storage
    settings.DATABASE_URL = old_db_url


class MockTransportClient(JanSetuAPIClient):
    """
    Subclass of JanSetuAPIClient that dispatches directly to FastAPI's TestClient
    to verify client logic without requiring a live socket port during test runs.
    """
    def __init__(self, test_client: TestClient):
        super().__init__(base_url="http://testserver")
        self._test_client = test_client

    def get_health(self):
        res = self._test_client.get("/health")
        return self._handle_test_response(res)

    def get_dashboard_summary(self):
        res = self._test_client.get("/api/v1/dashboard/summary")
        return self._handle_test_response(res)

    def get_incidents(self, category=None, status=None, limit=50, offset=0):
        params = {"limit": limit, "offset": offset}
        if category and category != "all":
            params["category"] = category
        if status and status != "all":
            params["status"] = status
        res = self._test_client.get("/api/v1/incidents", params=params)
        return self._handle_test_response(res)

    def get_incident(self, incident_id: str):
        res = self._test_client.get(f"/api/v1/incidents/{incident_id}")
        return self._handle_test_response(res)

    def submit_incident(
        self,
        complaint: str,
        category: str = "pothole",
        latitude=None,
        longitude=None,
        accuracy_meters=None,
        location_source="MANUAL_ENTRY",
        is_user_confirmed=True,
        image_bytes=None,
        image_filename=None,
    ):
        data = {
            "complaint": complaint,
            "category": category,
            "location_source": location_source,
            "is_user_confirmed": str(is_user_confirmed).lower(),
        }
        if latitude is not None:
            data["latitude"] = str(latitude)
        if longitude is not None:
            data["longitude"] = str(longitude)
        if accuracy_meters is not None:
            data["accuracy_meters"] = str(accuracy_meters)

        files = None
        if image_bytes and len(image_bytes) > 0:
            filename = image_filename or "evidence.jpg"
            files = {"image": (filename, image_bytes, "image/jpeg")}

        res = self._test_client.post("/api/v1/incidents", data=data, files=files)
        return self._handle_test_response(res)

    def run_workflow(self, incident_id: str, simulation_scenario=None, failure_reason=None):
        payload = {}
        if simulation_scenario:
            payload["simulation_scenario"] = simulation_scenario
        if failure_reason:
            payload["failure_reason"] = failure_reason
        res = self._test_client.post(f"/api/v1/incidents/{incident_id}/run", json=payload)
        return self._handle_test_response(res)

    def simulate_scenario(self, incident_id: str, scenario: str):
        res = self._test_client.post(f"/api/v1/incidents/{incident_id}/simulate", json={"scenario": scenario})
        return self._handle_test_response(res)

    def get_audit(self, incident_id: str):
        res = self._test_client.get(f"/api/v1/incidents/{incident_id}/audit")
        return self._handle_test_response(res)

    def get_traces(self, incident_id: str):
        res = self._test_client.get(f"/api/v1/incidents/{incident_id}/trace")
        return self._handle_test_response(res)

    def seed_demonstration_data(self):
        res = self._test_client.post("/api/v1/incidents/seed")
        return self._handle_test_response(res)

    def _handle_test_response(self, response):
        if response.status_code >= 400:
            detail = response.json().get("detail", "Error") if response.headers.get("content-type") == "application/json" else response.text
            raise BackendAPIError(response.status_code, str(detail))
        return response.json()


def make_test_jpg(color="gray") -> bytes:
    img = Image.new("RGB", (200, 150), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ============================================================================
# Integration Tests
# ============================================================================

def test_shared_api_creation_and_retrieval(cross_test_env):
    """Test incident creation and retrieval using the API client against FastAPI."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)

        # 1. Create with photograph
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Severe roadway collapse across arterial highway.",
            category="pothole",
            latitude=19.0760,
            longitude=72.8777,
            image_bytes=img_bytes,
            image_filename="pothole.jpg",
        )
        assert inc["incident_id"].startswith("INC-")
        assert inc["has_photograph"] is True
        assert inc["category"] == "pothole"

        # 2. Retrieve detail
        detail = client.get_incident(inc["incident_id"])
        assert detail["incident_id"] == inc["incident_id"]
        assert detail["complaint"] == "Severe roadway collapse across arterial highway."
        assert detail["location"]["latitude"] == 19.0760


def test_incidents_without_photos_preserved(cross_test_env):
    """Incidents submitted without photographs are preserved as RECORDED_PENDING_REVIEW."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        inc = client.submit_incident(
            complaint="Overflowing municipal garbage container attracting stray animals.",
            category="garbage",
            image_bytes=None,
        )
        assert inc["has_photograph"] is False
        assert inc["evidence_status"] == EvidenceOutcome.NOT_PROVIDED.value
        assert inc["operational_status"] == OperationalStatus.RECORDED_PENDING_REVIEW.value


def test_evidence_and_operational_statuses_remain_distinct(cross_test_env):
    """Evidence status (visual match) must remain decoupled from operational resolution."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Large water stagnation pooling around school entrance.",
            category="waterlogging",
            image_bytes=img_bytes,
        )
        # Even with an image attached, operational status must never be RESOLVED
        assert inc["operational_status"] != OperationalStatus.RESOLVED.value
        assert inc["operational_status"] != OperationalStatus.SIMULATED_RESOLVED.value


def test_dashboard_summary_traces_and_audit_retrieval(cross_test_env):
    """Client retrieves real dashboard metrics, audit timeline, and traces."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)

        # Seed demonstration cases
        seed_res = client.seed_demonstration_data()
        assert len(seed_res["seeded_ids"]) >= 1

        # Check dashboard summary
        summary = client.get_dashboard_summary()
        assert summary["total_incidents"] >= len(seed_res["seeded_ids"])
        assert "pothole" in summary["categories"]

        # Check audit trail retrieval
        target_id = seed_res["seeded_ids"][0]
        audit = client.get_audit(target_id)
        assert isinstance(audit, list)
        assert len(audit) >= 1

        # Check trace retrieval
        traces = client.get_traces(target_id)
        assert isinstance(traces, list)


def test_crew_unavailability_invokes_adaptive_recovery(cross_test_env):
    """Scenario 'crew_unavailable' mutates the resolution plan and engages Adaptive Recovery."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Deep trench across transit corridor.",
            category="pothole",
            image_bytes=img_bytes,
        )
        sim_res = client.simulate_scenario(inc["incident_id"], "crew_unavailable")

        # Must not be successfully resolved
        assert sim_res["operational_status"] != OperationalStatus.RESOLVED.value
        assert sim_res["is_simulated_resolution"] is False

        # Verify audit records record contractor/recovery adaptation
        audit = client.get_audit(inc["incident_id"])
        audit_results = [e.get("result", "").lower() for e in audit]
        assert any("contractor" in r or "crew" in r or "recovery" in r for r in audit_results)


def test_insufficient_closure_evidence_blocks_closure(cross_test_env):
    """Missing post-repair verification photo deterministically blocks closure gate."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Roadway cavity requiring cold-mix fill.",
            category="pothole",
            image_bytes=img_bytes,
        )
        sim_res = client.simulate_scenario(inc["incident_id"], "insufficient_closure_evidence")
        assert sim_res["operational_status"] == OperationalStatus.CLOSURE_BLOCKED.value
        assert sim_res["is_simulated_resolution"] is False


def test_normal_scenario_explicitly_labeled_as_simulated(cross_test_env):
    """Successful normal execution must be marked as SIMULATED_RESOLVED, never real RESOLVED."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Hazardous crater on arterial roadway.",
            category="pothole",
            image_bytes=img_bytes,
        )
        sim_res = client.simulate_scenario(inc["incident_id"], "normal")
        assert sim_res["operational_status"] == OperationalStatus.SIMULATED_RESOLVED.value
        assert sim_res["is_simulated_resolution"] is True
        assert sim_res["operational_status"] != OperationalStatus.RESOLVED.value


def test_backend_disconnection_informative_error():
    """Client raises BackendConnectionError with explanatory guidance when server is offline."""
    offline_client = JanSetuAPIClient(base_url="http://127.0.0.1:59999", timeout=1.0)
    with pytest.raises(BackendConnectionError) as exc_info:
        offline_client.get_health()
    assert "Cannot connect to JanSetu backend" in str(exc_info.value)


def test_zero_credential_leakage(cross_test_env):
    """API responses and audit records never return API keys or raw credentials."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        health = client.get_health()
        assert "api_key" not in str(health).lower()
        assert "groq_api_key" not in str(health).lower()

        # Check incidents response
        seed_res = client.seed_demonstration_data()
        inc_id = seed_res["seeded_ids"][0]
        inc = client.get_incident(inc_id)
        inc_str = str(inc).lower()
        assert "groq_api_key" not in inc_str
        assert "gsk_" not in inc_str  # Groq key prefix


def test_photo_provenance_marker_enforcement(cross_test_env):
    """Ensure photographic evidence analysis contains an explicit provenance marker."""
    with TestClient(app) as test_client:
        client = MockTransportClient(test_client)
        img_bytes = make_test_jpg()
        inc = client.submit_incident(
            complaint="Pothole on expressway lane.",
            category="pothole",
            image_bytes=img_bytes,
        )
        detail = client.get_incident(inc["incident_id"])
        ev_analysis = detail.get("evidence_analysis") or {}
        # Must have provenance field
        assert "provenance" in ev_analysis
        assert ev_analysis["provenance"] in [
            "GROQ_VISION",
            "DETERMINISTIC_FALLBACK",
            "SEEDED_SIMULATION",
            "INTAKE_SANITIZED_PRELIMINARY",
            "NOT_PROVIDED",
        ]
