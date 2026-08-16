# TICKET 2026-07-16 — Promote `mania_behavior_underway` to a `safety_check` flag (post-CF-007-ratification)

**Owner:** HR-1 workstream. **Priority:** medium. **Trigger (do NOT start before this):** CF-007 (`mania_disclosure`) is ratified by clinical lead and activated (`active:true` + `approved_by`).

## The interim (current state, Stage 2)
`high_risk_response_node` computes `mania_behavior_underway(disclosure_message)` **inside the terminal node** at T1 entry (`src/sage_poc/safety/hr_distress.py`), to set `hr_escalate_regardless`. This is a phrase-class match — i.e. *detection* — running in a terminal, re-checking a message Node 1 (`safety_check`) already saw. It duplicates the spending/risk-taking subset of CF-007's patterns.

## Why it is an interim, not the target
The architectural principle is **detection lives in Node 1**; the terminal should read a flag, not re-detect. The clean design is: `safety_check` emits a `mania_behavior_underway` flag (a CF-007 refinement or derived flag), the terminal reads it via the persisted `hr_escalate_regardless` channel.

**Why it is NOT done now:** CF-007 ships `active:false` / unsigned pending clinician ratification. Emitting a live Node-1 flag *now* would make routing code depend on **unratified clinical authority** — a #270-class inversion (active/authoritative behavior running ahead of sign-off). So the honest interim is: the node computes the load-bearing subset itself, documented as interim with this promotion condition named in-code (`hr_distress.py` module docstring).

## The refinement (this ticket)
When CF-007 activates: (1) emit `mania_behavior_underway` from `safety_check` (rules-engine flag, governed like every other clinical flag), (2) have `high_risk_response_node` read it instead of re-matching the disclosure text, (3) delete the verbatim phrase-copy from `hr_distress.py`, keeping only the reply-parsing detectors (`parse_distress`, `risk_language`) which legitimately belong to the node (they parse the *reply*, which Node 1 lacks the protocol context to interpret).

## Acceptance
No phrase-class *detection* of the original disclosure remains inside any terminal node; `mania_behavior_underway` is a `safety_check`-emitted flag; the Finding-1 critical case (manic user, low self-reported score, behavior underway → higher-severity) still passes end-to-end.
