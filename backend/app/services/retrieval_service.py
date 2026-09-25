"""
Retrieval service — TF-IDF cosine similarity over the historical retrieval
corpus (primary method; see decision_log.md D8 for why TF-IDF was chosen
over the spaCy embeddings for this dataset).
"""
import pickle
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_BACKEND_DIR))
from configs.config import MODELS_DIR, DATA_PROCESSED_DIR
from app.core.llm_provider import EvidenceCase

MENTION_RE = re.compile(r"@\w+")


class RetrievalService:
    def __init__(self):
        try:
            with open(MODELS_DIR / "tfidf_vectorizer.pkl", "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(MODELS_DIR / "tfidf_nn.pkl", "rb") as f:
                self.nn = pickle.load(f)
            self.corpus = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
        except FileNotFoundError as e:
            raise RuntimeError(
                "Retrieval index files not found. Run 'python scripts/setup_check.py' "
                "(or 'python scripts/prepare_data.py' then 'python scripts/build_index.py' "
                f"directly) to build them before starting the server. Original error: {e}"
            ) from e

    def retrieve(self, query_text: str, k: int = 3) -> List[EvidenceCase]:
        cleaned = MENTION_RE.sub(" ", query_text)
        q_vec = self.vectorizer.transform([cleaned])
        dist, idxs = self.nn.kneighbors(q_vec, n_neighbors=min(k, len(self.corpus)))
        results = []
        for d, idx in zip(dist[0], idxs[0]):
            row = self.corpus.iloc[idx]
            results.append(EvidenceCase(
                example_id=row["example_id"],
                customer_text=row["customer_text_clean"],
                brand_text=row["brand_text_clean"],
                similarity=round(1 - d, 4),
            ))
        return results
