# ESC-2026-07-15 — 16 safety rules ACTIVE in production without sign-off (#270)

**Class:** Safety governance — LIVE. Own line to clinical lead **today**. Does NOT wait in the packet.
**Route to:** Clinical lead (per-rule disposition) + eng (structural CI gate, separate ticket).
**Surfaced by:** the 2026-07-15 conformance re-run loader on the serving tree (`5b33a0e`).

## Finding
16 clinician-authored (`authored_by=sage_clinics`) safety rules are **`active: true` in production with no sign-off record.** The rules loader logs `UNAPPROVED ACTIVE SAFETY RULE … clinical sign-off required before production` for each and **runs them anyway.** These rules are deciding safety routing for live users right now with no clinical authority behind them.

**This is the mirror image of B1.** B1 was *signed-but-not-shipped* (a required safety screen written and never built). This is *shipped-but-not-signed* — and this direction is arguably worse: the code is live and load-bearing, but unratified.

## The 16 rules
- **CF-001, CF-002, CF-003, CF-004** — clinical-flag rules. **Almost certainly load-bearing** (crisis/clinical-flag detection). Deactivation is NOT automatically safe.
- **SK-AR-001, SK-AR-003** — **unsigned Arabic safety rules, live, in the language we cannot yet measure** (0 AR corpus). Highest-attention: unsigned safety in the primary language with no measurement behind it.
- **SK-AZ-001, SK-AZ-002** — Arabizi safety rules.
- **SK-EN-001, SK-EN-003, SK-EN-004, SK-EN-005, SK-EN-006, SK-EN-HTO-001** — English safety/keyword rules (HTO = harm-to-others).

## Ask — per rule, one of: RATIFY / AMEND / DEACTIVATE
Each of the 16 needs a disposition. **Do NOT bulk-deactivate** — CF-* and the SK-*-safety rules are plausibly load-bearing; turning them off could open a safety gap, which is exactly why this is a clinical triage, not an engineering default. The disposition per rule:
- **Ratify** — clinician confirms the rule as-is → record sign-off, `approved:true`.
- **Amend** — clinician corrects it → sign the amended version.
- **Deactivate** — clinician judges it should not run → `active:false` (only after confirming nothing safety-critical depends on it).

## Structural fix (ticket, separate)
See `2026-07-15-active-implies-signed-ci-gate.md`. The signed-fields manifest is a one-directional gate (signed things can't change unremarked); the invariant is two-directional (active safety rules must be signed). CI must also fail on `active:true` + missing sign-off.
