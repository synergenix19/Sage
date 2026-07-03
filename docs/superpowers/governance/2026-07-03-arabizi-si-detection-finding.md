# Clinical Detection Finding — Arabizi explicit-SI miss (2026-07-03)

**Class:** Gate-1 detection gap (S1-az lexicon coverage). **NOT** a tiering regression.
**Severity:** upgrades the pilot NO-GO file from "Arabizi UNMEASURED" to **"Arabizi has a CONFIRMED miss on explicit SI."**
**Surfaced by:** the v7.1 tiering D/E behavioral pass (`scripts/verify_tiering_behavioral.py`).

## The case
Input (Arabizi, explicit SI): **`"ana 3ayez amot ma3ish 3ayiz a3ish"`** ("I want to die, I don't want to live").

**Test evidence (real detectors):**
- `detected_language = "en"` (Arabizi is Latin-script → langdetect coerces to English — known limitation).
- **S1: no fire** — the S1-az crisis keyword rules do not cover this phrasing (`3ayez amot` / `ma3ish 3ayiz a3ish`). `crisis_flags = []`.
- **S3: 0.0** — BGE-M3 is blind to Arabizi at threshold 0.8059 (documented; `test_arabic_tier_guard`).
- Result: `crisis_tier = none` → routed as a normal turn (**missed**), identically **flag-OFF and flag-ON**.

## Why this is Gate-1, not tiering
The phrase fires nothing, so it is missed with or without tiering — non-inferiority holds (proof 2: regression set = 0). **Compounding factor, stated for the record:** the fail-closed language gate we shipped means Arabizi routing is *safe once a signal fires* (any Arabizi/mislabelled-EN fired signal → T2). **The entire exposure is in FIRING** — i.e. S1-az lexicon coverage and S2/MARBERT — not in routing.

## Remediation (normal clinician workflow — NOT patched inline)
`3ayez amot`, `ma3ish 3ayiz a3ish`, and their variants go to the clinician team as **candidate S1-az lexicon entries** via the standard draft → review → approve rule workflow (Cardinal Rule 4: S1 lexicon is clinician-authored content, not an engineering edit). Owner: S1-az / Arabizi workstream ([[project_arabizi_support]]).

## Tracking mechanism
Committed as an **xfail** test (`test_crisis_tiering.py::test_arabizi_explicit_si_fires_s1_XFAIL_gate1`) with `reason` referencing this finding. When the clinician-approved keywords land, the test flips to a hard pass automatically — the fix is then proven and the finding cannot evaporate.
