# EMR Packet Addendum — Detector vs Pending-Offer Precedence (with alternatives)

Date: 2026-07-28. Joins the §1a/EMR sign-off packet. Decides surface 3 of the
explicit-modality-request re-plan: the turn where `explicit_modality_request` fires
WHILE `offered_skill_ids` is pending. Observed instance (rerun turn 3): "are there
any exercises i can do" over a pending [psychoed_anxiety, worry_time] offer was
classified `offer_ignored` and the request was dropped.

## Proposed rule (Option A — recommended)

Deterministic resolution, evaluated before the LLM offer-reply classification is
trusted, in this order:

1. **Promote-if-member:** if the requested modality (or the binding table's
   first-line skill for the modality hint) is IN the pending offer → treat as
   acceptance of that member; activate via the existing offer-promotion path
   (`offer_promoted` semantics, entry screens preserved).
2. **Route-with-release:** otherwise → release the pending offer (marker
   `offer_released_modality_request`, NOT `offer_ignored` — the user engaged, with a
   different ask) and route the request through the binding table + consent gate,
   declined-filtering preserved.
3. LLM offer-reply classification applies only when the deterministic detector did
   not fire.

Rationale: the user's explicit request is the most recent, most specific signal;
honoring it is both spec-conformant (§1a: don't make the user ask twice) and
neutral to the bistability (no LLM in the loop). Never double-serve: exactly one
offer state exists after the turn.

## Alternatives (for the record, with tradeoffs)

- **Option B — detector always wins:** void the pending offer unconditionally,
  fresh first-line re-offer. Simpler, but jarring when the user asked for exactly
  what was offered (voids then re-offers the same skill through a different path);
  loses the promotion audit trail.
- **Option C — offer always wins (status quo ante):** pending offer resolution is
  authoritative; the detector defers until the offer resolves. Preserves current
  offer lifecycle exactly, but reproduces the observed defect whenever the reply
  classifier reads a request as `offer_ignored` — this is the trajectory we
  measured. Included for completeness; not recommended.
- **Option D — clarify:** ask the user which they meant. Maximally safe against
  misreading, but §1a's own design notes weigh against added friction on an
  explicit ask, and it burns a turn in the tier where momentum matters.

## Ask

Approve Option A (or select an alternative). One-branch change either way; the
consumer-3 task implements whichever is signed. Both-direction guards regardless of
choice: genuine ignores still release; genuine declines still never re-offer.
