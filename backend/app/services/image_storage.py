"""
JanSetu AI — Secure Image Storage Service & Provider Abstraction.

Supports:
- Local filesystem storage for development, CI, and isolated tests.
- Supabase Storage (private bucket) for production deployment.
- Strict EXIF metadata stripping and resolution bounding before persistence.
- Zero public bucket exposures.
- Backend-mediated photo access via short-lived signed URLs (Supabase) or streaming (Local).
- Unguessable storage paths without citizen PII.
- Zero credential or payload leakage in logs.
"""

from __future__ import annotations

import logging
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import httpx

from app.config import settings
from app.core.image_processing import (
    sanitize_image_bytes,
    sanitize_base64_image,
    SanitizedImageResult,
)
from app.schemas.incident import ImageQualityAssessment

logger = logging.getLogger("jansetu.image_storage")


# ============================================================================
# Storage Provider Interface
# ============================================================================

class StorageProvider(ABC):
    """Abstract storage interface for civic incident evidence persistence."""

    @abstractmethod
    def save_image(
        self,
        image_bytes: bytes,
        incident_id: str,
        filename: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Persist sanitized image bytes.
        Returns: (success, storage_identifier, error_message)
        """
        pass

    @abstractmethod
    def load_image(self, storage_identifier: str) -> Optional[bytes]:
        """Retrieve sanitized image bytes."""
        pass

    @abstractmethod
    def get_signed_url(self, storage_identifier: str) -> Optional[str]:
        """Generate a short-lived signed URL for private access, or None if local."""
        pass

    @abstractmethod
    def delete_image(self, storage_identifier: str) -> bool:
        """Delete stored image artifact for compliance and retention."""
        pass


# ============================================================================
# Local Filesystem Storage Provider (Dev / Test)
# ============================================================================

class LocalStorageProvider(StorageProvider):
    """Stores sanitized photographs in a non-public local directory."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or settings.STORAGE_DIR)

    def _ensure_dir(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_image(
        self,
        image_bytes: bytes,
        incident_id: str,
        filename: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        try:
            self._ensure_dir()
            target_path = self.storage_dir / filename
            with open(target_path, "wb") as f:
                f.write(image_bytes)
            logger.info("Privately stored sanitized image locally for %s: %s", incident_id, filename)
            return True, str(target_path), None
        except Exception as exc:
            logger.error("Failed to write image to local disk for incident %s: %s", incident_id, str(exc))
            return False, None, "Failed to persist sanitized photograph to local storage."

    def load_image(self, storage_identifier: str) -> Optional[bytes]:
        if not storage_identifier or not os.path.exists(storage_identifier):
            return None
        try:
            with open(storage_identifier, "rb") as f:
                return f.read()
        except Exception as exc:
            logger.error("Failed to read local image at %s: %s", storage_identifier, str(exc))
            return None

    def get_signed_url(self, storage_identifier: str) -> Optional[str]:
        # Local filesystem storage uses backend-mediated streaming; no signed URL
        return None

    def delete_image(self, storage_identifier: str) -> bool:
        if not storage_identifier or not os.path.exists(storage_identifier):
            return False
        try:
            os.remove(storage_identifier)
            logger.info("Deleted local image at %s", storage_identifier)
            return True
        except Exception as exc:
            logger.error("Failed to delete local image at %s: %s", storage_identifier, str(exc))
            return False


# ============================================================================
# Supabase Private Storage Provider (Production)
# ============================================================================

class SupabaseStorageProvider(StorageProvider):
    """
    Stores sanitized photographs in a private Supabase Storage bucket.
    
    Guarantees:
    - Never uses public bucket URLs.
    - Uses backend service-role key exclusively (never in frontend).
    - Unique object path namespaced under `evidence/{incident_id}/{uuid}.jpg` (no PII).
    - Short-lived signed URLs for retrieval (15 minutes).
    - Failure during upload returns clean error and aborts creation without broken state.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        signed_url_expiry_seconds: Optional[int] = None,
    ):
        self.supabase_url = (supabase_url or settings.SUPABASE_URL or "").rstrip("/")
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.bucket_name = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "jansetu-evidence"
        self.signed_url_expiry = signed_url_expiry_seconds or settings.SUPABASE_SIGNED_URL_EXPIRY_SECONDS or 900

    def _headers(self) -> dict:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    def _validate_config(self) -> Optional[str]:
        if not self.supabase_url:
            return "SUPABASE_URL is not configured."
        if not self.service_role_key:
            return "SUPABASE_SERVICE_ROLE_KEY is not configured."
        return None

    def save_image(
        self,
        image_bytes: bytes,
        incident_id: str,
        filename: str,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        err = self._validate_config()
        if err:
            logger.error("Supabase Storage configuration error: %s", err)
            return False, None, f"Remote storage misconfigured: {err}"

        # Clean object path without citizen PII: evidence/<incident_id>/<filename>
        object_path = f"evidence/{incident_id}/{filename}"
        upload_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{object_path}"

        headers = self._headers()
        headers["Content-Type"] = "image/jpeg"
        headers["x-upsert"] = "true"

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(upload_url, headers=headers, content=image_bytes)
                if res.status_code in (200, 201):
                    logger.info("Privately uploaded image to Supabase bucket '%s': %s", self.bucket_name, object_path)
                    return True, object_path, None
                else:
                    logger.error(
                        "Supabase storage upload failed with status %d: %s",
                        res.status_code,
                        res.text[:200],
                    )
                    return False, None, f"Supabase storage rejected upload with status {res.status_code}."
        except Exception as exc:
            logger.error("Supabase storage upload network error: %s", str(exc))
            return False, None, "Remote storage network connection error."

    def load_image(self, storage_identifier: str) -> Optional[bytes]:
        """Download image bytes from private Supabase bucket via authenticated endpoint."""
        err = self._validate_config()
        if err or not storage_identifier:
            return None

        # Supabase authenticated object download URL
        object_path = storage_identifier.lstrip("/")
        download_url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{object_path}"

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(download_url, headers=self._headers())
                if res.status_code == 200:
                    return res.content
                logger.warning("Supabase load_image failed (HTTP %d) for %s", res.status_code, object_path)
                return None
        except Exception as exc:
            logger.error("Supabase storage download error for %s: %s", storage_identifier, str(exc))
            return None

    def get_signed_url(self, storage_identifier: str) -> Optional[str]:
        """Generate a short-lived signed URL for secure backend-mediated access."""
        err = self._validate_config()
        if err or not storage_identifier:
            return None

        object_path = storage_identifier.lstrip("/")
        sign_url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket_name}/{object_path}"

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    sign_url,
                    headers=self._headers(),
                    json={"expiresIn": self.signed_url_expiry},
                )
                if res.status_code == 200:
                    data = res.json()
                    signed_path = data.get("signedURL", "")
                    if signed_path.startswith("http://") or signed_path.startswith("https://"):
                        return signed_path
                    return f"{self.supabase_url}/storage/v1{signed_path}"
                logger.warning("Supabase get_signed_url returned HTTP %d for %s", res.status_code, object_path)
                return None
        except Exception as exc:
            logger.error("Failed to generate Supabase signed URL: %s", str(exc))
            return None

    def delete_image(self, storage_identifier: str) -> bool:
        """Delete an object from the private Supabase bucket."""
        err = self._validate_config()
        if err or not storage_identifier:
            return False

        object_path = storage_identifier.lstrip("/")
        delete_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{object_path}"

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.delete(delete_url, headers=self._headers())
                if res.status_code in (200, 204):
                    logger.info("Deleted object %s from Supabase bucket '%s'", object_path, self.bucket_name)
                    return True
                logger.warning("Failed to delete object from Supabase (HTTP %d)", res.status_code)
                return False
        except Exception as exc:
            logger.error("Supabase storage delete error: %s", str(exc))
            return False


# ============================================================================
# Storage Factory & High-Level API
# ============================================================================

def get_storage_provider() -> StorageProvider:
    """Factory selecting the active StorageProvider based on configuration."""
    provider_type = settings.STORAGE_PROVIDER.strip().lower()
    if provider_type == "supabase":
        return SupabaseStorageProvider()
    return LocalStorageProvider()


def save_sanitized_image(
    raw_bytes: bytes,
    incident_id: str,
) -> Tuple[bool, Optional[str], Optional[bytes], Optional[str], ImageQualityAssessment]:
    """
    Sanitize and privately store raw uploaded image bytes.

    Returns:
    - (is_valid, storage_identifier, sanitized_bytes, error_message, quality_assessment)

    Guarantees:
    - Never stores raw unsanitized or unverified bytes.
    - Strips all EXIF metadata (camera serial, GPS, timestamps).
    - Persists using configured StorageProvider (Local or Supabase).
    - Zero sensitive payload logging.
    """
    # 1. Sanitize image bytes through Pillow pipeline
    result: SanitizedImageResult = sanitize_image_bytes(raw_bytes)
    if not result.is_valid or not result.sanitized_bytes:
        logger.warning(
            "Image sanitization rejected upload for incident %s: %s (Quality: %s)",
            incident_id,
            result.error_message,
            result.quality_assessment,
        )
        return False, None, None, result.error_message, result.quality_assessment

    # 2. Generate private unguessable storage filename
    unique_suffix = uuid.uuid4().hex[:12]
    filename = f"{incident_id}_{unique_suffix}.jpg"

    provider = get_storage_provider()
    success, identifier, error_msg = provider.save_image(
        image_bytes=result.sanitized_bytes,
        incident_id=incident_id,
        filename=filename,
    )

    if not success:
        return False, None, None, error_msg or "Failed to persist sanitized photograph.", ImageQualityAssessment.CORRUPTED

    return True, identifier, result.sanitized_bytes, None, result.quality_assessment


def save_sanitized_base64(
    base64_str: str,
    incident_id: str,
) -> Tuple[bool, Optional[str], Optional[bytes], Optional[str], ImageQualityAssessment]:
    """Sanitize and store an incoming Base64 image payload."""
    result = sanitize_base64_image(base64_str)
    if not result.is_valid or not result.sanitized_bytes:
        return False, None, None, result.error_message, result.quality_assessment

    unique_suffix = uuid.uuid4().hex[:12]
    filename = f"{incident_id}_{unique_suffix}.jpg"

    provider = get_storage_provider()
    success, identifier, error_msg = provider.save_image(
        image_bytes=result.sanitized_bytes,
        incident_id=incident_id,
        filename=filename,
    )

    if not success:
        return False, None, None, error_msg or "Failed to persist sanitized photograph.", ImageQualityAssessment.CORRUPTED

    return True, identifier, result.sanitized_bytes, None, result.quality_assessment


def load_sanitized_image(storage_identifier: Optional[str]) -> Optional[bytes]:
    """
    Safely retrieve stored sanitized image bytes for workflow processing.
    Supports both local filesystem paths and remote object storage identifiers.
    """
    if not storage_identifier:
        return None

    # If it is a direct local file path that exists, load directly
    if os.path.exists(storage_identifier):
        try:
            with open(storage_identifier, "rb") as f:
                return f.read()
        except Exception as exc:
            logger.error("Failed to read local file %s: %s", storage_identifier, str(exc))

    provider = get_storage_provider()
    return provider.load_image(storage_identifier)


def get_image_access_url(storage_identifier: Optional[str]) -> Optional[str]:
    """
    Get a short-lived signed URL for the image if using remote storage.
    Returns None if using local storage (which streams directly).
    """
    if not storage_identifier:
        return None
    provider = get_storage_provider()
    return provider.get_signed_url(storage_identifier)


def delete_stored_image(storage_identifier: Optional[str]) -> bool:
    """Delete a stored image artifact."""
    if not storage_identifier:
        return False
    provider = get_storage_provider()
    return provider.delete_image(storage_identifier)
