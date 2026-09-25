"""
Merge an exported annotation file (from golden_annotation_tool.html) back
into the canonical data/golden/golden_pool_candidates.csv.

Usage:
    python3 evaluation/annotation/merge_labels.py path/to/golden_labels_export.json
    python3 evaluation/annotation/merge_labels.py path/to/golden_labels_export.csv

Only fills in human_label_intent / human_escalation_label / annotator_notes
where the export has a non-empty value -- never overwrites an existing
human label with an empty one (so partial re-exports mid-session are safe).
"""
import json
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_PATH = _REPO_ROOT / "data" / "golden" / "golden_eval_200.csv"


def load_export(path: Path) -> pd.DataFrame:
    if path.suffix == ".json":
        records = json.loads(path.read_text())
        return pd.DataFrame(records)
    elif path.suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)
    else:
        raise ValueError(f"Unsupported export format: {path.suffix}")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    export_path = Path(sys.argv[1])
    export_df = load_export(export_path)

    golden_df = pd.read_csv(GOLDEN_PATH, dtype=str, keep_default_na=False, na_filter=False)
    for col in ["human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes"]:
        if col not in golden_df.columns:
            golden_df[col] = ""
        golden_df[col] = golden_df[col].fillna("")

    export_df = export_df.set_index("example_id")
    golden_df = golden_df.set_index("example_id")

    n_updated = 0
    for col in ["human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes"]:
        if col not in export_df.columns:
            continue
        new_vals = export_df[col].fillna("").astype(str)
        # only overwrite where the export has a non-empty value
        mask = new_vals.str.len() > 0
        overlap_idx = golden_df.index.intersection(new_vals[mask].index)
        n_updated += (golden_df.loc[overlap_idx, col] != new_vals.loc[overlap_idx]).sum()
        golden_df.loc[overlap_idx, col] = new_vals.loc[overlap_idx]

    golden_df = golden_df.reset_index()
    golden_df.to_csv(GOLDEN_PATH, index=False)

    n_labeled = (golden_df["human_label_intent"].astype(str).str.len() > 0).sum()
    print(f"Merged {export_path.name} into {GOLDEN_PATH}")
    print(f"Fields changed this merge: {n_updated}")
    print(f"Total examples with a human_label_intent now: {n_labeled} / {len(golden_df)}")


if __name__ == "__main__":
    main()
