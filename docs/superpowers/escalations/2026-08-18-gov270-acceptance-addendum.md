# GOV-270 approval-sheet addendum — nulls confirmed as scaffold artifacts, signatures stand

**Date:** 2026-08-18
**Signer:** Vee (clinical lead), via PO relay per house convention; owner countersign in the
same relay (merge condition 2, 2026-08-18).
**Amends:** the GOV-270 approval sheet
(`docs/superpowers/escalations/2026-07-15-270-approval-sheet.md`, committed `ea49af17`,
resolved `c755f1f4`, PR #323 — file later removed from the tree in the 2026-08-17 docs
purge; the record stands in history and is cited here by SHA rather than resurrected).

**Acceptance:** the eight duplicate `approved_by` keys found in `crisis_keywords.json`
(SK-EN-003, SK-EN-004, CK-CH-001, CK-CH-002, SK-EN-006) and `passive_si_patterns.json`
(SK-AZ-002, SK-AR-003, SK-EN-005) are **confirmed as scaffold artifacts** of the signing
commit `f4ed6740` — the insertion of `"approved_by": "clinical_lead"` never removed the
pre-existing scaffold `null`, and JSON last-key-wins discarded the recorded signature.
**The GOV-270 signatures stand for all eight rules.** The remediation (deleting only the
surviving `null` keys; zero content change) and the migration of the fifteen GOV-270 rules
to manifest signing (`signed_clinical_fields.json`, whole-object hash pins) are accepted as
presented in the consolidated packet
(`docs/superpowers/governance/2026-08-18-consolidated-packet-to-vee.md`, item 2, evidence
SHAs `8152919c` / `265924d5` @ `c0f66e49`).

**Not covered by this addendum:** the item-1 shortened `_meta.match` wording (pending
Vee's tick on the shortened form — it merges nowhere until that lands), and the CD1 tier
assignments in the draft v2 oracle (pending her signature on v2 as a new artifact).
