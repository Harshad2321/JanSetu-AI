"""
JanSetu AI — Multimodal Fusion Layer (Phase 4, P4.5).

Implements every tracker fusion rule from Section 5.2:
- Case A: Vision and NLP agree -> fused category, preserve both contributing outputs and provenance.
- Case B: Vision and NLP disagree -> flag disagreement, route to clarification/review without forcing a category.
- Case C: Vision unavailable, NLP available -> NLP partial evidence, vision marked unavailable.
- Case D: NLP unavailable, vision available -> vision partial evidence, NLP marked unavailable.
- Case E: Both unavailable -> require manual category selection, strictly labeled as manual selection (not ML).
- Case F: Required fields missing -> targeted clarification questions without inferring missing coordinates, images, or facts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.ml.nlp_classifier import NLPClassificationResult
from app.ml.vision import VisionClassificationResult
from app.schemas.incident import ModelPrediction

logger = logging.getLogger("jansetu.ml.fusion")


class MultimodalFusionResult(BaseModel):
    """Structured output from the multimodal fusion layer."""
    model_config = ConfigDict(use_enum_values=True)

    status: str = Field(description="Fusion branch: AGREEMENT, DISAGREEMENT, NLP_ONLY, VISION_ONLY, MANUAL_SELECTION, MISSING_FIELDS")
    fused_category: Optional[str] = Field(default=None, description="Agreed or partial category; None on disagreement or missing input")
    confidence: Optional[float] = Field(default=None, description="Combined or partial confidence score; None for manual selection")
    fusion_method: str = Field(default="NONE", description="AGREED_MULTIMODAL, NLP_PARTIAL, VISION_PARTIAL, MANUAL_SELECTION, NONE")
    nlp_prediction: Optional[NLPClassificationResult] = Field(default=None)
    vision_prediction: Optional[VisionClassificationResult] = Field(default=None)
    disagreement_detected: bool = Field(default=False)
    clarification_questions: List[str] = Field(default_factory=list)
    needs_human_review: bool = Field(default=False)
    is_model_prediction: bool = Field(default=True, description="False when category was manually selected")
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_model_prediction(self, incident_id: str = "") -> ModelPrediction:
        """Converts fusion outcome into the standard ModelPrediction persistence contract."""
        prov = "direct"
        if not self.is_model_prediction:
            prov = "manual_selection"
        elif self.status in ("NLP_ONLY", "VISION_ONLY"):
            prov = "partial"
        elif self.disagreement_detected:
            prov = "disagreement"

        return ModelPrediction(
            prediction_id=f"pred_fus_{uuid.uuid4().hex[:12]}",
            incident_id=incident_id or f"inc_fus_{uuid.uuid4().hex[:8]}",
            task_type="fusion",
            predicted_label=self.fused_category or "",
            scores={},
            confidence=float(self.confidence) if self.confidence is not None else 0.0,
            model_name=f"MultimodalFusion({self.fusion_method})",
            model_version="v1.0.0",
            available=self.fused_category is not None,
            fallback_provenance=prov,
            is_synthetic=True,
            created_at=self.created_at,
        )


def fuse_incident_evidence(
    nlp_result: Optional[NLPClassificationResult] = None,
    vision_result: Optional[VisionClassificationResult] = None,
    description: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    manual_category: Optional[str] = None,
    require_location: bool = False,
) -> MultimodalFusionResult:
    """
    Executes multimodal fusion logic across NLP and Vision outputs according to
    tracker Section 5.2.
    """
    # Case F: Check required fields missing
    missing_fields: List[str] = []
    clarification_questions: List[str] = []

    if not description or not description.strip():
        missing_fields.append("description")
        clarification_questions.append("Please provide a description of the civic incident.")

    if require_location and (latitude is None or longitude is None):
        missing_fields.append("coordinates")
        clarification_questions.append("Please provide geographic coordinates or a valid street address for the incident.")

    if missing_fields:
        return MultimodalFusionResult(
            status="MISSING_FIELDS",
            fused_category=None,
            confidence=None,
            fusion_method="NONE",
            nlp_prediction=nlp_result,
            vision_prediction=vision_result,
            clarification_questions=clarification_questions,
            needs_human_review=False,
            is_model_prediction=False,
            notes=f"Missing required fields: {', '.join(missing_fields)}. Clarification requested.",
        )

    nlp_available = nlp_result is not None and nlp_result.available and bool(nlp_result.predicted_label)
    vision_available = vision_result is not None and vision_result.available and bool(vision_result.label)

    # Case A & B: Both models available
    if nlp_available and vision_available:
        assert nlp_result is not None
        assert vision_result is not None

        if nlp_result.predicted_label == vision_result.label:
            # Case A: Vision and NLP agree
            nlp_conf = nlp_result.confidence or 0.5
            vis_conf = vision_result.confidence or 0.5
            combined_conf = round((nlp_conf + vis_conf) / 2.0, 4)

            return MultimodalFusionResult(
                status="AGREEMENT",
                fused_category=nlp_result.predicted_label,
                confidence=combined_conf,
                fusion_method="AGREED_MULTIMODAL",
                nlp_prediction=nlp_result,
                vision_prediction=vision_result,
                disagreement_detected=False,
                clarification_questions=[],
                needs_human_review=False,
                is_model_prediction=True,
                notes=f"NLP and Vision agree on '{nlp_result.predicted_label}'. Both evidence streams verified.",
            )
        else:
            # Case B: Vision and NLP disagree -> DO NOT force a category
            return MultimodalFusionResult(
                status="DISAGREEMENT",
                fused_category=None,
                confidence=None,
                fusion_method="NONE",
                nlp_prediction=nlp_result,
                vision_prediction=vision_result,
                disagreement_detected=True,
                clarification_questions=[
                    f"Text complaint indicates '{nlp_result.predicted_label}' whereas photo analysis indicates '{vision_result.label}'. "
                    "Please confirm the correct category or provide additional details."
                ],
                needs_human_review=True,
                is_model_prediction=True,
                notes=f"Disagreement between NLP ('{nlp_result.predicted_label}') and Vision ('{vision_result.label}'). Routed to clarification/review.",
            )

    # Case C: Vision unavailable, NLP available
    if nlp_available and not vision_available:
        assert nlp_result is not None
        return MultimodalFusionResult(
            status="NLP_ONLY",
            fused_category=nlp_result.predicted_label,
            confidence=nlp_result.confidence,
            fusion_method="NLP_PARTIAL",
            nlp_prediction=nlp_result,
            vision_prediction=vision_result,
            disagreement_detected=False,
            clarification_questions=[],
            needs_human_review=False,
            is_model_prediction=True,
            notes="Vision provider unavailable. Categorized using NLP text complaint as partial evidence.",
        )

    # Case D: NLP unavailable, vision available
    if vision_available and not nlp_available:
        assert vision_result is not None
        return MultimodalFusionResult(
            status="VISION_ONLY",
            fused_category=vision_result.label,
            confidence=vision_result.confidence,
            fusion_method="VISION_PARTIAL",
            nlp_prediction=nlp_result,
            vision_prediction=vision_result,
            disagreement_detected=False,
            clarification_questions=[],
            needs_human_review=False,
            is_model_prediction=True,
            notes="NLP model unavailable. Categorized using sanitized vision analysis as partial evidence.",
        )

    # Case E: Both models unavailable
    if manual_category and manual_category.strip():
        # Manual selection provided
        clean_cat = manual_category.strip().lower()
        return MultimodalFusionResult(
            status="MANUAL_SELECTION",
            fused_category=clean_cat,
            confidence=None,
            fusion_method="MANUAL_SELECTION",
            nlp_prediction=nlp_result,
            vision_prediction=vision_result,
            disagreement_detected=False,
            clarification_questions=[],
            needs_human_review=False,
            is_model_prediction=False,
            notes="Both automated intelligence providers unavailable. Category assigned via citizen/operator manual selection.",
        )

    # Both unavailable and no manual selection provided
    return MultimodalFusionResult(
        status="MANUAL_SELECTION_REQUIRED",
        fused_category=None,
        confidence=None,
        fusion_method="NONE",
        nlp_prediction=nlp_result,
        vision_prediction=vision_result,
        disagreement_detected=False,
        clarification_questions=[
            "Automated classification models are currently unavailable. Please manually select the category (pothole, waterlogging, garbage)."
        ],
        needs_human_review=True,
        is_model_prediction=False,
        notes="Both models unavailable and no manual category provided. Manual category selection required.",
    )
