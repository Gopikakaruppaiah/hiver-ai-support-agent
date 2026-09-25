"""
Golden-set annotation tool (Phase 7).

Terminal-based, resumable, saves after every example so nothing is lost.
Strictly separates `model_suggestion_intent` (pre-filled by the rule-based
labeler, to speed you up) from `human_label_intent` (what YOU decide) --
the two are never conflated (assignment Section 3).

Usage:
    python evaluation/annotation/annotate_golden.py

Controls at each example:
    <number>  - accept a taxonomy intent by number
    <enter>   - accept the model's suggested intent as-is
    s         - mark suggested escalation decision (prompts AUTO_HANDLE/ESCALATE)
    n         - add a free-text note (e.g. "ambiguous", "multi-intent")
    p         - go to previous example
    q         - save and quit (resumes from here next time)
"""
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_PATH = _REPO_ROOT / "data" / "golden" / "golden_pool_candidates.csv"

TAXONOMY = [
    "fare_billing_dispute",
    "driver_cancellation_noshow",
    "driver_behavior_safety",
    "account_access_security",
    "lost_item",
    "general_unresolved",
]


def load():
    df = pd.read_csv(GOLDEN_PATH, dtype=str)
    if "human_label_intent" not in df.columns:
        df["human_label_intent"] = ""
    if "human_escalation_label" not in df.columns:
        df["human_escalation_label"] = ""
    if "annotator_notes" not in df.columns:
        df["annotator_notes"] = ""
    df["human_label_intent"] = df["human_label_intent"].fillna("")
    df["human_escalation_label"] = df["human_escalation_label"].fillna("")
    df["annotator_notes"] = df["annotator_notes"].fillna("")
    return df


def save(df):
    df.to_csv(GOLDEN_PATH, index=False)


def main():
    df = load()
    n = len(df)
    done = (df["human_label_intent"] != "").sum()
    print(f"Golden pool: {n} candidates. {done} already labeled. {n - done} remaining.\n")

    # resume at first unlabeled example
    start = df[df["human_label_intent"] == ""].index.min()
    if pd.isna(start):
        print("All examples already labeled!")
        return
    i = int(start)

    while 0 <= i < n:
        row = df.loc[i]
        print("\n" + "=" * 80)
        print(f"[{i+1}/{n}]  example_id={row['example_id']}")
        print(f"CUSTOMER MESSAGE:\n  {row['customer_text_clean']}")
        print(f"\nMODEL SUGGESTION (not a human label): {row['model_suggestion_intent']}")
        print("\nTaxonomy:")
        for idx, t in enumerate(TAXONOMY, 1):
            print(f"  {idx}. {t}")
        if row["human_label_intent"]:
            print(f"\n(already labeled: {row['human_label_intent']})")

        choice = input("\nYour label [number / Enter=accept suggestion / s / n / p / q]: ").strip()

        if choice == "q":
            save(df)
            print("Saved. Resume anytime -- progress is kept.")
            return
        elif choice == "p":
            i = max(0, i - 1)
            continue
        elif choice == "n":
            note = input("Note: ").strip()
            df.at[i, "annotator_notes"] = note
            continue
        elif choice == "s":
            esc = input("Escalation label [AUTO_HANDLE / ESCALATE]: ").strip().upper()
            if esc in {"AUTO_HANDLE", "ESCALATE"}:
                df.at[i, "human_escalation_label"] = esc
            continue
        elif choice == "":
            df.at[i, "human_label_intent"] = row["model_suggestion_intent"]
        elif choice.isdigit() and 1 <= int(choice) <= len(TAXONOMY):
            df.at[i, "human_label_intent"] = TAXONOMY[int(choice) - 1]
        else:
            print("Unrecognized input, try again.")
            continue

        save(df)  # save after every example -- never lose progress
        i += 1

    save(df)
    print("\nAll examples labeled. Golden set annotation complete.")


if __name__ == "__main__":
    main()
