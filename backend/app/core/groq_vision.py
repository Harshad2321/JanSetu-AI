"""
JanSetu AI — Groq Multimodal Vision Client & Pipeline.

Provides robust, privacy-respecting multimodal analysis using the official Groq SDK.
- Default vision model: qwen/qwen3.8-27b
- Strictly server-side API credentials from GROQ_API_KEY
- Zero logging of raw image bytes, Base64 strings, or credentials
- Bounded retries, timeouts, and graceful fallbacks for rate limits and outages
- Clear distinction between real API verification, simulated demo results, and fallbacks
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    Groq,
    RateLimitError,
)
from pydantic import BaseModel, Field

from app.schemas.incident import (
    EvidenceOutcome,
    EvidenceRecommendation,
    ImageQualityAssessment,
    IncidentCategory,
    IncidentExtraction,
    PhotoEvidenceAnalysis,
)

# Load environment configuration safely
load_dotenv()

# Configure logger with zero sensitive data output
logger = logging.getLogger("jansetu.groq_vision")

# Default vision configuration
DEFAULT_GROQ_VISION_MODEL: str = "qwen/qwen3.8-27b"
GROQ_TIMEOUT_SECONDS: float = 30.0
MAX_GROQ_RETRIES: int = 2


# ============================================================================
# Response Wrapper Model
# ============================================================================

class GroqVisionResult(BaseModel):
    """Encapsulates the multimodal analysis result, error telemetry, and provenance."""
    success: bool = Field(description="True if model completed analysis successfully")
    extraction: IncidentExtraction = Field(description="Structured facts extracted from complaint")
    evidence: PhotoEvidenceAnalysis = Field(description="Visual evidence analysis")
    is_fallback: bool = Field(default=False, description="True if output was produced by fallback handler")
    is_simulated: bool = Field(default=False, description="True if output was produced by seeded demonstration mode")
    error_type: Optional[str] = Field(default=None, description="Error classification if failed")
    error_message: Optional[str] = Field(default=None, description="Safe error description")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Inference latency in milliseconds")


# ============================================================================
# Credential & Model Utilities
# ============================================================================

def get_groq_api_key() -> Optional[str]:
    """Retrieve Groq API key from environment, checking both standard and legacy casing."""
    return os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")


def get_groq_vision_model() -> str:
    """Retrieve configured vision model ID, defaulting to qwen/qwen3.8-27b."""
    return os.getenv("GROQ_VISION_MODEL") or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_VISION_MODEL


def get_groq_client(timeout: float = GROQ_TIMEOUT_SECONDS) -> Optional[Groq]:
    """Instantiate official Groq client with timeout and bounded retries."""
    api_key = get_groq_api_key()
    if not api_key:
        logger.warning("Groq API key not configured; client unavailable.")
        return None
    return Groq(
        api_key=api_key,
        timeout=timeout,
        max_retries=MAX_GROQ_RETRIES,
    )


# ============================================================================
# Prompt Construction
# ============================================================================

SYSTEM_VISION_PROMPT: str = """You are the Incident Intelligence Agent for JanSetu AI, an autonomous civic triage system.
Your job is to analyze a citizen's civic report and any uploaded photographic evidence.

You MUST respond with a strictly valid JSON object matching the schema below. Do not output markdown fences or explanatory text.

JSON Schema:
{
  "extraction": {
    "category": "pothole | waterlogging | garbage | uncertain_other",
    "severity_indicators": ["concrete severity indicators mentioned in text"],
    "public_exposure_clues": ["clues indicating arterial road, school zone, pedestrian hazard, or traffic blockage"],
    "missing_info": ["essential information missing from text"],
    "extracted_location_clues": "string landmark or null",
    "confidence_score": 0.0 to 1.0
  },
  "evidence": {
    "detected_category": "pothole | waterlogging | garbage | uncertain_other | unclear",
    "visible_evidence": "concrete objective description of physical artifacts in image",
    "relevance_score": 0.0 to 1.0,
    "image_quality": "GOOD | BLURRY | DARK | OCCLUDED | TOO_SMALL",
    "confidence_score": 0.0 to 1.0,
    "outcome": "MATCHED | MISMATCH | INCONCLUSIVE | LOW_QUALITY",
    "recommendation": "PROCEED | REQUEST_CLARIFICATION | REQUEST_RETAKE | HUMAN_REVIEW",
    "explanation": "concise explanation of outcome and recommendation"
  }
}

EVIDENCE RULES:
1. MATCHED: The photograph clearly shows civic damage/hazards matching the reported category. Quality is GOOD. Recommendation: PROCEED.
2. MISMATCH: The photograph clearly depicts an unrelated subject (e.g. indoor room, cat, food, furniture, clean undamaged pavement). Recommendation: REQUEST_CLARIFICATION.
3. LOW_QUALITY: The photograph is too blurry, too dark, obstructed, or corrupted to evaluate. Recommendation: REQUEST_RETAKE.
4. INCONCLUSIVE: The scene is ambiguous, distant, or insufficient to confirm civic symptoms. Recommendation: HUMAN_REVIEW.

SAFETY BOUNDARY:
- The photograph does NOT legally prove physical presence at GPS coordinates or timestamp authenticity.
- Do NOT authorize physical repairs or allocate municipal crews. That belongs to later agents.
"""


def build_user_prompt(
    complaint_text: str,
    selected_category: str,
    location_text: Optional[str] = None,
) -> str:
    """Build user message prompt without exposing image payloads."""
    parts = [
        f"Citizen Complaint: {complaint_text}",
        f"Citizen Selected Category: {selected_category}",
    ]
    if location_text:
        parts.append(f"Reported Location/Landmark: {location_text}")
    return "\n".join(parts)


# ============================================================================
# Deterministic Fallback & Simulation Engines
# ============================================================================

def make_fallback_result(
    complaint_text: str,
    selected_category: str,
    error_type: str,
    error_message: str,
    has_image: bool = False,
) -> GroqVisionResult:
    """
    Produce an honest fallback result when Groq API is unavailable or unconfigured.
    
    Crucial policy:
    - Never pretend that an image has been visually verified.
    - If a photo was supplied, it is flagged as INCONCLUSIVE and routed to human review.
    - If no photo was supplied, it receives NOT_PROVIDED.
    - Label clearly as a fallback result.
    """
    logger.info("Engaging deterministic fallback: reason=%s", error_type)
    
    # Safe category normalization
    cat = selected_category if selected_category in [c.value for c in IncidentCategory] else "uncertain_other"
    
    extraction = IncidentExtraction(
        category=cat,
        severity_indicators=["Analysis performed via fallback rules (API unavailable)"],
        missing_info=["Automated multimodal analysis unavailable due to service error"],
        confidence_score=0.2,
        public_exposure_clues=[],
        extracted_location_clues=None,
    )
    
    if has_image:
        evidence = PhotoEvidenceAnalysis(
            detected_category="unverified",
            visible_evidence=f"Visual analysis unavailable: {error_message}. Awaiting human review.",
            relevance_score=0.0,
            image_quality=ImageQualityAssessment.GOOD,
            confidence_score=0.0,
            recommendation=EvidenceRecommendation.HUMAN_REVIEW,
            outcome=EvidenceOutcome.INCONCLUSIVE,
            quality_explanation=f"Fallback routed to human inspector: {error_message}",
            provenance="DETERMINISTIC_FALLBACK",
        )
    else:
        evidence = PhotoEvidenceAnalysis(
            detected_category="none",
            visible_evidence="No photograph provided with report.",
            relevance_score=0.0,
            image_quality=ImageQualityAssessment.ABSENT,
            confidence_score=0.0,
            recommendation=EvidenceRecommendation.HUMAN_REVIEW,
            outcome=EvidenceOutcome.NOT_PROVIDED,
            quality_explanation="Complaint recorded without photograph. Conservative field review scheduled.",
            provenance="NOT_PROVIDED",
        )
        
    return GroqVisionResult(
        success=False,
        extraction=extraction,
        evidence=evidence,
        is_fallback=True,
        is_simulated=False,
        error_type=error_type,
        error_message=error_message,
    )


def to_str(val: Any) -> str:
    """Safely obtain string representation of an enum or string value."""
    return str(val.value) if hasattr(val, "value") else str(val)


def make_simulated_result(
    complaint_text: str,
    selected_category: str,
    outcome: EvidenceOutcome = EvidenceOutcome.MATCHED,
) -> GroqVisionResult:
    """Produce explicitly labeled simulated result for seeded demonstrations."""
    logger.info("Generating simulated demonstration result: outcome=%s", to_str(outcome))
    
    cat = selected_category if selected_category in [c.value for c in IncidentCategory] else "uncertain_other"
    
    extraction = IncidentExtraction(
        category=cat,
        severity_indicators=["Simulated: Road cavity visible", "Simulated: Moderate vehicular hazard"],
        missing_info=[],
        confidence_score=0.95,
        public_exposure_clues=["Simulated: Arterial corridor"],
        extracted_location_clues="Simulated Location",
    )
    
    rec_map = {
        EvidenceOutcome.MATCHED: EvidenceRecommendation.PROCEED,
        EvidenceOutcome.MISMATCH: EvidenceRecommendation.REQUEST_CLARIFICATION,
        EvidenceOutcome.LOW_QUALITY: EvidenceRecommendation.REQUEST_RETAKE,
        EvidenceOutcome.INCONCLUSIVE: EvidenceRecommendation.HUMAN_REVIEW,
        EvidenceOutcome.NOT_PROVIDED: EvidenceRecommendation.HUMAN_REVIEW,
    }
    
    evidence = PhotoEvidenceAnalysis(
        detected_category=cat if outcome == EvidenceOutcome.MATCHED else "unrelated_object",
        visible_evidence=f"Simulated demonstration evidence: {to_str(outcome)}",
        relevance_score=0.9 if outcome == EvidenceOutcome.MATCHED else 0.1,
        image_quality=ImageQualityAssessment.GOOD if outcome != EvidenceOutcome.LOW_QUALITY else ImageQualityAssessment.BLURRY,
        confidence_score=0.9,
        recommendation=rec_map.get(outcome, EvidenceRecommendation.PROCEED),
        outcome=outcome,
        quality_explanation="Simulated seeded demonstration outcome.",
        provenance="SEEDED_SIMULATION",
    )
    
    return GroqVisionResult(
        success=True,
        extraction=extraction,
        evidence=evidence,
        is_fallback=False,
        is_simulated=True,
    )


# ============================================================================
# Main Groq Multimodal Invocation
# ============================================================================

def analyze_with_groq_vision(
    complaint_text: str,
    selected_category: str,
    location_text: Optional[str] = None,
    sanitized_image_data_uri: Optional[str] = None,
    simulation_mode: bool = False,
    simulated_outcome: Optional[EvidenceOutcome] = None,
    client: Optional[Groq] = None,
) -> GroqVisionResult:
    """
    Invoke Groq vision model to analyze citizen complaint and photographic evidence.
    
    Enforces:
    - Bounded retries and timeouts
    - Strictly sanitized Base64 URI (never logs payloads or credentials)
    - Handling of rate limits, network outages, and malformed JSON
    - Pure text fallback when no image is present
    """
    has_image = bool(sanitized_image_data_uri and sanitized_image_data_uri.startswith("data:image/"))

    # Check for seeded demonstration mode
    if simulation_mode:
        outcome = simulated_outcome or (EvidenceOutcome.MATCHED if has_image else EvidenceOutcome.NOT_PROVIDED)
        return make_simulated_result(complaint_text, selected_category, outcome)

    # Instantiate Groq client if not provided
    groq_client = client or get_groq_client()
    if not groq_client:
        return make_fallback_result(
            complaint_text=complaint_text,
            selected_category=selected_category,
            error_type="MISSING_CREDENTIALS",
            error_message="GROQ_API_KEY is not configured.",
            has_image=has_image,
        )

    model_id = get_groq_vision_model()
    user_text = build_user_prompt(complaint_text, selected_category, location_text)

    # Build multimodal messages payload
    if has_image:
        user_content = [
            {"type": "text", "text": user_text},
            {"type": "image_url", "image_url": {"url": sanitized_image_data_uri}},
        ]
    else:
        user_content = [
            {"type": "text", "text": user_text + "\n(Note: No photograph was provided with this report.)"},
        ]

    messages = [
        {"role": "system", "content": SYSTEM_VISION_PROMPT},
        {"role": "user", "content": user_content},
    ]

    start_time = time.perf_counter()
    logger.info("Dispatching Groq vision call: model=%s, has_image=%s", model_id, has_image)

    try:
        response = groq_client.chat.completions.create(
            model=model_id,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        raw_content = response.choices[0].message.content or "{}"
        
        # Clean any potential markdown wrapping
        clean_content = raw_content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()

        parsed_json = json.loads(clean_content)

        # Parse extraction facts
        ext_data = parsed_json.get("extraction", {})
        extraction = IncidentExtraction(
            category=ext_data.get("category", selected_category or "uncertain_other"),
            severity_indicators=ext_data.get("severity_indicators", []),
            public_exposure_clues=ext_data.get("public_exposure_clues", []),
            missing_info=ext_data.get("missing_info", []),
            extracted_location_clues=ext_data.get("extracted_location_clues"),
            confidence_score=float(ext_data.get("confidence_score", 0.8)),
        )

        # Parse evidence analysis
        if has_image:
            ev_data = parsed_json.get("evidence", {})
            
            # Map outcome safely
            raw_outcome = str(ev_data.get("outcome", "INCONCLUSIVE")).upper()
            try:
                outcome = EvidenceOutcome(raw_outcome)
            except ValueError:
                outcome = EvidenceOutcome.INCONCLUSIVE

            # Map recommendation safely
            raw_rec = str(ev_data.get("recommendation", "HUMAN_REVIEW")).upper()
            try:
                recommendation = EvidenceRecommendation(raw_rec)
            except ValueError:
                recommendation = EvidenceRecommendation.HUMAN_REVIEW

            # Map image quality safely
            raw_quality = str(ev_data.get("image_quality", "GOOD")).upper()
            try:
                quality = ImageQualityAssessment(raw_quality)
            except ValueError:
                quality = ImageQualityAssessment.GOOD

            evidence = PhotoEvidenceAnalysis(
                detected_category=str(ev_data.get("detected_category", "unclear")),
                visible_evidence=str(ev_data.get("visible_evidence", "Observable visual indicators.")),
                relevance_score=float(ev_data.get("relevance_score", 0.5)),
                image_quality=quality,
                confidence_score=float(ev_data.get("confidence_score", 0.8)),
                recommendation=recommendation,
                outcome=outcome,
                quality_explanation=ev_data.get("explanation"),
                provenance="GROQ_VISION",
            )
        else:
            evidence = PhotoEvidenceAnalysis(
                detected_category="none",
                visible_evidence="No photograph provided with report.",
                relevance_score=0.0,
                image_quality=ImageQualityAssessment.ABSENT,
                confidence_score=0.0,
                recommendation=EvidenceRecommendation.HUMAN_REVIEW,
                outcome=EvidenceOutcome.NOT_PROVIDED,
                quality_explanation="Complaint recorded without photograph. Conservative field review scheduled.",
                provenance="NOT_PROVIDED",
            )

        logger.info(
            "Groq vision completed: latency=%.1fms, outcome=%s",
            latency_ms,
            to_str(evidence.outcome),
        )

        return GroqVisionResult(
            success=True,
            extraction=extraction,
            evidence=evidence,
            is_fallback=False,
            is_simulated=False,
            latency_ms=latency_ms,
        )

    except RateLimitError as e:
        logger.warning("Groq API rate limit encountered: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "RATE_LIMIT", "Groq rate limit exceeded.", has_image
        )
    except APITimeoutError as e:
        logger.warning("Groq API request timed out: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "TIMEOUT", "Groq request timed out.", has_image
        )
    except APIConnectionError as e:
        logger.warning("Groq API connection failure: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "CONNECTION_ERROR", "Unable to connect to Groq API.", has_image
        )
    except AuthenticationError as e:
        logger.warning("Groq API authentication failed: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "AUTH_ERROR", "Groq authentication failed.", has_image
        )
    except APIError as e:
        logger.warning("Groq API error encountered: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "API_ERROR", "Groq API error occurred.", has_image
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Malformed JSON response from Groq vision: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "MALFORMED_OUTPUT", "Malformed response from vision model.", has_image
        )
    except Exception as e:
        logger.error("Unexpected error in Groq vision invocation: %s", type(e).__name__)
        return make_fallback_result(
            complaint_text, selected_category, "UNEXPECTED_ERROR", "An unexpected error occurred during vision analysis.", has_image
        )
