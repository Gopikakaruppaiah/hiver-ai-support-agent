"""Direct side-by-side comparison of the two retrieval methods on identical
queries, to honestly assess whether the 'semantic' embedding approach is
actually beating simple lexical TF-IDF on this short, boilerplate-heavy
Twitter data."""
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import spacy
import faiss

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.config import DATA_PROCESSED_DIR, MODELS_DIR

MENTION_RE = re.compile(r"@\w+")

corpus = pd.read_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv")
golden = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "golden" / "golden_pool_candidates.csv")

nlp = spacy.load("en_core_web_md", disable=["parser", "ner", "tagger", "lemmatizer", "attribute_ruler"])
index = faiss.read_index(str(MODELS_DIR / "spacy_faiss.index"))

with open(MODELS_DIR / "tfidf_vectorizer.pkl", "rb") as f:
    tfidf = pickle.load(f)
with open(MODELS_DIR / "tfidf_nn.pkl", "rb") as f:
    nn = pickle.load(f)

sample_queries = golden.sample(5, random_state=42)

for _, row in sample_queries.iterrows():
    q_raw = str(row["customer_text_clean"])
    q_text = MENTION_RE.sub(" ", q_raw)
    print(f"\n{'='*80}\nQUERY: {q_raw[:110]}")

    # spaCy+FAISS
    q_vec = nlp(q_text).vector.reshape(1, -1).astype("float32")
    faiss.normalize_L2(q_vec)
    D, I = index.search(q_vec, 3)
    print("-- spaCy+FAISS top-3 --")
    for score, idx in zip(D[0], I[0]):
        print(f"   sim={score:.3f} | {corpus.iloc[idx]['customer_text_clean'][:95]}")

    # TF-IDF cosine
    q_tfidf = tfidf.transform([q_text])
    dist, idxs = nn.kneighbors(q_tfidf, n_neighbors=3)
    print("-- TF-IDF cosine top-3 --")
    for d, idx in zip(dist[0], idxs[0]):
        print(f"   sim={1-d:.3f} | {corpus.iloc[idx]['customer_text_clean'][:95]}")
