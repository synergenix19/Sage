# Clinician touchpoint — Vee — HR referral template: hours + 24/7 pairing (SAFETY-ADJACENT, prompt)

The Node-8 flip made the psychosis-referral template the ONLY thing users see on this path (deterministic).
Verifying it live surfaced a content issue that is now FROZEN into a signed template and is more than
register-polish. Two asks, bundled (a signed-copy question, so yours).

## The issue
The template's helpline is `800-HOPE (800-4673)`, which operates **8am–8pm daily, NOT 24/7**. The referral
can fire at any hour (a psychosis disclosure at 3am is not a crisis by our precedence, so it does NOT get
the hours-aware crisis card — it gets this fixed template). So at 3am the user permanently reads:
- an **English** hours string `8am–8pm daily` (in the AR template too — not localized), and
- a warm support line that is **closed at that hour**, with only `999` (emergency) as the dialable option
  — and 999 is over-escalation for a non-crisis psychosis disclosure.

The crisis card solves this with `select_crisis_resources()` (hours-aware, always pairs a 24/7 line). The
HR referral template does NOT — it is fixed.

## Ask 1 — localize the AR hours string (copy)
The AR template currently renders `(مجاني، 8am–8pm daily)` — Arabic prose, English hours. Ratify the
Arabic hours string (e.g. `من ٨ صباحاً إلى ٨ مساءً يومياً`) so the AR referral reads fully Khaleeji.
→ ☐ approve Arabic hours (your exact wording: __________)  ☐ edit

## Ask 2 — pair a 24/7 alternative in the referral (content + SAFETY)
Because the referral can fire when `800-HOPE` is closed, should the template ALSO carry a 24/7 non-emergency
line — **Abu Dhabi `800-SAKINA (800-725462)`, 24/7** — so a 3am user has a dialable support option that
isn't emergency services? Rec: **yes, pair it** (the referral should never leave a user with only a closed
line + 999). This mirrors the crisis card's always-pair-24/7 guarantee, applied to the HR referral.
→ ☐ approve 24/7 pairing (800-SAKINA) EN+AR  ☐ edit  ☐ reject (999 is sufficient)

## Ask 3 — the mnemonic (finding #3, carried over)
The template shows `800-HOPE` (English mnemonic) in both languages. Earlier rec: keep English (only English
maps to 4673 on a keypad; أمل doesn't). Confirm alongside the above so the template copy is settled in one pass.
→ ☐ keep English `800-HOPE`  ☐ edit

**On approval:** re-render the signed fallback template (still verbatim from the ratified psychotic_referral
copy), re-pin (signed_clinical_fields, provenance = this ratification), re-verify live. The gate stays on.
