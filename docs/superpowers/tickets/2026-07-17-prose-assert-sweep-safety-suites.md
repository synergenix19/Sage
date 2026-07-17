# Ticket (QUEUED, not a blocker): sweep safety suites for assert-on-PROSE tests before they drift

**Base rate just went up.** The loader-gate audit predicted a silent-failure class and found it —
and worse than a coverage gap: an actual LIVE RED (`test_medical_redflag_guard::test_honesty_notes_ship_verbatim`,
asserting a stale copy string #329 changed). That test drifted red because it (a) was ungated and
(b) asserts on a PROSE string rather than behavior — the standing anti-pattern
([[feedback_assert_on_behavior_not_prose]]). Two terminals (psychosis loader, medical honesty note)
exhibited it in one audit. That is a strong signal the pattern is not unique to them.

**The sweep.** After the medical P0 and Node-8 land, one focused pass: grep the safety suites
(`tests/test_*crisis*`, `*medical*`, `*hr*`, `*harm*`, `*ocd*`, `*containment*`, `*safety*`) for
assertions anchored on copy/prose strings (e.g. `assert "…" in reply`, `== "<user-facing string>"`,
honesty-note / disclosure / template equality). For each: is it asserting BEHAVIOR (the guard fires /
routes / the disclosure reflects reality) or a literal STRING (drifts the moment copy changes)?
Re-anchor the string ones on behavior, or convert to a signed-field manifest pin if the exact bytes
genuinely must not change without sign-off (`signed_clinical_fields.json` is the right home for
must-not-drift copy, NOT a brittle test-string equality).

**⚠️ INTEGRITY ≠ ACCURACY — build the pin with the right framing or it becomes the prose-assert trap
relocated.** A `signed_clinical_fields.json` hash-pin guarantees the shipped copy MATCHES the signed
value (nobody changed the disclosure without re-signing) — it does NOT guarantee the signed value is
TRUE. The medical P0 is exactly where these diverge: `"INTERIM native Arabic layer"` can be perfectly
pinned + signed and still be WRONG if the system's actual Arabic state has moved. So:
- **The pin's assertion = "this shipped string equals the signed clinical field"** (integrity).
- **The SIGN-OFF event carries the claim-check** — accuracy (does the disclosure reflect reality) is
  verified by the human signing, not by the pin.
- **A capability change (INTERIM → full native Arabic) FORCES a re-sign** — that re-sign is where
  accuracy gets re-verified.
If instead the pin is framed as "the pin makes the disclosure correct," it's the same
disclosure/prose trap wearing better clothes: integrity mistaken for truth. Pin enforces integrity;
sign-off enforces accuracy; capability-change forces re-sign. Keep the disclosure corollary
(see [[feedback_assert_on_behavior_not_prose]]) intact as it moves into the pin mechanism.

**Priority:** QUEUED — not a blocker for the medical P0 or Node-8. Do it as its own focused pass once
those land, BEFORE the next drift surfaces one the hard way. Ordering: medical P0 → Node-8 → this sweep.

**Special case to watch:** honesty/capability DISCLOSURE tests (like the medical one). Re-anchoring
those is not just a test fix — it requires confirming the shipped disclosure is ACCURATE first (a
clinician/PO claim-check), then anchoring the test to "note reflects reality," not to the string. See
the medical P0 STEP ZERO in `2026-07-17-loader-gate-audit-findings.md`.
