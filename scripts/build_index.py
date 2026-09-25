"""
Phase 5: Historical retrieval index.

Embedding model: spaCy `en_core_web_md` (GloVe-style static word vectors,
300-dim, mean-pooled over tokens per message). Chosen because:
  - Fully offline after one install: weights come from a GitHub release
    asset (release-assets.githubusercontent.com), not huggingface.co,
    which this sandbox cannot reach (see decision_log.md D4).
  - Small (~40MB), loads in ~1s, embeds ~47K short messages in seconds
    on CPU -- fits the assignment's <15min reproducibility target easily.
  - It is NOT a fine-tuned sentence-transformer. Word-averaging is a real,
    known-weaker technique for semantic similarity vs. paraphrased text.
    Sanity-checked below; see reports/embedding_model_card.md for the
    measured limitation.

We build TWO retrieval indexes for direct comparison:
  1. spaCy embeddings + FAISS (cosine via inner product on normalized vectors)
  2. TF-IDF + cosine similarity (the pre-existing baseline representation)

No retrieval QUALITY metrics (Recall@K, MRR, etc.) are computed here --
those require human-labeled "is this retrieved case actually relevant"
judgments, which do not exist yet. This script only builds the indexes
and runs qualitative spot-checks.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import spacy
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.config import DATA_PROCESSED_DIR, MODELS_DIR
import re

MENTION_RE = re.compile(r"@\w+")


def main():
    corpus = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
    texts_for_vec = corpus["customer_text_clean"].astype(str).map(lambda t: MENTION_RE.sub(" ", t)).tolist()
    n = len(texts_for_vec)
    print(f"Building retrieval indexes for {n} messages...")

    # --- 1. spaCy embeddings + FAISS ---
    print("\nLoading spaCy en_core_web_md ...")
    nlp = spacy.load("en_core_web_md", disable=["parser", "ner", "tagger", "lemmatizer", "attribute_ruler"])

    t0 = time.time()
    vectors = np.zeros((n, 300), dtype="float32")
    oov_count = 0
    for i, doc in enumerate(nlp.pipe(texts_for_vec, batch_size=256)):
        v = doc.vector
        if not doc.has_vector or np.linalg.norm(v) == 0:
            oov_count += 1
        vectors[i] = v
    embed_time = time.time() - t0
    print(f"Embedded {n} messages in {embed_time:.1f}s ({n/embed_time:.0f} msgs/sec). "
          f"Zero-vector (fully OOV) messages: {oov_count} ({100*oov_count/n:.2f}%)")

    # normalize for cosine similarity via inner product
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(300)
    index.add(vectors)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(MODELS_DIR / "spacy_faiss.index"))
    np.save(MODELS_DIR / "spacy_embeddings.npy", vectors)
    corpus[["example_id"]].to_csv(MODELS_DIR / "spacy_faiss_id_map.csv", index=False)

    # --- 2. TF-IDF + cosine (comparison baseline) ---
    print("\nBuilding TF-IDF cosine retrieval index...")
    t0 = time.time()
    tfidf = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=2, stop_words="english")
    X_tfidf = tfidf.fit_transform(texts_for_vec)
    nn = NearestNeighbors(metric="cosine", n_neighbors=5, algorithm="brute")
    nn.fit(X_tfidf)
    tfidf_build_time = time.time() - t0
    print(f"Built TF-IDF index ({X_tfidf.shape}) in {tfidf_build_time:.1f}s")

    import pickle
    with open(MODELS_DIR / "tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(tfidf, f)
    with open(MODELS_DIR / "tfidf_nn.pkl", "wb") as f:
        pickle.dump(nn, f)

    stats = {
        "n_messages_indexed": n,
        "spacy_model": "en_core_web_md",
        "embedding_dim": 300,
        "spacy_embed_time_sec": round(embed_time, 2),
        "spacy_embed_msgs_per_sec": round(n / embed_time, 1),
        "spacy_oov_zero_vector_count": oov_count,
        "spacy_oov_zero_vector_pct": round(100 * oov_count / n, 2),
        "tfidf_build_time_sec": round(tfidf_build_time, 2),
        "tfidf_vocab_size": len(tfidf.vocabulary_),
    }
    with open(Path(__file__).resolve().parent.parent / "reports" / "retrieval_index_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("\n" + json.dumps(stats, indent=2))

    # --- Qualitative spot-check: query with golden-pool examples (not indexed, safe to use as queries) ---
    golden = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_pool_candidates.csv")
    sample_queries = golden.sample(5, random_state=42)

    print("\n" + "=" * 70)
    print("QUALITATIVE SPOT-CHECK: spaCy+FAISS retrieval on 5 golden-pool queries")
    print("(golden pool was never indexed -- querying it against the corpus is safe, no leakage)")
    for _, row in sample_queries.iterrows():
        q_text = MENTION_RE.sub(" ", str(row["customer_text_clean"]))
        q_vec = nlp(q_text).vector.reshape(1, -1).astype("float32")
        faiss.normalize_L2(q_vec)
        D, I = index.search(q_vec, 3)
        print(f"\nQUERY: {row['customer_text_clean'][:120]}")
        for rank, (score, idx) in enumerate(zip(D[0], I[0]), 1):
            match = corpus.iloc[idx]
            print(f"  [{rank}] sim={score:.3f} | {match['customer_text_clean'][:100]}")
            print(f"        -> brand reply: {match['brand_text_clean'][:100]}")


if __name__ == "__main__":
    main()
