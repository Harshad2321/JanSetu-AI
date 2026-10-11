"""
JanSetu AI — Streamlit Companion REST API Client.

Interfaces with the FastAPI backend using structured error envelopes,
bounded timeouts, and native multipart file upload support.
"""

from typing import Any, Dict, List, Optional
import httpx
from streamlit_app.config import API_BASE_URL, DEFAULT_TIMEOUT_SECONDS


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

    def __init__(self, base_url: str = API_BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS):
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

    def get_dashboard_summary(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/api/v1/dashboard/summary")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def get_incidents(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if category and category != "all":
            params["category"] = category
        if status and status != "all":
            params["status"] = status

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/api/v1/incidents", params=params)
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/api/v1/incidents/{incident_id}")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def submit_incident(
        self,
        complaint: str,
        category: str = "pothole",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        accuracy_meters: Optional[float] = None,
        location_source: str = "MANUAL_ENTRY",
        is_user_confirmed: bool = True,
        image_bytes: Optional[bytes] = None,
        image_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            files = {"image": (filename, image_bytes, content_type)}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    f"{self.base_url}/api/v1/incidents",
                    data=data,
                    files=files,
                )
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def run_workflow(
        self,
        incident_id: str,
        simulation_scenario: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if simulation_scenario:
            payload["simulation_scenario"] = simulation_scenario
        if failure_reason:
            payload["failure_reason"] = failure_reason

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    f"{self.base_url}/api/v1/incidents/{incident_id}/run",
                    json=payload,
                )
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def simulate_scenario(self, incident_id: str, scenario: str) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(
                    f"{self.base_url}/api/v1/incidents/{incident_id}/simulate",
                    json={"scenario": scenario},
                )
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def get_audit(self, incident_id: str) -> List[Dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/api/v1/incidents/{incident_id}/audit")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def get_traces(self, incident_id: str) -> List[Dict[str, Any]]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(f"{self.base_url}/api/v1/incidents/{incident_id}/trace")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")

    def seed_demonstration_data(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/api/v1/incidents/seed")
                return self._handle_response(res)
        except httpx.RequestError as exc:
            raise BackendConnectionError(f"Backend unreachable at {self.base_url}: {str(exc)}")
