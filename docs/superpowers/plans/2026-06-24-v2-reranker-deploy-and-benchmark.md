# V2 reranker — deploy + benchmark procedure (DO NOT DEPLOY until authorized)

Branch `feat/v2-calibrated-retrieval-core` (tip = the reranker build, commits 1–4). The build code is
done and flag-off byte-identical V1 through every commit. Two things remain, and they are **different in
kind** — one is offline, one needs Railway.

## The honesty state to carry in (the 85 vs 90 distinction)
- **62/90/100** = the honest CV-OOF (disjoint) number, on the **standalone** pipeline (NO Tier-1).
- **64/85/100** = the **wired** node check — but with **in-sample τ** (inflates) and **post-Tier-1-veto**.
These are not the same measurement. **Wiring faithfulness is proven (the Tier-1 leak was caught and fixed);
the honest WIRED per-stratum number is NOT yet measured.** It could land 85–90 under disjoint τ.

## Step A — Honest wired re-gate (QUALITY) — OFFLINE, model-deterministic, does NOT need Railway
Run `skill_select_node` (both flags on, int8) on the EN held-out cells **with per-fold (CV-OOF) τ**, not
the in-sample production τ — i.e., assign folds, set `_RERANK_TAU` to each fold's calibration τ, evaluate
the test fold. Report all three cells, positive-control-gated. This is the **honest wired per-stratum verdict**
(Tier-1 + veto + disjoint τ). Quality is model-deterministic, so int8 here == Railway int8 (modulo the
tiny int8/fp32 numeric delta). Do this offline before the deploy — if the honest wired number doesn't hold
(in_scope ≥ V1, id_oos >> V1, far_oos ~100), fix offline, no deploy wasted.

## Step B — Railway latency (int8 AND fp32) — NEEDS the deploy (the deferred precision fork)
Only latency is hardware-specific and unmeasurable on the Apple-Silicon dev proxy (qnnpack int8 reads
slower than Accelerate fp32 — artifact). On Railway x86 int8 uses FBGEMM (~2–4× faster than fp32).

Deploy procedure (use-railway skill; do NOT run unilaterally):
1. Confirm Railway context — project `sage-api`, a NON-prod environment (staging). Verify no concurrent
   deploy in flight (the collision-#5 discipline).
2. Reranker model (~2.2GB bge-reranker-v2-m3) availability on Railway: either bake into the image or
   warm-download at startup (network). **Verify the head-loaded positive control passes on Railway**
   (the CrossEncoder-headless bug class — assert logit gap >3 at startup) before trusting any number.
3. Deploy the branch with flags: `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1`. Run the benchmark twice:
   `SKILL_RERANK_PRECISION=int8` then `=fp32`.
4. Measure the **V2-incremental** latency (the reranker forward-pass on routing turns specifically — k=5),
   median + p95, on routing turns only (not crisis/info_request). Compare both precisions.

Read three ways:
- int8 adds little (expected on FBGEMM x86) → ship int8.
- int8 ≈ fp32 or worse for some reason → fp32 fallback (~1s proxy); reconsider.
- Either way: the **9.6s baseline p95 is the real wall** — V2-incremental latency only sets V2's *addition*;
  the baseline gates V1 and V2 both and is a SEPARATE workstream that must land for anything to ship.

## Precision fork — RESOLVED BY MEASUREMENT (not now)
int8 and fp32 are the same m3 weights, identical quality (proven). The choice is purely Step-B latency.
Default int8 (hypothesis: faster on x86); fp32 the configurable fallback. Record the choice once measured.

## Keyword-veto τ operating point — decided OFFLINE before deploy (see /tmp/keyword_tau_decide.py)
The keyword-route veto reuses the semantic τ (-6.0843). DECIDED (sweep /tmp/keyword_tau_decide.py, 53
keyword-matched EN cells): **KEEP the semantic τ — no refinement.** A lower keyword-τ (-7.0) nets +2 on
raw equal-weighted correctness (36 vs 34/53), BUT the +2 is safety-for-coverage: lower τ vetoes less →
recovers ~4 in_scope false-vetoes (coverage) at the cost of catching ~2 fewer id_oos bypasses (re-leaks
clinician-territory over-routes — the exact failure the veto exists to fix). id_oos is the safety cell the
+45pp win is about, so the safety-favoring -6.08 is the defensible default; in_scope already holds ≥62.
The -7.0 coverage-favoring point is a CLINICAL weighting choice (same id_oos↔in_scope tension as the whole
effort), surfaced not taken. Deploy the current (semantic-τ) config.

## Standing gates the deploy does NOT resolve (feeds into, doesn't fix)
- **9.6s baseline p95** — pre-existing, gates V1 + V2, separate latency-reduction workstream.
- **AR EN-only** — AR τ = −inf (uncalibrated), pending native-Khaleeji review. Bilingual ship waits on the
  DATA (the model is multilingual; the AR cells/τ don't exist yet). EN-first ships on the EN verdict.

## After deploy
Record: chosen precision + its measured V2-incremental latency; the honest wired re-gate cells; the
precision/global-τ/keyword-τ/bge-reranker-for-Falcon-3B deviations. Then the flip decision is a real
end-to-end verdict gated on the baseline-latency and AR-data workstreams.
