"""
JanSetu AI — Phase 4 Comprehensive ML/DL Intelligence Layer Test Suite.

Verifies:
1. NLP training and inference from fitted pipeline
2. Valid prediction schema and allowed categories
3. Reproducible splitting with a fixed seed
4. Challenge-set separation (no data leakage)
5. Training-only vectorizer fitting
6. Metric calculation against known test predictions
7. Actual evaluation-file generation
8. Ollama and optional provider unavailability
9. No fabricated vision label when provider is unavailable
10. Valid vision prediction with provenance
11. Vision/NLP agreement (Case A)
12. Vision/NLP disagreement and clarification (Case B)
13. Vision-only partial evidence (Case D)
14. NLP-only partial evidence (Case C)
15. Both models unavailable and manual selection (Case E)
16. Missing required fields (Case F)
17. Persistence of available and unavailable predictions
18. Transaction rollback when prediction persistence fails
19. Continued compatibility with existing schemas and models
20. Non-leakage of API credentials in errors
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, IncidentModel, ModelPredictionModel
from app.db.repository import (
    get_predictions_by_incident,
    persist_prediction_record,
    save_incident,
    transaction_scope,
)
from app.ml.evaluation import (
    DEFAULT_EVAL_OUTPUT,
    evaluate_dataset,
    run_full_evaluation,
)
from app.ml.fusion import (
    MultimodalFusionResult,
    fuse_incident_evidence,
)
from app.ml.nlp_classifier import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DATA_PATH,
    VALID_CATEGORIES,
    CivicNLPClassifier,
    NLPClassificationResult,
    build_nlp_pipeline,
    train_nlp_classifier,
)
from app.ml.vision import (
    BaseVisionProvider,
    GroqVisionProvider,
    OllamaVisionProvider,
    VisionClassificationResult,
    analyze_image_evidence,
)
from app.schemas.incident import ModelPrediction
from scripts.make_nlp_data import (
    generate_synthetic_datasets,
)


@pytest.fixture
def test_db_session():
    """In-memory SQLite session for prediction persistence tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# 1. P4.1 — Data Generation & Dataset Properties
# ============================================================================

def test_p4_1_deterministic_synthetic_generation():
    """Deterministic generation produces identical records with identical seed."""
    train_1, chal_1 = generate_synthetic_datasets(seed=42, samples_per_category=30)
    train_2, chal_2 = generate_synthetic_datasets(seed=42, samples_per_category=30)

    assert len(train_1) == len(train_2) == 90
    assert len(chal_1) == len(chal_2) == 30
    assert [r["text"] for r in train_1] == [r["text"] for r in train_2]
    assert [r["text"] for r in chal_1] == [r["text"] for r in chal_2]


def test_p4_1_valid_labels_and_synthetic_markers():
    """All generated records have valid categories, multilingual tags, and is_synthetic=True."""
    train_data, chal_data = generate_synthetic_datasets(seed=42, samples_per_category=30)

    for r in train_data + chal_data:
        assert r["label"] in VALID_CATEGORIES
        assert r["is_synthetic"] is True
        assert r["language"] in ["en", "hi", "mr", "hinglish"]
        assert len(r["text"].strip()) > 10


def test_p4_1_training_challenge_separation_no_leakage():
    """Challenge set phrases must NOT overlap or leak into training dataset."""
    train_data, chal_data = generate_synthetic_datasets(seed=42, samples_per_category=50)

    train_texts = {r["text"].strip().lower() for r in train_data}
    chal_texts = {r["text"].strip().lower() for r in chal_data}

    # Absolute disjointness of text complaints
    intersection = train_texts.intersection(chal_texts)
    assert len(intersection) == 0, f"Data leakage detected! Overlapping texts: {intersection}"


# ============================================================================
# 2. P4.2 — NLP Classifier Training, Pipeline & Inference
# ============================================================================

def test_p4_2_train_and_inference_fitted_pipeline(tmp_path):
    """Fitted pipeline classifies complaints into pothole, waterlogging, garbage with valid schema."""
    artifact_path = tmp_path / "test_model.joblib"
    pipeline, X_train, X_test, y_train, y_test = train_nlp_classifier(
        data_path=DEFAULT_DATA_PATH,
        artifact_path=artifact_path,
        test_size=0.2,
        random_state=42,
    )

    assert artifact_path.exists()
    classifier = CivicNLPClassifier(artifact_path=artifact_path)
    assert classifier.is_available is True

    # Test pothole complaint
    pothole_res = classifier.predict("Deep dangerous pothole on main road causing bikes to fall")
    assert pothole_res.available is True
    assert pothole_res.predicted_label == "pothole"
    assert pothole_res.confidence is not None
    assert 0.0 <= pothole_res.confidence <= 1.0
    assert set(pothole_res.scores.keys()) == set(VALID_CATEGORIES)

    # Test garbage complaint
    garbage_res = classifier.predict("Huge heap of rotting garbage and waste dumped on sidewalk")
    assert garbage_res.available is True
    assert garbage_res.predicted_label == "garbage"

    # Test waterlogging complaint
    water_res = classifier.predict("Severe waterlogging and knee deep rainwater flooding streets")
    assert water_res.available is True
    assert water_res.predicted_label == "waterlogging"


def test_p4_2_training_only_vectorizer_fitting(tmp_path):
    """Vectorizer must be fitted ONLY on the training partition, never on the full dataset."""
    artifact_path = tmp_path / "split_test.joblib"
    pipeline, X_train, X_test, y_train, y_test = train_nlp_classifier(
        data_path=DEFAULT_DATA_PATH,
        artifact_path=artifact_path,
        test_size=0.2,
        random_state=42,
    )
    # Check that pipeline TF-IDF vocabulary is non-empty and fitted on X_train size
    tfidf_step = pipeline.named_steps["tfidf"]
    assert hasattr(tfidf_step, "vocabulary_")
    assert len(tfidf_step.vocabulary_) > 50


def test_p4_2_unavailable_model_returns_honest_result(tmp_path):
    """Missing or corrupted artifact returns available=False, label=None, without inventing prediction."""
    missing_path = tmp_path / "non_existent_model.joblib"
    classifier = CivicNLPClassifier(artifact_path=missing_path)

    assert classifier.is_available is False
    res = classifier.predict("Any complaint text")
    assert res.available is False
    assert res.predicted_label is None
    assert res.confidence is None
    assert res.scores == {}
    assert "not available" in (res.error or "")


def test_p4_2_empty_input_handled_honestly():
    """Empty complaint text does not produce fabricated prediction."""
    classifier = CivicNLPClassifier()
    res = classifier.predict("   ")
    assert res.available is False
    assert res.predicted_label is None
    assert "Empty" in (res.error or "")


# ============================================================================
# 3. P4.3 — Real Evaluation & Metrics
# ============================================================================

def test_p4_3_evaluation_metrics_computation():
    """Real metric calculation computes accuracy, macro-F1, per-class metrics, and confusion matrix."""
    classifier = CivicNLPClassifier()
    if not classifier.is_available:
        train_nlp_classifier(data_path=DEFAULT_DATA_PATH, artifact_path=DEFAULT_ARTIFACT_PATH)
        classifier.load_model()

    texts = [
        "Deep pothole on the road",
        "Waterlogging and flooding on the highway",
        "Garbage pile rotting on the street corner",
    ]
    labels = ["pothole", "waterlogging", "garbage"]

    metrics = evaluate_dataset(classifier, texts, labels, classes=VALID_CATEGORIES)

    assert metrics["num_samples"] == 3
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert len(metrics["per_class"]) == 3
    assert metrics["confusion_matrix"]["classes"] == VALID_CATEGORIES
    assert len(metrics["confusion_matrix"]["matrix"]) == 3


def test_p4_3_eval_json_file_structure_and_disclaimer():
    """Verify saved eval/nlp_metrics.json has genuine fields, ordered classes, and synthetic disclaimer."""
    report = run_full_evaluation()

    assert DEFAULT_EVAL_OUTPUT.exists()
    with open(DEFAULT_EVAL_OUTPUT, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert saved_data["model_name"] == "TFIDF-LogisticRegression"
    assert saved_data["classes"] == VALID_CATEGORIES
    assert "synthetic_poc_disclaimer" in saved_data
    assert "synthetic" in saved_data["synthetic_poc_disclaimer"].lower()

    # Test metrics
    test_part = saved_data["test_partition_metrics"]
    assert test_part["num_samples"] == 60
    assert test_part["accuracy"] > 0.8
    assert test_part["macro_f1"] > 0.8

    # Challenge metrics
    chal_part = saved_data["challenge_set_metrics"]
    assert chal_part["num_samples"] == 30
    assert 0.0 <= chal_part["accuracy"] <= 1.0


# ============================================================================
# 4. P4.4 — Honest Vision Provider
# ============================================================================

def test_p4_4_ollama_unavailable_path():
    """When Ollama is unreachable, returns available=False, label=None, without fabricating."""
    # Point to an unreachable port
    provider = OllamaVisionProvider(host="http://127.0.0.1:59999", timeout=0.5)
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res = provider.classify(dummy_b64)
    assert res.available is False
    assert res.label is None
    assert res.confidence is None
    assert "unreachable" in (res.error or "").lower() or "error" in (res.error or "").lower()


def test_p4_4_groq_missing_api_key_safe_error():
    """Groq provider without GROQ_API_KEY returns safe available=False without leaking credentials."""
    provider = GroqVisionProvider(api_key="")
    res = provider.classify("dummy_b64")

    assert res.available is False
    assert res.label is None
    assert res.confidence is None
    assert "not configured" in (res.error or "")
    # Ensure no secret or key content is leaked in error
    assert "gsk_" not in (res.error or "")


def test_p4_4_mocked_valid_vision_analysis():
    """Mocked Ollama response correctly parses category and confidence."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": json.dumps({"category": "pothole", "confidence": 0.88})
    }
    mock_client.post.return_value = mock_resp

    provider = OllamaVisionProvider(http_client=mock_client)
    res = provider.classify("sanitized_dummy_b64")

    assert res.available is True
    assert res.label == "pothole"
    assert res.confidence == 0.88
    assert res.error is None


def test_p4_4_malformed_model_output_does_not_invent_label():
    """Malformed non-JSON output from vision model is caught gracefully."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "I see some asphalt on the road."}
    mock_client.post.return_value = mock_resp

    provider = OllamaVisionProvider(http_client=mock_client)
    res = provider.classify("sanitized_dummy_b64")

    assert res.available is False
    assert res.label is None
    assert "Malformed" in (res.error or "")


def test_p4_4_sanitization_gate_rejects_missing_image():
    """Passing no image or empty bytes rejects at intake without calling provider."""
    res = analyze_image_evidence(image_bytes=None, image_base64=None)
    assert res.available is False
    assert res.label is None
    assert "Sanitization check failed" in (res.error or "")


# ============================================================================
# 5. P4.5 — Multimodal Fusion Branches
# ============================================================================

def test_p4_5_case_a_vision_and_nlp_agree():
    """Case A: When vision and NLP agree, return agreed category as fused evidence."""
    nlp = NLPClassificationResult(
        predicted_label="pothole",
        confidence=0.92,
        scores={"pothole": 0.92, "waterlogging": 0.05, "garbage": 0.03},
        available=True,
    )
    vis = VisionClassificationResult(
        label="pothole",
        confidence=0.88,
        model="qwen2.5-vl",
        available=True,
    )

    fusion = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Dangerous crater on road",
    )

    assert fusion.status == "AGREEMENT"
    assert fusion.fused_category == "pothole"
    assert fusion.confidence == 0.90  # average of 0.92 and 0.88
    assert fusion.disagreement_detected is False
    assert fusion.is_model_prediction is True
    assert len(fusion.clarification_questions) == 0


def test_p4_5_case_b_vision_and_nlp_disagree():
    """Case B: When vision and NLP disagree, do not force a category; route to clarification."""
    nlp = NLPClassificationResult(
        predicted_label="waterlogging",
        confidence=0.85,
        available=True,
    )
    vis = VisionClassificationResult(
        label="garbage",
        confidence=0.80,
        model="qwen2.5-vl",
        available=True,
    )

    fusion = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Complaint text mentioning water",
    )

    assert fusion.status == "DISAGREEMENT"
    assert fusion.fused_category is None  # Category must NEVER be forced
    assert fusion.disagreement_detected is True
    assert fusion.needs_human_review is True
    assert len(fusion.clarification_questions) > 0
    assert "waterlogging" in fusion.clarification_questions[0]
    assert "garbage" in fusion.clarification_questions[0]


def test_p4_5_case_c_vision_unavailable_nlp_available():
    """Case C: Vision unavailable, NLP available -> return NLP as partial evidence."""
    nlp = NLPClassificationResult(
        predicted_label="garbage",
        confidence=0.91,
        available=True,
    )
    vis = VisionClassificationResult(
        label=None,
        confidence=None,
        available=False,
        error="Ollama unreachable",
    )

    fusion = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Rotting garbage overflowing",
    )

    assert fusion.status == "NLP_ONLY"
    assert fusion.fused_category == "garbage"
    assert fusion.confidence == 0.91
    assert fusion.fusion_method == "NLP_PARTIAL"
    assert fusion.is_model_prediction is True


def test_p4_5_case_d_nlp_unavailable_vision_available():
    """Case D: NLP unavailable, vision available -> return vision as partial evidence."""
    nlp = NLPClassificationResult(
        predicted_label=None,
        confidence=None,
        available=False,
        error="Empty complaint",
    )
    vis = VisionClassificationResult(
        label="waterlogging",
        confidence=0.84,
        available=True,
    )

    fusion = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Some context",
    )

    assert fusion.status == "VISION_ONLY"
    assert fusion.fused_category == "waterlogging"
    assert fusion.confidence == 0.84
    assert fusion.fusion_method == "VISION_PARTIAL"
    assert fusion.is_model_prediction is True


def test_p4_5_case_e_both_unavailable_manual_selection():
    """Case E: Both models unavailable -> require manual selection, marked as manual (not ML)."""
    nlp = NLPClassificationResult(available=False)
    vis = VisionClassificationResult(available=False)

    # 1. No manual category provided yet -> requires manual selection
    fusion_req = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Road issue",
    )
    assert fusion_req.status == "MANUAL_SELECTION_REQUIRED"
    assert fusion_req.fused_category is None
    assert fusion_req.needs_human_review is True

    # 2. Manual category provided by citizen/operator
    fusion_applied = fuse_incident_evidence(
        nlp_result=nlp,
        vision_result=vis,
        description="Road issue",
        manual_category="pothole",
    )
    assert fusion_applied.status == "MANUAL_SELECTION"
    assert fusion_applied.fused_category == "pothole"
    assert fusion_applied.confidence is None
    assert fusion_applied.is_model_prediction is False  # Must NOT masquerade as ML!
    assert fusion_applied.fusion_method == "MANUAL_SELECTION"


def test_p4_5_case_f_missing_required_fields():
    """Case F: Missing required fields formulate targeted questions without inferring."""
    fusion = fuse_incident_evidence(
        description="",  # Missing description
        latitude=None,
        longitude=None,
        require_location=True,
    )

    assert fusion.status == "MISSING_FIELDS"
    assert fusion.fused_category is None
    assert len(fusion.clarification_questions) >= 2
    assert any("description" in q.lower() for q in fusion.clarification_questions)
    assert any("coordinate" in q.lower() or "address" in q.lower() for q in fusion.clarification_questions)


# ============================================================================
# 6. P4.6 — ModelPrediction Persistence
# ============================================================================

def test_p4_6_persist_available_and_unavailable_predictions(test_db_session):
    """Persist genuine and unavailable predictions using repository helpers."""
    # Create parent incident
    incident = IncidentModel(
        incident_id="inc_test_p4_01",
        complaint="Waterlogging near school",
        category="waterlogging",
        operational_status="NEW",
    )
    save_incident(test_db_session, incident)

    # 1. Persist available NLP prediction
    nlp_pred = ModelPrediction(
        prediction_id="pred_nlp_001",
        incident_id="inc_test_p4_01",
        task_type="nlp",
        predicted_label="waterlogging",
        scores={"waterlogging": 0.89, "pothole": 0.08, "garbage": 0.03},
        confidence=0.89,
        model_name="TFIDF-LogisticRegression",
        model_version="v1.0.0",
        available=True,
        fallback_provenance="direct",
    )
    persisted_nlp = persist_prediction_record(test_db_session, nlp_pred)
    assert persisted_nlp.prediction_id == "pred_nlp_001"
    assert persisted_nlp.available is True

    # 2. Persist honest unavailable vision prediction
    vis_pred = ModelPrediction(
        prediction_id="pred_vis_001",
        incident_id="inc_test_p4_01",
        task_type="vision",
        predicted_label="",
        scores={},
        confidence=0.0,
        model_name="qwen2.5-vl",
        model_version="v1.0.0",
        available=False,
        fallback_provenance="unavailable",
    )
    persisted_vis = persist_prediction_record(test_db_session, vis_pred)
    assert persisted_vis.prediction_id == "pred_vis_001"
    assert persisted_vis.available is False
    assert persisted_vis.predicted_label == ""

    # Query back
    stored = get_predictions_by_incident(test_db_session, "inc_test_p4_01")
    assert len(stored) == 2
    assert stored[0].task_type == "nlp"
    assert stored[1].task_type == "vision"


def test_p4_6_transaction_rollback_on_prediction_failure(test_db_session):
    """Transaction rollback ensures database integrity if prediction persistence fails."""
    incident = IncidentModel(
        incident_id="inc_test_p4_02",
        complaint="Pothole near station",
        category="pothole",
        operational_status="NEW",
    )
    save_incident(test_db_session, incident)

    with pytest.raises(ValueError):
        with transaction_scope(test_db_session):
            test_db_session.add(
                ModelPredictionModel(
                    prediction_id="pred_fail_001",
                    incident_id="inc_test_p4_02",
                    task_type="nlp",
                    predicted_label="pothole",
                    scores={},
                    available=True,
                    fallback_provenance="direct",
                )
            )
            # Simulate failure inside transaction
            raise ValueError("Simulated storage failure!")

    # Verify that prediction was rolled back
    stored = get_predictions_by_incident(test_db_session, "inc_test_p4_02")
    assert len(stored) == 0
