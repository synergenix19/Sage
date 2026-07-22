# D1 enable — REDESIGNED as a convergence-gated deploy (supersedes the flip section of the checklist) (#338)

**Why this replaces the old flip step:** three halts showed a serve-path enable cannot be probed while a
rolling deploy is mid-transition — the probe measures a superposition of enforce-on and enforce-off replicas.
The fix is not another probe patch; it is to make convergence a PRECONDITION of the probe. See
`docs/ARCHITECTURE_BOUNDARIES.md` (serve-path enables do not ride rolling flag-flips). My read of the deploy
path: all 31 enables are runtime flags with no committed-per-env mechanism, so the enable stays a runtime flag
(option 2), but the flip is restructured below so it rides a single convergence-gated motion.

## Preconditions (unchanged from the flip checklist)
- ▢ Vee (c) ruling stands · migration 015 applied+verified · serve/resume fix deployed dark & verified
  (prod at 37fed748, byte-identical, dark drive + branch-by-branch on deployed bytes) · halt lever named
  (SAGE_D1_SCREEN=0).

## The enable motion (convergence-gated — ONE window, probe after single-version convergence)
1. **Set `SAGE_D1_SCREEN=true`** — this triggers ONE rolling redeploy of 37fed748 with enforce committed as
   the served env. **Do NOT also `railway up`/`railway redeploy`** — extra calls spawn concurrent deploys
   (observed in attempts 1–3); the single var-triggered redeploy is the motion. Record it as the enable
   artifact: (SHA 37fed748 + SAGE_D1_SCREEN=true + timestamp) with a provenance line.
2. **HARD CONVERGENCE GATE — all three must hold before the probe fires:**
   - ▢ the new deployment is fully **SUCCESS** and **every prior deployment is REMOVED** (not merely
     "healthcheck succeeded" — that precedes promotion). Poll `railway deployment list` until exactly one
     non-REMOVED deployment remains.
   - ▢ `/health/version` readback **enforce=true on 8/8** hits (necessary, not sufficient).
   - ▢ **SERVE-PATH UNIFORMITY (the sufficient signal):** drive an acute-overwhelm serve turn via `/chat`
     **10 times against fresh sessions**; ALL 10 must serve the signed question (byte-hash match to the
     manifest). Any non-serve = a replica still enforce-off = NOT converged → wait, do not probe. This is the
     `/health`-vs-`/chat` gap that halted attempt 3, promoted to a precondition.
3. **The 10/10 serve-uniformity IS the acceptance — NO separate stateful live probe (retired 2026-07-21).**
   Branch correctness is proven by two quieter instruments BEFORE the enable, not re-driven live through a
   checkpointer-backed fleet (see ARCHITECTURE_BOUNDARIES "a stateful live acceptance probe is the wrong final
   gate"). Those two pre-enable confirmations:
   - **Compiled-graph test green on the deployed bytes:** `test_screen_serve_resume_graph.py` drives all 8
     branches (serve byte-hash · clear_no→resume · contra→grounding · explicit→998-via-either ·
     subtle→screen medical_guard · evaded→grounding · AR no-screen · crisis-in-answer), fresh checkpointer per
     run, deterministic, at prod flag-parity — confirmed byte-identical to the deployed SHA.
   - **Dark drive on the deployed bytes** (already banked for 37fed748).
   The live gate then proves the CONVERGED FLEET runs that correct code on the serve path: the 10/10
   fresh-session serve-uniformity. Code correct (offline+bytes) + fleet serves it (10/10) = complete.
4. **Halt lever armed as always:** `SAGE_D1_SCREEN=0` → rollback → enforce=false. A real problem now surfaces
   as a **serve-uniformity miss** (a replica not serving) at the gate, or a **monitored-enforce anomaly**
   after — NOT a session-state artifact. The stateful-probe false-halt class is retired with the probe.

## The residual window (named honestly, not eliminated)
Setting the flag triggers ONE rolling restart; during it, old (enforce-off) and new (enforce-on) replicas
briefly coexist — real traffic in that ~minutes window hits the mix. This is inherent to Railway rolling
deploys and is NOT removed by this design; it is (a) ONE window (the enable rides one motion, not
dark-deploy-then-flip = two), (b) low-impact at the measured 4.5% TIPP base rate with BOTH states safe
(screen=correct, shadow=status-quo), and (c) no longer measured by the probe. Eliminating even this window
needs atomic-restart / canary infra — overkill for this base rate (option 3, rejected).

## Rollback
`SAGE_D1_SCREEN=0` → one rolling redeploy back to enforce=false (converged, verified 8/8 + serve-uniformity
that NO session serves). Proven three times.

## What is NOT changing
The mechanism code (37fed748) — sound, verified live on the enforce replicas three times (serve, resume,
grounding, 998-via-both-paths, crisis, and the subtle screen-backstop, all correct). Vee's (c) ruling — stands.
This redesign is purely the ENABLE MOTION, gating convergence ahead of the probe.
