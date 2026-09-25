# Intent Taxonomy — Uber_Support (ride-hailing scope)

Discovered via: TF-IDF + KMeans clustering (2 passes, 2nd pass with
@mention tokens stripped from vectorization) on the 46,740-message
retrieval corpus, cross-checked against the 40 manually-read samples
from Phase 1. Not asserted upfront — refined from what the clusters
actually showed, including where they were messy.

---

## 1. Fare / Billing Dispute
- **Description**: Customer believes they were charged incorrectly — double charge, wrong fare amount, disputed cancellation fee, refund request.
- **Belongs**: "charged twice", "cancellation fee was unfair", "fare was higher than quoted", refund asks.
- **Does not belong**: general "your app is broken" (→ General/Unresolved) unless a specific charge is named.
- **Example (real)**: "@Uber_Support My account was charged multiple times for one ride."
- **Typical historical resolution**: agent asks for trip details/DM, promises to "look into it" — rarely a concrete resolution visible in the tweet itself.
- **Risk level**: High (financial).
- **Expected escalation behavior**: Escalate by default — financial commitments should not be auto-promised without human review.

## 2. Driver Cancellation / No-show
- **Description**: Driver cancelled, never arrived, or the app repeatedly failed to complete a booking.
- **Belongs**: "driver cancelled on me", "waited 20 minutes, no driver", ETA complaints.
- **Does not belong**: cancellation *fee* disputes (→ Fare/Billing) unless the message is purely about the no-show itself.
- **Example (real)**: "@Uber_Support why is it that I wait 30 mins for your driver to get lost, then cancel it without even notifying me?"
- **Risk level**: Low–Medium.
- **Expected escalation behavior**: Auto-handle candidate if historical evidence is strong (this is one of the most common, well-precedented issues in the corpus).

## 3. Driver Behavior / Safety Complaint
- **Description**: Unsafe driving, rude/abusive driver, harassment, accidents involving a driver.
- **Belongs**: "driver was rude", "unsafe driving", accident reports, harassment.
- **Does not belong**: routine cancellations with no behavior/safety complaint.
- **Example (real)**: "Guys be safe out here some boy just pulled my uber guys bumper with his hand..."
- **Risk level**: High (safety/legal).
- **Expected escalation behavior**: Always escalate — safety issues are never auto-handled in this system, regardless of confidence.

## 4. Account Access / Security Issue
- **Description**: Account hacked, disabled, locked; email/login problems; unauthorized use.
- **Belongs**: "my account was hacked", "can't log in", "someone else is using my account".
- **Example (real)**: "My @115873 account got hacked! Help!!"
- **Risk level**: High (security/financial exposure).
- **Expected escalation behavior**: Escalate by default — account security should not be auto-resolved.

## 5. Lost Item
- **Description**: Customer left a personal item (phone, bag, etc.) in a vehicle and needs the driver contacted.
- **Belongs**: "left my phone in the car", "driver has my item".
- **Example (real)**: "@Uber_Support need to get in touch with one of yur drivers left phone in the car how do we get in touch with Selvaraj."
- **Risk level**: Medium.
- **Expected escalation behavior**: Auto-handle candidate for the "how do I report a lost item" informational step; escalate if it requires direct driver contact/coordination.

## 6. General Inquiry / Unresolved Follow-up (catch-all)
- **Description**: Generic dissatisfaction, "I already messaged/DMed and got no response," vague complaints with no single identifiable issue, or ambiguous/very short messages.
- **Belongs**: "still waiting for a response", one-line insults, messages under ~4 words with no extractable issue.
- **Honest note**: this is the **largest bucket by far** (~45-50% of the corpus across both clustering passes). This is a real, load-bearing fact about this dataset, not a modeling failure to paper over — it will matter directly in the "what's misleading about my headline number" section, since a large share of "test" traffic is inherently low-information.
- **Risk level**: Unknown by construction (that's the point).
- **Expected escalation behavior**: Escalate by default — insufficient information to safely auto-handle.

---

### Explicitly out of scope
Uber Eats / food-delivery messages are excluded from this taxonomy entirely (see decision log D2), not folded into any category above.
