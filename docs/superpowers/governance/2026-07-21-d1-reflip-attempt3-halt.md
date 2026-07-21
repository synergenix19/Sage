# D1 re-flip attempt #3 — halted on replica non-uniformity, NOT a code defect (#338)

**Status: HALTED 2026-07-21 on the live probe. Prod restored to shadow (enforce=False, uniform 10/10). ZERO
real users affected across all three attempts. Mechanism SOUND — the enforce replicas served correctly; the
probe fired before Railway's rolling deploy fully converged.**

## What happened
Corrected probe (prod-flag-parity, [4a] outcome-via-either-path, [4b] subtle backstop) ran into the re-flip.
Results were INTERNALLY INCONSISTENT:
- PASS [4a] red_flag explicit → 998 via safety-layer medical_response
- PASS [4b] red_flag SUBTLE → screen's OWN medical_guard backstop (**the screen served + classified LIVE**)
- PASS [6] AR no-screen · PASS [7] crisis-in-answer
- FAIL [1] serve · FAIL [2] clear_no · FAIL [3] contra · FAIL [5] evaded  (all branch=None / no serve)

`[4b]` passing REQUIRES the screen to have served turn 1 and classified turn 2 — impossible if serve were
globally broken. So `[1]` serve failing while `[4b]` passing is only explicable by **replica non-uniformity**:
some `/chat` sessions hit enforce=True replicas (screen worked), others hit enforce=False replicas (no screen)
during Railway's rolling deploy. The screen-INDEPENDENT checks (`[4a]` via safety layer, `[6]`, `[7]`) passed
regardless of which replica they hit; the screen-DEPENDENT checks split by their turn-1 replica.

Halted immediately per posture (SAGE_D1_SCREEN=0), then diagnosed.

## Root cause: probed before full rollout convergence (/health 8/8 ≠ /chat replica uniformity)
The flag flip triggers a rolling redeploy. Old replicas (enforce=False) keep serving until all new replicas
(enforce=True) are up. The pre-probe `/health` 8/8 check hit converged replicas; `/chat` load-balanced across
a mix. **`/health` convergence is necessary but NOT sufficient — the acceptance probe must confirm enforce
uniformity on the SERVE PATH itself before firing.**

## Mechanism is sound (the important conclusion)
Every enforce=True replica served correctly: `[4b]` drove the screen's own medical_guard backstop LIVE, `[4a]`
delivered 998 via the safety layer, `[7]` short-circuited crisis before the seam. The code (37fed748) is
correct. This third halt is a PROBE-TIMING procedure gap, not a defect — the third consecutive attempt where
the mechanism itself was sound and the halt caught a harness/procedure issue (attempt 1: real channel-drop
bug; attempt 2: probe-assertion + flag-parity; attempt 3: replica-timing).

## Fix: replica-uniformity gate before the acceptance probe (standing procedure)
After the enforce flip, do NOT run the acceptance probe until enforce is uniform on the SERVE PATH: drive a
serve turn via `/chat` repeatedly (e.g. 10 consecutive) and require ALL to serve the signed question before
proceeding. Only then run the full probe. This closes the /health-vs-/chat convergence gap. Goes into the
dark/live + probe-procedure rules (ARCHITECTURE_BOUNDARIES). Belt: wait for the deployment to fully SUCCESS
(all prior REMOVED), not just healthcheck-succeeded, before the uniformity poll.

## Impact
Zero real users through the enforce path (query: 0, all attempts). During the mixed-replica window, enforce
replicas delivered CORRECT outcomes, enforce-off replicas delivered the safe shadow behavior — neither
harmful. Fail-safe intact.

## Posture note
Third halt, third clean catch, zero exposure. The halt-first posture absorbs "is it a defect or a harness
issue?" so the answer can be found safely every time. The mechanism has been ready since 37fed748; the probe
PROCEDURE needed two more hardenings (flag-parity, replica-uniformity). Next attempt runs with the uniformity
gate; renewed go still contingent on a clean live full-branch probe.
