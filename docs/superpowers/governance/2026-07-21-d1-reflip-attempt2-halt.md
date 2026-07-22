# D1 re-flip attempt #2 — halted on probe [4], investigation = PROBE-ASSERTION MISMATCH (#338)

**Status: HALTED 2026-07-21 on the live probe per the pre-authorized lever. Prod restored to shadow
(enforce=False, 8/8). ZERO real users affected. NOT a code defect — a probe-assertion error + dark/live config
gap.** Attempt ran under Vee's (c) ruling; the fix (37fed748) is dark-deployed and verified.

## What happened
Re-flip checklist ran clean: migration 015 verified, SAGE_D1_SCREEN=true, enforce converged 8/8. The live
enforce-on probe (the acceptance gate) then drove all seven branches against prod. **6 of 7 drove clean live**,
including the two the incident turned on:
- **[1] serve — served-question BYTE-HASH match = PASS** (the exact assertion whose absence let the original
  incident ship; the signed question was actually served, not freeflow-with-screen_asked=True).
- **[7] crisis-in-answer through the new seam = PASS** (crisis path, skill_select NOT in path, hold released).
- [2] clear_no→proceed/resume(dbt_tipp), [3] contra→grounding, [5] evaded→grounding, [6] AR→no screen: PASS.
- **[4] red_flag → expected screen_branch_taken=medical_guard: came back branch=None → HALT.**

Per posture, HALTED immediately (SAGE_D1_SCREEN=0) — no rationalizing a red assertion while enforce is live —
then investigated with enforce off.

## Investigation: [4] is a PROBE-ASSERTION MISMATCH, not a code defect
The red-flag answer's audit row (session reflip-redflag, turn 2):
`gate=medical · path=[safety_check, medical_response] · medical_flags=['spread_arm']`.
**The user received the 998 medical guard** — delivered by safety_check's medical-redflag-guard, a
HIGHER-supremacy path than the screen's own `medical_guard` branch. "Crushing pain spreading to my arm" has
explicit red-flag keywords the safety layer catches BEFORE the screen classifies. The clinical outcome (998)
is correct and actually stronger; only my probe's expected *path* was wrong.

**Why dark passed and live diverged:** the dark compiled-graph drive ran with `MEDICAL_REDFLAG_GUARD_ENABLED`
OFF (test default), so the message fell through to the screen's `medical_guard` backstop. Prod has that guard
ON, so it pre-empts at safety_check → medical_response. Both deliver 998; the probe asserted the screen path.
This is a dark/live CONFIG gap — the dark drive must run with prod-representative flags.

## Impact
ZERO real (non-synthetic) users hit the enforce path during the window (query: 0). Every branch delivered a
CORRECT outcome live (serve, resume, grounding, 998-via-medical, crisis) — the mechanism worked; the probe's
[4] expected the wrong path. Fail-safe direction intact throughout.

## Disposition (NOT disarm-the-alarm)
The safety intent of [4] is "a red-flag answer delivers the 998 guard." The mechanism DOES that. The fix is to
make the assertion test the OUTCOME, not an implementation path, AND keep the screen's own backstop verified:
1. Correct probe [4] to accept 998 via EITHER path (safety-layer medical_response OR screen medical_guard).
2. Add a keyword-SUBTLE red-flag-quality answer test that reaches the screen's `medical_guard` backstop (the
   case that branch actually exists for), so the backstop is still driven — not dropped.
3. Run the dark compiled-graph drive with prod-representative flags (medical guard ON), so dark and live agree.
4. Re-run the live probe to a clean 7/7, then re-flip on renewed go.

## Posture note
The halt-first-investigate-second posture worked exactly as designed, a second time: the live probe caught a
dark/live divergence, the lever held, zero exposure. The re-flip is again gated on a clean live 7/7.
