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
