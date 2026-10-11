"""
JanSetu AI — Incident Intelligence Agent & Groq Vision Test Suite.

Automated tests for Phase 2:
1. Relevant pothole image -> MATCHED
2. Relevant waterlogging image -> MATCHED
3. Relevant garbage image -> MATCHED
4. Clearly mismatched image (e.g. cat/living room) -> MISMATCH (clarification requested, report preserved)
5. Low-quality (blur/occlusion) and inconclusive images -> LOW_QUALITY / INCONCLUSIVE
6. Complaint without an image -> NOT_PROVIDED (recorded, conservative triage)
7. Malformed model output -> Graceful recovery, INCONCLUSIVE fallback
8. Missing API credentials -> Safe fallback, no unhandled exceptions
9. Groq rate limits, timeouts, and network connection errors -> Handled cleanly
10. Strict privacy verification: Raw image payloads and API credentials never appear in logs
11. Optional real Groq vision integration check
"""

import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from groq import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from app.agents.incident_intel import incident_intel_node
from app.core.groq_vision import (
    analyze_with_groq_vision,
    get_groq_api_key,
)
from app.schemas.incident import (
    EvidenceOutcome,
    EvidenceRecommendation,
    ImageQualityAssessment,
    IncidentCategory,
    IncidentExtraction,
    IncidentLocation,
    OperationalStatus,
    PhotoEvidenceAnalysis,
)


# ============================================================================
# Helpers for Mocking Groq API Responses
# ============================================================================

def make_mock_groq_completion(content_dict: dict) -> MagicMock:
    """Build a mock ChatCompletion response object containing JSON content."""
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(content_dict)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ============================================================================
# 1. Relevant Pothole Image Test
# ============================================================================

def test_pothole_image_matched(valid_jpeg_bytes):
    """Ensure a clear photograph matching a pothole complaint produces MATCHED and TRIAGED status."""
    mock_payload = {
        "extraction": {
            "category": "pothole",
            "severity_indicators": ["deep crater ~15cm", "rim damage risk"],
            "public_exposure_clues": ["arterial road", "high traffic lane"],
            "missing_info": ["exact cross street"],
            "extracted_location_clues": "Main arterial road near pillar 12",
            "confidence_score": 0.95,
        },
        "evidence": {
            "detected_category": "pothole",
            "visible_evidence": "Asphalt depression with loose aggregate and broken wearing course",
            "relevance_score": 0.96,
            "image_quality": "GOOD",
            "confidence_score": 0.94,
            "outcome": "MATCHED",
            "recommendation": "PROCEED",
            "explanation": "Clear photograph confirming hazardous pothole on roadway.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Huge pothole on main road causing severe tyre damage near pillar 12.",
            "selected_category": "pothole",
            "image_bytes": valid_jpeg_bytes,
            "location_data": IncidentLocation(latitude=28.6139, longitude=77.2090),
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "MATCHED"
    assert res["status"] == OperationalStatus.TRIAGED.value
    assert res["extracted_facts"].category == "pothole"
    assert res["evidence_analysis"].outcome == EvidenceOutcome.MATCHED
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.PROCEED
    assert "pothole" in res["evidence_analysis"].detected_category.lower()


# ============================================================================
# 2. Relevant Waterlogging Image Test
# ============================================================================

def test_waterlogging_image_matched(valid_jpeg_bytes):
    """Ensure a submerged roadway photograph produces MATCHED and TRIAGED status."""
    mock_payload = {
        "extraction": {
            "category": "waterlogging",
            "severity_indicators": ["knee-deep floodwater", "submerged vehicles"],
            "public_exposure_clues": ["transit underpass", "metro station entrance"],
            "missing_info": [],
            "extracted_location_clues": "Underpass exit",
            "confidence_score": 0.92,
        },
        "evidence": {
            "detected_category": "waterlogging",
            "visible_evidence": "Submerged roadway with pooled standing stormwater spanning multiple lanes",
            "relevance_score": 0.98,
            "image_quality": "GOOD",
            "confidence_score": 0.95,
            "outcome": "MATCHED",
            "recommendation": "PROCEED",
            "explanation": "Photograph demonstrates severe stormwater accumulation across carriageway.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Severe waterlogging outside underpass, two cars stuck in water.",
            "selected_category": "waterlogging",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "MATCHED"
    assert res["status"] == OperationalStatus.TRIAGED.value
    assert res["extracted_facts"].category == "waterlogging"
    assert res["evidence_analysis"].outcome == EvidenceOutcome.MATCHED


# ============================================================================
# 3. Relevant Garbage Image Test
# ============================================================================

def test_garbage_image_matched(valid_jpeg_bytes):
    """Ensure a garbage accumulation photograph produces MATCHED and TRIAGED status."""
    mock_payload = {
        "extraction": {
            "category": "garbage",
            "severity_indicators": ["overflowing dumpster", "pedestrian pathway blocked"],
            "public_exposure_clues": ["adjacent to primary school"],
            "missing_info": [],
            "confidence_score": 0.90,
        },
        "evidence": {
            "detected_category": "garbage",
            "visible_evidence": "Uncontained municipal solid waste accumulating on public walkway",
            "relevance_score": 0.94,
            "image_quality": "GOOD",
            "confidence_score": 0.92,
            "outcome": "MATCHED",
            "recommendation": "PROCEED",
            "explanation": "Visual artifacts confirm large pile of uncollected waste.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Huge pile of rotting garbage on the footpath next to the school.",
            "selected_category": "garbage",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "MATCHED"
    assert res["status"] == OperationalStatus.TRIAGED.value
    assert res["extracted_facts"].category == "garbage"


# ============================================================================
# 4. Clearly Mismatched Image Test
# ============================================================================

def test_mismatched_image_requests_clarification(valid_jpeg_bytes):
    """
    Ensure an irrelevant image (e.g. indoor pet/furniture for garbage complaint)
    triggers MISMATCH, requests clarification, and does NOT drop the complaint.
    """
    mock_payload = {
        "extraction": {
            "category": "garbage",
            "severity_indicators": ["foul smell reported"],
            "public_exposure_clues": [],
            "missing_info": [],
            "confidence_score": 0.85,
        },
        "evidence": {
            "detected_category": "unrelated_object",
            "visible_evidence": "Photograph depicts an indoor cat resting on a household sofa",
            "relevance_score": 0.02,
            "image_quality": "GOOD",
            "confidence_score": 0.98,
            "outcome": "MISMATCH",
            "recommendation": "REQUEST_CLARIFICATION",
            "explanation": "Uploaded photo depicts a domestic feline pet, which has no relevance to outdoor municipal garbage.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Trash overflowing in alleyway behind market.",
            "selected_category": "garbage",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    # Must set MISMATCH evidence status and route to clarification
    assert res["evidence_status"] == "MISMATCH"
    assert res["status"] == OperationalStatus.AWAITING_CLARIFICATION.value
    assert res["evidence_analysis"].outcome == EvidenceOutcome.MISMATCH
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.REQUEST_CLARIFICATION
    
    # Original complaint must be preserved and fact-extracted
    assert res["extracted_facts"] is not None
    assert res["extracted_facts"].category == "garbage"


# ============================================================================
# 5. Low-Quality & Inconclusive Image Tests
# ============================================================================

def test_low_quality_blurry_image(valid_jpeg_bytes):
    """Ensure blurry or unreadable image triggers LOW_QUALITY and retake recommendation."""
    mock_payload = {
        "extraction": {
            "category": "pothole",
            "severity_indicators": ["vehicle jarred violently"],
            "missing_info": [],
            "confidence_score": 0.80,
        },
        "evidence": {
            "detected_category": "unclear",
            "visible_evidence": "Heavy motion blur and camera glare; road features cannot be resolved",
            "relevance_score": 0.20,
            "image_quality": "BLURRY",
            "confidence_score": 0.25,
            "outcome": "LOW_QUALITY",
            "recommendation": "REQUEST_RETAKE",
            "explanation": "Image is severely blurred by vehicle motion. Retake requested.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Bad pothole on high speed ring road.",
            "selected_category": "pothole",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "LOW_QUALITY"
    assert res["status"] == OperationalStatus.AWAITING_EVIDENCE_RETAKE.value
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.REQUEST_RETAKE


def test_inconclusive_image_routes_to_human_review(valid_jpeg_bytes):
    """Ensure ambiguous visual scene triggers INCONCLUSIVE and human review recommendation."""
    mock_payload = {
        "extraction": {
            "category": "waterlogging",
            "severity_indicators": [],
            "missing_info": [],
            "confidence_score": 0.70,
        },
        "evidence": {
            "detected_category": "unclear",
            "visible_evidence": "Distracted perspective showing distant foliage and pavement edge; water depth uncertain",
            "relevance_score": 0.45,
            "image_quality": "GOOD",
            "confidence_score": 0.40,
            "outcome": "INCONCLUSIVE",
            "recommendation": "HUMAN_REVIEW",
            "explanation": "Cannot reliably verify waterlogging extent from submitted angle.",
        },
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Water accumulating near sidewalk.",
            "selected_category": "waterlogging",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.HUMAN_REVIEW


# ============================================================================
# 6. Complaint Without an Image Test
# ============================================================================

def test_complaint_without_image_preserved():
    """Ensure reports filed without photographs are recorded with NOT_PROVIDED and preserved."""
    mock_payload = {
        "extraction": {
            "category": "pothole",
            "severity_indicators": ["deep crater"],
            "public_exposure_clues": ["school bus route"],
            "missing_info": ["photographic evidence"],
            "confidence_score": 0.88,
        },
        "evidence": {},
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Large dangerous pothole right in front of primary school gate.",
            "selected_category": "pothole",
            "image_bytes": None,
            "image_base64": None,
        }
        res = incident_intel_node(state)

    # Must be recorded and routed to pending review
    assert res["evidence_status"] == "NOT_PROVIDED"
    assert res["status"] == OperationalStatus.RECORDED_PENDING_REVIEW.value
    assert res["evidence_analysis"].outcome == EvidenceOutcome.NOT_PROVIDED
    assert res["evidence_analysis"].image_quality == ImageQualityAssessment.ABSENT
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.HUMAN_REVIEW
    
    # Text facts must be extracted accurately
    assert res["extracted_facts"].category == "pothole"
    assert "school bus route" in res["extracted_facts"].public_exposure_clues


# ============================================================================
# 7. Malformed Model Output Test
# ============================================================================

def test_malformed_model_output_fallback(valid_jpeg_bytes):
    """Ensure malformed model output triggers safe fallback without crashing."""
    mock_choice = MagicMock()
    mock_choice.message.content = "Internal model reasoning: {broken_json: True, invalid syntax"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Pothole damaging cars.",
            "selected_category": "pothole",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value
    assert res["extracted_facts"] is not None
    assert "Fallback" in res["audit_timeline"][0]["result"]


# ============================================================================
# 8. Missing API Credentials Test
# ============================================================================

def test_missing_api_credentials_safe_fallback(valid_jpeg_bytes):
    """Ensure missing GROQ_API_KEY activates fallback without raising exceptions."""
    with patch("app.core.groq_vision.get_groq_api_key", return_value=None):
        state = {
            "raw_input": "Flooded street after heavy downpour.",
            "selected_category": "waterlogging",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value
    assert res["evidence_analysis"].recommendation == EvidenceRecommendation.HUMAN_REVIEW
    assert "unavailable" in res["evidence_analysis"].visible_evidence.lower()


# ============================================================================
# 9. Groq Rate Limits & Network Errors Test
# ============================================================================

def test_groq_rate_limit_handled(valid_jpeg_bytes):
    """Ensure RateLimitError is caught and routed to inconclusive human review."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Rate limit reached",
        response=mock_resp,
        body=None,
    )

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Garbage pile blocking sidewalk.",
            "selected_category": "garbage",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value
    assert "Fallback" in res["audit_timeline"][0]["result"]


def test_groq_timeout_handled(valid_jpeg_bytes):
    """Ensure APITimeoutError is caught and routed to inconclusive human review."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Pothole on Main St.",
            "selected_category": "pothole",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value


def test_groq_connection_error_handled(valid_jpeg_bytes):
    """Ensure APIConnectionError is caught and handled safely."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())

    with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
        state = {
            "raw_input": "Open manhole cover.",
            "selected_category": "uncertain_other",
            "image_bytes": valid_jpeg_bytes,
        }
        res = incident_intel_node(state)

    assert res["evidence_status"] == "INCONCLUSIVE"
    assert res["status"] == OperationalStatus.AWAITING_HUMAN_REVIEW.value


# ============================================================================
# 10. Privacy: No Raw Images or Credentials in Logs
# ============================================================================

def test_privacy_no_image_or_credentials_in_logs(caplog, valid_jpeg_bytes):
    """
    Ensure raw image bytes, Base64 URI strings, and API credential tokens
    are NEVER emitted in log messages.
    """
    secret_token = "gsk_super_secret_credential_token_999888777"
    unique_marker = "UNIQUE_BASE64_BYTE_SIGNATURE_MARKER_12345"

    # Inject mock completion
    mock_payload = {
        "extraction": {"category": "pothole", "severity_indicators": [], "missing_info": []},
        "evidence": {
            "detected_category": "pothole",
            "visible_evidence": "Confirmed cavity",
            "outcome": "MATCHED",
            "recommendation": "PROCEED",
            "image_quality": "GOOD",
        },
    }
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = make_mock_groq_completion(mock_payload)

    with caplog.at_level(logging.DEBUG):
        with patch("app.core.groq_vision.get_groq_api_key", return_value=secret_token):
            with patch("app.core.groq_vision.get_groq_client", return_value=mock_client):
                state = {
                    "raw_input": "Road damage report.",
                    "selected_category": "pothole",
                    "image_bytes": valid_jpeg_bytes,
                }
                incident_intel_node(state)

    all_log_text = " ".join(record.message for record in caplog.records)

    # 1. Credentials must never appear
    assert secret_token not in all_log_text
    
    # 2. Base64 payload data URI must never appear in raw format
    assert "data:image/jpeg;base64," not in all_log_text
    assert unique_marker not in all_log_text


# ============================================================================
# 11. Optional Real Groq Vision Integration Check
# ============================================================================

@pytest.mark.skipif(
    not get_groq_api_key(),
    reason="Live GROQ_API_KEY not configured in environment.",
)
def test_live_groq_vision_invocation_optional(valid_jpeg_bytes):
    """
    Optional live integration test against Groq's qwen/qwen3.8-27b vision model.
    Runs only if GROQ_API_KEY is present in the environment.
    """
    from app.core.image_processing import sanitize_image_bytes

    sanitized = sanitize_image_bytes(valid_jpeg_bytes)
    assert sanitized.is_valid is True

    result = analyze_with_groq_vision(
        complaint_text="Deep pothole in asphalt road lane causing vehicle damage.",
        selected_category="pothole",
        sanitized_image_data_uri=sanitized.base64_data_uri,
        simulation_mode=False,
    )

    # Verify structured outcome
    assert result.success is True
    assert result.is_fallback is False
    assert result.extraction is not None
    assert result.evidence is not None
    assert result.evidence.outcome in [
        EvidenceOutcome.MATCHED,
        EvidenceOutcome.MISMATCH,
        EvidenceOutcome.LOW_QUALITY,
        EvidenceOutcome.INCONCLUSIVE,
    ]
