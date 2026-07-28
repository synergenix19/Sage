# Clinical Sign-off Packet — Explicit Modality Request / §1a (for Vee)

Date: 2026-07-28. Architecture side COMPLETE (reviewer-signed). This packet is the
single clinical decision surface for the EMR workstream; nothing in it ships until
signed. Components, each a doc on branch `1a-gap-phase0`:

1. **Screen design + chronic adjudication** —
   `2026-07-28-1a-screen-design-clinical-questions.md`
   Q-A: condensed screen wording (onset+duration, draft copy). Q-B: conditional
   red-flag clause (never blanket; draft copy). Q-C: OPEN SPEC CONFLICT, §1a chronic
   case, "referral instead of tools" (section 6) vs "skill alongside referral"
   (section 2) — both readings quoted; implementation currently "alongside",
   isolated to one branch; your ruling either way is a one-branch change.
   Q-D: scope confirms (Mild-only v1; Arabic inert pending Lane-3 validation).
2. **Offer-precedence rule** — `2026-07-28-emr-packet-addendum-offer-precedence.md`
   Option A (promote-if-member, else route-with-release), architecture-SIGNED, with
   BINDING reoffer semantics: released ≠ declined; released skills never enter
   declined_skills and stay eligible for natural reoffer. Alternatives B/C/D with
   tradeoffs.
3. **Deviations + measurement validity** — in
   `2026-07-28-explicit-modality-request-handling.md` (re-plan): moderate tier not
   bound in v1 (§B condensed path unimplemented), consent-gate offer shape for
   mild, v5 §1a baseline invalid as comparator (mechanism change + single-run);
   fresh distributional baseline replaces it.
4. **Context for the ruling weight:** the request-dropping defect is live in prod
   across three mechanisms (memo + rerun addendum,
   `2026-07-28-1a-gap-mechanism.md`); the fix is deterministic and consent-gated;
   the screen you are signing is what stands between an explicit request and an
   unscreened tool offer.

Dispatch: prepared as an email draft from this session; recipient/channel held by
the product owner (no verified clinician address in repo — test accounts excluded).
