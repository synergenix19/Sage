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

1. **STALE BASE (collision-#5 invariant). — RESOLVED 2026-06-25 (reconcile `408e8fe`, branch `reconcile/v2-onto-db8eb39`, pushed).** Was ahead 77 / behind 41 vs `origin/master` `db8eb39` (the banned-opener #58 work shipped to prod 2026-06-25). Reconciled: merged `db8eb39` into a discardable branch off the V2 tip (live `feat/v2` untouched). ONE hand-resolved conflict in `skill_select.py` — master's D3 offer-cooldown block and V2's clinical_flag_abstain block were inserted at the same location; **kept BOTH, clinical safety gate FIRST** (a crisis-adjacent disclosure DEFERS for the clinical reason, not masked by cooldown). All other master changes auto-merged. Both directions verified (master D3 pieces + V2 machinery present; `test_skill_select_offer_cooldown` + V2 byte-identity + 175 fast tests pass). **RE-GATED on the reconciled tree with the pre-registered rule (6b08189, no re-fit): in_scope 60 (131/217) TIE / id_oos 86 (61/71) WIN / far_oos 100 (36/36) — identical counts to pre-reconcile → merge is routing-neutral for the eval (cooldown inert default-OFF). PASS holds on the shipping tree.** Now ahead 79 / behind 0.

2. **RERANKER NOT BAKED + NO STARTUP HEAD-CONTROL (load-bearing). — RESOLVED 2026-06-25 (commit `55a1fbe`).** Was: reranker absent from startup (no bake, `_REVISION=None`, no `local_files_only` → runtime ~2.2GB download; `head_loaded_ok()` never fired → silent-headless-load = confident-wrong routing with no error). Fixed in three parts: (a) `server.py` `_warmup_reranker()` wired into `_warmup_task()` AFTER BGE-M3 / BEFORE `_bge_ready=True`, **readiness-BLOCKING** — `head_loaded_ok()` failure RAISES → `_bge_ready` stays False → `/health/ready` 503 (out of rotation), NOT warn-and-continue; no-op when `SKILL_RERANK_ENABLED!=1`; (b) `_REVISION` pinned to `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (the snapshot every gate result was measured on), `local_files_only` first; (c) Dockerfile bakes the reranker @ that revision via canonical `AutoModelForSequenceClassification`. TDD RED→GREEN (blocks-on-headless / passes-when-loaded / skips-when-disabled), verified with the REAL pinned-revision fp32 load + slow head tests + 41 server tests.

3. **MEMORY HEADROOM. — RESOLVED 2026-06-25 (CLI/GraphQL, accessToken from `~/.railway/config.json`).** Workspace container limit = **24 GB RAM / 24 vCPU / 100 GB disk** (Railway allocates dynamically up to the cap — no fixed small reservation to OOM against). Current V1 staging (one model) MEMORY_USAGE_GB = 1.17–2.47, latest **2.37 GB**. V2 adds the ~2.2GB reranker → est. **~5 GB** working set vs the 24 GB cap = ~5× headroom. No OOM risk. (Staging vars confirm `SAGE_API_KEY` set, `SAGE_WARMUP_BGE=1`; `SKILL_ROUTING_V2`/`SKILL_RERANK_ENABLED` NOT yet set — the deploy sets them. Staging URL `sage-api-staging-a334.up.railway.app`.)

**ALL THREE BLOCKERS CLEARED.** Deploy candidate = branch `reconcile/v2-onto-db8eb39` (tip `79ca973`). Remaining = user authorization for the `railway up` to staging.

## DEPLOY RUNBOOK — STAGED, AWAITING EXPLICIT USER "DEPLOY" (do NOT run unilaterally)
Pre-verified 2026-06-25 (read-only): on `reconcile/v2-onto-db8eb39`, **no CODE change since the measured `55a1fbe`** (docs only), working tree CLEAN, behind 0, linked `sage-api`/`staging`. This is a real **V1→V2 flip on staging** (the flags aren't set there today), which is what the benchmark needs.

**Step 0 — pre-up guard (the "ship what I measured" check; we've been bitten by assumed state before):** confirm on `reconcile/v2-onto-db8eb39`, tip carries `55a1fbe` (code), `git status` clean, `railway status` = sage-api/staging. Stop if any differ.

**Step 1 — set flags + deploy:**
```
railway variables --set SKILL_ROUTING_V2=1 --set SKILL_RERANK_ENABLED=1   # precision defaults fp32 (int8 safety-disqualified)
railway up --detach -m "V2 fp32 reranker — staging benchmark (reconcile/v2-onto-db8eb39)"
```

**Step 2 — HARD HEALTH GATE (stop point — do NOT benchmark until it passes):**
- `curl -s $URL/health/ready` → **HTTP 200** AND JSON body **`"reranker_head_control": "passed"`** (or `"disabled"` if deploying with the reranker off). This is a DIRECT readable check — no reliance on logs.
  - (Superseded 2026-06-25: the original gate said "logs show `reranker head-control passed (warm)`", but that success line is `_log.info` and the app logger defaults to WARNING, so the string is never emitted — the gate was structurally unsatisfiable. Fixed by surfacing the result as the `reranker_head_control` field on `/health/ready`. The functional probe below remains a valid secondary confirmation.)
- **If 503, or the field is `failed`/`pending`/absent: STOP and diagnose the model load.** A 503/`failed` here is NOT "deploy failed, retry" — it's blocker-2's readiness-blocking head-control doing its job: it caught a headless/failed reranker load and took the instance out of rotation (a headless load never reaches 200). The field is the proof the deployed reranker is the real head-bearing routing model, not a silently-headless one serving confident-wrong routes. **Benchmarking a headless instance yields latency for confident-wrong routing — worse than no number.**
- Optional secondary confirmation (functional): POST a known id_oos case (`"I am a perfectionist and it is making me miserable"`) → path has NO `skill_offer_made` (ABSTAIN); POST an in_scope case (`"I keep ruminating on worst-case scenarios I cannot control"`) → path has `skill_offer_made`. The ABSTAIN/offer contrast is the live V2 signature (impossible for a headless reranker).

**Step 3 — benchmark (only past the gate):** fp32 **batch-1**, **k=5** (the validated config), routing turns only (not crisis/info_request), median + p95. Reranker is warm (Step 2), so this is steady-state, not cold-load.

**Step 4 — read vs the 9.6s baseline (the real wall, gates V1+V2 both):** the number is V2's *increment*; the read is the TOTAL and whether it fits the per-turn budget. Three outcomes: (a) increment small, total ≈9.6s → V2 acceptable, remaining gate is the pre-existing 9.6s workstream; (b) increment pushes total well past 9.6s → fp32-batch-1-k5 too slow, levers = k-pruning (quality cost) or baseline-latency workstream first — a real finding, not a failure; (c) number looks implausible → suspect the measurement first (confirm warm + batch-1 + fp32 via the head-control line and config), same discipline as every number in this chain.

Standing gates unaffected by this deploy: 9.6s baseline (own workstream), AR EN-only (τ=−inf, native review + the separate AR precision check the quantization finding flagged).

## ★ PRODUCTION DEPLOY 2026-06-25 — V2 LIVE, clean V1→V2 flip, zero-downtime ★
User-authorized go. Pre-up guard passed (on `fdf6013`/code-frozen-at-`647f515`, behind master 0, clean tree, `railway.json`=600s, routing identical to gated tree). Linked production, set `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1` (fp32), `railway up` (build `fd3e8e08`). RESULT:
- **Zero-downtime CONFIRMED for real users:** prod public `/health/ready` stayed **200 the entire ~9.5min deploy — NO 503-window**. Old V1 container served continuously; Railway held DEPLOYING ~6min waiting for V2 readiness (600s healthcheck), then cut over. The staging-verified healthcheck behavior reproduced on prod.
- **Hard gate PASSED:** `/health/ready` 200 + `{"reranker_head_control":"passed"}`.
- **Functional confirmation (V2 live):** prod `/chat` — id_oos "perfectionist" → ABSTAIN (no `skill_offer_made`); in_scope "ruminating" → `skill_offer_made`. The live V2 60/86/100 signature on production.

**V2 fp32 reranker is LIVE in production.** EN-first: the +45 id_oos safety win reaches EN users now; **AR remains V1/τ=−inf** (native review + AR precision check pending). ROLLBACK: set `SKILL_RERANK_ENABLED=0` (→ byte-identical V1, verified) or `railway redeploy` the prior deployment. Prod URL `sage-api-production-3328.up.railway.app`. Standing: 9.6s baseline (own workstream), AR path.

## DEPLOY EXECUTED 2026-06-25 — staging, V2 live, benchmark PASS
User-authorized. Re-verified latest master first (master had moved db8eb39→**`59b6d8e`** PR#75 #66; the 4 commits touch only L0/prompt templates, NOT routing — merged clean `54296d2`, routing code byte-identical to gated tree, gate transfers by determinism). Deployed `reconcile/v2-onto-db8eb39` `54296d2` to `sage-api/staging` (`railway up`, build `a404edbc` SUCCESS) with `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1` (fp32 default).

**HARD HEALTH GATE — PASSED:** `/health/ready` 200. Head-control: the success line is `_log.info` and the app logger has no `basicConfig` (defaults WARNING) → the "passed (warm)" STRING is never emitted (not retrievable, by logging config, not failure); the FAILURE path is `_log.error` and is ABSENT. Confirmed instead (stronger): (a) deductively — 200+flag-set is unreachable through the readiness-blocking `_warmup_reranker` unless `head_loaded_ok()` returned True; (b) functionally — live /chat probes show the V2 signature: id_oos "perfectionist" → path `[...skill_select, freeflow_respond...]` ABSTAIN (no `skill_offer_made`; V1 would offer self_compassion_break), in_scope "ruminating" → `skill_offer_made`. A headless reranker (~0 logits) can't produce that discrimination.

**BENCHMARK — PASS:** 12 routing turns, warm, fp32 batch-1 k=5: median **6.02s**, p95 **7.01s** (min 5.16 / max 7.90). **Below the 9.6s baseline p95** → reranker increment small (LLM-dominated turn); the remaining latency wall is the pre-existing 9.6s workstream (gates V1 too), not V2. Caveat: TOTAL /chat latency (low-concurrency warm staging), not an isolated reranker microbenchmark or apples-to-apples with the baseline's heavier context; a V1-vs-V2 A/B on the same instance would isolate the increment precisely, but the total clearly fits budget.

**FOLLOW-UPS:**
1. **observability — RESOLVED + VERIFIED 2026-06-25 (commit `4f20c52`).** The hard gate's "logs show head-control passed" condition was structurally unsatisfiable (success line is `_log.info`, app logger defaults WARNING → never emitted). Fixed: `_reranker_status` surfaced as the `reranker_head_control` field on `/health/ready`; runbook Step-2 gate updated to check it. Verified on a staging redeploy (`4f20c52`): `/health/ready` → `{"status":"ready","reranker_head_control":"passed"}`. The prod hard gate is now a direct readable check. TDD'd (7 warmup tests).
2. **PROD HEALTHCHECK — fix VERIFIED ON STAGING 2026-06-25 (reconcile `647f515`, railway.json healthcheckTimeout=600).** After reconciling master (PR#77 latency/embed-cache + PR#78 healthcheck; re-gate PASS identical 60/86/100 — embed-cache is bit-for-bit routing-neutral), deployed the integrated tree to staging and proved the fix empirically: **public `/health/ready` stayed 200 for the ENTIRE ~7.5min deploy (NO 503-window** — vs the ~4.5min 503-window on the prior no-healthcheck deploy); the deploy held in DEPLOYING ~6min (Railway WAITED for `/health/ready` instead of cutting over on port-open) → SUCCESS only after warm, within 600s, final body `reranker_head_control:passed`. So **both preconditions proven: (i) zero-downtime (old container serves until new passes readiness), (ii) Railway treats the readiness-blocking warmup-503 as "still starting, wait" not "failed"** — the healthcheck + blocker-2 head-control coexist correctly. 600s confirmed sufficient (master's 300s too tight, issue #80). The prod precondition "create the healthcheck" is now a VALIDATED fix, not assumed. **WHICH-TREE PRECONDITION RESOLVED 2026-06-25 (read-only):** prod `source: None` (NO GitHub auto-deploy from master); recent prod deploys carry `meta.cliMessage`+`configFile` → prod deploys via manual `railway up` (CLI upload), shipping whatever tree it's run from. So the prod deploy ships `647f515` (railway.json **600s**) and has **NO dependency on master's 300s or on issue #80 landing** — the master-300s failure path (prod auto-deploying master) does not exist. Verified empirically that `railway up` applies the uploaded railway.json (staging healthcheck verification used my branch's 600s and Railway honored it). PROD PRE-UP GUARD: before `railway up --environment production`, confirm on `647f515` and `railway.json` shows `healthcheckTimeout:600` (verify actual config, not intent). Issue #80 = hygiene (bump master 300→600 so a future master-based deploy/merge can't reintroduce 300s) — parallel session's call, NOT a blocker for this prod deploy. ORIGINAL FINDING (for the record):

**PROD HEALTHCHECK — NOT CONFIGURED (was a blocking config precondition; read-only check 2026-06-25).** GraphQL shows BOTH prod and staging have `healthcheckPath=None`, `healthcheckTimeout=None` — the doc's earlier "configure healthcheck ≥120s" was a recommendation NEVER APPLIED. Consequence (two-model warmup ~4.5min observed): (a) no premature-kill risk (no timeout to trip — good by absence); BUT (b) **503-WINDOW TO USERS** — with no healthcheck Railway gates cutover on PORT-OPEN (uvicorn startup), not `/health/ready`, so the new container takes traffic before warmup finishes. CONFIRMED on the staging redeploy: public `/health/ready` returned 503 for 14:52→14:57 even though a warm old container existed (if Railway served the old one, it'd be 200) → no readiness-gated cutover → ~4.5min of 503s per deploy. On staging = harmless (my monitor); on PROD = real users get 503s. **FIX (one change solves both preconditions): set `healthcheckPath=/health/ready` + `healthcheckTimeout≥300s` on prod** (GraphQL `serviceInstanceUpdate`, or dashboard Settings→Healthcheck). Then Railway holds the old V1 container until new V2 passes `/health/ready` 200 (zero-downtime, no 503 window) AND tolerates the ~4.5min warmup. RECOMMENDED: verify the fix on STAGING first (set healthcheck, redeploy, confirm public `/health/ready` stays 200 from the old container throughout warmup — no 503 window — then `passed`), then apply to prod. NOT applied unilaterally (prod config mutation — user-gated).
3. **PROD deploy is a SEPARATE decision** (now favorable: clean per-stratum quality + acceptable latency + satisfiable gate); staging stays V2. Prod is a real V1→V2 flip for users (not a benchmark) — weigh: the 9.6s baseline gates prod-for-users in a way it didn't a staging benchmark; AR ships EN-V2 with AR still V1/τ=−inf (native review + AR precision check outstanding). None necessarily block, but they're the user-facing weights a staging benchmark didn't surface.
4. standing gates unchanged: 9.6s baseline (own workstream), AR EN-only.

**Benchmark to run on Railway (the actual remaining question):**
- Measure **fp32 batch-1 V2-incremental latency** specifically — NOT batched (batch-1 is the deterministic shipping scorer and is slower), NOT int8 (safety-disqualified, out of scope). The number = fp32-batch-1's added per-turn cost over baseline.
- At **k=5** (the pipeline the gate validated) so latency corresponds to the quality-validated config.
- On **routing turns only** (not crisis/info_request), median + p95.
- Read against the **9.6s baseline p95** — V2-incremental is what V2 *adds*; the 9.6s is the pre-existing wall gating V1+V2 both and is its own (over-KPI) workstream. Do NOT let "V2 adds little" read as "latency fine" — the baseline is the real wall.
- Reranker must be WARM (blocker-2 fix) so the benchmark measures steady-state batch-1, not the cold-load.

**Deploy procedure (only after 1–3 resolved; do NOT run unilaterally — user-authorized):** reconcile→re-gate→bake+wire→confirm RAM → deploy reconciled tip to **staging** with `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1` (precision defaults fp32) → verify `/health/ready` 200 AND startup head-control passed in logs → run the fp32-batch-1-k5 benchmark → read vs 9.6s baseline.
