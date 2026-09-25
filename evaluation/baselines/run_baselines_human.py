"""
Real evaluation harness — computes intent classification AND escalation
metrics against data/golden/golden_eval_200.csv's human_label_intent
/ human_escalation_label columns.

Strictly separate from evaluation/baselines/run_baselines.py, which
evaluates against rule-based PSEUDO-labels. Results from this script go to
reports/human_evaluation_results.json; pseudo-label results stay in
reports/baseline_results.json. Never merged into one number.

If no human labels exist yet, this script says so explicitly and exits
without computing or printing any metric -- it does not fall back to
pseudo-labels silently.

Run:
    python3 evaluation/baselines/run_baselines_human.py
"""
import json
import pickle
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, classification_report,
    confusion_matrix,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_BACKEND_DIR))

from configs.config import DATA_GOLDEN_DIR, MODELS_DIR, DATA_PROCESSED_DIR

MENTION_RE = re.compile(r"@\w+")


def main():
    golden_path = DATA_GOLDEN_DIR / "golden_eval_200.csv"
    df = pd.read_csv(golden_path, dtype=str, keep_default_na=False, na_filter=False)

    labeled = df[df["human_label_intent"].str.len() > 0].copy()
    n_labeled = len(labeled)

    print(f"Golden EVALUATION set (fixed, 200): {len(df)} examples total, {n_labeled} human-labeled.")
    n_uncertain = (df["human_uncertain"].str.len() > 0).sum() if "human_uncertain" in df.columns else 0
    if n_uncertain:
        print(f"  ({n_uncertain} marked ambiguous/uncertain by the annotator)")

    if n_labeled == 0:
        result = {
            "status": "PENDING_HUMAN_ANNOTATION",
            "n_labeled": 0,
            "message": (
                "No human_label_intent values found in data/golden/golden_eval_200.csv. "
                "Open evaluation/annotation/golden_annotation_tool.html in a browser, "
                "label examples, export, then run "
                "evaluation/annotation/merge_labels.py <export_file>, then re-run this script."
            ),
        }
        out_path = _REPO_ROOT / "reports" / "human_evaluation_results.json"
        out_path.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return

    # --- Intent classification metrics vs. human labels ---
    with open(MODELS_DIR / "intent_tfidf_vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(MODELS_DIR / "intent_logreg_model.pkl", "rb") as f:
        clf = pickle.load(f)

    X_text = labeled["customer_text_clean"].astype(str).map(lambda t: MENTION_RE.sub(" ", t))
    X = vectorizer.transform(X_text)
    y_true = labeled["human_label_intent"]
    y_pred = clf.predict(X)

    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)

    # majority-class baseline, using the pseudo-labeled retrieval corpus's
    # class distribution as the fixed prediction (matches what a real
    # production majority-baseline would use, since it can't see test labels)
    corpus = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
    corpus_labels_path = MODELS_DIR / "intent_classes.json"
    # simplest honest majority baseline: most frequent human label IN THIS
    # labeled set is not fair (that's fit-on-test); use the retrieval
    # corpus's pseudo-label distribution instead, consistent with training data
    sys.path.insert(0, str(_REPO_ROOT / "evaluation" / "baselines"))
    from pseudo_labeler import classify as pseudo_classify
    corpus["model_suggestion_intent"] = [
        pseudo_classify(t, n) for t, n in zip(corpus["customer_text_clean"].astype(str), corpus["n_words"])
    ]
    majority_class = Counter(corpus["model_suggestion_intent"]).most_common(1)[0][0]
    y_pred_majority = [majority_class] * len(y_true)
    acc_maj = accuracy_score(y_true, y_pred_majority)
    pm, rm, f1m, _ = precision_recall_fscore_support(y_true, y_pred_majority, average="macro", zero_division=0)

    print("\n=== INTENT CLASSIFICATION vs. HUMAN LABELS (real evaluation) ===")
    print(f"n = {n_labeled}")
    print(f"\nMajority-class baseline (predicts '{majority_class}' always):")
    print(json.dumps({"accuracy": acc_maj, "macro_precision": pm, "macro_recall": rm, "macro_f1": f1m}, indent=2))
    print(f"\nTF-IDF + Logistic Regression (production classifier):")
    print(json.dumps({"accuracy": acc, "macro_precision": p, "macro_recall": r, "macro_f1": f1}, indent=2))
    print("\nPer-class report:")
    print(classification_report(y_true, y_pred, zero_division=0))

    labels_sorted = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels_sorted)
    cm_df = pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted)
    print("\nConfusion matrix (rows=true human label, cols=predicted):")
    print(cm_df)

    # --- Escalation metrics vs. human labels (if provided) ---
    escalation_result = None
    esc_labeled = labeled[labeled["human_escalation_label"].str.len() > 0]
    if len(esc_labeled) > 0:
        sys.path.insert(0, str(_BACKEND_DIR))
        from app.services.escalation_engine import decide
        from app.services.retrieval_service import RetrievalService
        retrieval = RetrievalService()

        y_true_esc, y_pred_esc = [], []
        for _, row in esc_labeled.iterrows():
            text = row["customer_text_clean"]
            n_words = len(text.split())
            X_row = vectorizer.transform([MENTION_RE.sub(" ", text)])
            proba = clf.predict_proba(X_row)[0]
            pred_intent = clf.classes_[proba.argmax()]
            pred_conf = float(proba.max())
            evidence = retrieval.retrieve(text, k=3)
            decision = decide(pred_intent, pred_conf, evidence, n_words)
            y_true_esc.append(row["human_escalation_label"])
            y_pred_esc.append(decision.decision)

        esc_acc = accuracy_score(y_true_esc, y_pred_esc)
        esc_p, esc_r, esc_f1, _ = precision_recall_fscore_support(
            y_true_esc, y_pred_esc, average="binary", pos_label="ESCALATE", zero_division=0
        )
        # missed-escalation rate: human said ESCALATE, system said AUTO_HANDLE (the dangerous case)
        missed = sum(1 for t, p_ in zip(y_true_esc, y_pred_esc) if t == "ESCALATE" and p_ == "AUTO_HANDLE")
        n_should_escalate = sum(1 for t in y_true_esc if t == "ESCALATE")
        missed_rate = missed / n_should_escalate if n_should_escalate else None

        escalation_result = {
            "n_labeled": len(esc_labeled),
            "accuracy": esc_acc,
            "escalate_precision": esc_p,
            "escalate_recall": esc_r,
            "escalate_f1": esc_f1,
            "missed_escalation_rate": missed_rate,
            "missed_escalation_count": missed,
            "n_should_escalate": n_should_escalate,
        }
        print("\n=== ESCALATION DECISION vs. HUMAN LABELS (real evaluation) ===")
        print(json.dumps(escalation_result, indent=2))
    else:
        print("\n=== ESCALATION DECISION ===\nNo human_escalation_label values found -- skipped.")

    result = {
        "status": "SCORED",
        "n_labeled": n_labeled,
        "n_golden_pool_total": len(df),
        "intent_classification": {
            "majority_baseline": {"accuracy": acc_maj, "macro_precision": pm, "macro_recall": rm, "macro_f1": f1m,
                                   "majority_class_used": majority_class},
            "tfidf_logreg": {"accuracy": acc, "macro_precision": p, "macro_recall": r, "macro_f1": f1},
        },
        "escalation": escalation_result,
        "note": "This is REAL evaluation against human-verified labels, kept separate from "
                "reports/baseline_results.json (which is vs. rule-based pseudo-labels).",
    }
    out_path = _REPO_ROOT / "reports" / "human_evaluation_results.json"
    out_path.write_text(json.dumps(result, indent=2))
    cm_df.to_csv(_REPO_ROOT / "reports" / "human_eval_confusion_matrix.csv")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
