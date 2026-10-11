"""
JanSetu AI — Incident Intelligence Agent.

Responsible for:
- Ingesting citizen complaints, category claims, location metadata, and optional photos
- Sanitizing uploaded images via Pillow (EXIF stripping, dimension bounding, orientation)
- Multimodal analysis via Groq (default model: qwen/qwen3.8-27b)
- Fact extraction: severity indicators, missing info, public-exposure clues
- Photo evidence analysis: visual category, quality, relevance, outcome (MATCHED, MISMATCH, LOW_QUALITY, INCONCLUSIVE, NOT_PROVIDED)
- Strict safety boundaries: no physical proof claims, no authoritative crew dispatch
- Graceful deterministic fallback handling when Groq is unavailable
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.groq_vision import (
    analyze_with_groq_vision,
    GroqVisionResult,
)
from app.core.image_processing import (
    evaluate_evidence_intake,
    SanitizedImageResult,
)
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    EvidenceOutcome,
    EvidenceRecommendation,
    ImageQualityAssessment,
    IncidentCategory,
    IncidentExtraction,
    IncidentLocation,
    OperationalStatus,
    PhotoEvidenceAnalysis,
)

logger = logging.getLogger("jansetu.incident_intel")


def to_str(val: Any) -> str:
    """Safely obtain string representation of an enum or string value."""
    return str(val.value) if hasattr(val, "value") else str(val)


def incident_intel_node(state: IncidentState) -> Dict[str, Any]:
    """
    Incident Intelligence Agent node for the JanSetu LangGraph workflow.
    
    Accepts:
    - raw_input: Citizen complaint text description
    - selected_category: Citizen-selected category (pothole, waterlogging, garbage, uncertain_other)
    - location_data: IncidentLocation model or dict with location metadata
    - image_base64 / image_bytes: Optional raw image input
    - simulation_mode: Optional boolean for seeded demonstrations
    
    Produces:
    - extracted_facts: IncidentExtraction
    - evidence_analysis: PhotoEvidenceAnalysis
    - evidence_status: str (MATCHED, MISMATCH, LOW_QUALITY, INCONCLUSIVE, NOT_PROVIDED)
    - status: str (OperationalStatus)
    - audit_timeline: list of AuditEvent
    """
    raw_input = state.get("raw_input", "")
    selected_category = state.get("selected_category", "uncertain_other")
    location_data = state.get("location_data")
    image_base64 = state.get("image_base64")
    image_bytes = state.get("image_bytes")
    simulation_mode = bool(state.get("simulation_mode", False))
    simulated_outcome = state.get("simulated_outcome")

    # Format location string for context if available
    location_text = None
    if isinstance(location_data, IncidentLocation):
        location_text = location_data.address_text or (
            f"Lat: {location_data.latitude}, Lon: {location_data.longitude} (Acc: {location_data.accuracy_meters}m)"
            if location_data.latitude is not None else None
        )
    elif isinstance(location_data, dict):
        location_text = location_data.get("address_text") or (
            f"Lat: {location_data.get('latitude')}, Lon: {location_data.get('longitude')}"
            if location_data.get("latitude") is not None else None
        )

    # Step 1: Secure image intake & sanitization (Pillow pipeline)
    sanitized_res, preliminary_analysis = evaluate_evidence_intake(
        image_bytes=image_bytes,
        image_base64=image_base64,
    )

    # Step 2: Route to Groq Vision or handle invalid/missing photo
    if sanitized_res is None and preliminary_analysis.outcome == EvidenceOutcome.NOT_PROVIDED:
        # Case A: No photograph attached
        # Run text extraction on the complaint; evidence is NOT_PROVIDED
        vision_res = analyze_with_groq_vision(
            complaint_text=raw_input,
            selected_category=selected_category,
            location_text=location_text,
            sanitized_image_data_uri=None,
            simulation_mode=simulation_mode,
            simulated_outcome=simulated_outcome,
        )
        extraction = vision_res.extraction
        evidence_analysis = preliminary_analysis  # NOT_PROVIDED

    elif sanitized_res is not None and not sanitized_res.is_valid:
        # Case B: Image was attached but failed sanitization (too small, corrupt, oversized)
        # Sanitizer has already assigned LOW_QUALITY; run text extraction
        vision_res = analyze_with_groq_vision(
            complaint_text=raw_input,
            selected_category=selected_category,
            location_text=location_text,
            sanitized_image_data_uri=None,
            simulation_mode=simulation_mode,
            simulated_outcome=simulated_outcome,
        )
        extraction = vision_res.extraction
        evidence_analysis = preliminary_analysis  # LOW_QUALITY from sanitizer

    else:
        # Case C: Image was attached and successfully sanitized
        # Pass clean data URI to Groq vision
        data_uri = sanitized_res.base64_data_uri if sanitized_res else None
        vision_res = analyze_with_groq_vision(
            complaint_text=raw_input,
            selected_category=selected_category,
            location_text=location_text,
            sanitized_image_data_uri=data_uri,
            simulation_mode=simulation_mode,
            simulated_outcome=simulated_outcome,
        )
        extraction = vision_res.extraction
        evidence_analysis = vision_res.evidence

    # Step 3: Determine operational workflow routing from evidence outcome
    outcome = evidence_analysis.outcome
    if outcome == EvidenceOutcome.MATCHED:
        operational_status = OperationalStatus.TRIAGED.value
    elif outcome == EvidenceOutcome.MISMATCH:
        operational_status = OperationalStatus.AWAITING_CLARIFICATION.value
    elif outcome == EvidenceOutcome.LOW_QUALITY:
        operational_status = OperationalStatus.AWAITING_EVIDENCE_RETAKE.value
    elif outcome == EvidenceOutcome.INCONCLUSIVE:
        operational_status = OperationalStatus.AWAITING_HUMAN_REVIEW.value
    elif outcome == EvidenceOutcome.NOT_PROVIDED:
        operational_status = OperationalStatus.RECORDED_PENDING_REVIEW.value
    else:
        operational_status = OperationalStatus.TRIAGED.value

    # Step 4: Construct audit trail entry with provenance
    now_iso = datetime.now(timezone.utc).isoformat()
    if vision_res.is_simulated:
        provenance = "Simulated Demo"
    elif vision_res.is_fallback:
        provenance = f"Fallback ({vision_res.error_type or 'Service Unavailable'})"
    else:
        provenance = "Groq Vision"

    outcome_str = to_str(evidence_analysis.outcome)
    rec_str = to_str(evidence_analysis.recommendation)

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Incident Intelligence",
        action="Multimodal Triage & Evidence Verification",
        result=(
            f"Category: {extraction.category} (Conf: {extraction.confidence_score:.2f}) | "
            f"Evidence: {outcome_str} [{provenance}] | "
            f"Recommendation: {rec_str}"
        ),
    )

    logger.info(
        "Incident Intelligence complete: incident_id=%s, category=%s, evidence=%s, status=%s",
        state.get("incident_id", "N/A"),
        extraction.category,
        outcome_str,
        operational_status,
    )

    return {
        "extracted_facts": extraction,
        "evidence_analysis": evidence_analysis,
        "evidence_status": outcome_str,
        "status": operational_status,
        "audit_timeline": [audit_event.model_dump()],
    }

