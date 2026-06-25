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

## Step B — Railway latency (fp32 ONLY — precision fork CLOSED on safety, see below)
Only latency is hardware-specific and unmeasurable on the Apple-Silicon dev proxy (qnnpack int8 reads
slower than Accelerate fp32 — artifact). int8 is **disqualified** (safety, below), so the deploy measures
**fp32 batch-1 only** — the deployable number.

Deploy procedure (use-railway skill; do NOT run unilaterally):
1. Confirm Railway context — project `sage-api`, a NON-prod environment (staging). Verify no concurrent
   deploy in flight (the collision-#5 discipline).
2. Reranker model (~2.2GB bge-reranker-v2-m3) availability on Railway: either bake into the image or
   warm-download at startup (network). **Verify the head-loaded positive control passes on Railway**
   (the CrossEncoder-headless bug class — assert logit gap >3 at startup) before trusting any number.
3. Deploy the branch with flags: `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1`. Precision defaults to fp32
   now — no need to set `SKILL_RERANK_PRECISION`. (int8 remains selectable for a curiosity latency probe
   only; it must NOT be shipped — see the safety disqualification.)
4. Measure the **V2-incremental** latency — the reranker forward-pass on routing turns, **DETERMINISTIC
   BATCH-1** (k=5 sequential forward passes, NOT a batched estimate; batch-1 is the shipping scorer and is
   slower than batched — that slower number is the real cost), median + p95, on routing turns only.

Read:
- fp32 batch-1 adds little over the 9.6s baseline → ship fp32.
- fp32 batch-1 adds materially → optimize the scorer (e.g. cache, smaller k) — but precision stays fp32.
- Either way: the **9.6s baseline p95 is the real wall** — V2-incremental latency only sets V2's *addition*;
  the baseline gates V1 and V2 both and is a SEPARATE workstream that must land for anything to ship.

## Precision fork — CLOSED ON SAFETY 2026-06-25 (commit b76ca28), NOT latency
The hypothesis "int8 == fp32 quality, latency the only axis" was **FALSIFIED**. Under deterministic
batch-1 scoring int8 and fp32 still route differently on 29/324 (9%) cases; the safety-relevance check on
those flips found the asymmetric gate TRIPPED — **6/6 id_oos flips in the disqualifying direction**: int8
ROUTES clinician-territory disclosures (disposition=ABSTAIN) that fp32 correctly ABSTAINS, 0 conservative.
Confirmed at the production node (global τ=-6.0843): fp32 6/6 ABSTAIN vs int8 6/6 ROUTE (incl. dbt_tipp on
an irritability disclosure, mindfulness_body_scan on body-image distress — the exact over-route class the
reranker exists to close). int8's higher aggregate id_oos (90 vs 86) was that over-routing, not better
routing. **Decision: fp32 required, regardless of latency. int8 disqualified — not a tradeoff.** Default
flipped to fp32 (`active_precision()`), int8 selectable for probing only.

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

---

## READ-ONLY RAILWAY PREP — 2026-06-25 (commits nothing; blockers surfaced before deploy)

**Railway context (resolved, no link):** project `sage-api` = `4f1811e7-cab2-4002-9107-a9f782f2f274`; service `sage-api` = `160e9f65-e3c8-409a-b647-fbe2339a265d`; environments `production` (`a227d912…`) and `staging` (`b890319d…`). CLI 4.44.0, authed `it@biosight.ai`. NOTE: staging reuses the same service instance and (per staging-env memory) shares prod Supabase — fine for a read-mostly latency probe, but do NOT run write-heavy load against it.

**Three deploy blockers — ALL require work BEFORE `railway up`; none are mid-deploy-discoverable safely:**

1. **STALE BASE (collision-#5 invariant).** Branch `feat/v2-calibrated-retrieval-core` tip `604c4f7` is **ahead 77 / behind 41** vs `origin/master` (tip `db8eb39`, merge-base `f5a56d30`). Master advanced 41 commits — the banned-opener #58 work that **shipped to prod 2026-06-25**. Deploying V2's tip would ship a base missing the live prod changes. → **Reconcile V2 onto `db8eb39` (rebase/merge), then RE-GATE** (the fp32 stabilized re-gate must hold on the reconciled tree — if the merge touches skill_select/routing, re-run it). Verify the exact ship commit carries 21a6994/b76ca28/6b08189/03fd086/604c4f7 (confirmed present on current tip) AND the master delta.

2. **RERANKER NOT BAKED + NO STARTUP HEAD-CONTROL (load-bearing).** `server.py` `_warmup_task()` warms BGE-M3 and gates `/health/ready` on it, but the reranker is ABSENT from startup: (a) Dockerfile bakes BGE-M3 only (`HF_HOME`, pinned revision) — the reranker (`skill_rerank_model._load`, `from_pretrained` with **no `local_files_only`**, `_REVISION=None`) would **download ~2.2GB from HF at runtime** on first routing turn (cold-start + network dependency + non-determinism); (b) **`head_loaded_ok()` never runs at startup** → a silent headless-load on Railway routes confident-wrong with NO error (the CrossEncoder-headless bug class that "nearly killed this" twice). → **Before deploy:** bake bge-reranker-v2-m3 into the Dockerfile (pin `_REVISION` to the deploy SHA, load `local_files_only=True`), AND wire reranker warmup + `head_loaded_ok()` into `_warmup_task()` BEFORE `_bge_ready=True`, gated like BGE-M3 (FAIL readiness / stay 503 on headless load — **block, not warn-and-continue**; the warmup-silent-failure anti-pattern must NOT apply to a safety-critical control). Only fire it when `SKILL_RERANK_ENABLED=1`.

3. **MEMORY HEADROOM (confirm on dashboard).** V2 holds TWO ~2.2GB models resident (BGE-M3 + bge-reranker-v2-m3) + app + httpx pools. Prod today runs BGE-M3 alone. → Confirm the staging instance RAM holds ~2× model footprint (~5–6GB+ working set) before `railway up`; a deploy that succeeds then OOMs at reranker-load is the failure read-only prep exists to pre-empt. (Could not pull the live RAM metric headless — GraphQL script needs a token the CLI doesn't expose; check via dashboard or `railway link`+`status`.)

**Benchmark to run on Railway (the actual remaining question):**
- Measure **fp32 batch-1 V2-incremental latency** specifically — NOT batched (batch-1 is the deterministic shipping scorer and is slower), NOT int8 (safety-disqualified, out of scope). The number = fp32-batch-1's added per-turn cost over baseline.
- At **k=5** (the pipeline the gate validated) so latency corresponds to the quality-validated config.
- On **routing turns only** (not crisis/info_request), median + p95.
- Read against the **9.6s baseline p95** — V2-incremental is what V2 *adds*; the 9.6s is the pre-existing wall gating V1+V2 both and is its own (over-KPI) workstream. Do NOT let "V2 adds little" read as "latency fine" — the baseline is the real wall.
- Reranker must be WARM (blocker-2 fix) so the benchmark measures steady-state batch-1, not the cold-load.

**Deploy procedure (only after 1–3 resolved; do NOT run unilaterally — user-authorized):** reconcile→re-gate→bake+wire→confirm RAM → deploy reconciled tip to **staging** with `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1` (precision defaults fp32) → verify `/health/ready` 200 AND startup head-control passed in logs → run the fp32-batch-1-k5 benchmark → read vs 9.6s baseline.
