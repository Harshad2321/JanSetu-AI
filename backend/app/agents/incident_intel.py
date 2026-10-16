"""
JanSetu AI — Incident Intelligence Agent (Phase 5, P5.2).

Responsible for:
- Implementing the shared CivicAgentProtocol: run(incident, context) -> IncidentIntelOutput
- Ingesting citizen complaints, category claims, location metadata, and optional photos
- Sanitizing uploaded images via Pillow pipeline
- Multimodal analysis combining real NLP classifier (TF-IDF + LogisticRegression) and vision provider
- Reconciling evidence via the Phase 4 Multimodal Fusion layer (Cases A through F)
- Identifying missing mandatory fields and generating targeted clarification questions
- Setting explicit needs_review flag upon disagreement, model unavailability, or missing data
- Preserving citizen original complaint separately from normalized or extracted fields
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import BaseCivicAgent
from app.core.groq_vision import (
    analyze_with_groq_vision,
    GroqVisionResult,
)
from app.core.image_processing import (
    evaluate_evidence_intake,
    SanitizedImageResult,
)
from app.graph.state import IncidentState
from app.ml.fusion import (
    MultimodalFusionResult,
    fuse_incident_evidence,
)
from app.ml.nlp_classifier import (
    NLPClassificationResult,
    get_nlp_classifier,
)
from app.ml.vision import (
    VisionClassificationResult,
    analyze_image_evidence,
)
from app.schemas.incident import (
    AuditEvent,
    EvidenceOutcome,
    EvidenceRecommendation,
    ImageQualityAssessment,
    IncidentCategory,
    IncidentExtraction,
    IncidentIntelOutput,
    IncidentLocation,
    ModelPrediction,
    OperationalStatus,
    PhotoEvidenceAnalysis,
)

logger = logging.getLogger("jansetu.incident_intel")


def to_str(val: Any) -> str:
    """Safely obtain string representation of an enum or string value."""
    return str(val.value) if hasattr(val, "value") else str(val)


class IncidentIntelligenceAgent(BaseCivicAgent[IncidentIntelOutput]):
    """Agent 1: Incident Intelligence Specialist."""

    agent_name: str = "Incident Intelligence"
    agent_role: str = "Research"

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> IncidentIntelOutput:
        """
        Execute incident intake, sanitization, NLP, vision, and multimodal fusion.
        Returns validated IncidentIntelOutput.
        """
        data = self.extract_incident_dict(incident)

        incident_id = data.get("incident_id") or f"inc_{uuid.uuid4().hex[:8]}"
        raw_input = (data.get("raw_input") or data.get("complaint") or data.get("description") or "").strip()
        selected_category = data.get("selected_category") or data.get("category") or "uncertain_other"
        location_data = data.get("location_data")
        image_bytes = data.get("image_bytes")
        image_base64 = data.get("image_base64")
        simulation_mode = bool(data.get("simulation_mode", False))
        simulated_outcome = data.get("simulated_outcome")

        # Format location string for context if available
        location_text = None
        lat: Optional[float] = None
        lon: Optional[float] = None
        if isinstance(location_data, IncidentLocation):
            lat = location_data.latitude
            lon = location_data.longitude
            location_text = location_data.address_text or (
                f"Lat: {lat}, Lon: {lon}" if lat is not None else None
            )
        elif isinstance(location_data, dict):
            lat = location_data.get("latitude")
            lon = location_data.get("longitude")
            location_text = location_data.get("address_text") or (
                f"Lat: {lat}, Lon: {lon}" if lat is not None else None
            )

        # Step 1: Secure image intake & sanitization (Pillow pipeline)
        sanitized_res, preliminary_analysis = evaluate_evidence_intake(
            image_bytes=image_bytes,
            image_base64=image_base64,
        )

        # Step 2: Vision Analysis via Groq / Ollama / Fallback pipeline
        if sanitized_res is None and preliminary_analysis.outcome == EvidenceOutcome.NOT_PROVIDED:
            vision_res = analyze_with_groq_vision(
                complaint_text=raw_input,
                selected_category=selected_category,
                location_text=location_text,
                sanitized_image_data_uri=None,
                simulation_mode=simulation_mode,
                simulated_outcome=simulated_outcome,
            )
            extraction = vision_res.extraction
            evidence_analysis = preliminary_analysis

        elif sanitized_res is not None and not sanitized_res.is_valid:
            vision_res = analyze_with_groq_vision(
                complaint_text=raw_input,
                selected_category=selected_category,
                location_text=location_text,
                sanitized_image_data_uri=None,
                simulation_mode=simulation_mode,
                simulated_outcome=simulated_outcome,
            )
            extraction = vision_res.extraction
            evidence_analysis = preliminary_analysis

        else:
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

        # Build VisionClassificationResult for Fusion
        vis_outcome = evidence_analysis.outcome
        vis_cat = evidence_analysis.detected_category.lower().strip()
        vis_available = (
            vis_outcome == EvidenceOutcome.MATCHED
            and not vision_res.is_fallback
            and vis_cat in ("pothole", "waterlogging", "garbage")
        )

        vis_res = VisionClassificationResult(
            label=vis_cat if vis_available else None,
            confidence=evidence_analysis.confidence_score if vis_available else None,
            available=vis_available,
            model="groq-vision" if not vision_res.is_fallback else "fallback",
            error=vision_res.error_message if not vis_available else None,
            provider="groq" if not vision_res.is_fallback else "fallback",
        )

        # Step 3: NLP Inference via Phase 4 Classifier
        classifier = get_nlp_classifier()
        nlp_res = classifier.predict(raw_input)

        # Step 4: Multimodal Fusion
        fusion_res = fuse_incident_evidence(
            nlp_result=nlp_res,
            vision_result=vis_res,
            description=raw_input,
            latitude=lat,
            longitude=lon,
            manual_category=selected_category if selected_category != "uncertain_other" else None,
        )

        # Step 5: Missing fields and targeted clarification questions
        missing_fields: List[str] = list(extraction.missing_info or [])
        clarification_questions: List[str] = list(fusion_res.clarification_questions)

        if not raw_input:
            if "complaint_description" not in missing_fields:
                missing_fields.append("complaint_description")
        elif len(raw_input) < 10:
            clarification_questions.append("Complaint is very brief. Please provide additional context regarding location, depth, or safety concerns.")

        if lat is None or lon is None:
            if "coordinates" not in missing_fields:
                missing_fields.append("coordinates")

        # Step 6: Operational status and review determination
        outcome = evidence_analysis.outcome
        needs_review = False

        if not raw_input:
            operational_status = OperationalStatus.NEEDS_CLARIFICATION.value
            needs_review = True
        elif fusion_res.status == "DISAGREEMENT":
            operational_status = OperationalStatus.NEEDS_CLARIFICATION.value
            needs_review = True
        elif outcome == EvidenceOutcome.MATCHED:
            operational_status = OperationalStatus.TRIAGED.value
        elif outcome == EvidenceOutcome.MISMATCH:
            operational_status = OperationalStatus.AWAITING_CLARIFICATION.value
            needs_review = True
        elif outcome == EvidenceOutcome.LOW_QUALITY:
            operational_status = OperationalStatus.AWAITING_EVIDENCE_RETAKE.value
            needs_review = True
        elif outcome == EvidenceOutcome.INCONCLUSIVE:
            operational_status = OperationalStatus.AWAITING_HUMAN_REVIEW.value
            needs_review = True
        elif outcome == EvidenceOutcome.NOT_PROVIDED:
            operational_status = OperationalStatus.RECORDED_PENDING_REVIEW.value
            # Missing photograph requires human review before closure
        else:
            operational_status = OperationalStatus.TRIAGED.value

        if not raw_input or len(clarification_questions) > 0 or fusion_res.disagreement_detected or fusion_res.needs_human_review:
            needs_review = True

        # Step 7: Build ModelPrediction provenance records
        predictions: List[ModelPrediction] = []
        if nlp_res is not None:
            predictions.append(nlp_res.to_model_prediction(incident_id=incident_id))
        if vis_res is not None:
            predictions.append(vis_res.to_model_prediction(incident_id=incident_id))
        if fusion_res is not None:
            predictions.append(fusion_res.to_model_prediction(incident_id=incident_id))

        # Build evidence summary
        outcome_str = to_str(evidence_analysis.outcome)
        rec_str = to_str(evidence_analysis.recommendation)
        if vision_res.is_simulated:
            provenance = "Simulated Demo"
        elif vision_res.is_fallback:
            provenance = f"Fallback ({vision_res.error_type or 'Service Unavailable'})"
        else:
            provenance = "Groq Vision"

        audit_result = (
            f"Category: {extraction.category} (Conf: {extraction.confidence_score:.2f}) | "
            f"Evidence: {outcome_str} [{provenance}] | "
            f"Recommendation: {rec_str}"
        )

        return IncidentIntelOutput(
            incident_id=incident_id,
            original_complaint=raw_input,
            selected_category=selected_category,
            predicted_category=fusion_res.fused_category if fusion_res.status != "DISAGREEMENT" else None,
            confidence=fusion_res.confidence if fusion_res.status != "DISAGREEMENT" else None,
            evidence_summary=audit_result,
            missing_fields=missing_fields,
            clarification_questions=clarification_questions,
            needs_review=needs_review,
            status=operational_status,
            extracted_facts=extraction,
            evidence_analysis=evidence_analysis,
            model_predictions=predictions,
        )


def incident_intel_node(state: IncidentState) -> Dict[str, Any]:
    """
    Incident Intelligence Agent node for the JanSetu LangGraph workflow.
    Wraps IncidentIntelligenceAgent().run(state) maintaining full backwards compatibility.
    """
    agent = IncidentIntelligenceAgent()
    output = agent.run(state)

    now_iso = datetime.now(timezone.utc).isoformat()
    cid = state.get("correlation_id") or f"corr_{state.get('incident_id', 'unknown')}"
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent=agent.agent_name,
        action="Multimodal Triage & Evidence Verification",
        result=output.evidence_summary,
        correlation_id=cid,
        event_type="intake",
    )

    logger.info(
        "Incident Intelligence complete: incident_id=%s, category=%s, evidence=%s, status=%s",
        state.get("incident_id", "N/A"),
        output.extracted_facts.category if output.extracted_facts else "N/A",
        to_str(output.evidence_analysis.outcome) if output.evidence_analysis else "N/A",
        output.status,
    )

    return {
        "extracted_facts": output.extracted_facts,
        "evidence_analysis": output.evidence_analysis,
        "evidence_status": to_str(output.evidence_analysis.outcome) if output.evidence_analysis else "NOT_PROVIDED",
        "status": output.status,
        "needs_review": output.needs_review,
        "clarification_questions": output.clarification_questions,
        "model_predictions": [p.model_dump() for p in output.model_predictions],
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }
