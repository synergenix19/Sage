# D5 is downstream of crisis recall — one gate, not two

**Date:** 2026-06-24 · **Status:** safety-architecture statement · **Binding on the D5 flip decision**
**Cross-ref:** D5 evidence `2026-06-24-d5-task6-evidence.md` · governance B1 `2026-06-24-conversational-style-signoff.md` · safety baseline (memory: *Safety Detection Baseline*, *S2/MARBERT Crisis Classifier*, *Passive-SI Detection Gap*).

## The statement
**D5's flip is gated on the same crisis-recall critical path that gates pilot. It is one gate, not two. D5 must not be flipped ahead of crisis recall closing — even if its other three conditions are met.**

## Why — D5 is not a tone feature with a crisis dependency bolted on
D5 changes how Sage responds **only on turns that route to freeflow**. Its instruction at peak distress is to **contain**: validate, stay supportive, do not challenge, do not probe. That is the correct behaviour for non-crisis acute distress — and the **wrong** behaviour for a crisis turn, which needs **active escalation and resources**, not containment.

So D5's safety depends entirely on a prior guarantee it does not itself provide: **that passive-SI / crisis turns have already been pulled OUT of freeflow by the crisis gate before D5 ever sees them.** D5 sits *downstream* of that routing decision. It cannot recover a misroute; it can only calmly contain it.

**Containing passive-SI is not the same as routing it.** That distinction is the whole safety case.

## Live proof (not hypothetical)
In the multi-turn durability probe (`2026-06-24-d5-task6-evidence.md`, Round 2), the pushback escalated to:
> "everyone would be doing better without me weighing them down"
That is burdensomeness / passive-SI — a turn that **should route to crisis**. Forced into freeflow, **D5 merely contained it** (validate, stay supportive, present-focused check-in). No escalation, no resources. If the live crisis classifier under-detects that turn at the freeflow boundary, D5 will do exactly this in production: respond warmly and calmly to someone who needed a crisis response.

## What this means for the flip conditions
D5's flip condition 1 — **crisis-gate false-negative rate at the freeflow boundary** — is **not a separate D5 check**. It **is** the existing crisis-recall critical path:
- CRADLE bench recall ~37.1% / self-harm recall well below KPI
- S2 / MARBERT crisis classifier **unbuilt**
- passive-SI recall **unmeasured** (the exact turn-3 class above)
- pilot gate already fails-closed on crisis recall

**Therefore D5's flip is downstream of pilot crisis recall.** Tracking it as a separate D5 condition invites it to be "closed" by a thin D5-specific check while the real recall gap stays open. It must be tracked as **the same gate**.

## The failure mode this document exists to prevent
Three of D5's four conditions (refined wording, multi-turn durability, AR cultural review, confusion matrix) are D5-local and closeable by this team. Condition 1 is **not** — it is the crisis-recall program, and it is not ours to close alone. The risk is that a future engineer or a PO under delivery pressure reads "D5 is three conditions from done," clears those three, and **flips D5 while crisis recall is still open** — putting containment behaviour on misrouted crisis turns at exactly the moment it does the most harm.

**The honest status is not "D5 is N conditions from done." It is: "D5 cannot flip until crisis recall closes (condition 1, not ours to close alone), plus three D5-local conditions."** Crisis recall leads; D5 follows.

## Operational rule
- `SAGE_D5_ACUITY_GATE` stays OFF until **all four** conditions clear, and **condition 1 (crisis recall) is a hard prerequisite** — the other three may complete in any order but **do not, on their own, authorise the flip**.
- Any future proposal to flip D5 must cite the **current crisis-recall recall number at the freeflow boundary** alongside the D5-local evidence. A flip proposal without that number is incomplete by construction.
- This gate is recorded in the D5 governance (B1) and in memory so it survives context loss and staff change.
