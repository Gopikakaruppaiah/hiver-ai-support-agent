"""
Selects a FIXED 200-example golden EVALUATION set from the 300-candidate
pool, using the same stratification methodology as the original pool
(length_bucket x has_risk_keyword), proportionally scaled to 200.

This is the set that gets human-annotated and used for all final headline
metrics. The 300-candidate pool (data/golden/golden_pool_candidates.csv)
is preserved unchanged as a separate, larger reserve -- not deleted, not
touched -- in case it's useful later (e.g. expanding the eval set, extra
qualitative spot-checks).

HARD GUARD: refuses to (re)generate data/golden/golden_eval_200.csv if it
already exists and contains ANY human annotation (human_label_intent,
human_escalation_label, or human_uncertain). Once annotation begins, this
set is frozen -- per explicit instruction not to regenerate or alter
examples after annotation starts.

Run:
    python3 scripts/select_golden_eval_200.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
from configs.config import DATA_GOLDEN_DIR, RANDOM_SEED

POOL_PATH = DATA_GOLDEN_DIR / "golden_pool_candidates.csv"
EVAL_PATH = DATA_GOLDEN_DIR / "golden_eval_200.csv"
TARGET_SIZE = 200

ANNOTATION_COLS = ["human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes"]


def main():
    if EVAL_PATH.exists():
        existing = pd.read_csv(EVAL_PATH, dtype=str, keep_default_na=False, na_filter=False)
        has_annotation = False
        for col in ANNOTATION_COLS:
            if col in existing.columns and existing[col].str.len().gt(0).any():
                has_annotation = True
                break
        if has_annotation:
            raise RuntimeError(
                f"REFUSING TO REGENERATE: {EVAL_PATH} already has annotation data. "
                f"The 200-example golden evaluation set is frozen once annotation "
                f"begins. If you truly need to rebuild it, back up the existing "
                f"file first and understand this invalidates any labeling already done."
            )

    pool = pd.read_csv(POOL_PATH, dtype=str, keep_default_na=False, na_filter=False)
    assert len(pool) == 300, f"Expected 300-candidate pool, got {len(pool)} -- check data/golden/golden_pool_candidates.csv"

    rng_seed = RANDOM_SEED
    strata = pool.groupby(["length_bucket", "has_risk_keyword"], group_keys=False)

    # Proportional allocation: each stratum contributes floor(n_stratum * 200/300),
    # remainder distributed to the largest strata (by fractional remainder) to hit exactly 200.
    proportions = []
    for key, group in strata:
        exact = len(group) * TARGET_SIZE / len(pool)
        proportions.append({"key": key, "group": group, "exact": exact, "floor": int(np.floor(exact))})

    allocated = sum(p["floor"] for p in proportions)
    remainder = TARGET_SIZE - allocated
    # give the remainder to strata with the largest fractional part
    proportions.sort(key=lambda p: p["exact"] - p["floor"], reverse=True)
    for i in range(remainder):
        proportions[i]["floor"] += 1

    selected_frames = []
    for p in proportions:
        n_take = min(p["floor"], len(p["group"]))
        sampled = p["group"].sample(n=n_take, random_state=rng_seed)
        selected_frames.append(sampled)

    eval_df = pd.concat(selected_frames).sample(frac=1, random_state=rng_seed).reset_index(drop=True)
    assert len(eval_df) == TARGET_SIZE, f"Stratified selection produced {len(eval_df)}, expected {TARGET_SIZE}"

    for col in ["human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes"]:
        if col not in eval_df.columns:
            eval_df[col] = ""

    eval_df.to_csv(EVAL_PATH, index=False)

    print(f"Selected {len(eval_df)} examples for the fixed golden evaluation set -> {EVAL_PATH}")
    print(f"\nStratification (target vs actual):")
    for p in sorted(proportions, key=lambda x: x["key"]):
        actual = ((eval_df["length_bucket"] == p["key"][0]) & (eval_df["has_risk_keyword"] == p["key"][1])).sum()
        print(f"  {p['key']}: pool={len(p['group'])}, target={p['floor']}, actual_in_eval_set={actual}")

    print(f"\n300-candidate pool preserved unchanged at {POOL_PATH} (not touched, not deleted).")


if __name__ == "__main__":
    main()
