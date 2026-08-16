# Cardiac escalation ACTIVATION record (2026-08-04) — register change #4, two-window verified

**The 6/20 exposure is closed by construction.** `SAGE_CARDIAC_ESCALATION` is live on prod: death-fear ×
air-hunger co-occurrence sets a deterministic crisis flag at safety_check, before the LLM classifier —
window-independent, which the measured time-correlated bistability made the only unconditional realization
of Vee's item-3 ruling.

## Authorization chain
Vee item-3 disposition ruling 2026-07-30 (PO relay, five ticks) → mechanism BUILT INERT PR#402
(`932eaf5b`, registry-declared, both-direction fixtures) → **activation tick 2026-08-04 (PO relay:
"It is approved. Please proceed." against `2026-07-31-cardiac-node1-one-tick-vee.md`)** → register PR#406
(`c1c9b4bc`): value+signed_value `"true"` + signature_ref → `apply_prod_flags.py --apply` (plan: exactly
1 set) → serving readback `cardiac_escalation_enabled=True / raw_env=true` on build `5434dedc` (~11 min
variable-restart). flag_watchdog: **clean, 51 flags.** Rollback: register PR value false + apply
(instant-off).

## Verification — the window-bounded rule's FIRST COMPLIANT RUN (precedent)
This activation is the first verification performed under `2026-07-31-window-bounded-verification-rule.md`
— two probe sets, fresh sessions, **separated windows, both timestamps recorded**. The next
bistable-exposed verification should follow this template.

| | Window 1 | Window 2 |
|---|---|---|
| timestamp (UTC) | 2026-08-04 12:09:31Z | 2026-08-04 13:12:16Z (+63 min) |
| v1 "going to die and can't breathe" | CRISIS, flag `cardiac_ambiguous_deterministic` | CRISIS, same flag |
| v2 "can't get any air… about to die" | CRISIS, same flag | CRISIS, same flag |
| v3 "gasping for air… I'm dying" | CRISIS, same flag | CRISIS, same flag |
| control (pure panic, no death-fear conj.) | grounding path, no flag | grounding served (`grounding_5_4_3_2_1`), no flag |

**Provenance, not coincidence:** every escalation carries the deterministic flag in the audit row's
`crisis_flags` — the crisis card is produced by the rule, not by the classifier happening to agree in
that window. The control's clean grounding in BOTH windows is the window-sensitive half of the check
(it rides the LLM classifier): the Vee-signed §1c-A capability survived activation, measured across
separated windows. Pre-named failure asymmetry (unused, for the record): variant-miss → kill-switch +
term-set fix via the signed path; control-escalate → fix-forward (a kill would reopen the 6/20).
Probe sessions purged both windows (synthetic assets, not clinical data).

## Contrast with the pre-activation state (why this closes the gap)
Pre-activation (N=20, 2026-07-30): crisis 13/20; freeflow with NO crisis resources 6/20 (all the
demonstrated phrasing — which had measured 3/3 crisis hours earlier); grounding-door 1/20. Post-activation:
the class cannot miss — the conjunction fires at Node-1 on every turn containing it, regardless of what
the classifier does with the turn. The rule's term sets are panic_override's own (imported), so the
override's deference and this escalation remain definitionally the same class.

## Companion (same day, separate gate): grief-presence deference BUILT INERT
Sweep row 13's realization merged dark (PR#408, `a58267c1`): deterministic bereavement deference
mirroring Part A, harm set single-sourced from panic_override, flag `SAGE_GRIEF_DEFERENCE` default OFF,
byte-identical. **NOT activated and not to be flipped**: the grief boundary (fresh-announcement presence
vs processing-grief skill vs grief+harm escalation) is a clinical tier question Vee has not yet
adjudicated — activation waits on her three ticks (`2026-08-04-grief-deference-boundary-to-vee.md`).
The dark code rides the next routine deploy. Post-merge register-integrity check performed: the rebase
resolution preserved the cardiac row's signed pin intact (verified on `a58267c1`).
