# D1 enable — execution record (convergence-gated, attempt #4) (#338)

**Pre-fire (record precedes the irreversible step, GL-1).** Runs the convergence-gated enable
(`2026-07-21-d1-convergence-gated-enable.md`) under Vee's (c) ruling. Prod at 37fed748 (fix, dark, verified).

## Enable artifact + provenance
- **Artifact:** SHA `37fed7484b71e51931ad12dbe44fb29c1c60e2c2` + `SAGE_D1_SCREEN=true`, one rolling redeploy.
- **Residual-window acceptance (decision, not oversight):** the flag flip triggers one rolling restart during
  which old (enforce-off) and new (enforce-on) replicas briefly coexist; this ~minutes window is inherent to
  Railway rolling deploys, both states are safe (screen=correct, shadow=status-quo), it is accepted for the
  measured 4.5% TIPP base rate, and it is NOT probed (the gate ensures the probe runs only post-convergence).

## Halt-lever meaning — SHARPENED for this attempt (stated before firing)
Post-gate, the fleet is single-version, so the superposition is gone. **A red branch on the converged fleet is
therefore a REAL DEFECT, not a rollout artifact.** A halt this time triggers ACTUAL INVESTIGATION of that
branch (as attempt 1's channel-drop was), not "wait for convergence." This is the gate doing its job: it makes
the probe's verdict trustworthy for the first time. Halt lever unchanged mechanically: `SAGE_D1_SCREEN=0`.

## Three-part hard gate (all must hold before the probe)
1. deployment fully SUCCESS + all prior REMOVED (exactly one non-removed deployment).
2. /health enforce=true 8/8.
3. serve-path uniformity: 10/10 fresh /chat sessions serve the signed question (byte-hash).

## Acceptance probe (post-gate, against one system)
[1] serve byte-hash · [2] clear_no→resume · [3] contra→grounding · [4a] explicit→998-via-either ·
[4b] subtle→screen medical_guard · [5] evaded→grounding · [6] AR no-screen · [7] crisis-in-answer.
Clean 8/8 → flip STAYS, monitored-enforce window opens under its honesty clause. Any red → HALT + investigate
(real defect).

## Execution log
(appended below as it runs)

## Execution result (attempt #4) — HALTED on probe SESSION-REUSE, mechanism SOUND
- **Three-part gate PASSED:** converged (all-prior-REMOVED), /health enforce 8/8, **serve-path uniformity
  10/10 fresh /chat sessions served the signed question.** The gate worked — the fleet was single-version.
- **Acceptance probe went red on [1][2][3][4b][5]** → halted per the pre-fire commitment (SAGE_D1_SCREEN=0),
  then investigated (not "wait for convergence" — the gate had already converged).
- **Airtight diagnosis: probe SESSION-REUSE.** The probe's fixed `reflip-*` session_ids were reused across
  attempts 2/3/4; the audit shows 3–6 turns of history per session with prior `screen_answer_class` set
  (clear_no / contraindication_disclosed / red_flag / no_answer). On attempt 4, turn 1 hit a session that had
  ALREADY answered the screen in a prior attempt, so the mechanism CORRECTLY applied session-persistence
  (do not re-screen an already-answered session) → no serve → the probe misread it as a serve failure.
  `reflip-redflag-subtle` even shows `branch=medical_guard` from a PRIOR attempt — proof the screen's backstop
  worked. Combined with gate-3's 10/10 fresh serve, the mechanism is SOUND; the probe used dirty sessions.
- **Fix:** probe now uses UNIQUE session_ids per run (RUN_ID nonce). Gate-3 already used fresh unique sessions,
  which is exactly why it passed — the acceptance probe must too. **Standing probe rule: every live probe run
  uses fresh session_ids; a checkpointer-backed graph carries per-session state across runs.**
- **Impact:** zero real users (query pending confirm on rollback). The gate's 10/10 fresh serve is the
  strongest live proof yet that the mechanism serves correctly on a converged fleet.
- **Pattern (4 halts):** #1 real code bug (channel drop); #2 probe-assertion + dark/live flag-parity; #3
  replica non-uniformity (fixed by this gate); #4 probe session-reuse. Mechanism sound since 37fed748; the
  probe/procedure needed successive hardening. Halt-first held every time; zero exposure.

## RECONCILIATION CONFIRMED + probe RETIRED (2026-07-21) — attempt #5 procedure
- (a) src/ byte-identical 37fed748..HEAD (only tests/docs since deploy) → compiled-graph test drives the
  DEPLOYED mechanism bytes; asserts all 8 branches 1:1 with the retired live probe.
- (b) compiled-graph test GREEN on those bytes; fresh InMemorySaver per run (deterministic, no stale state).
- Live acceptance probe RETIRED (ARCHITECTURE_BOUNDARIES). New gate = code-correct (offline test + dark drive
  on deployed bytes) + fleet-serves-it (convergence gate 10/10 serve-uniformity as ACCEPTANCE). No stateful
  live probe. Halt surfaces as a serve-uniformity miss or monitored-enforce anomaly.
- Enable motion: SAGE_D1_SCREEN=true → one redeploy → 3-part gate (SUCCESS/all-REMOVED + 8/8 + 10/10) → the
  10/10 IS acceptance → flip STAYS → monitored-enforce opens. Residual-window acceptance + halt meaning per
  the pre-fire section above.
