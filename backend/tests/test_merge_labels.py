import importlib
import json
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "evaluation" / "annotation"))


def test_merge_labels_only_fills_nonempty_and_preserves_existing(tmp_path, monkeypatch):
    import merge_labels

    # Isolated temp copy of the real golden CSV structure/size -- NOT the real file.
    real_golden = _REPO_ROOT / "data" / "golden" / "golden_eval_200.csv"
    temp_golden = tmp_path / "golden_eval_200.csv"
    shutil.copy(real_golden, temp_golden)

    monkeypatch.setattr(merge_labels, "GOLDEN_PATH", temp_golden)

    import pandas as pd
    df = pd.read_csv(temp_golden, dtype=str)
    first_id = df.iloc[0]["example_id"]
    second_id = df.iloc[1]["example_id"]

    # synthetic TEST FIXTURE labels -- not real human judgments, isolated to tmp_path
    export = [
        {"example_id": first_id, "human_label_intent": "lost_item",
         "human_escalation_label": "ESCALATE", "annotator_notes": "test note"},
        {"example_id": second_id, "human_label_intent": "",
         "human_escalation_label": "", "annotator_notes": ""},
    ]
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(export))

    sys.argv = ["merge_labels.py", str(export_path)]
    merge_labels.main()

    result = pd.read_csv(temp_golden, dtype=str, keep_default_na=False, na_filter=False)
    row0 = result[result["example_id"] == first_id].iloc[0]
    row1 = result[result["example_id"] == second_id].iloc[0]

    assert row0["human_label_intent"] == "lost_item"
    assert row0["human_escalation_label"] == "ESCALATE"
    # empty export values must NOT overwrite (here: still empty, since original was empty)
    assert row1["human_label_intent"] == ""
