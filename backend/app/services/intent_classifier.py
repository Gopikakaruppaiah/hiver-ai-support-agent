"""
Intent classifier service.

Loads the TF-IDF + Logistic Regression model persisted by
evaluation/baselines/run_baselines.py.

CAVEAT (surfaced to every caller, not buried): this model was trained on
RULE-BASED PSEUDO-LABELS, not human-verified labels (see decision_log.md
D6). Confidence scores below reflect the model's certainty about matching
the pseudo-labeler's patterns -- not a validated real-world accuracy.
"""
import json
import pickle
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from configs.config import MODELS_DIR

MENTION_RE = re.compile(r"@\w+")


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    alternatives: List[dict]
    reason: str
    caveat: str = "Model trained on rule-based pseudo-labels, not human-verified ground truth (PENDING HUMAN ANNOTATION)."


class IntentClassifier:
    def __init__(self):
        try:
            with open(MODELS_DIR / "intent_tfidf_vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(MODELS_DIR / "intent_logreg_model.pkl", "rb") as f:
                self.model = pickle.load(f)
            with open(MODELS_DIR / "intent_classes.json") as f:
                self.classes = json.load(f)
        except FileNotFoundError as e:
            raise RuntimeError(
                "Intent classifier model files not found in models/. "
                "Run 'python scripts/setup_check.py' (or "
                "'python evaluation/baselines/run_baselines.py' directly) to build them "
                f"before starting the server. Original error: {e}"
            ) from e

    def classify(self, text: str) -> IntentPrediction:
        cleaned = MENTION_RE.sub(" ", text)
        X = self.vectorizer.transform([cleaned])
        proba = self.model.predict_proba(X)[0]
        order = proba.argsort()[::-1]
        top_idx = order[0]
        top_intent = self.classes[top_idx]
        top_conf = float(proba[top_idx])

        alternatives = [
            {"intent": self.classes[i], "confidence": round(float(proba[i]), 3)}
            for i in order[1:3]
        ]
        reason = f"TF-IDF+LogisticRegression predicted '{top_intent}' with {top_conf:.0%} model confidence."
        return IntentPrediction(
            intent=top_intent, confidence=round(top_conf, 3),
            alternatives=alternatives, reason=reason,
        )
