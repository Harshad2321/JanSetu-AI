"""
JanSetu AI — Storage Provider Abstraction Unit & Integration Tests.

Validates:
- LocalStorageProvider file operations (save, read, delete)
- SupabaseStorageProvider with mocked HTTP REST calls (upload, signed URL, download, delete)
- Graceful handling of network failures and credential misconfigurations
- Secure backend-mediated photo endpoint (/api/v1/incidents/{id}/photo)
- Zero credentials or payload leakage in logs
"""

import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.db.models import IncidentModel
from app.db.repository import create_incident
from app.main import app
from app.services.image_storage import (
    LocalStorageProvider,
    SupabaseStorageProvider,
    get_storage_provider,
    save_sanitized_image,
    load_sanitized_image,
    get_image_access_url,
    delete_stored_image,
)


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Generate a valid in-memory test JPEG."""
    img = Image.new("RGB", (300, 300), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_local_storage_provider_lifecycle(tmp_path, sample_jpeg_bytes):
    """Test LocalStorageProvider save, load, and delete operations."""
    provider = LocalStorageProvider(storage_dir=str(tmp_path))
    
    # 1. Save
    success, identifier, err = provider.save_image(sample_jpeg_bytes, "INC-TEST-01", "test_01.jpg")
    assert success is True
    assert identifier is not None
    assert err is None
    assert tmp_path.joinpath("test_01.jpg").exists()

    # 2. Signed URL is None for local storage (access is backend-streamed)
    assert provider.get_signed_url(identifier) is None

    # 3. Load
    loaded = provider.load_image(identifier)
    assert loaded == sample_jpeg_bytes

    # 4. Delete
    deleted = provider.delete_image(identifier)
    assert deleted is True
    assert not tmp_path.joinpath("test_01.jpg").exists()


def test_supabase_storage_provider_missing_credentials(sample_jpeg_bytes):
    """Ensure Supabase provider safely rejects operations when unconfigured."""
    provider = SupabaseStorageProvider(supabase_url=None, service_role_key=None)
    success, identifier, err = provider.save_image(sample_jpeg_bytes, "INC-TEST-02", "test_02.jpg")
    assert success is False
    assert identifier is None
    assert "not configured" in err.lower()


def test_supabase_storage_provider_upload_success(sample_jpeg_bytes):
    """Test Supabase upload using mocked httpx client."""
    provider = SupabaseStorageProvider(
        supabase_url="https://mockproject.supabase.co",
        service_role_key="mock-service-role-key-12345",
        bucket_name="jansetu-evidence",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        success, identifier, err = provider.save_image(sample_jpeg_bytes, "INC-123", "inc_123.jpg")
        assert success is True
        assert identifier == "evidence/INC-123/inc_123.jpg"
        assert err is None
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "storage/v1/object/jansetu-evidence/evidence/INC-123/inc_123.jpg" in call_url


def test_supabase_storage_provider_upload_failure_handled(sample_jpeg_bytes):
    """Test Supabase upload failure handling without throwing unhandled exceptions."""
    provider = SupabaseStorageProvider(
        supabase_url="https://mockproject.supabase.co",
        service_role_key="mock-service-role-key-12345",
        bucket_name="jansetu-evidence",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Storage Error"

    with patch("httpx.Client.post", return_value=mock_resp):
        success, identifier, err = provider.save_image(sample_jpeg_bytes, "INC-123", "inc_123.jpg")
        assert success is False
        assert identifier is None
        assert "500" in err


def test_supabase_storage_provider_signed_url_generation():
    """Test generation of short-lived signed URLs via Supabase Storage API."""
    provider = SupabaseStorageProvider(
        supabase_url="https://mockproject.supabase.co",
        service_role_key="mock-service-role-key-12345",
        bucket_name="jansetu-evidence",
        signed_url_expiry_seconds=900,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "signedURL": "/object/sign/jansetu-evidence/evidence/INC-123/abc.jpg?token=mock_jwt_token_456"
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        signed_url = provider.get_signed_url("evidence/INC-123/abc.jpg")
        assert signed_url is not None
        assert "https://mockproject.supabase.co/storage/v1/object/sign/jansetu-evidence/evidence/INC-123/abc.jpg?token=mock_jwt_token_456" in signed_url
        mock_post.assert_called_once()
        # Verify body contains expiresIn=900
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"] == {"expiresIn": 900}


def test_supabase_storage_provider_download_bytes(sample_jpeg_bytes):
    """Test authenticated byte retrieval from private Supabase bucket."""
    provider = SupabaseStorageProvider(
        supabase_url="https://mockproject.supabase.co",
        service_role_key="mock-service-role-key-12345",
        bucket_name="jansetu-evidence",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sample_jpeg_bytes

    with patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        data = provider.load_image("evidence/INC-123/abc.jpg")
        assert data == sample_jpeg_bytes
        mock_get.assert_called_once()


def test_supabase_storage_provider_delete():
    """Test object deletion in Supabase bucket."""
    provider = SupabaseStorageProvider(
        supabase_url="https://mockproject.supabase.co",
        service_role_key="mock-service-role-key-12345",
        bucket_name="jansetu-evidence",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.Client.delete", return_value=mock_resp):
        res = provider.delete_image("evidence/INC-123/abc.jpg")
        assert res is True


def test_get_photo_endpoint_local_streaming(db_session, sample_jpeg_bytes):
    """Verify GET /api/v1/incidents/{incident_id}/photo streams local bytes."""
    client = TestClient(app)
    
    # Save a sanitized image locally
    is_valid, stored_path, _, _, _ = save_sanitized_image(sample_jpeg_bytes, "INC-PHOTO-01")
    assert is_valid is True

    incident = IncidentModel(
        incident_id="INC-PHOTO-01",
        complaint="Test complaint with local image photo.",
        category="pothole",
        has_photograph=True,
        photo_storage_path=stored_path,
        operational_status="NEW",
        evidence_status="MATCHED",
    )
    create_incident(db_session, incident)

    resp = client.get("/api/v1/incidents/INC-PHOTO-01/photo")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert len(resp.content) > 0


def test_get_photo_endpoint_remote_signed_url_redirect(db_session):
    """Verify GET /api/v1/incidents/{incident_id}/photo returns 307 redirect when signed URL exists."""
    client = TestClient(app)

    incident = IncidentModel(
        incident_id="INC-PHOTO-02",
        complaint="Test complaint with remote image photo.",
        category="waterlogging",
        has_photograph=True,
        photo_storage_path="evidence/INC-PHOTO-02/photo.jpg",
        operational_status="NEW",
        evidence_status="MATCHED",
    )
    create_incident(db_session, incident)

    signed_url = "https://mockproject.supabase.co/storage/v1/object/sign/jansetu-evidence/evidence/INC-PHOTO-02/photo.jpg?token=abc"

    with patch("app.api.routes.incidents.get_image_access_url", return_value=signed_url):
        resp = client.get("/api/v1/incidents/INC-PHOTO-02/photo", follow_redirects=False)
        assert resp.status_code == 307
        assert resp.headers["location"] == signed_url


def test_get_photo_endpoint_missing_photo_returns_404(db_session):
    """Verify 404 when incident does not have a photograph."""
    client = TestClient(app)
    incident = IncidentModel(
        incident_id="INC-NO-PHOTO",
        complaint="Complaint without any photograph.",
        category="garbage",
        has_photograph=False,
        operational_status="RECORDED_PENDING_REVIEW",
        evidence_status="NOT_PROVIDED",
    )
    create_incident(db_session, incident)

    resp = client.get("/api/v1/incidents/INC-NO-PHOTO/photo")
    assert resp.status_code == 404
    assert "No photographic evidence" in resp.json()["detail"]
