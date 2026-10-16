"""
JanSetu AI — Vision Provider & Classification Interface (Phase 4, P4.4).

Follows strict tracker & academic requirements:
1. Works 100% offline without Groq credentials, without network connection, and with Ollama off.
2. Prefers explicitly configured local Ollama vision-language model for local demonstration.
3. Keeps existing Groq vision support as an optional, explicitly configured provider.
4. Never automatically fabricates visual classification when the selected provider is unavailable.
5. All images are sanitized before being passed to any vision model.
6. Returns {label, confidence, model, available, error}.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.image_processing import (
    sanitize_base64_image,
    sanitize_image_bytes,
)
from app.schemas.incident import ModelPrediction

logger = logging.getLogger("jansetu.ml.vision")

VALID_CATEGORIES = ["pothole", "waterlogging", "garbage"]

DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5-vl")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")


class VisionClassificationResult(BaseModel):
    """Output contract for civic vision analysis."""
    model_config = ConfigDict(use_enum_values=True)

    label: Optional[str] = Field(default=None, description="Visual category or None if unavailable")
    confidence: Optional[float] = Field(default=None, description="Model-reported confidence (not calibrated) or None")
    model: str = Field(default="unavailable", description="Model identifier")
    available: bool = Field(default=False, description="True only if provider produced an actual prediction")
    error: Optional[str] = Field(default=None, description="Safe informative reason without credential leakage")
    provider: str = Field(default="none", description="ollama, groq, or none")
    is_synthetic: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_model_prediction(self, incident_id: str = "") -> ModelPrediction:
        """Convert to standard persistence ModelPrediction record."""
        return ModelPrediction(
            prediction_id=f"pred_vis_{uuid.uuid4().hex[:12]}",
            incident_id=incident_id or f"inc_vis_{uuid.uuid4().hex[:8]}",
            task_type="vision",
            predicted_label=self.label or "",
            scores={self.label: float(self.confidence)} if (self.label and self.confidence is not None) else {},
            confidence=float(self.confidence) if self.confidence is not None else 0.0,
            model_name=self.model,
            model_version="v1.0.0",
            available=self.available,
            fallback_provenance="direct" if self.available else "unavailable",
            is_synthetic=self.is_synthetic,
            created_at=self.created_at,
        )


class BaseVisionProvider(ABC):
    """Abstract interface for civic vision inference."""

    @abstractmethod
    def classify(self, sanitized_image_b64: str) -> VisionClassificationResult:
        """Analyze sanitized image and return typed VisionClassificationResult."""
        pass


class OllamaVisionProvider(BaseVisionProvider):
    """Local Ollama vision provider using local models (qwen2.5-vl, llama3.2-vision)."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 3.0,
        http_client: Optional[httpx.Client] = None,
    ):
        self.host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.timeout = timeout
        self._client = http_client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def classify(self, sanitized_image_b64: str) -> VisionClassificationResult:
        """Sends sanitized image to local Ollama instance."""
        url = f"{self.host}/api/generate"
        prompt = (
            "You are a civic infrastructure classifier. Examine this image and classify the primary issue into exactly one of: "
            "pothole, waterlogging, garbage. "
            "Respond in strictly valid JSON format: {\"category\": \"<pothole|waterlogging|garbage>\", \"confidence\": <float 0.0-1.0>}."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [sanitized_image_b64],
            "stream": False,
            "format": "json",
        }

        try:
            client = self._get_client()
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning("Ollama vision returned HTTP %s", resp.status_code)
                return VisionClassificationResult(
                    label=None,
                    confidence=None,
                    model=self.model,
                    available=False,
                    error=f"Ollama returned HTTP status {resp.status_code}",
                    provider="ollama",
                )

            data = resp.json()
            raw_response = data.get("response", "")
            if not raw_response:
                return VisionClassificationResult(
                    label=None,
                    confidence=None,
                    model=self.model,
                    available=False,
                    error="Empty response received from Ollama model",
                    provider="ollama",
                )

            # Parse structured JSON from model response
            parsed = json.loads(raw_response)
            category = str(parsed.get("category", "")).strip().lower()
            conf = parsed.get("confidence")

            if category not in VALID_CATEGORIES:
                return VisionClassificationResult(
                    label=None,
                    confidence=None,
                    model=self.model,
                    available=False,
                    error=f"Model output category '{category}' is not one of {VALID_CATEGORIES}",
                    provider="ollama",
                )

            conf_val = float(conf) if conf is not None else 0.5
            conf_val = max(0.0, min(1.0, conf_val))

            return VisionClassificationResult(
                label=category,
                confidence=round(conf_val, 4),
                model=self.model,
                available=True,
                error=None,
                provider="ollama",
            )

        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.info("Ollama service unreachable at %s: %s", self.host, type(exc).__name__)
            return VisionClassificationResult(
                label=None,
                confidence=None,
                model=self.model,
                available=False,
                error=f"Ollama vision service unreachable at {self.host}",
                provider="ollama",
            )
        except json.JSONDecodeError:
            logger.warning("Failed to decode JSON from Ollama response")
            return VisionClassificationResult(
                label=None,
                confidence=None,
                model=self.model,
                available=False,
                error="Malformed non-JSON output from vision model",
                provider="ollama",
            )
        except Exception as exc:
            # Safe exception logging without exposing credentials or internal paths
            logger.error("Ollama vision call failed: %s", type(exc).__name__)
            return VisionClassificationResult(
                label=None,
                confidence=None,
                model=self.model,
                available=False,
                error=f"Vision provider error: {type(exc).__name__}",
                provider="ollama",
            )


class GroqVisionProvider(BaseVisionProvider):
    """Optional Groq vision provider for cloud-enabled environments."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("GROQ_API_KEY")
        self.model = model or DEFAULT_GROQ_MODEL

    def classify(self, sanitized_image_b64: str) -> VisionClassificationResult:
        """Sends sanitized image to Groq VLM if API key is explicitly configured."""
        if not self.api_key or not self.api_key.strip():
            return VisionClassificationResult(
                label=None,
                confidence=None,
                model=self.model,
                available=False,
                error="GROQ_API_KEY not configured or empty",
                provider="groq",
            )

        try:
            from groq import Groq

            client = Groq(api_key=self.api_key, timeout=10.0)
            data_uri = f"data:image/jpeg;base64,{sanitized_image_b64}"

            prompt = (
                "You are a civic vision classifier. Classify this infrastructure image into exactly one category: "
                "pothole, waterlogging, garbage. "
                "Return strictly valid JSON: {\"category\": \"<pothole|waterlogging|garbage>\", \"confidence\": <float 0.0-1.0>}."
            )

            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            content = completion.choices[0].message.content or ""
            parsed = json.loads(content)
            cat = str(parsed.get("category", "")).strip().lower()
            conf = parsed.get("confidence", 0.5)

            if cat not in VALID_CATEGORIES:
                return VisionClassificationResult(
                    label=None,
                    confidence=None,
                    model=self.model,
                    available=False,
                    error=f"Groq vision returned invalid category: {cat}",
                    provider="groq",
                )

            return VisionClassificationResult(
                label=cat,
                confidence=round(float(conf), 4),
                model=self.model,
                available=True,
                error=None,
                provider="groq",
            )
        except Exception as exc:
            # Mask API keys and sensitive credentials in error message
            safe_error = f"Groq vision call failed ({type(exc).__name__})"
            logger.warning("Groq vision error: %s", safe_error)
            return VisionClassificationResult(
                label=None,
                confidence=None,
                model=self.model,
                available=False,
                error=safe_error,
                provider="groq",
            )


def get_vision_provider(
    provider_name: Optional[str] = None,
    http_client: Optional[httpx.Client] = None,
) -> BaseVisionProvider:
    """
    Factory returning the selected vision provider.
    Defaults to Ollama (local) as preferred by the tracker.
    """
    name = (provider_name or os.getenv("VISION_PROVIDER", "ollama")).strip().lower()
    if name == "groq":
        return GroqVisionProvider()
    return OllamaVisionProvider(http_client=http_client)


def analyze_image_evidence(
    image_bytes: Optional[bytes] = None,
    image_base64: Optional[str] = None,
    provider_name: Optional[str] = None,
    custom_provider: Optional[BaseVisionProvider] = None,
) -> VisionClassificationResult:
    """
    Sanitizes raw image input and runs visual classification.
    Guarantees:
    - Never passes unsanitized data to any model.
    - If provider is unavailable, returns available=False, label=None, without fabricating.
    - Does NOT treat valid image or HTTP 200 as proof of physical issue.
    """
    # Step 1: Strict image sanitization
    sanitized_res = None
    if image_bytes is not None and len(image_bytes) > 0:
        sanitized_res = sanitize_image_bytes(image_bytes)
    elif image_base64 is not None and len(image_base64.strip()) > 0:
        sanitized_res = sanitize_base64_image(image_base64)

    if sanitized_res is None or not sanitized_res.is_valid or not sanitized_res.sanitized_bytes:
        error_msg = sanitized_res.error_message if sanitized_res else "No image attached"
        return VisionClassificationResult(
            label=None,
            confidence=None,
            model="none",
            available=False,
            error=f"Sanitization check failed: {error_msg}",
            provider="none",
        )

    # Encode sanitized bytes to standard base64 for provider intake
    sanitized_b64 = base64.b64encode(sanitized_res.sanitized_bytes).decode("utf-8")

    # Step 2: Dispatch to provider
    provider = custom_provider or get_vision_provider(provider_name)
    return provider.classify(sanitized_b64)
