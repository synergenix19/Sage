# TICKET 2026-07-15 — CI gate: active safety rule implies signed (two-directional invariant)

**Owner:** whoever holds #270. **Priority:** high (it's the control that prevents the #270 class recurring).

## Problem
`signed_clinical_fields.json` + `check_signed_fields.py` enforce **one direction**: a *signed* field cannot change without a new hash + sign-off in the same PR. But the #270 finding (16 rules `active:true` with no sign-off) is the **other direction** — an active safety rule that was never signed. The current gate does not catch it. A one-directional gate on a two-directional invariant.

## Fix
Extend the CI check so it **fails on `active: true` + missing/`approved:false` sign-off** for any `authored_by` clinical rule, exactly as it fails on an unsigned change to a pinned field. Concretely:
- Enumerate every rule with `active: true` under `rules/data/**` authored by a clinical author.
- For each, require a sign-off record (approved:true + a signoff reference in the manifest).
- CI red if any active rule lacks it. Same forcing function, opposite direction.

This makes "a safety rule's approval AND activation state changed" impossible to merge unremarked — catching both #270 (active-but-not-signed) and the original signed-but-clobbered class in one gate. (Matches the manifest's own `v2_scope` note.)

## Non-goal
Not deciding the 16 rules' dispositions — that's the clinical triage (`2026-07-15-270-unsigned-active-safety-rules.md`). This ticket is the gate that stops the next 16.
