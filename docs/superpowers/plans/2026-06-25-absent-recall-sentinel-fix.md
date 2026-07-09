# Absent-Recall Empty-Retrieval Sentinel — Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or executing-plans. Steps use `- [ ]`. Continuation of `2026-06-24-l0-history-regression.md` (read its "Absent-side confabulation — DIAGNOSIS" section first).

**Goal:** Cut the prod absent-side confabulation (~12%, 95% CI ~2–25%; bad for this domain) to near-zero-with-safe-failure by giving the model an explicit "memory retrieval ran and found nothing" anchor — mirroring the knowledge path's existing sentinel — instead of silence it fabricates into.

**Why this fix (diagnosis, already done):** `freeflow_respond.py:112` injects prior-context only when it exists; when empty there is **no sentinel** (the knowledge path has one at `composer.py:354`). PR#51 shipped the L0 *instruction* to admit but never the *signal* to admit against. Root cause = missing signal, not (mainly) wording.

**Dependency graph (the order is load-bearing):**
`Phase 0 gate-methodology fix` → `Phase 1 sentinel build` → `Phase 2 full-path measure` — **all safe to do now, changes nothing live.** Then **Rohan's call gates SHIP** (and whether ~12% sits live in the meantime). Fix-2 (deterministic admit-template) is **NOT** built now — only if Phase 2 residual is still above bar.

**ETA for Rohan's decision:** Phases 0–2 are ~1 day of engineering. So his choice is "accept ~12% live for a **bounded ~1-day window** while a diagnosed, cheap fix ships," not "accept it indefinitely vs roll back to the false-denial vector." Attach this ETA to the finding.

## Global Constraints

- **The sentinel is engineering, not signed content.** It is an internal instruction to the model (like the knowledge sentinel), NOT a change to the Rohan-approved L0 MEMORY clause wording. No re-sign-off required to build; the L0 clause is untouched. (If Rohan wants to review the internal wording, offer it — but it does not gate.)
- **Validate through the FULL STATEFUL GRAPH, never an isolated node call.** This is the methodology hole that produced the overstated 5/5. Phase 0 fixes the gate FIRST; the Phase-0 gate must FAIL on current code (reproduce prod confab) before Phase 1 makes it pass.
- **Do not reach for the deterministic admit-template (fix 2) until the sentinel is measured.** A canned line is a real UX cost on a warmth-critical system; the sentinel may solve it without paying that cost. Escalate only on measured residual.
- **No em dashes in any model-facing string** (commas). One commit per task.
- **Nothing ships to prod from this plan without Rohan's live-vs-rollback decision.** Build + validate are safe; deploy is gated.

---

## Phase 0 — Gate-methodology fix (PRECONDITION; reproduce prod before fixing)

### Task 0: Full-path A4 gate that actually models production

**Files:**
- Create: `tests/test_a4_gate_full_path.py`
- Reference: `tests/test_graph.py` (`make_e2e_state`, `carry_state`, `build_graph` pattern)

**Interfaces:** runs the REAL compiled graph (`build_graph().ainvoke`), stateful, multi-turn via `carry_state` — exercising `intent_route → skill_select → freeflow → output_gate`, NOT a direct `freeflow_respond_node` call.

- [ ] **Step 1: Write the full-path gate (live_llm, majority-vote N=10).** It must encode BOTH sides and currently FAIL on the absent side.

```python
# tests/test_a4_gate_full_path.py
import asyncio, pytest
from sage_poc.graph import build_graph
from tests.test_graph import make_e2e_state, carry_state   # reuse the established full-graph harness

N, NEED = 10, 9   # absent side must admit >=9/10 (near-zero-fail-safe bar)
DENY = ["no record","cannot see","can't see","don't have","do not have","no mention","no information",
        "no earlier","share it again","tell me again","nothing you","not see anything"]

def _resp(result): return (result.get("response_en") or result.get("response") or "").lower()

@pytest.mark.live_llm
def test_present_recall_full_path_answers():
    # disclosure turn -> recall turn (same threaded state). Must RECALL the disclosure.
    g = build_graph()
    ok = 0
    for _ in range(N):
        s1 = asyncio.run(g.ainvoke(make_e2e_state("things at home with my husband have gotten scary")))
        s2 = asyncio.run(g.ainvoke(carry_state(s1, "what did I just tell you about my husband?")))
        r = _resp(s2)
        if "husband" in r and "scary" in r and not any(d in r for d in DENY): ok += 1
    assert ok >= NEED, f"present-recall {ok}/{N}"

@pytest.mark.live_llm
def test_absent_recall_full_path_admits():
    # recall with NO prior disclosure. Must ADMIT, not confabulate. EXPECTED TO FAIL pre-sentinel.
    g = build_graph()
    admits = 0
    for _ in range(N):
        s = asyncio.run(g.ainvoke(make_e2e_state("what did I just tell you about my husband?")))
        if any(d in _resp(s) for d in DENY): admits += 1
    assert admits >= NEED, f"absent-recall admitted only {admits}/{N} (confabulated the rest)"
```

- [ ] **Step 2: Run, and CHECK CONCORDANCE — "red" is necessary but NOT sufficient.** `pytest tests/test_a4_gate_full_path.py -v -m live_llm`. Present ≥9/10 PASS; absent FAILS. **But the real exit criterion is that the gate reproduces confabulation at a rate CONSISTENT with prod's ~12% (95% CI ~2–25%), not merely non-zero.** A full-path gate that confabulates ~1-in-2 when prod is ~1-in-8 is over-sensitive — a harsher path than production — and a fix that greens *it* may overshoot or chase an artifact. That would be swapping one unvalidated gate for another that just fails in the right direction.
  - **Measure it:** run the absent case n≥30 (not the 10-seed assert) and compute admit-rate + Wilson CI. **Exit Phase 0 only if the gate's confab rate overlaps the prod band (~2–25%).** If it's materially harsher (e.g., >40%), the harness diverges from prod — investigate the path difference before building the sentinel against it. Bring the gate's reproduced rate back ALONGSIDE the prod ~12% for the concordance check before Phase 1.

- [ ] **Step 3: Commit (the gate, red on absent).**

```bash
git add tests/test_a4_gate_full_path.py
git commit -m "test(a4): full-path A4 gate (stateful graph); absent side red, reproducing prod confab"
```

- [ ] **Step 4: Mark the isolated gate as non-authoritative.** Add a docstring note to `tests/test_l0_memory_clause.py` that it tests freeflow in ISOLATION and OVERSTATED A4 (gate 5/5 vs prod ~12%); the full-path gate is authoritative. Do not delete (it still guards the clause text cheaply). Commit.

---

## Phase 1 — Composer empty-retrieval sentinel

### Task 1: `memory_absent_sentinel` helper (reuses Task-3 anchor)

**Files:**
- Modify: `src/sage_poc/prompts/composer.py` (near the anchor helpers, ~line 537)
- Test: `tests/test_memory_absent_sentinel.py`

**Interfaces:** `memory_absent_sentinel(state, prior_context_present: bool) -> str | None` — returns the sentinel only when a recall was requested (`self_reference`) AND grounding is genuinely empty (no prior-context, and no salient-token overlap between the recall and any history turn). `None` on the present case so the model still recalls.

- [ ] **Step 1: Failing test**

```python
# tests/test_memory_absent_sentinel.py
from sage_poc.prompts.composer import memory_absent_sentinel

def _s(**k):
    base = {"self_reference": True, "detected_language": "en",
            "message_en": "what did I just tell you about my husband?", "raw_message": "...",
            "conversation_history": []}
    base.update(k); return base

def test_sentinel_fires_when_recall_and_no_grounding():
    assert memory_absent_sentinel(_s(), prior_context_present=False) is not None

def test_no_sentinel_when_disclosure_present_in_history():
    s = _s(conversation_history=[{"role":"user","content":"things at home with my husband have gotten scary"},
                                 {"role":"assistant","content":"thank you"}])
    assert memory_absent_sentinel(s, prior_context_present=False) is None   # present case -> model recalls

def test_no_sentinel_when_history_exists_but_unrelated():
    # BACK-DOOR PROTECTION: history present but no keyword match to the recall. Sentinel must NOT fire,
    # or it would assert "I can't see that" over real history = false-denial reintroduced.
    s = _s(conversation_history=[{"role":"user","content":"work has been really stressful this week"},
                                 {"role":"assistant","content":"that sounds hard"}])
    assert memory_absent_sentinel(s, prior_context_present=False) is None

def test_no_sentinel_when_prior_context_exists():
    assert memory_absent_sentinel(_s(), prior_context_present=True) is None

def test_no_sentinel_when_not_a_recall():
    assert memory_absent_sentinel(_s(self_reference=False), prior_context_present=False) is None
```

- [ ] **Step 2: Run → fail** (`ImportError`).

- [ ] **Step 3: Implement** in `composer.py`. **SAFE TRIGGER (do not use the keyword-anchor here):** fire ONLY when grounding is genuinely, unambiguously empty — no prior-context AND no user turns in history. Rationale (the back-door seam): a salient-overlap test would declare "absent" whenever the disclosure and the recall use different words, firing "I can't see that" over a REAL disclosure = the false-denial vector reintroduced. The two failure directions are not equally safe, so the sentinel must err toward NOT firing when any history exists. This is a role-based check, so it also carries no Arabic-anchor dependency (no English-only re-derivation risk). The "history-exists-but-not-the-recalled-topic" sub-case is intentionally NOT covered here (deferred) — covering it requires resolving the topic, which is exactly where the back-door lives.

```python
_MEMORY_ABSENT_SENTINEL = (
    "MEMORY CHECK: the person is asking you to recall something, but no earlier record of it was "
    "found, not in this conversation and not in any prior-session context above. Do not invent, "
    "infer, or guess what they said. Tell them you do not have a record of that and invite them to "
    "share it again."
)

def memory_absent_sentinel(state: SageState, prior_context_present: bool) -> str | None:
    """Empty-retrieval anchor for the MEMORY path (mirrors the knowledge sentinel). Fires ONLY when a
    recall is requested AND grounding is genuinely empty: no prior-session context and no user turns
    in this conversation. Errs toward NOT firing when any history exists, so it can never assert
    absence over real disclosure (that would re-introduce the false-denial vector v2.4.0 fixed)."""
    if not state.get("self_reference") or prior_context_present:
        return None
    if any(m.get("role") == "user" for m in state.get("conversation_history", [])):
        return None  # any user history -> do NOT assert absence (avoid false-denial back-door)
    return _MEMORY_ABSENT_SENTINEL
```

**Anchor-reuse note (your Phase-1 verify):** this trigger deliberately does NOT reuse `_anchor_turn`, so the Arabic-parity fix can't silently reopen — but it also means the eviction-exemption (Task 3) is the path that still depends on the Arabic-aware anchor; that dependency is unchanged and already tested. The sentinel and the eviction-pin are now independent.

- [ ] **Step 4: Run → pass.** Commit.

### Task 2: Inject the sentinel in freeflow (the absent branch)

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py:112-114`
- Test: `tests/test_freeflow_sentinel_injection.py`

- [ ] **Step 1: Failing test** — assert the `memory_absent_sentinel` layer is present on a recall-with-no-grounding turn and absent on a present-history turn (assert via `prompt_layers` to avoid a live call).

```python
# tests/test_freeflow_sentinel_injection.py — uses a stubbed llm to avoid network; asserts prompt_layers
import asyncio, pytest
from sage_poc.nodes import freeflow_respond as ff

class _Stub:
    async def ainvoke(self, msgs): 
        class M: content="ok"
        return M()
    def bind_tools(self, t): return self

def _state(hist):
    return {"self_reference": True, "message_en":"what did I just tell you about my husband?",
            "raw_message":"...", "detected_language":"en", "conversation_history":hist,
            "user_id":None, "session_id":None, "primary_intent":"general_chat", "active_skill_id":None,
            "emotional_intensity":5, "engagement":5, "clinical_flags":[], "crisis_state":"none", "path":[],
            "directive_posture":False, "stall_detected":False, "declined_skills":[], "conversation_summary":None}

@pytest.mark.asyncio
async def test_sentinel_layer_on_absent_recall(monkeypatch):
    out = await ff.freeflow_respond_node(_state([]), llm=_Stub())
    assert "memory_absent_sentinel" in out["prompt_layers"]

@pytest.mark.asyncio
async def test_no_sentinel_layer_when_disclosure_present(monkeypatch):
    out = await ff.freeflow_respond_node(_state(
        [{"role":"user","content":"things at home with my husband have gotten scary"},
         {"role":"assistant","content":"thanks"}]), llm=_Stub())
    assert "memory_absent_sentinel" not in out["prompt_layers"]
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement** — change the `if prior_context:` block:

```python
    if prior_context:
        system_str = system_str + "\n\nPRIOR SESSION CONTEXT (share naturally, not verbatim):\n" + prior_context
        prompt_layers = list(prompt_layers) + ["prior_session_context"]
    else:
        from sage_poc.prompts.composer import memory_absent_sentinel  # noqa: PLC0415
        _sentinel = memory_absent_sentinel(state, prior_context_present=False)
        if _sentinel:
            system_str = system_str + "\n\n" + _sentinel
            prompt_layers = list(prompt_layers) + ["memory_absent_sentinel"]
```

- [ ] **Step 4: Run → pass. Full suite `pytest -q` (no regressions).** Commit.

---

## Phase 2 — Validate through the full path + measure

### Task 3: Make the Phase-0 gate go green; measure the residual

- [ ] **Step 1: Re-run the full-path A4 gate to ITERATE (9/10 is a fast signal, NOT a certification).** `pytest ... -m live_llm`. ≥9/10 admit = keep going. **Do not quote 9/10 as "the fix worked"** — at N=10 that's a wide CI (a true rate anywhere from ~80% to ~95%), the same don't-outrun-the-sample trap corrected twice already.
- [ ] **Step 2: CERTIFY with a larger sample.** Full-path absent measurement n≥30 (ideally ≥50), report admit-rate + Wilson CI. The number that backs "the fix worked" to Rohan must come from this, not the 10-seed iteration gate. Bar: near-zero confab, every residual failing safe (admit).
- [ ] **Step 3: Decision point on fix-2.** If residual confab is still above bar after the sentinel, spec the deterministic admit-template (self_reference + empty grounding → templated admit, not free generation) as a SEPARATE task — weighing its warmth/UX cost. Do not build pre-emptively.

### Task 4: Prod validation — GATED on Rohan's ship decision

- [ ] **Do not deploy until Rohan decides** (accept-live-while-fixing vs rollback). When cleared: `railway up` to prod, then the **stateful two-turn prod smoke test** (disclosure→recall present = accurate; fresh-session recall absent = admits), report admit-rate. Roll forward only if prod matches the full-path gate.

---

## CERTIFICATION RESULT (2026-06-25, full-path gate, n=30)

- **Pre-sentinel full-path absent: ~28% confab (7/25, CI ~14–47%)** — concordant with prod ~12% (overlapping bands; synthesized true rate ~15–25%).
- **Post-sentinel full-path absent (TIGHTENED, n=55): 0/55 confab.** 95% upper bound ~6% (rule-of-three ~5.5%, ≈ 1-in-18), down from ~15–25%. Decisively clears the pre-fix range.
- **Present-side regression check (full-path, real N): NO regression.** EN recall 15/15, Arabic recall 6/6, sentinel misfired 0/21. Fixing the absent side did not degrade the already-live present-side fix; the Arabic detect→recall→no-sentinel chain holds end-to-end.
- Unit/injection tests green: `test_memory_absent_sentinel.py` (5/5, incl. back-door protection), `test_freeflow_sentinel_injection.py` (2/2).

## Documented seam (absent side) — detection regex, not the sentinel

The sentinel fires only when `self_reference` is True, which is set by the EN/AR **regex** detector. A recall the regex MISSES (e.g. an Arabic phrasing outside the pattern) gets `self_reference=False` → no sentinel (and no eviction protection). **Its absent-side behavior then degrades to the pre-fix baseline: silence + the L0 instruction → confabulates at ~15–25%.** This is the *same* failure as before the fix, NOT a new or worse one — the sentinel adds no harm to missed-detection cases, it just does not fix them. Safe-failure direction confirmed (no regression for the seam). Closing the seam = widening detector recall (separate, lower-priority), not changing the sentinel.

## Hand to Rohan now (with ETA)

Update `docs/superpowers/governance/2026-06-25-L0-v2.4.0-prod-A4-finding.md`: the fix is diagnosed and cheap (engineering sentinel, no clause re-sign-off), full-path-validated before ship, ETA ~1 day. His decision is bounded: accept ~12% (CI 2–25%) for ~1 day while the sentinel ships, vs roll back to the false-denial vector. Denial-vs-fabrication, time-boxed.
