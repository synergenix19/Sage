# EMR lexicon sign-off (Vee) + flip authorization record (2026-08-12)

**Sign-off:** Vee approved the EMR clinical data files, relayed by the PO in-session
2026-08-12 ("vee has approved the lexicon and signed off"). Same relay grade as the
prior records in this stream. Scope, pinned to content:

- `src/sage_poc/rules/data/skill_matching/skill_request_phrases.json`
  (git blob `65783567f52e9968f0ef161759ec99e37fcf516d`): the 44-entry request lexicon
  (incl. the 2026-08-12 recall extension from measured misses) + the first-line
  binding table (default = the section-1a Tier-1 pair in spec order; hint rows).
- `src/sage_poc/rules/data/skill_matching/modality_screen.json`
  (git blob `b1ce3957e4e360723aca46d493313059c18a353f`): the supplied-detection
  lexicons (duration/onset/physical/red-flag markers incl. the ever-since onset
  extension). The lead-in + questions inside it were ALREADY signed (2026-07-29
  item 1 + ratified section-1a step-2 copy; adopted-sentence pin 2026-08-11) — this
  sign-off adds the marker lexicons.

Any future edit to either file requires a fresh sign-off (draft-pending-review
lifecycle ends here; these are signed clinical data as of this record).

**Flip authorization:** deploy owner (PO) in-session 2026-08-12 ("please continue"),
read as the per-deploy authorization for this specific activation, per the pattern of
this stream. Evidence basis: Phase-3 deltas report (drop 28/30 -> 0/30; loop closure
first-line 1.00 x30; controls neutral; measurement boundary stated).

**Serving delta carried by the flip deploy (`07056b3a..master`, src-only):** the EMR
mechanism end-to-end (detector, screening foundation, three consumers, resumption,
readback field) plus its two in-family fixes (screen_response preserve-not-force;
corpus_constants comment). Nothing else touches src in this range.

**Post-flip verification plan (window-bounded rule):** readback both sides; drift
probe; smoke all tiers; live request-family probes (request -> signed screen question;
answer -> first-line offer; benign + crisis controls). Window 2 re-verification on a
separate day before any served-stability claim.
