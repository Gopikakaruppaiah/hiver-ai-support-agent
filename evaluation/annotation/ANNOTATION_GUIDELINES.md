# Golden Set Annotation Guidelines

## What you're doing

Labeling the **fixed 200-example golden evaluation set** at
`data/golden/golden_eval_200.csv`. This set was sampled from the original
300-candidate pool using the same stratification methodology (by message
length bucket and risk-keyword presence), proportionally scaled to 200 —
see `decision_log.md` D16. The 300-candidate pool is preserved separately,
untouched, at `data/golden/golden_pool_candidates.csv` in case it's useful
later; it is **not** what you're annotating.

**This 200-example set is now frozen.** The selection script
(`scripts/select_golden_eval_200.py`) refuses to regenerate it once any
annotation exists — your labels won't be invalidated by a later pipeline
re-run.

Use the tool:

```
evaluation/annotation/golden_annotation_tool.html
```

Open it directly in any browser (no server needed). It shows one example
at a time, the model's suggested intent in a **clearly separate, labeled
panel** (not pre-filled as your answer), lets you pick your own label,
and exports your progress as JSON/CSV whenever you want.

**You do not need to label all 200.** The assignment asks for 150-250,
and this set has exactly 200 — so label as many as you can, ideally all
200, but 150+ satisfies the requirement. The tool's progress bar tracks
this.

## Intent taxonomy (what you're choosing between)

| Intent | One-line definition | Example (real, from the dataset) |
|---|---|---|
| `fare_billing_dispute` | Customer believes they were charged incorrectly, or wants a refund/fee dispute resolved. | "My account was charged multiple times for one ride." |
| `driver_cancellation_noshow` | Driver cancelled, never arrived, or the app failed to complete a booking. | "why is it that I wait 30 mins for your driver to get lost, then cancel it without even notifying me?" |
| `driver_behavior_safety` | Unsafe driving, rude/abusive driver, harassment, or an accident involving a driver. | "Guys be safe out here some boy just pulled my uber guys bumper with his hand..." |
| `account_access_security` | Account hacked, disabled, locked; login/email problems; unauthorized use. | "My account got hacked! Help!!" |
| `lost_item` | Customer left a personal item in a vehicle and needs the driver contacted. | "need to get in touch with one of yur drivers left phone in the car" |
| `general_unresolved` | Generic dissatisfaction, "already messaged, no response," vague/ambiguous, or very short messages with no extractable issue. | "worst app ever" / "??" / "still waiting to hear back" |
| `OTHER_MULTI_INTENT` | Doesn't fit cleanly, or genuinely contains two-plus distinct issues that can't be reduced to one label. | "My order hasn't arrived and I was also charged twice." |

Full definitions with more examples and what does/doesn't belong in each
category: `docs/intent_taxonomy.md`.

## Deciding intent when it's ambiguous

- **Pick the most specific applicable category.** A message that's both
  vague AND mentions a charge should go to `fare_billing_dispute`, not
  `general_unresolved` — specificity wins.
- **Short/low-information messages** ("worst app ever", "??", "hi") →
  `general_unresolved` unless they clearly reference one of the 5 specific
  categories.
- **Multi-intent messages** → use `OTHER_MULTI_INTENT`, and use the notes
  field to name both issues, rather than forcing a single label.

## AUTO_HANDLE vs. ESCALATE — the exact rule to apply

Use this decision rule (matches the system's own escalation-engine logic,
so your labels are directly comparable to what the system currently does):

1. **Is the message very short or has no clear actionable content
   (roughly under 5 words, or genuinely unclear what's being asked)?**
   → **ESCALATE.** Too little information to safely resolve.
2. **Does it involve money (fares/charges/refunds), safety (unsafe
   driving, harassment, accidents), or account security (hacked/locked
   accounts)?** → **ESCALATE**, always, regardless of how simple it looks.
   The cost of a wrong auto-handled reply in these categories is too high.
3. **Otherwise** (routine cancellations, lost items, clear informational
   asks): → **AUTO_HANDLE** if you believe a reasonable, generic reply
   grounded in "here's what typically happens next" would genuinely
   resolve it without needing a human's judgment call; **ESCALATE** if you
   think it needs a human's judgment even though it's not
   financial/safety/security (e.g., a driver dispute that sounds like it
   could escalate into a complaint).

You are the ground truth here — if your judgment differs from this rule
in a specific case, follow your own judgment and note why. Disagreement
with the system's rule is useful signal for the failure analysis, not
something to suppress.

## Ambiguous / uncertain cases — how to mark them

The tool has a dedicated **"Mark as ambiguous/uncertain"** checkbox,
separate from the intent and escalation choices. Check it when:

- You genuinely could see two different, reasonable annotators disagreeing
  on this example.
- The message is a borderline call between two intents.
- You're not confident your escalation call is right.

**This does not block saving** — you still pick your best-guess intent
and escalation label, and the checkbox flags the example for extra
attention during failure analysis. It is explicitly supported and
recorded in the `human_uncertain` column (kept separate from
`OTHER_MULTI_INTENT`, which is about the intent taxonomy specifically,
whereas "uncertain" can apply to any example including a clean one where
you're just unsure about escalation).

## What NOT to do

- **Don't just accept the model's suggestion by default.** It's shown for
  speed, not because it's likely correct — it was generated by a simple
  keyword regex, not a validated classifier. Read the actual message.
- **Don't skip the escalation label** — both fields matter for the
  evaluation.
- **Don't worry about being "wrong."** There's no external right answer
  here except your own considered judgment; disagreement/difficulty notes
  are valuable data for the failure analysis, not something to smooth
  over.

## How to save / export your completed labels

1. In the tool, click **"⬇ Export progress (JSON)"** (preferred) or
   **"⬇ Export progress (CSV)"** at any point — including partway through,
   to checkpoint your work. The file downloads to your normal Downloads
   folder.
2. Your progress also auto-saves in the browser tab's local storage as you
   go (so refreshing the page won't lose work), but **the JSON/CSV export
   is the durable copy** — don't rely on the browser alone.
3. To resume a previous session in a fresh browser tab, use **"⬆ Import
   previous progress"** and select your last export.

## Exact command to run after annotation to calculate final metrics

Once you've exported your labels:

```bash
python3 evaluation/annotation/merge_labels.py path/to/golden_labels_export.json
```

This writes your `human_label_intent` / `human_escalation_label` /
`human_uncertain` / `annotator_notes` values into
`data/golden/golden_eval_200.csv` (only overwriting fields where your
export has a non-empty value — safe to run multiple times as you export
more).

Then, to compute the actual headline metrics:

```bash
python3 evaluation/baselines/run_baselines_human.py
```

This is the **only** command that produces real, human-verified metrics.
It will report exactly how many examples were labeled, intent
classification accuracy/precision/recall/F1 against your labels
(separately from the majority-class baseline), and — if you filled in
escalation labels — escalation precision/recall/F1 and the
missed-escalation rate. Results are written to
`reports/human_evaluation_results.json`, kept strictly separate from the
pseudo-label results in `reports/baseline_results.json`.

**No final metrics will be calculated or reported until you've actually
run this command against real labels** — running it now, before you
annotate, will (correctly) just say `PENDING_HUMAN_ANNOTATION`.

