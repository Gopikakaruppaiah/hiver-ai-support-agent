"""
Phase 4b: Required baselines (assignment Sections 8-9).

CAVEAT (read before trusting these numbers): these baselines are
evaluated against RULE-BASED PSEUDO-LABELS (evaluation/baselines/pseudo_labeler.py),
not human-verified ground truth. The golden set has NOT been human-annotated
yet. Treat every metric below as "how well does this model reproduce the
heuristic labeler," not "how good is this at real intent classification."
Final, trustworthy metrics require re-running this same evaluation against
data/golden/golden_pool_candidates.csv once the `human_label_intent` column
is filled in.
"""
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, classification_report,
    confusion_matrix,
)
import json

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from configs.config import DATA_PROCESSED_DIR, RANDOM_SEED
import re

MENTION_RE = re.compile(r"@\w+")


def main():
    df = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
    # need pseudo-labels; regenerate inline to avoid import path pain
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pseudo_labeler import classify
    df["model_suggestion_intent"] = [
        classify(t, n) for t, n in zip(df["customer_text_clean"].astype(str), df["n_words"])
    ]

    X_text = df["customer_text_clean"].astype(str).map(lambda t: MENTION_RE.sub(" ", t))
    y = df["model_suggestion_intent"]

    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )
    print(f"Train: {len(X_train)}  Test: {len(X_test)}")

    results = {}

    # --- Baseline 1: trivial majority-class ---
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    pred_dummy = dummy.predict(X_test)
    acc = accuracy_score(y_test, pred_dummy)
    p, r, f1, _ = precision_recall_fscore_support(y_test, pred_dummy, average="macro", zero_division=0)
    results["majority_baseline"] = {"accuracy": acc, "macro_precision": p, "macro_recall": r, "macro_f1": f1}
    print("\n=== BASELINE 1: Majority Class ===")
    print(json.dumps(results["majority_baseline"], indent=2))

    # --- Baseline 2: TF-IDF + Logistic Regression ---
    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=3, stop_words="english")
    Xtr = vectorizer.fit_transform(X_train)
    Xte = vectorizer.transform(X_test)

    clf = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_SEED)
    clf.fit(Xtr, y_train)
    pred_lr = clf.predict(Xte)
    acc = accuracy_score(y_test, pred_lr)
    p, r, f1, _ = precision_recall_fscore_support(y_test, pred_lr, average="macro", zero_division=0)
    results["tfidf_logreg"] = {"accuracy": acc, "macro_precision": p, "macro_recall": r, "macro_f1": f1}
    print("\n=== BASELINE 2: TF-IDF + Logistic Regression ===")
    print(json.dumps(results["tfidf_logreg"], indent=2))
    print("\nPer-class report:")
    print(classification_report(y_test, pred_lr, zero_division=0))

    labels_sorted = sorted(y.unique())
    cm = confusion_matrix(y_test, pred_lr, labels=labels_sorted)
    cm_df = pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted)
    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(cm_df)

    # Persist the fitted vectorizer + classifier so the live pipeline can
    # reuse them (Phase 6). NOTE: trained on pseudo-labels -- see caveat below.
    import pickle
    MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODELS_DIR / "intent_tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(MODELS_DIR / "intent_logreg_model.pkl", "wb") as f:
        pickle.dump(clf, f)
    with open(MODELS_DIR / "intent_classes.json", "w") as f:
        json.dump(list(clf.classes_), f)

    out_dir = Path(__file__).resolve().parent.parent.parent / "reports"
    with open(out_dir / "baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    cm_df.to_csv(out_dir / "baseline2_confusion_matrix.csv")

    print("\n" + "=" * 70)
    print("REMINDER: metrics above are vs. pseudo-labels, not human ground truth.")
    print("Human-vs-model agreement: PENDING HUMAN ANNOTATION of golden set.")


if __name__ == "__main__":
    main()
