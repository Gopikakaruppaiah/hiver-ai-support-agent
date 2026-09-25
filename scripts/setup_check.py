"""
One-command setup: checks prerequisites, builds all runtime artifacts
(TF-IDF/LogReg model, retrieval indexes, intent taxonomy pseudo-labels,
golden evaluation set) if they don't already exist. Safe to re-run --
skips any step whose output already exists, and never touches the golden
evaluation set once it has real annotation (the underlying scripts guard
that themselves).

Run this once after cloning, before starting the backend:
    python scripts/setup_check.py
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from configs.config import DATA_RAW, MODELS_DIR, DATA_PROCESSED_DIR, DATA_GOLDEN_DIR

PY = sys.executable  # use the exact same interpreter running this script


def check(label, condition, fix_hint):
    status = "OK" if condition else "MISSING"
    print(f"  [{status}] {label}")
    if not condition:
        print(f"           -> {fix_hint}")
    return condition


def run_step(label, cmd):
    print(f"\n>>> {label}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"\nFAILED: {label} (exit code {result.returncode})")
        sys.exit(1)


def main():
    print("=" * 70)
    print("Hiver AI Support Agent — setup check")
    print("=" * 70)

    print("\n--- Step 1: Prerequisites ---")
    raw_ok = check(
        "Raw dataset (data/raw/twcs.csv)",
        DATA_RAW.exists(),
        "Download 'Customer Support on Twitter' from Kaggle "
        "(https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) "
        f"and place twcs.csv at: {DATA_RAW}",
    )
    if not raw_ok:
        print("\nCannot continue without the raw dataset. Fix the above and re-run.")
        sys.exit(1)

    try:
        import sklearn, spacy, faiss, pandas, fastapi  # noqa: F401
    except ImportError as e:
        print(f"\n  [MISSING] Python dependency: {e}")
        print("           -> Run: pip install -r backend/requirements.txt")
        sys.exit(1)
    print("  [OK] Python dependencies importable")

    try:
        spacy.load("en_core_web_md")
        print("  [OK] spaCy en_core_web_md model installed")
    except OSError:
        print("  [MISSING] spaCy en_core_web_md model")
        print("           -> Run: pip install "
              "https://github.com/explosion/spacy-models/releases/download/"
              "en_core_web_md-3.7.1/en_core_web_md-3.7.1-py3-none-any.whl")
        sys.exit(1)

    print("\n--- Step 2: Build pipeline artifacts (skips steps already done) ---")

    retrieval_corpus = DATA_PROCESSED_DIR / "retrieval_corpus.csv"
    golden_eval = DATA_GOLDEN_DIR / "golden_eval_200.csv"
    golden_pool = DATA_GOLDEN_DIR / "golden_pool_candidates.csv"
    intent_model = MODELS_DIR / "intent_logreg_model.pkl"
    faiss_index = MODELS_DIR / "spacy_faiss.index"
    tfidf_retrieval = MODELS_DIR / "tfidf_nn.pkl"

    if not retrieval_corpus.exists() or not golden_pool.exists():
        run_step("Data pipeline (filter, clean, split)", [PY, "scripts/prepare_data.py"])
    else:
        print("  [SKIP] Data pipeline already built (data/processed/retrieval_corpus.csv exists)")

    if "model_suggestion_intent" not in _read_header(golden_pool):
        run_step("Pseudo-labeling (intent suggestions)", [PY, "evaluation/baselines/pseudo_labeler.py"])
    else:
        print("  [SKIP] Pseudo-labels already present")

    if not golden_eval.exists():
        run_step("Fixed 200-example golden evaluation set", [PY, "scripts/select_golden_eval_200.py"])
    else:
        print("  [SKIP] Golden evaluation set already exists (frozen if annotation has begun)")

    if not intent_model.exists():
        run_step("Baselines (majority-class, TF-IDF+LogReg) + persist classifier", [PY, "evaluation/baselines/run_baselines.py"])
    else:
        print("  [SKIP] Intent classifier already trained")

    if not faiss_index.exists() or not tfidf_retrieval.exists():
        run_step("Retrieval indexes (spaCy+FAISS, TF-IDF)", [PY, "scripts/build_index.py"])
    else:
        print("  [SKIP] Retrieval indexes already built")

    annotation_tool = REPO_ROOT / "evaluation" / "annotation" / "golden_annotation_tool.html"
    if not annotation_tool.exists():
        run_step("Annotation tool (HTML)", [PY, "evaluation/annotation/build_annotation_tool.py"])
    else:
        print("  [SKIP] Annotation tool already built")

    print("\n" + "=" * 70)
    print("Setup complete. Start the backend with:")
    print(f"  {PY} -m uvicorn backend.app.main:app --reload --port 8000")
    print("=" * 70)


def _read_header(csv_path: Path) -> str:
    if not csv_path.exists():
        return ""
    with open(csv_path) as f:
        return f.readline()


if __name__ == "__main__":
    main()
