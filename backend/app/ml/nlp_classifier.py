"""
JanSetu AI — NLP Complaint Classifier (Phase 4, P4.2).

Implements real Scikit-learn TF-IDF + Logistic Regression classification for civic complaints:
- Categories: pothole, waterlogging, garbage
- Stratified train/test split (random_state=42)
- Vectorizer fitted strictly on the training partition only
- Preserves model version, availability, and class probabilities
- Never invents predictions when the model is unavailable or corrupted
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
from pydantic import BaseModel, ConfigDict, Field
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.schemas.incident import ModelPrediction

logger = logging.getLogger("jansetu.nlp_classifier")

# Constants
MODEL_VERSION = "v1.0.0"
MODEL_NAME = "TFIDF-LogisticRegression"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_ARTIFACT_PATH = DEFAULT_ARTIFACT_DIR / "nlp_classifier_v1.joblib"
DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic_complaints_train.json"

VALID_CATEGORIES = ["pothole", "waterlogging", "garbage"]


class NLPClassificationResult(BaseModel):
    """Validated typed prediction output from the NLP classifier."""
    model_config = ConfigDict(use_enum_values=True)

    predicted_label: Optional[str] = Field(default=None, description="Predicted class or None if unavailable")
    confidence: Optional[float] = Field(default=None, description="Model-reported probability of top class")
    scores: Dict[str, float] = Field(default_factory=dict, description="Per-class model probabilities")
    model_name: str = Field(default=MODEL_NAME)
    model_version: str = Field(default=MODEL_VERSION)
    available: bool = Field(default=True, description="True only if model produced this prediction")
    error: Optional[str] = Field(default=None, description="Reason if model unavailable")
    is_synthetic: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_model_prediction(self, incident_id: str = "") -> ModelPrediction:
        """Convert to the persistence ModelPrediction Pydantic contract."""
        return ModelPrediction(
            prediction_id=f"pred_nlp_{uuid.uuid4().hex[:12]}",
            incident_id=incident_id or f"inc_nlp_{uuid.uuid4().hex[:8]}",
            task_type="nlp",
            predicted_label=self.predicted_label or "",
            scores=self.scores,
            confidence=float(self.confidence) if self.confidence is not None else 0.0,
            model_name=self.model_name,
            model_version=self.model_version,
            available=self.available,
            fallback_provenance="direct" if self.available else "unavailable",
            is_synthetic=self.is_synthetic,
            created_at=self.created_at,
        )


def build_nlp_pipeline(random_state: int = 42) -> Pipeline:
    """Constructs TF-IDF vectorizer + LogisticRegression pipeline."""
    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                token_pattern=r"(?u)\b\w+\b",
                sublinear_tf=True,
                min_df=1,
            ),
        ),
        (
            "clf",
            LogisticRegression(
                random_state=random_state,
                max_iter=1000,
                class_weight="balanced",
                C=1.0,
            ),
        ),
    ])


def train_nlp_classifier(
    data_path: Path,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Pipeline, List[str], List[str], List[str], List[str]]:
    """
    Trains the classifier strictly on the training partition of the dataset.
    
    Returns:
    - (fitted_pipeline, X_train, X_test, y_train, y_test)
    """
    if not data_path.exists():
        raise FileNotFoundError(f"Training dataset not found at: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    texts = [r["text"] for r in records]
    labels = [r["label"] for r in records]

    # Stratified split to preserve class distribution
    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=random_state,
        stratify=labels,
    )

    pipeline = build_nlp_pipeline(random_state=random_state)
    # Fit strictly on the training split only!
    pipeline.fit(X_train, y_train)

    # Save versioned artifact
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pipeline": pipeline,
        "model_version": MODEL_VERSION,
        "model_name": MODEL_NAME,
        "classes": list(pipeline.classes_),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "num_train_samples": len(X_train),
    }
    joblib.dump(payload, artifact_path)
    logger.info("Saved NLP classifier artifact to: %s", artifact_path)

    return pipeline, X_train, X_test, y_train, y_test


class CivicNLPClassifier:
    """Production inference wrapper for the civic complaint NLP classifier."""

    def __init__(self, artifact_path: Optional[Path] = None):
        self.artifact_path = artifact_path or DEFAULT_ARTIFACT_PATH
        self.pipeline: Optional[Pipeline] = None
        self.model_version: str = MODEL_VERSION
        self.classes: List[str] = VALID_CATEGORIES
        self.load_model()

    def load_model(self) -> bool:
        """Loads versioned pipeline artifact if available."""
        if not self.artifact_path.exists():
            logger.warning("NLP classifier artifact not found at %s. Marking unavailable.", self.artifact_path)
            self.pipeline = None
            return False

        try:
            payload = joblib.load(self.artifact_path)
            if isinstance(payload, dict) and "pipeline" in payload:
                self.pipeline = payload["pipeline"]
                self.model_version = payload.get("model_version", MODEL_VERSION)
                self.classes = payload.get("classes", list(self.pipeline.classes_))
            elif isinstance(payload, Pipeline):
                self.pipeline = payload
                self.classes = list(payload.classes_)
            else:
                logger.error("Corrupted artifact format at %s", self.artifact_path)
                self.pipeline = None
                return False
            return True
        except Exception as exc:
            logger.error("Failed to load NLP artifact: %s", exc)
            self.pipeline = None
            return False

    @property
    def is_available(self) -> bool:
        return self.pipeline is not None

    def predict(self, text: str) -> NLPClassificationResult:
        """
        Classifies complaint text.
        If the model is unavailable or input is invalid, returns an honest unavailable result.
        """
        if not text or not text.strip():
            return NLPClassificationResult(
                predicted_label=None,
                confidence=None,
                scores={},
                available=False,
                error="Empty or whitespace-only complaint text",
                model_name=MODEL_NAME,
                model_version=self.model_version,
            )

        if not self.is_available:
            return NLPClassificationResult(
                predicted_label=None,
                confidence=None,
                scores={},
                available=False,
                error=f"Model artifact not available at {self.artifact_path}",
                model_name=MODEL_NAME,
                model_version=self.model_version,
            )

        try:
            assert self.pipeline is not None
            probs = self.pipeline.predict_proba([text])[0]
            classes = list(self.pipeline.classes_)

            scores = {cls_name: float(round(p, 4)) for cls_name, p in zip(classes, probs)}
            best_idx = int(probs.argmax())
            best_class = str(classes[best_idx])
            best_conf = float(round(probs[best_idx], 4))

            return NLPClassificationResult(
                predicted_label=best_class,
                confidence=best_conf,
                scores=scores,
                model_name=MODEL_NAME,
                model_version=self.model_version,
                available=True,
                error=None,
            )
        except Exception as exc:
            logger.error("Inference failed: %s", exc)
            return NLPClassificationResult(
                predicted_label=None,
                confidence=None,
                scores={},
                available=False,
                error=f"Prediction error: {str(exc)}",
                model_name=MODEL_NAME,
                model_version=self.model_version,
            )


# Global singleton instance for application use
_classifier_instance: Optional[CivicNLPClassifier] = None


def get_nlp_classifier() -> CivicNLPClassifier:
    """Returns singleton instance of the classifier."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = CivicNLPClassifier()
    return _classifier_instance


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and inspect the NLP complaint classifier.")
    parser.add_argument("--train", action="store_true", help="Train the model artifact from data")
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATA_PATH), help="Path to training JSON")
    parser.add_argument("--artifact", type=str, default=str(DEFAULT_ARTIFACT_PATH), help="Path to save joblib artifact")
    parser.add_argument("--predict", type=str, default=None, help="Predict label for a sample text")
    args = parser.parse_args()

    data_file = Path(args.data)
    art_file = Path(args.artifact)

    if args.train:
        print(f"Training NLP classifier on {data_file}...")
        pipeline, X_train, X_test, y_train, y_test = train_nlp_classifier(
            data_path=data_file,
            artifact_path=art_file,
            test_size=0.2,
            random_state=42,
        )
        print(f"[SUCCESS] Trained on {len(X_train)} samples. Saved to: {art_file}")

        try:
            from app.ml.evaluation import run_full_evaluation
            print("Evaluating NLP classifier on held-out test and challenge sets...")
            report = run_full_evaluation(
                train_data_path=data_file,
                artifact_path=art_file,
            )
            print(f"[SUCCESS] Evaluation complete. Test Accuracy: {report['test_partition_metrics']['accuracy']*100:.1f}%, Challenge Accuracy: {report['challenge_set_metrics']['accuracy']*100:.1f}%")
        except Exception as eval_exc:
            print(f"[WARNING] Could not auto-generate evaluation report: {eval_exc}")

    if args.predict:
        classifier = CivicNLPClassifier(artifact_path=art_file)
        res = classifier.predict(args.predict)
        print("Prediction result:", res.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
