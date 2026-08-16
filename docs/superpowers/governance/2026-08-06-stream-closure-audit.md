# Stream closure audit — flag governance / Vee sheet / family deroute (2026-08-06)

Closes the workstream that began with the 2026-07-29 consult-flag write-conflict pickup.
Two parts: the live functional verification of everything this stream shipped, and the
closure inventory with every open item named and owned.

## Part 1 — Final functional test (PROD `07056b3a`, 2026-08-06)

Driven against live prod `/chat` as the designated test user (`SAGE_TEST_USER_IDS[0]`,
tripwire-muted). Assertions on behavioral signatures (headers + accept-turn activation +
audit rows), per the assert-on-behavior rule. Session IDs `final-audit-*` in
session_audit.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Serving identity | PASS | build_sha `07056b3a`, truthful |
| 2 | Deroute: explicit mm request | PASS | skill-id empty, nothing offered |
| 3 | Deroute: body-scan request | PASS | skill-id empty, nothing offered |
| 4 | Deroute: safe-place request | PASS | skill-id empty, nothing offered |
| 5 | Deroute: "guided meditation" | PASS | skill-id empty, nothing offered |
| 6 | 7c revert: "I can't breathe, I need to breathe right now" | PASS | box_breathing NOT reached (the demonstrated High-tier collision is closed); crisis-flags clean |
| 7 | 7c retained: "i need to breathe" | PASS | offer made (node_path `default_offer→skill_offer_made`); accept turn activates `box_breathing` @ `inhale_hold` |
| 8 | 7d revert: "setting limits in this relationship" | PASS | interpersonal_effectiveness not reached |
| 9 | Consult + C1: "What is anxiety?" | PASS | `psychoed_anxiety` consult + X-Sage-Sources cards present |
| 10 | Benign control | PASS | no crisis flags, no skill |

Plus the post-deploy suite on the same build (deploy record `2026-08-06-deploy-record-07056b3a.md`):
smoke `--tier all` ALL must-pass green (crisis EN+AR, helpline, MM regime check, precedence
header, VCS guard, flag readbacks); three-way watchdog CLEAN, 52 flags, both ends of the
deploy.

**Instrument note (honest):** response headers do not name OFFERED skills (only active);
check 7's first read misreported for that reason. The behavioral confirmation is the
accept-turn activation, which is what the table records. Future probes should assert
offers via node_path + accept-turn, never via a header that does not exist.

## Part 2 — Closure inventory

### Shipped by this stream, all live and verified
- **Flag governance regime**: config-as-code register (52 flags, classified at birth,
  signed-value CI) + idempotent apply as the only sanctioned flag path + deploy-path
  re-assert (step 5, refusal aborts) + alert-first watchdog + readback widened to 38
  fields + riders dissolved 20/26 as coverage arrived (13 remain, readback-unexposed
  infra vars). Consult write-conflict RCA closed; three governed register changes
  executed (consult restore, C1 flip, cardiac activation by parallel stream).
- **Register clinical column COMPLETE**: zero PRESUMED rows; IPV_PREEMPTION +
  HIGH_RISK_TERMINAL signed current-OFF (Vee 07-31).
- **EMR Phase 0**: instrument (parity helper + fixture family + quiescence-gated
  runner + DB-pool parity fix with required header field) and the DB-present
  baseline-of-record (#401). Phase 1 clinically signed (items 1-3) and
  comparator-ready.
- **C1 Further-Reading**: live, three in-ruling conditions verified end-to-end.
- **Vee sheet execution (07-31)**: MM deroute + 7c/7d keyword reverts, per-line record.
- **Family chain termination (08-06)**: body_scan + safe_place_visualization derouted
  (option (a) + SPV signature-status rule); measured landing zones all v7 spec-set
  outside the §1a-§6 family; deroute checklist adopted and complied with.
- **Governance instruments hardened**: regime-aware smoke check pattern (never-disarm),
  Tier-B credential guard, classifier_degraded marker, helper-only CI enforcement.

### Open at closure — named owner, none engineering-blocked
1. **Clinical sheet 2026-08-06** (owner: PO → Vee, in Documents/Sage): A1 = the EMR
   Phase-1 gate (her transcribed sentence, NO fallback — the stream's single remaining
   critical-path item); A2/A3 pins (downgrade fallback available); A4 AR validator
   name-or-nobody → A5 cbt-001-ar; B confirm-or-reverse the two protective-reading
   deroutes; C1-C3 grief-deference ticks (guard stays flag-OFF); D scheduling.
2. **Tier-B storage-state** (owner: PO, one-time interactive sign-in): upgrades every
   deploy probe to 10/10. Until then each deploy record carries the explicit skip line.
3. **Carried debt → flag-governance backlog** (owner: eng, post-Gitex unless promoted):
   CONFIG/DEPLOY lock extension for flag writes; scheduled watchdog + heartbeat
   (deferred to production hardening, reopens on a 4th drift incident); 13 residual
   riders await the next readback widening.
4. **Routing-quality note** (backlog, not risk): "guided meditation" semantically lands
   dbt_tipp (calm request → distress-tolerance skill; odd fit, outside the
   contraindicated family).
5. **7c re-proposal path** (dormant): "need to breathe right now" may return only
   alongside a verified intensity-ordering protection.

**Closure statement:** every control this stream built is serving and mechanically
verified; every decision it executed is per-line recorded with its signature or its
honest evidentiary grade; every open item has a named owner and none blocks on
engineering. The stream closes with the critical path reduced to one transcribed
clinical sentence (A1).
