# V2 Calibrated Retrieval-Core — Build Scope

**Status:** SCOPED 2026-06-24. Greenlit on evidence (V1 held-out baseline, below). Internal-testing exposure only — no live users — so byte-identical proofs are *measurement controls*, not safety guarantees.

## The bar V2 must clear (V1 held-out baseline, 2026-06-24)
Full Tier-1+Tier-2 pipeline, flag OFF = pure V1, EN, decontaminated (5 provenance-shared cases excluded), positive-control-gated:

| EN cell | V1 | failure mode |
|---|---|---|
| in_scope | **66%** (144/217) | Tier-1 keyword caught **0**; all correct routes are Tier-2 semantic; 21% wrong-skill |
| id_oos | **35%** (25/71) | over-offers a skill on 65% that should ABSTAIN (OCD→cbt_thought_record, substance→dbt_tipp, ADHD-dx→psychoed_depression) |
| far_oos | **100%** (36/36) | rejects obvious off-topic cleanly |

V2 must beat 66% / 35% where V1 is weak (novel in_scope, id_oos ABSTAIN) **without regressing the 100%** far_oos. id_oos violations are logged as **known-bugs-V2-fixes** (POC, internal-only) — not patched, because V2 supersedes them.

## Dependency chain (in order)

### Step 1 — EN calibration/eval methodology: **5-fold CV** (the gating prerequisite, reviewer-independent)
The harness already splits on the `held_out` flag (`calibration.py` fits the `held_out=False` + `prior_state=None` slice; per-route threshold earns out only at ≥ min-N TPs, else cluster fallback §6.3). But **all current cells are `held_out=True` — there is no calibration slice.**

Split-in-half is rejected: it drops id_oos to 35 (floor 66) and far_oos to 18/15 (floor 30), and fixing that needs ~60 new id_oos cases requiring fresh clinical ABSTAIN-disposition sign-off (the queued reviewer). **5-fold CV** reuses all clinically-signed data, clears every floor via pooled out-of-fold N, and is pure engineering.

Work (TDD, against fixtures first):
- Add deterministic fold assignment (seeded by record id; stratified within each lang×stratum so folds stay balanced).
- Generalize `calibrate_base_thresholds` to fit per-fold on that fold's 4/5 calibration portion.
- `gate_runner` / AUGRC consume **pooled OOF predictions** (each case scored by the model that excluded it) — no leakage, full-N per cell.
- Shipped thresholds: refit on all data after CV validates the procedure (standard practice; document the distinction).

AR uses the same methodology when its dialect review clears (queued behind the crisis sprint — the native reviewer is the shared bottleneck). EN proceeds now.

### Step 2 — Build + wire the calibrated retrieval-core into `skill_select` behind `SKILL_ROUTING_V2`
Four pieces. `calibration.py` and `debias.py` are **built offline but unwired** — `skill_select` still routes on the global 0.4593. Wire them into the live path:
1. **Per-route + per-language thresholds** (replace global 0.4593) — consume `calibrate_base_thresholds`; cluster-fallback for low-N routes.
2. **Explicit ABSTAIN** (the id_oos fix) — return None/freeflow when no route clears its threshold, instead of argmax-over-global.
3. **Anchor-count debias** — wire `debias.py` (the §6.1 ranking-bleed fix the probe proved necessary).
4. **Crisis-guardrail category fix** — crisis-adjacent inputs route to ABSTAIN (defer to Node-1), never to a skill.

**Byte-identical-when-flag-OFF proof + CI lane** (purpose now: a clean V1 control for the gate, not user-safety): flag-off must reproduce V1 exactly — 240/10 wrong-skill suite before+after, stash control, enforced as a standing CI check. Default off → internal "production" stays V1 until the gate decides.

### Step 3 — Flip-gate: calibrated V2 vs the V1 baseline, on pooled OOF
§5 gate renders the verdict: V2 replaces V1 only if it **beats the baseline per-stratum** (66/35/100), with the harm gate biting and underpowered cells blocking (BC3 `insufficient_to_assert`). Crisis-path-invariance (BC1) checked with the flag **ON**. A strong in_scope gain cannot mask a far_oos regression.

### Step 4 — Ship-if-it-wins = flip the flag for **internal testing**
Low-stakes test-in-the-loop, not a user-facing flip. If V2 loses, it stays off and the baseline says what to fix.

## Open dependencies
- **AR evaluation** — gated on native-Khaleeji dialect review, queued behind the crisis sprint.
- **en/id_oos tight tolerance (0.046)** — still a fail-closed *recommendation* pending product-owner confirm (tolerances.py note); confirm or relax to 0.10 before the gate is authoritative.
- Crisis recall / Arabic bench (task #21) — independent stream, does not gate this.
