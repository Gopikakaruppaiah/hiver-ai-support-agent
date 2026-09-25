"""
Phase 4a: Intent discovery via TF-IDF + KMeans clustering on the
retrieval corpus (never touches the golden pool).

Outputs top terms + sample messages per cluster so a human (us) can
name/define each cluster into a small taxonomy grounded in real data,
per assignment Section 6.
"""
import sys
from pathlib import Path

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.config import DATA_PROCESSED_DIR, RANDOM_SEED

N_CLUSTERS = 8  # start slightly above target taxonomy size; merge similar ones after inspection

MENTION_RE = re.compile(r"@\w+")


def vectorizer_text(t: str) -> str:
    """Strip @mentions for CLUSTERING/VECTORIZATION only. Mentions here are
    either the brand handle (present in ~every message, zero signal) or
    anonymized numeric account IDs (e.g. @115873) that carry no lexical
    meaning about the issue -- but dominated TF-IDF top-terms in the first
    clustering pass. The original customer_text_clean (with mentions intact)
    is still what gets stored/displayed/used for reply generation."""
    return MENTION_RE.sub(" ", t)


def main():
    corpus = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
    texts = corpus["customer_text_clean"].astype(str).map(vectorizer_text).tolist()
    print(f"Clustering {len(texts)} retrieval-corpus messages into {N_CLUSTERS} clusters...")

    vectorizer = TfidfVectorizer(
        max_features=20000, stop_words="english", ngram_range=(1, 2), min_df=5
    )
    X = vectorizer.fit_transform(texts)
    print(f"TF-IDF matrix shape: {X.shape}")

    km = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_SEED, n_init=10)
    labels = km.fit_predict(X)
    corpus["cluster_id"] = labels

    terms = np.array(vectorizer.get_feature_names_out())
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]

    for c in range(N_CLUSTERS):
        size = (labels == c).sum()
        top_terms = terms[order_centroids[c, :12]]
        print(f"\n{'='*70}\nCLUSTER {c}  (n={size}, {100*size/len(labels):.1f}%)")
        print("Top terms:", ", ".join(top_terms))
        samples = corpus[corpus["cluster_id"] == c]["customer_text_clean"].sample(
            min(6, size), random_state=RANDOM_SEED
        )
        for s in samples:
            print("  -", s[:140])

    corpus.to_csv(DATA_PROCESSED_DIR / "retrieval_corpus_clustered.csv", index=False)
    # persist the fitted vectorizer's vocabulary size + cluster sizes for the report
    dist = pd.Series(labels).value_counts().sort_index()
    print(f"\n\nCluster size distribution:\n{dist}")


if __name__ == "__main__":
    main()
