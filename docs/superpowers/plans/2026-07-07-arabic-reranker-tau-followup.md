# Arabic Reranker-τ Calibration — Follow-up Plan (severed from the EN V2-live deploy)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Calibrate the Arabic global reranker-τ so Arabic turns route through V2 with a real ABSTAIN gate (closing the bilingual safety gate), instead of failing closed to V1.

**Parent:** `2026-07-07-make-v2-semantic-routing-live.md`. This plan runs AFTER V2 is live for English. It is the "BLOCKING" item for the **bilingual pilot** — not for the EN deploy (parent Task 6b makes AR fail closed to V1 in the interim).

**Hard dependency (gate):** the 125 AR eval cells are `native_review_required` (native Khaleeji reviewer, Phase 1 of 2 — Lane 3 clinician clock). **Do not start Step 2 until that native-review sign-off exists.** Do not fake AR-τ with the EN-τ.

## Global Constraints

- Same calibration method as EN: balanced Youden's-J on **AR reranker logits** (not bi-encoder), GLOBAL (per-language, not per-route), full-data fit on native-reviewed cells.
- fp32 reranker, pinned revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` — identical to EN.
- Landing AR-τ flips AR from the parent's `v1_fallback_uncalibrated_lang` audit mode to `v2_reranked`/`v2_abstained` automatically (parent Task 6b/6c already read `math.isfinite(_rerank_tau('ar'))`). No routing-code change here — data + calibration only.

---

### Task 1: Confirm the native-review gate

- [ ] **Step 1:** Locate the signed AR native-review record (the Phase-2 completion of the "native Khaleeji reviewer kickoff"). If absent → STOP; report to the command session. This plan cannot proceed.

### Task 2: Calibrate AR-τ

**Files:** Modify `src/sage_poc/nodes/rerank_calibration.json`; Use `src/sage_poc/routing_eval/calibration.py`; Test `tests/routing_eval/test_calibration.py`.

- [ ] **Step 1: Write the failing test**

```python
def test_ar_tau_present_and_gates_abstain():
    from sage_poc.nodes.skill_select import _load_rerank_calibration
    tau = _load_rerank_calibration()
    assert "ar" in tau and tau["ar"] > float("-inf")
```

- [ ] **Step 2: Run → FAIL** (`ar` absent). `uv run pytest tests/routing_eval/test_calibration.py::test_ar_tau_present_and_gates_abstain -v`

- [ ] **Step 3: Compute AR-τ**

Run: `uv run python -m sage_poc.routing_eval.calibration --lang ar --emit tau`
Add to `rerank_calibration.json` under `rerank_tau.ar` with provenance (basis, cell count, native-review SHA).

- [ ] **Step 4: Gate + test**

Run: `uv run python -m sage_poc.routing_eval.gate_runner --lang ar` → AR id_oos ABSTAINs clinician-territory cells, no top-1 over-route, in_scope collateral within tolerance.
Run: `uv run pytest tests/routing_eval/test_calibration.py -v` → PASS.

- [ ] **Step 5: Commit** `git commit -am "feat(routing): calibrate AR reranker-tau from native-reviewed cells (bilingual ABSTAIN gate)"`

### Task 3: Verify AR now takes the V2 path (not the fail-closed fallback)

- [ ] **Step 1:** Re-run the parent's `test_ar_fails_closed_to_v1` — it should now FLIP: with a finite AR-τ, the AR clinician-territory disclosure routes through the reranker and ABSTAINs (mode `v2_abstained`), no longer `v1_fallback_uncalibrated_lang`. Update that test to assert the calibrated behavior in this PR.

### Task 4: Deploy + measure AR in prod

- [ ] **Step 1:** Deploy the AR-τ change (staging → hard health gate → prod), same runbook as parent Task 11.
- [ ] **Step 2:** `uv run python -m sage_poc.routing_eval.gate_runner --target prod --lang ar` → confirm AR id_oos now ABSTAINs live. Record the AR V1→V2 prod delta. Declare the **bilingual safety gate met**.
