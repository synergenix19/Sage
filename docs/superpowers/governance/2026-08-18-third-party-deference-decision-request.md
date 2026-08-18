# Third-party deference (R4) — dark build landed; decision request for Vee's signature

**Date:** 2026-08-18 · **Flag:** `SAGE_THIRD_PARTY_DEFERENCE` (default OFF, register row at
birth, readback pair live) · **Content:** `CC-EN-TP-001` in
`rules/data/crisis_content/en_uae.json` — **DRAFT, unsigned; serves nothing until the flag
flips, and the flip is gated on her signature + manifest pin.**

## What is built (dark)

Per her R4 spec: when the flag is ON, a **Layer-1-clean** turn (`crisis_flags` empty)
carrying a third-party signal (`third_party_crisis: true`) that reaches `crisis_response`
serves the helper-support content instead of the first-person crisis script. The two hard
boundaries from her ruling are code + tests, not convention:

1. **The first-person script never serves the clean third-party case** under the flag
   (and flag-OFF is byte-identical — the acute script serves, pinned).
2. **Deference applies only on Layer-1-clean turns.** A co-occurring first-person flag
   means the deterministic layer fired (F1's span-scoped suppression guarantees the
   compound case), so the first-person script serves in BOTH flag states — tested in both
   directions. Additionally: a locale with no signed third-party content **falls back
   toward crisis** (acute script) — the AR case today, tested.

Stage 1 is delivery-content-only: monitoring entry, gate path, audit row, and the
clinician-review notify are identical to the first-person case.

## The DRAFT content (hers to sign, amend, or rewrite — structure is her spec verbatim-intent)

> "I can hear how much you care about them, and carrying that worry is heavy. You can
> help. Ask them directly how they are feeling, including whether they are thinking of
> ending their life; asking directly does not plant the idea. Listen without trying to
> fix everything. And help them connect with support: {{crisis_label}} {{crisis_number}}
> (free, {{crisis_hours}}) can support them, and in an emergency call
> {{crisis_emergency}}. You matter here too. How are you holding up?"

Helpline via the load-time `{{crisis_*}}` single-source templating (never a literal); no
em dashes in action content per the mirroring rule. Elements: validate the concern ·
gatekeeper guidance (ask directly / listen without fixing / help connect) · helpline
framed for the friend · one helper-state check.

## Two clinical questions flagged, defaulted conservatively pending her word

1. **Monitoring semantics:** the helper turn currently enters `crisis_state=monitoring`
   exactly like a first-person crisis turn (delivery-only change). Should a helper-support
   turn enroll the HELPER in post-crisis monitoring? Default kept = yes (fail-toward-more-
   support) until she rules.
2. **Crisis card:** the pinned crisis-card UI (driven by the crisis gate path) still shows
   on the helper turn, so 800-HOPE is visually present. Keep, or should the helper case
   carry a different surface? Default kept = show (fail-toward-more-support).

## Sign-off shape (when she is ready)

Signature on `CC-EN-TP-001` (with the R2 signature block: version, date, review-by
trigger) + manifest pin + her answers to the two questions above → the flip returns as its
own decision request per the register row. AR content is a separate authoring item
(Khaleeji lane), and the fallback keeps AR fail-toward-crisis until it exists.

**Evidence anchor for why this path exists:** prod audit row `prodsuite-f1ctrl-01A44C94`
(`crisis_flags: []` + `primary_intent: "crisis"`) — the T-10 deviation measured live,
packet 2 item 3.
