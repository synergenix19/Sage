# Async Reranker Integration — Paper Scope (pre-wiring)

**Status:** SCOPE ONLY (no code). Decides the wiring topology before any wiring, because the async decision is a control-flow shape, not a parameter — building sync-first and bolting async on = a rewrite.

## The reframe that simplifies the whole design
The honest global-τ gate: **in_scope 60 (TIE V1) / id_oos 86 (+45 WIN) / far_oos 100 (TIE)**. The reranker's *net* value is **the id_oos ABSTAIN** — it does not improve in_scope over V1, it ties it. So the reranker is not a re-router; it is an **ABSTAIN-veto on bi-encoder over-routes** (don't send a self-help skill to a clinician-territory disclosure). That changes the async question from the hard one ("get the reranker's *pick* into the response") to the easy one ("get the reranker's *veto* to suppress an over-route this turn").

## Topologies considered
1. **Sync-blocking** (reranker inside skill_select's critical path): REJECTED — adds ~1s (k=5, conservative proxy; Railway slower) to a system already at 9.6s p95, over-KPI.
2. **Async-defer-to-next-turn** (respond on bi-encoder, reranker informs the *next* turn): REJECTED — the +45pp id_oos win is safety-relevant ("don't offer dbt_tipp to a substance disclosure"); deferring it a turn async's away the exact benefit that justified the build. This is async's load-bearing failure mode.
3. **Async parallel ABSTAIN-veto** (CANDIDATE): skill_select returns the bi-encoder routing immediately and spawns the reranker as a parallel task; the composer generates on the bi-encoder routing; **output_gate awaits the reranker result and, if it ABSTAINs, suppresses the skill response → freeflow/referral — this turn.**
4. **Uncertainty-gated cascade** (reranker only when bi-encoder is uncertain): INSUFFICIENT ALONE — id_oos over-routes are *confident-but-wrong* (exemplar inflation gives a high bi-encoder score), so a bi-encoder-confidence gate would skip exactly the cases the veto must catch. Usable only as a latency optimization layered on (3), not a substitute.

## Load-bearing question — does async preserve the SAME-TURN id_oos safety win? → YES (topology 3)
The veto is applied at **output_gate** (after the composer, before send) — i.e., *this* turn. The composer's LLM generation is the slow path (multi-second; the 9.6s p95 is mostly LLM); the reranker is ~1s. So the reranker finishes **during** the composer's generation → output_gate awaits an already-complete reranker → the ABSTAIN suppresses the over-route response and substitutes freeflow/referral **on the turn that carried the disclosure.** Same-turn safety preserved. (Worst case — composer finishes faster than the reranker — output_gate waits the residual reranker time, a bounded ≤~1s, never losing the veto.)

## Latency profile
- **Common path (no veto):** near-zero added latency — reranker runs parallel to the composer and finishes first; output_gate consumes a ready result.
- **Veto path (id_oos over-routes only):** the suppressed skill response is wasted (but it ran in parallel, no extra wall-clock), and a freeflow/referral must be produced — ~1 extra LLM call, **only on the safety-critical turns** where safety outranks latency. (Optional: speculatively generate freeflow in parallel to remove even that, at the cost of one always-on extra LLM call — a tradeoff to measure, not decide here.)

## Composition with existing ABSTAIN mechanisms
The reranker-veto **complements** behavior #4 (deterministic clinical-flag ABSTAIN): #4 catches keyworded substance_use etc. via the rules engine; the reranker-veto catches the *semantic* over-routes #4's flags miss (OCD/diagnosis without a flag, substance phrased without keywords). Both are ABSTAIN paths; they compose (either ABSTAINs → freeflow). Must reconcile with the R1 offer model (a vetoed offer must not still surface).

## Risks / open questions to resolve IN this scope (cheap, pre-wiring)
- **[MEASURED BELOW] Does veto-not-promote hold in_scope?** The async-veto keeps bi-encoder routing for in_scope (no promotion) and only ABSTAINs on low reranker confidence. If the veto wrongly ABSTAINs in_scope cases, in_scope drops below the 60 tie. Measured with saved scores before any wiring.
- **BC1 crisis-path-invariance:** the veto is strictly downstream of Node-1 crisis interception (BC1: crisis never reaches skill_select). The veto only suppresses *skill* routing → freeflow; it can never suppress a crisis escalation. Confirm BC1 holds with the flag ON.
- **Graph topology:** skill_select must return immediately + spawn the reranker as a parallel coroutine whose handle rides in state; output_gate awaits it. LangGraph async-node coordination + checkpoint serialization of the pending handle.
- **Freeflow-on-veto latency** (the one real cost) — measure on the vetoed fraction.

## Wiring shape this dictates (different from sync — why scope precedes wiring)
- `skill_rerank` is NOT called inside skill_select's blocking return. skill_select returns bi-encoder routing + spawns the reranker task.
- output_gate gains a veto step: await reranker → if ABSTAIN, replace skill response with freeflow/referral.
- Reranker invocation: **canonical `AutoModelForSequenceClassification`** (never `CrossEncoder` — it silently doesn't load the head), pinned by a **positive-control test** (head loaded, relevant-vs-offtopic logit gap > 3) so a refactor can't silently revert it.

## Deviations from §4.3 (record so the claim is precise)
- **bge-reranker-v2-m3 substituted for Falcon-3B** — cost/fit, justified by the probe (+7.23 control gap, clean per-stratum win).
- **global-τ, not per-route** — the cross-encoder's confidence is uniformly scaled; per-route fragments it (measured 52 vs 60 in_scope).

## ⛔ VALIDATION RESULT (2026-06-24) — TOPOLOGY 3 IS INSUFFICIENT; ASYNC DOES NOT ESCAPE THE CORNER
The veto-not-promote check (/tmp/async_veto_check.py, honest global-τ CV-OOF) measured the async-veto at **in_scope 53 / id_oos 82 / far_oos 100 — in_scope REGRESSES vs V1 60.** The scope's central reframe ("net value is the id_oos veto; in_scope ties anyway") is FALSE: the in_scope tie REQUIRES the **promotion** (route a different skill for the 18% rank-2-3), which the veto topology cannot do — it only suppresses, losing the promotion gains AND wrongly abstaining 15 correct in_scope cases (low reranker confidence on correct V1 routes). And **promotion changes the response content → it cannot run async-after-the-response.** The reranker's full value (promote + veto) is irreducibly on the critical path.

CONSEQUENCE: the clean win (60/86/100) needs **sync** reranking (~1s, k=5). Every latency mitigation tested sacrifices the in_scope tie: async-veto 53, k=3 56. Uncertainty-gating can't help the id_oos veto either (over-routes are confident-but-wrong → no cheap uncertainty signal flags them). **Async is disqualified as the resolution.**

## REVISED OPTIONS (the real corner, no topology escapes it)
1. **Sync k=5, accept the latency** — the clean win, ~1s added on routing turns, on a system already at 9.6s p95 over-KPI. A product/infra decision (id_oos +45 safety vs latency), coupled with the broader latency-reduction effort. Possible infra mitigation: GPU on Railway (cross-encoder is ~10x faster on GPU).
2. **Faster reranker (MOST PROMISING)** — a smaller/distilled/quantized cross-encoder (bge-reranker-base, or int8-quantized bge-reranker-v2-m3) doing promote+veto SYNC at <0.4s. Re-probe quality at the smaller model (the confidence gap may weaken). If it keeps the per-stratum win at viable latency → ships clean. This is the next cheap measurement before any wiring.
3. **Surface the tradeoff as a clinical/product decision** — V1 stays (no latency cost) vs sync-V2 (clean win, +1s on routing turns). The id_oos win is safety-adjacent (don't over-route clinician-territory); the in_scope is coverage (safe freeflow fallback); latency is a hard pilot KPI. This is a three-way weighting above the gate, not an engineering default — same shape as the original tradeoff finding, now with the reranker having shifted the numbers (id_oos +45, in_scope tie achievable at sync cost).

## Build sequence (only after option 2 is probed)
1. Probe a faster reranker's quality (next cheap measurement) — does promote+veto survive a smaller model?
2. If yes → wire SYNC behind the flag, byte-identical-off, head-loaded positive-control, measure Railway latency, full re-gate per-stratum + BC1.
3. If no → surface option 1 vs 3 to product/clinical.
