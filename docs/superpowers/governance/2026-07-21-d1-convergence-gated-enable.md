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
3. **Only after the gate holds: run the acceptance probe** (the corrected 8-check live probe: [1] serve
   byte-hash · [2] clear_no→resume · [3] contra→grounding · [4a] explicit→998-via-either-path ·
   [4b] subtle→screen medical_guard · [5] evaded→grounding · [6] AR no-screen · [7] crisis-in-answer), cited
   individually. Because the fleet is single-version, the probe now measures ONE system.
4. **Halt lever on any real miss:** `SAGE_D1_SCREEN=0` → rollback redeploy → converge to enforce=false. Same
   held posture. "Real miss" now means an actual branch defect, not a superposition artifact (the gate removed
   those).

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
