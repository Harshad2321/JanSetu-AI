"""
JanSetu AI — NLP Model Evaluation Runner (Phase 4, P4.3).

Computes real evaluation metrics from actual predictions of the trained NLP classifier on:
1. Held-out test partition (stratified split with random_state=42)
2. Distinct challenge set (non-overlapping vocabulary and phrasing)

Computes:
- Accuracy
- Macro-F1
- Per-class precision
- Per-class recall
- Confusion matrix
- Evaluated sample counts

Saves verified metrics to eval/nlp_metrics.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

from app.ml.nlp_classifier import (
    DEFAULT_ARTIFACT_PATH,
    DEFAULT_DATA_PATH,
    MODEL_NAME,
    MODEL_VERSION,
    VALID_CATEGORIES,
    CivicNLPClassifier,
    train_nlp_classifier,
)

logger = logging.getLogger("jansetu.ml.evaluation")

DEFAULT_EVAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "eval"
DEFAULT_EVAL_OUTPUT = DEFAULT_EVAL_DIR / "nlp_metrics.json"
DEFAULT_CHALLENGE_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic_complaints_challenge.json"


def evaluate_dataset(
    classifier: CivicNLPClassifier,
    texts: List[str],
    true_labels: List[str],
    classes: List[str] = VALID_CATEGORIES,
) -> Dict[str, Any]:
    """
    Runs real inference over texts and computes accuracy, macro-F1, per-class
    precision/recall, and confusion matrix against true labels.
    """
    if not classifier.is_available:
        raise RuntimeError("Classifier model artifact is not available. Cannot evaluate.")

    if len(texts) != len(true_labels):
        raise ValueError(f"Mismatch between texts ({len(texts)}) and labels ({len(true_labels)})")

    if not texts:
        raise ValueError("Cannot evaluate an empty dataset.")

    # Real predictions
    pred_results = [classifier.predict(t) for t in texts]
    y_pred: List[str] = []
    for r in pred_results:
        if not r.available or r.predicted_label is None:
            raise RuntimeError(f"Prediction failed during evaluation: {r.error}")
        y_pred.append(r.predicted_label)

    # Calculate actual metrics
    acc = float(accuracy_score(true_labels, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        true_labels, y_pred, average="macro", labels=classes, zero_division=0
    )
    p_class, r_class, f1_class, support = precision_recall_fscore_support(
        true_labels, y_pred, average=None, labels=classes, zero_division=0
    )
    cm = confusion_matrix(true_labels, y_pred, labels=classes).tolist()

    per_class_metrics: Dict[str, Dict[str, float]] = {}
    for i, cls_name in enumerate(classes):
        per_class_metrics[cls_name] = {
            "precision": float(round(p_class[i], 4)),
            "recall": float(round(r_class[i], 4)),
            "f1": float(round(f1_class[i], 4)),
            "support": int(support[i]),
        }

    return {
        "num_samples": len(texts),
        "accuracy": float(round(acc, 4)),
        "macro_f1": float(round(f1_macro, 4)),
        "macro_precision": float(round(p_macro, 4)),
        "macro_recall": float(round(r_macro, 4)),
        "per_class": per_class_metrics,
        "confusion_matrix": {
            "classes": classes,
            "matrix": cm,
        },
    }


def run_full_evaluation(
    train_data_path: Path = DEFAULT_DATA_PATH,
    challenge_data_path: Path = DEFAULT_CHALLENGE_DATA_PATH,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
    output_path: Path = DEFAULT_EVAL_OUTPUT,
    random_state: int = 42,
    retrain_if_missing: bool = True,
) -> Dict[str, Any]:
    """
    Executes real evaluation across:
    1. Held-out test split (20% of train dataset via stratified split)
    2. Distinct challenge set
    
    Writes structured, verified metrics to output_path.
    """
    if not train_data_path.exists():
        raise FileNotFoundError(f"Train data file does not exist at: {train_data_path}")

    # Retrain or ensure model artifact exists
    if not artifact_path.exists():
        if retrain_if_missing:
            logger.info("Artifact not found at %s. Fitting model now...", artifact_path)
            train_nlp_classifier(
                data_path=train_data_path,
                artifact_path=artifact_path,
                test_size=0.2,
                random_state=random_state,
            )
        else:
            raise FileNotFoundError(f"Classifier artifact missing: {artifact_path}")

    classifier = CivicNLPClassifier(artifact_path=artifact_path)
    if not classifier.is_available:
        raise RuntimeError("Classifier could not be loaded for evaluation.")

    # Load training dataset and regenerate exact held-out test split using random_state=42
    with open(train_data_path, "r", encoding="utf-8") as f:
        train_records = json.load(f)

    train_texts = [r["text"] for r in train_records]
    train_labels = [r["label"] for r in train_records]

    _, X_test, _, y_test = train_test_split(
        train_texts,
        train_labels,
        test_size=0.2,
        random_state=random_state,
        stratify=train_labels,
    )

    # 1. Evaluate held-out test partition
    test_metrics = evaluate_dataset(
        classifier=classifier,
        texts=X_test,
        true_labels=y_test,
        classes=VALID_CATEGORIES,
    )

    # 2. Evaluate distinct challenge partition
    if not challenge_data_path.exists():
        raise FileNotFoundError(f"Challenge data file does not exist at: {challenge_data_path}")

    with open(challenge_data_path, "r", encoding="utf-8") as f:
        challenge_records = json.load(f)

    challenge_texts = [r["text"] for r in challenge_records]
    challenge_labels = [r["label"] for r in challenge_records]

    challenge_metrics = evaluate_dataset(
        classifier=classifier,
        texts=challenge_texts,
        true_labels=challenge_labels,
        classes=VALID_CATEGORIES,
    )

    # Assemble comprehensive evaluation report
    report: Dict[str, Any] = {
        "model_name": MODEL_NAME,
        "model_version": classifier.model_version,
        "classes": VALID_CATEGORIES,
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "test_partition_metrics": test_metrics,
        "challenge_set_metrics": challenge_metrics,
        "synthetic_poc_disclaimer": (
            "Results measure performance strictly on synthetic data for academic Proof of Concept demonstration. "
            "These metrics do not represent real-world municipal classification accuracy."
        ),
    }

    # Save to eval/nlp_metrics.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Successfully wrote evaluation metrics to %s", output_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NLP evaluation on test and challenge sets.")
    parser.add_argument("--train-data", type=str, default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--challenge-data", type=str, default=str(DEFAULT_CHALLENGE_DATA_PATH))
    parser.add_argument("--artifact", type=str, default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--output", type=str, default=str(DEFAULT_EVAL_OUTPUT))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = run_full_evaluation(
        train_data_path=Path(args.train_data),
        challenge_data_path=Path(args.challenge_data),
        artifact_path=Path(args.artifact),
        output_path=Path(args.output),
        random_state=args.seed,
    )

    print("\n================== NLP EVALUATION SUMMARY ==================")
    print(f"Model: {report['model_name']} ({report['model_version']})")
    print(f"Held-out Test Samples: {report['test_partition_metrics']['num_samples']}")
    print(f"Test Accuracy:         {report['test_partition_metrics']['accuracy'] * 100:.2f}%")
    print(f"Test Macro-F1:         {report['test_partition_metrics']['macro_f1']:.4f}")
    print(f"Challenge Set Samples: {report['challenge_set_metrics']['num_samples']}")
    print(f"Challenge Accuracy:    {report['challenge_set_metrics']['accuracy'] * 100:.2f}%")
    print(f"Challenge Macro-F1:    {report['challenge_set_metrics']['macro_f1']:.4f}")
    print(f"Output saved to:       {args.output}")
    print("============================================================\n")


if __name__ == "__main__":
    main()
