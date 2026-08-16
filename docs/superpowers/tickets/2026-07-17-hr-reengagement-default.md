# TICKET 2026-07-17 — HR re-engagement: implement the ratified default (flip-gate)

**Owner:** HR-1 workstream. **Blocks:** the HR flip (must land before `SAGE_HIGH_RISK_TERMINAL` flips ON).

## The gap
Stage-2 code (merged, inert) ships **strict once-per-session**: `hr_referral_delivered` (+ `psychotic_referral_delivered`) suppress ALL HR re-entry after the first delivery. But the clinician packet's re-engagement default was corrected to the **doc's** default (§HR: HR "takes priority... the same way crisis category does"): one-shot **per HR class per disclosure-episode**, NOT per session. So code and the ratified default will diverge.

## The clinically dangerous case the strict-once code creates
Paranoia disclosed turn 3 → referral delivered → `hr_referral_delivered=True`. Turn 12: "I've been spending loads of money" (mania, behavior-underway = §3 escalate-regardless). Strict-once **swallows it** — a higher-acuity, different-class disclosure suppressed by a session bit set nine turns earlier.

## Implement (whatever the clinician ratifies; default below)
Default = per-class-per-episode:
- **New, distinct HR class** later in the session → protocol re-engages (fresh two-turn).
- **Any behavior-underway content** (spending/risk-taking) → always re-engages, regardless of a prior referral.
- **Same disclosure repeated** (same class, no new evidence) → brief fixed-copy **reaffirm** (one line, no two-turn re-run) — this repeat-loop is the only thing strict-once legitimately prevents.

Requires: track delivered state **per HR class** (not one global bit); a behavior-underway re-engage check; a reaffirm copy string (single-sourced, ratified). If she amends to strict-once, this ticket closes as "no change."

## Acceptance
Red test: turn-3 paranoia referral → turn-12 mania-with-spending → protocol re-engages (not swallowed). Same-class-repeat → reaffirm, no full re-run. Crisis precedence unchanged.
