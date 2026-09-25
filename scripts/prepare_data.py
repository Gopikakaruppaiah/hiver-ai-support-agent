"""
Phase 3 data pipeline.

Raw Twitter CSV -> validated, cleaned, brand-filtered, ride-scoped,
leakage-safe golden-pool / retrieval-corpus split.

Run:
    python scripts/prepare_data.py

All numbers this script prints are computed from the real dataset --
nothing here is a placeholder or an assumed value.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.config import (
    DATA_RAW, DATA_PROCESSED_DIR, DATA_GOLDEN_DIR, BRAND_NAME,
    EATS_EXCLUSION_KEYWORDS, RANDOM_SEED, GOLDEN_POOL_SIZE,
    MIN_CUSTOMER_MSG_CHARS,
)

URL_RE = re.compile(r"https?://\S+")
WHITESPACE_RE = re.compile(r"\s+")

RISK_KEYWORDS = [
    "charge", "charged", "refund", "money", "fee", "fare", "bank",
    "safe", "safety", "unsafe", "assault", "harass", "danger", "police",
    "lost", "left my", "accident",
]


def clean_text(raw: str) -> str:
    """Light-touch cleaning: strip URLs and normalize whitespace only.
    We deliberately do NOT strip @mentions/hashtags -- they can carry
    meaning (e.g. product mentions) and destroying them risks losing
    information the reply-generation step might need (assignment Sec 5)."""
    t = URL_RE.sub("", raw)
    t = WHITESPACE_RE.sub(" ", t).strip()
    return t


def is_probably_eats(text: str) -> bool:
    low = f" {text.lower()} "
    return any(kw in low for kw in EATS_EXCLUSION_KEYWORDS)


def length_bucket(n_words: int) -> str:
    if n_words <= 5:
        return "short"
    if n_words <= 25:
        return "medium"
    return "long"


def has_risk_keyword(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in RISK_KEYWORDS)


def main():
    stats = {}
    rng = np.random.default_rng(RANDOM_SEED)

    print(f"Loading raw dataset from {DATA_RAW} ...")
    df = pd.read_csv(
        DATA_RAW,
        dtype={"tweet_id": "int64", "author_id": str,
               "response_tweet_id": str, "in_response_to_tweet_id": str},
        low_memory=False,
    )
    stats["raw_rows_total"] = int(len(df))

    df["parent_id"] = pd.to_numeric(df["in_response_to_tweet_id"], errors="coerce")
    tw = df.set_index("tweet_id", drop=False)

    # 1. Resolved pairs: brand outbound reply -> its customer (inbound) parent
    brand_out = df[(df["author_id"] == BRAND_NAME) & (df["inbound"] == False)].copy()
    stats["brand_outbound_tweets_total"] = int(len(brand_out))

    parents = tw.reindex(brand_out["parent_id"].dropna().unique())
    valid_parents = parents[(parents["tweet_id"].notna()) & (parents["inbound"] == True)]

    # build pair table: one row per resolved (customer_msg, brand_reply)
    parent_lookup = valid_parents["text"].to_dict()
    parent_id_set = set(valid_parents.index)

    brand_out = brand_out[brand_out["parent_id"].isin(parent_id_set)].copy()
    pairs = pd.DataFrame({
        "customer_tweet_id": brand_out["parent_id"].astype("int64").values,
        "brand_tweet_id": brand_out["tweet_id"].values,
        "customer_text_raw": brand_out["parent_id"].map(parent_lookup).values,
        "brand_text_raw": brand_out["text"].values,
        "customer_created_at": brand_out["parent_id"].map(valid_parents["created_at"].to_dict()).values,
    })
    stats["resolved_customer_brand_pairs"] = int(len(pairs))

    # 2. Clean text
    pairs["customer_text_clean"] = pairs["customer_text_raw"].astype(str).map(clean_text)
    pairs["brand_text_clean"] = pairs["brand_text_raw"].astype(str).map(clean_text)

    # 3. Drop unusable (too short after cleaning)
    before = len(pairs)
    pairs = pairs[pairs["customer_text_clean"].str.len() >= MIN_CUSTOMER_MSG_CHARS].copy()
    stats["dropped_too_short"] = int(before - len(pairs))

    # 4. Exact-duplicate customer message dedup (keep first occurrence)
    before = len(pairs)
    pairs = pairs.drop_duplicates(subset=["customer_text_clean"], keep="first").copy()
    stats["dropped_exact_duplicate_customer_text"] = int(before - len(pairs))

    # 5. Scope to ride-hailing only: exclude probable Uber Eats messages
    pairs["is_probable_eats"] = pairs["customer_text_clean"].map(is_probably_eats)
    stats["excluded_as_probable_eats"] = int(pairs["is_probable_eats"].sum())
    eats_examples = pairs[pairs["is_probable_eats"]]["customer_text_clean"].head(10).tolist()
    rides = pairs[~pairs["is_probable_eats"]].copy()
    stats["rides_scope_final_count"] = int(len(rides))

    # 6. Feature tags used for stratified golden sampling (not model features)
    rides["n_words"] = rides["customer_text_clean"].str.split().apply(len)
    rides["length_bucket"] = rides["n_words"].map(length_bucket)
    rides["has_risk_keyword"] = rides["customer_text_clean"].map(has_risk_keyword)
    rides = rides.reset_index(drop=True)
    rides["example_id"] = ["UBER-" + str(i).zfill(6) for i in range(len(rides))]

    # 7. Stratified golden-pool reservation (BEFORE any modeling/retrieval-index
    #    building) to guarantee zero leakage into training/retrieval corpus.
    strata = rides.groupby(["length_bucket", "has_risk_keyword"], group_keys=False)
    n_strata = rides.groupby(["length_bucket", "has_risk_keyword"]).ngroups
    per_stratum = max(1, GOLDEN_POOL_SIZE // n_strata)

    golden_idx = []
    for _, group in strata:
        take = min(len(group), per_stratum)
        sampled = group.sample(n=take, random_state=RANDOM_SEED)
        golden_idx.extend(sampled.index.tolist())

    golden_idx = list(dict.fromkeys(golden_idx))  # de-dup, preserve order
    # top up to GOLDEN_POOL_SIZE if strata gave us fewer, from remaining pool
    if len(golden_idx) < GOLDEN_POOL_SIZE:
        remaining = rides.index.difference(golden_idx)
        extra_n = min(GOLDEN_POOL_SIZE - len(golden_idx), len(remaining))
        extra = pd.Index(remaining).to_series().sample(n=extra_n, random_state=RANDOM_SEED).index
        golden_idx.extend(extra.tolist())
    golden_idx = golden_idx[:GOLDEN_POOL_SIZE]

    golden_pool = rides.loc[golden_idx].copy()
    retrieval_corpus = rides.drop(index=golden_idx).copy()

    # 8. Leakage check: verify zero text overlap between golden pool and retrieval corpus
    overlap = set(golden_pool["customer_text_clean"]) & set(retrieval_corpus["customer_text_clean"])
    stats["golden_retrieval_text_overlap_count"] = int(len(overlap))
    assert len(overlap) == 0, "Leakage detected between golden pool and retrieval corpus!"

    stats["golden_pool_size"] = int(len(golden_pool))
    stats["retrieval_corpus_size"] = int(len(retrieval_corpus))
    stats["golden_pool_length_bucket_distribution"] = golden_pool["length_bucket"].value_counts().to_dict()
    stats["golden_pool_risk_keyword_distribution"] = golden_pool["has_risk_keyword"].value_counts().to_dict()

    # --- Persist ---
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    DATA_GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    golden_out_path = DATA_GOLDEN_DIR / "golden_pool_candidates.csv"
    if golden_out_path.exists():
        existing = pd.read_csv(golden_out_path, dtype=str)
        if "human_label_intent" in existing.columns and existing["human_label_intent"].fillna("").str.len().gt(0).any():
            n_labeled = existing["human_label_intent"].fillna("").str.len().gt(0).sum()
            raise RuntimeError(
                f"REFUSING TO OVERWRITE: {golden_out_path} already contains {n_labeled} "
                f"human-labeled examples. Re-running prepare_data.py would destroy real "
                f"annotation work. If you really intend to rebuild the golden pool from "
                f"scratch, move or back up the existing file first."
            )

    keep_cols = ["example_id", "customer_tweet_id", "brand_tweet_id",
                 "customer_text_raw", "customer_text_clean",
                 "brand_text_raw", "brand_text_clean",
                 "customer_created_at", "n_words", "length_bucket", "has_risk_keyword"]

    retrieval_corpus[keep_cols].to_csv(DATA_PROCESSED_DIR / "retrieval_corpus.csv", index=False)
    golden_pool[keep_cols].to_csv(DATA_GOLDEN_DIR / "golden_pool_candidates.csv", index=False)

    with open(Path(__file__).resolve().parent.parent / "reports" / "data_pipeline_stats.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    print(json.dumps(stats, indent=2, default=str))
    print("\nSample excluded-as-Eats messages (for spot-checking the heuristic):")
    for e in eats_examples:
        print(" -", e[:120])


if __name__ == "__main__":
    main()
