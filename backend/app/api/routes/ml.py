"""
JanSetu AI — ML Model Lab & Evaluation API Routes.

Exposes endpoints for:
- Retrieving real model evaluation metrics, per-class stats, and confusion matrix
- Testing live predictions against the active NLP complaint classifier
- Inspecting multimodal vision availability
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.ml.nlp_classifier import MODEL_NAME, MODEL_VERSION, get_nlp_classifier

logger = logging.getLogger("jansetu.api.ml")

router = APIRouter(prefix="/ml", tags=["ML Model Lab"])

EVAL_METRICS_PATH = Path("eval/nlp_metrics.json")


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Complaint text to classify")


class PredictResponse(BaseModel):
    predicted_label: Optional[str] = None
    confidence: Optional[float] = None
    scores: Dict[str, float] = Field(default_factory=dict)
    available: bool = True
    error: Optional[str] = None
    model_name: str
    model_version: str


@router.get("/metrics")
def get_model_metrics() -> Dict[str, Any]:
    """
    Retrieve real evaluation metrics, per-class performance, and confusion matrix
    generated from model training and evaluation pipeline.
    """
    classifier = get_nlp_classifier()
    groq_configured = bool(settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 5)

    metrics_data = None
    if EVAL_METRICS_PATH.exists():
        try:
            with open(EVAL_METRICS_PATH, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception as exc:
            logger.warning("Could not read evaluation metrics file: %s", exc)

    return {
        "status": "ready" if classifier.is_available else "artifact_missing",
        "model_name": MODEL_NAME,
        "model_version": classifier.model_version or MODEL_VERSION,
        "artifact_path": str(classifier.artifact_path),
        "is_available": classifier.is_available,
        "classes": classifier.classes,
        "vision_provider": {
            "name": "Groq Llama-3.2-11b-Vision-Preview",
            "is_configured": groq_configured,
            "status": "active" if groq_configured else "offline / unconfigured",
        },
        "evaluation_report": metrics_data,
    }


@router.post("/predict", response_model=PredictResponse)
def predict_complaint(req: PredictRequest) -> PredictResponse:
    """
    Execute real-time NLP inference for a citizen complaint text.
    """
    classifier = get_nlp_classifier()
    result = classifier.predict(req.text)
    return PredictResponse(
        predicted_label=result.predicted_label,
        confidence=result.confidence,
        scores=result.scores,
        available=result.available,
        error=result.error,
        model_name=result.model_name,
        model_version=result.model_version,
    )
