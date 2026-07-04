# Clinician micro-form — G4-b monitoring-turn copy (closes W2)

**Context:** W2 PR #102 shipped the monitoring→supportive step-down MECHANICS (signed G4 criteria). The second signed-G4 half — **monitoring turns reading as warm conversation, not a repeated crisis card** (the F2 "sticky canned card" tester complaint) — is outstanding. This is crisis-path copy, so it needs a clinician wording sign-off (same pattern as G2). One checkbox.

## G4-b — monitoring-turn posture frame
**Decision:** how should a post-crisis *monitoring* turn read (the turns AFTER the initial crisis card, while `crisis_state="monitoring"`, before step-down to supportive)?

**Recommendation:** a ~40-word posture frame the LLM varies within — never the repeated card:

> _"You were talking with them about something heavy a little earlier. Open gently, let them know you're still here, and let the conversation go where they need it to. Don't re-ask what happened or re-list the crisis. Support is one tap away whenever they want it."_

**Invariants (non-negotiable, enforced separately from wording):**
- **Resources one tap away** — the helpline/support stays available via the pinned crisis card (UI), NOT re-pasted into every monitoring message.
- **No interrogation** — do not re-ask "what happened", do not re-enumerate the crisis.
- **`_EMPTY_MONITORING_FALLBACK` retained** — an empty model reply on a monitoring turn still surfaces resources (never silence); unchanged from today.
- **Re-escalation overrides** — this frame applies ONLY to a genuine monitoring turn. If S1/S3 fires or S7 returns NEW_CRISIS, that turn re-escalates to `crisis_response` and the frame does not apply (safety floor untouched).
- **Vary within the frame, never the card** — successive monitoring turns must not repeat verbatim (the F2 complaint).

☐ Approve as recommended  ☐ Amend wording: ______________

(On approval: implement as a monitoring-turn posture instruction injected into freeflow — same mechanism as G2's supportive_posture — with a test asserting successive monitoring turns are not the repeated card and the empty-fallback invariant holds. Closes W2.)

---

## NOT on this form — mood-trigger item withdrawn (fix-the-wrong-layer)
The earlier plan to draft `mood_check_in` trigger additions is **withdrawn**: measurement showed the triggers **already match locally** (`skill_select` offers `mood_check_in` for "how are you tracking my mood today" via `keyword_offer`). The mood-reachability gap is **upstream** — `intent_route` LLM-classifier consistency + the offer→accept flow, plus the AR classification case — **not** missing Node-4 keywords. It needs the **W6 measured pass** (multi-sample per phrase to handle classifier non-determinism), not a clinician trigger-pattern checkbox. Filed there; no clinician action.
