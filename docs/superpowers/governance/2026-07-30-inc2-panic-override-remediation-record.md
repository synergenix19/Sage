# panic_override remediation — increment 2 execution record (2026-07-30)

**Increment 2 of the four-increment §1c execution** (Vee's five ticks, PO relay). PR#398 → master
`ada1855a`. One mechanism narrowed to its signed scope, both rulings in one PR; deployed staging-first
per the RCA, then prod under lock.

## The change
- **Item-1 scope-back**: `_PANIC_TERMS` → pure panic only (breathing/chest/heart/dizzy/trembling/
  closing-in/panic-attack + fear-of-death). Removed: derealization set (CF-010's territory, live since
  increment 1 at higher precedence — no fall-through window) + HR-family terms (CF-007/009) — all four
  disposition-ownership overlaps closed.
- **Item-3 cardiac deference**: death-fear × air-hunger co-occurrence → defer (crisis stands); knowingly
  reverses the 07-28 demonstrated anchor, as ruled.
- **Audit provenance**: derealization terminal turns now persist `gate_path="derealization"` (increment-1
  finding: only medical turns persisted gate_path; served referrals audited NULL and the method-of-record
  driver misclassified them).
- Fixture oracle amended RULED (three directions); 12/12 unit + 68/68 audit tests; zero unique full-suite
  regressions vs master.

## Verification
- **Staging trio** (d3a0dd30, flag mirror set): dereal→referral ✓, pure-panic→grounding offer ✓,
  cardiac→`[[CRISIS_DETECTED]]` ✓.
- **Prod (ada1855a, code-truth-verified)**: dereal→referral **with `gate_path=derealization` in the audit
  row** (the code-truth marker), pure-panic→grounding offer, cardiac→crisis card. flag_watchdog clean
  (50 flags). Lock released after verification (variable delete, singular).
- **Guarded §1c re-measure (prod-HTTP, ×3, stable, flag-stamped ada1855a):**
  **{escalate_crisis: 1, derealization_referral: 1, self_help_skill: 1, presence_only: 2}.**
  Lineage: 07-29 baseline (09013f19) {skill:2, presence:3} → increment 1 (dec4a9e7+CF-010)
  {skill:2, presence:2, referral:1} (dereal row moved) → increment 2 (ada1855a) adds the cardiac row
  skill→crisis. **Every move is single-row attributable to its increment.** The served §1c map now
  matches the doc and every signature: derealization→referral (L151), pure panic→grounding (§1c-A),
  cardiac-ambiguous→crisis (item-3), knowing residuals per Ruling-3.

## Deploy-ops findings (for the runbook)
1. **Variable-triggered rebuilds race `railway up` and WEAR THE NEW SHA STAMP** (three occurrences today,
   staging + prod): the deploy script's variable writes spawn rebuilds of the OLD tarball which pick up the
   new `RAILWAY_GIT_COMMIT_SHA`, so `/health/version` reports the new SHA while serving old code. The
   health SHA is a stamp, not the truth — **verify with a code-truth behavioral marker and wait for YOUR
   deployment id to be the serving SUCCESS.** (First prod probe round measured old code wearing the new
   SHA; caught by the gate_path marker.)
2. **BGE-M3 cold-start healthcheck failure**: fresh image rebuild lost the warm layer; `/health/ready`
   flapped 503 (~20 min) and Railway FAILED the deployment; retry against warm cache succeeded. Consider
   raising the healthcheck window or hard-baking the model layer.
3. Staging `DATABASE_URL` points at a dead Supabase tenant (ENOTFOUND) — staging audit persistence is
   broken; behavioral reads unaffected. Owner: infra.

## Open follow-up (named, for Vee — not blocking)
**Item-3's full realization needs a deterministic Node-1 escalation.** The deference covers the
intent=crisis door; on some runs the pinned classifier routes the cardiac phrasing
`acute_direct_entry→grounding` (observed on the pre-inc2 build; Node-2 bistability class), a door the
override never sees. A deterministic rule (death-fear × air-hunger → crisis at safety_check) would make
"stays at crisis" unconditional — it touches the signed activation map, so it rides to Vee as the
implementation ask of her own item-3 ruling. Current ×3 re-measure shows crisis stable, so exposure is
the bistable tail, not the steady state.

## ADDENDUM (2026-07-30 evening) — cardiac tail CHARACTERIZED (N=20, fresh sessions, prod ada1855a)
Three phrasings of the death-fear × air-hunger class, ~7 drives each: **crisis card 13/20; empathic
freeflow (primary_intent=general_chat — NO crisis resources, no grounding) 6/20; grounding-skill door
(acute_direct_entry) 1/20.** The 6 freeflow outcomes were ALL the demonstrated phrasing ("going to die +
can't breathe") — which had measured crisis 3/3 a few hours earlier in the §1c re-measure. **The
bistability is time-correlated: the pinned classifier (seed + provider pin) still flips attractors across
windows.** Net for the Vee ask: the demonstrated cardiac phrasing reached NO crisis resources in 6 of its
9 fresh-session drives today; "stays at crisis" is currently ~65% overall and phrase/window-dependent.
The deterministic Node-1 rule (death-fear × air-hunger → crisis at safety_check) is the only unconditional
realization of her item-3 ruling — the ask upgrades from belt-and-suspenders to URGENT, with these
measured rates as its calibration.
