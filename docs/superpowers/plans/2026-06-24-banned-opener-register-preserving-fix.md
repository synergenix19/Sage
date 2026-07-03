# Banned-Opener Register-Preserving Fix — Implementation Plan (resolves #58)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the banned-opener *full regeneration → canned fallback* with an inline **gpt-4o-mini opener-only rewrite** (given the rejected reply + the exact opener as context), and **pass the model's real reply through** instead of a content-free placeholder when the rewrite can't satisfy the rule.

**Architecture:** Today `output_gate` detects a banned opener (`_BANNED_OPENER_RE`) and routes back to `freeflow_respond` for a fresh **gpt-4o** generation (`_route_after_output_gate`, `graph.py:244`); if that also offends, it substitutes the canned `_VETTED_FALLBACK_RESPONSE`. We replace that with a single **in-node** rewrite call: pass the model its own rejected reply + the matched opener to **gpt-4o-mini**, instruct it to rewrite *only the opening* and keep the rest verbatim. If the rewrite still opens badly or is empty, **pass the original reply through** (lesser evil) rather than the placeholder. This removes the graph re-entry entirely, turns a ~2-4s second gpt-4o generation into a ~1s gpt-4o-mini edit, preserves the model's content/register, and kills the 2.8% content-free-fallback rate.

**Tech Stack:** LangGraph, FastAPI, `langchain_openai` (gpt-4o-mini via OpenRouter), pytest.

> ## Rev 2 — review dispositions (2026-06-24, verified against code)
> - **[was flagged as a live safety hole — corrected] Crisis cannot reach the rewrite.** `_crisis_response_node` routes straight to `END` (`graph.py:142`, "output_gate is bypassed for crisis responses"). So crisis copy is never eligible. BUT the original guard was a fragile *blocklist*; **fixed by inverting to an allowlist** — the rewrite runs ONLY on ordinary turns (`gate_path in (None, "standard")`), which structurally excludes `scope_refusal`, `jailbreak`, and any future scripted/safety `gate_path`. Test asserts crisis/scope/jailbreak never reach `_rewrite_opener`. (T-11: the four output-gate patterns stay distinct.)
> - **[upgraded minor→must-fix] Fail-fast rewrite timeout.** `resilient_invoke` uses a fixed 30s timeout × 2 retries (no per-call override) and the graph ceiling is 55s — a hanging rewrite on ~27% of turns could time the whole turn into a SERVER_ERROR. The rewrite therefore does NOT use `resilient_invoke`; it uses a dedicated ~4s `asyncio.wait_for`, no retries, failing to pass-through. The rewrite is non-critical (pass-through is a safe fallback), so the circuit breaker isn't needed.
> - **[accepted] Audit traceability.** The rewrite is a second model invocation that mutates user-facing content → record it (model, matched opener, applied/passthrough) so the reply stays traceable (v7 §13.1, explainability). Added to the audit write.
> - **[accepted] Named determinism deviation.** v7 §5.5 / ABSOLUTE RULE 1: Node 8 cultural rules are deterministic "no LLM." This introduces a probabilistic edit at Node 8. It is bounded: the deterministic `_BANNED_OPENER_RE` re-check after the rewrite is **load-bearing and must never be skipped** (LLM proposes, regex disposes, failure → deterministic pass-through). Flagged as a deliberate deviation in the sign-off.
> - **[accepted] Production sovereign-model gate.** Reusing `get_classifier()` is deliberate so the rewrite follows the eventual sovereign Node 8 model swap — but gpt-4o-mini register quality will NOT transfer 1:1 to a 3B model. Production gate: must be sovereign AND re-validate rewrite register on the sovereign model before shipping beyond POC.
> - **[accepted] Root cause is the prompt.** A 27.2% banned-opener rate means L0/L2 register isn't holding at source. The inline rewrite is a **symptom mitigation, not the cure**; every point shaved at the prompt removes a rewrite call from the critical path. Sequence the L0/L2 strengthening **soon after** this, not "eventually."
> - **[accepted] Arabic has no opener guard** (pre-existing — detection is English-only). Not introduced here; tracked as a separate item.

## Global Constraints (verified facts — do not re-derive)
- Backend repo `sage-poc`; prod deploys from `master` via `railway up` from a clean git worktree (see the 2026-06-24 latency quick-wins plan / PR #54 for the exact flow). Do NOT deploy from a feature branch.
- **Baseline (real users, from `session_audit.node_path` markers, n=1423):** banned-opener regeneration fires on **27.2%** of turns; canned fallback substitutes on **2.8%**. These are the before-numbers; re-run the query in Task 5 after deploy.
- **CLINICAL SIGN-OFF REQUIRED before merge/deploy** (this touches user-facing register), on three items: (a) the rewrite-instruction copy, (b) the decision "pass a real reply with a soft banned opener through > substitute a content-free placeholder" (strong prior: yes), (c) confirmation the rewrite output preserves the warm-not-clinical register. Engineering may build + test behind a DRAFT instruction in parallel; the merge is gated on sign-off. This is its own change and must NOT ride an infra deploy.
- Banned-opener detection runs on the **English** response only (`response_en`, `output_gate.py:409` guard `not _response_en_is_arabic`); the rewrite is English-only, before any Arabic translation. Do not change that scoping.
- The em-dash / format rules in the action-content strings still apply: **no em dashes in any new copy**; use commas.
- Reuse `get_classifier()` (gpt-4o-mini) for the rewrite — do NOT add a new model client. The rewrite call does **NOT** use `resilient_invoke` (its fixed 30s×2 timeout under the 55s graph ceiling is a SERVER_ERROR vector on the 27% of turns that fire); it uses a dedicated ~4s `asyncio.wait_for`, no retries, degrading to pass-through (see Task 1).
- **Defense-in-depth, not a single invariant:** the rewrite must be skipped for BOTH the `gate_path` allowlist AND an in-node crisis-state check (`not state.get("crisis_flags")`). Crisis currently can't reach output_gate (`crisis_flags` → `is_safe=False` → `crisis` route → `END`, verified `graph.py:149-155`), but the highest-stakes case must not depend on an upstream routing invariant alone.

---

## Wave 0 — Clinical sign-off package (the bottleneck; start immediately, in parallel with code)

- [ ] **Step 0.1: Write the sign-off request doc**

Create `docs/superpowers/reviews/2026-06-24-banned-opener-rewrite-signoff.md` containing: the baseline numbers (27.2% regen, 2.8% canned); the three clinical decisions (rewrite copy, pass-through > placeholder, register preservation); the **named determinism deviation** (Node 8 now uses a probabilistic edit, bounded by the load-bearing `_BANNED_OPENER_RE` re-check — ABSOLUTE RULE 1 disclosure); the **production sovereign-model gate** (rewrite must re-validate register on the sovereign Node 8 model before shipping beyond POC); the DRAFT rewrite instruction (from Task 1); and 3-4 worked before/after examples ("It sounds like things are hard right now." / "That sounds really tough." / "I'm sorry to hear you've been struggling."). Link issue #58. This is the artifact the clinical lead signs.

The code tasks below proceed in parallel; only the **merge** (Task 5) is gated on this returning signed-off.

---

## File Structure
- `sage-poc/src/sage_poc/nodes/output_gate.py` — replace the banned-opener regen/fallback block (`:409-446`) with an inline rewrite + pass-through; add the rewrite helper + draft instruction constants.
- `sage-poc/src/sage_poc/graph.py` — remove the banned-opener re-entry branch from `_route_after_output_gate` (`:244-249`).
- `sage-poc/src/sage_poc/prompts/composer.py` — remove the now-dead `[CORRECTION]` injection (`:894-897`).
- `sage-poc/tests/test_output_gate_banned_opener.py` (new) — unit + behavioral tests for the rewrite, pass-through, and empty-fallback paths.
- `scratchpad/banned_opener_rate.py` (throwaway) — the before/after prod query.

---

## Task 1: Opener-rewrite helper

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py` (add constants + helper near the existing banned-opener constants, ~`:164`)
- Test: `sage-poc/tests/test_output_gate_banned_opener.py`

**Interfaces:**
- Produces: `async def _rewrite_opener(response_en: str, opener: str, user_message_en: str) -> str` — returns the full reply with only the opening rewritten, or `""` on LLM failure.

- [ ] **Step 1: Add the DRAFT rewrite instruction constants**

In `output_gate.py`, near the existing `_BANNED_OPENER_CORRECTION`:

```python
# DRAFT — pending clinical sign-off (see docs/superpowers/reviews/2026-06-24-banned-opener-rewrite-signoff.md).
# Rewrites ONLY the opening of a reply that began with a banned reflective/sympathy/praise opener,
# preserving the model's own subsequent sentences and the warm Khaleeji wellness-companion register.
# No em dashes (commas only). Returns the full revised reply, nothing else.
_OPENER_REWRITE_SYSTEM = (
    "You are lightly editing one wellness-companion reply that you wrote. It began with a "
    "reflective or sympathy cliche we avoid. Rewrite ONLY the opening so it names the specific "
    "thing the person said, warm and present, one to one. Keep every following sentence exactly "
    "as written. Do not add advice, do not add a question, do not change the length or the meaning. "
    "Use plain prose, commas not dashes, no emojis. Return only the full revised reply."
)
def _opener_rewrite_user(user_message_en: str, response_en: str, opener: str) -> str:
    return (
        f"The person said: {user_message_en}\n\n"
        f"Your reply (revise only the opening, keep the rest verbatim): {response_en}\n\n"
        f"The banned opener you used and must replace: {opener}"
    )
```

- [ ] **Step 2: Write the failing test**

In `tests/test_output_gate_banned_opener.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes import output_gate

@pytest.mark.asyncio
async def test_rewrite_opener_passes_context_and_returns_text():
    captured = {}
    async def fake_invoke(llm, messages, **kwargs):
        captured["messages"] = messages
        return "You're carrying a lot with these deadlines. The lack of sleep makes it heavier."
    with patch.object(output_gate, "resilient_invoke", side_effect=fake_invoke):
        out = await output_gate._rewrite_opener(
            response_en="It sounds like things are hard right now. The lack of sleep makes it heavier.",
            opener="It sounds like",
            user_message_en="deadlines keep piling up and I can't sleep",
        )
    # the rejected reply AND the specific opener must reach the model
    joined = " ".join(m["content"] for m in captured["messages"])
    assert "It sounds like" in joined and "deadlines keep piling up" in joined
    assert out.startswith("You're carrying")
    assert "it sounds like" not in out.lower()
```

- [ ] **Step 3: Run it — expect fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_output_gate_banned_opener.py::test_rewrite_opener_passes_context_and_returns_text -v`
Expected: FAIL — `output_gate has no attribute '_rewrite_opener'`.

- [ ] **Step 4: Implement the helper**

In `output_gate.py` add `from sage_poc.llm import get_classifier` if absent (do NOT use `resilient_invoke` here — its fixed 30s×2 timeout would risk the 55s graph ceiling; the rewrite is non-critical and must fail fast to pass-through):

```python
import asyncio  # if not already imported
_OPENER_REWRITE_TIMEOUT = 4.0  # fail fast → pass-through; never block the turn on a non-critical edit

async def _rewrite_opener(response_en: str, opener: str, user_message_en: str) -> str:
    """Rewrite only the banned opening of an existing reply via the classifier model,
    preserving the rest. Returns "" on timeout/failure (caller passes the original through).
    Deliberately NOT wrapped in resilient_invoke: a slow rewrite must degrade to pass-through,
    not consume the graph's 55s budget. No retries — pass-through is the safe fallback."""
    if not response_en:
        return ""
    try:
        msg = await asyncio.wait_for(
            get_classifier().ainvoke([
                {"role": "system", "content": _OPENER_REWRITE_SYSTEM},
                {"role": "user", "content": _opener_rewrite_user(user_message_en, response_en, opener)},
            ]),
            timeout=_OPENER_REWRITE_TIMEOUT,
        )
        return msg if isinstance(msg, str) else (getattr(msg, "content", None) or "")
    except Exception:
        # asyncio.TimeoutError is an Exception subclass; CancelledError is NOT and is correctly
        # not swallowed. Any failure → "" → caller passes the original reply through.
        return ""
```

Add a fail-fast test:

```python
@pytest.mark.asyncio
async def test_rewrite_opener_times_out_to_empty(monkeypatch):
    import asyncio
    class _Slow:
        async def ainvoke(self, *a, **k):
            await asyncio.sleep(10)  # longer than the 4s budget
            return "never"
    monkeypatch.setattr(output_gate, "get_classifier", lambda: _Slow())
    monkeypatch.setattr(output_gate, "_OPENER_REWRITE_TIMEOUT", 0.2)
    out = await output_gate._rewrite_opener("It sounds like things are hard.", "It sounds like", "msg")
    assert out == ""   # timed out → empty → caller passes original through
```

- [ ] **Step 5: Run it — expect pass**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_output_gate_banned_opener.py::test_rewrite_opener_passes_context_and_returns_text -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_banned_opener.py
git commit -m "feat(output_gate): add gpt-4o-mini opener-rewrite helper (draft copy, #58)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Wire the rewrite into output_gate (replace regen + canned-default)

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/output_gate.py:409-446`
- Test: `sage-poc/tests/test_output_gate_banned_opener.py`

**Interfaces:**
- Consumes: `_rewrite_opener` (Task 1), `_BANNED_OPENER_RE`, `_VETTED_FALLBACK_RESPONSE` (existing).
- Produces: when a banned opener is detected, `response_en` becomes the rewritten reply (path marker `output_gate_opener_rewritten`) or the original reply (path marker `output_gate_opener_passthrough`); the canned fallback is used ONLY when the original reply is empty.

- [ ] **Step 1: Write the failing behavioral tests**

Add to `tests/test_output_gate_banned_opener.py`:

```python
async def _run_gate(monkeypatch, response_en, rewrite_return, user_msg="I can't sleep",
                    gate_path=None, crisis_flags=None):
    from sage_poc.nodes import output_gate as og
    calls = []
    async def fake_rewrite(response_en, opener, user_message_en):
        calls.append(opener); return rewrite_return
    monkeypatch.setattr(og, "_rewrite_opener", fake_rewrite)
    state = {
        "response_en": response_en, "message_en": user_msg, "path": ["freeflow_respond"],
        "detected_language": "en", "gate_path": gate_path, "banned_opener_retry_count": 0,
        "crisis_flags": crisis_flags or [], "clinical_flags": [], "turn_count": 3,
        "conversation_history": [], "session_id": None, "user_id": None,
    }
    res = await og.output_gate_node(state); res["_rewrite_calls"] = calls
    return res

@pytest.mark.asyncio
async def test_scripted_safety_paths_are_never_rewritten(monkeypatch):
    # scope_refusal/jailbreak copy must never be sent to the opener rewriter, even if it
    # happens to match a banned-opener pattern.
    for gp in ("scope_refusal", "jailbreak"):
        res = await _run_gate(monkeypatch,
            response_en="It sounds like you want a diagnosis, which I can't give.",
            rewrite_return="REWRITTEN", gate_path=gp)
        assert res["_rewrite_calls"] == []                      # rewriter not invoked
        assert "output_gate_opener_rewritten" not in res["path"]

@pytest.mark.asyncio
async def test_crisis_state_is_never_rewritten(monkeypatch):
    # Highest-stakes case: even if a crisis-flagged turn reached output_gate with gate_path=None
    # (it shouldn't, but safety must not depend on the routing invariant alone), the in-node
    # crisis guard skips the rewriter entirely.
    res = await _run_gate(monkeypatch,
        response_en="It sounds like you're in real danger right now. Please call 999.",
        rewrite_return="REWRITTEN", gate_path=None, crisis_flags=["si_explicit"])
    assert res["_rewrite_calls"] == []
    assert "output_gate_opener_rewritten" not in res["path"]

@pytest.mark.asyncio
async def test_banned_opener_is_rewritten_inline(monkeypatch):
    res = await _run_gate(monkeypatch,
        response_en="It sounds like things are hard. You're not alone in this.",
        rewrite_return="The deadlines are stacking up on you. You're not alone in this.")
    assert res["response"].startswith("The deadlines")
    assert "output_gate_opener_rewritten" in res["path"]

@pytest.mark.asyncio
async def test_rewrite_failure_passes_original_through_not_canned(monkeypatch):
    original = "It sounds like things are hard. You're not alone in this."
    res = await _run_gate(monkeypatch, response_en=original, rewrite_return="")  # rewrite failed
    assert res["response"] == original              # the REAL reply, not the placeholder
    assert _placeholder_text() not in res["response"]
    assert "output_gate_opener_passthrough" in res["path"]

@pytest.mark.asyncio
async def test_empty_response_still_uses_canned_fallback(monkeypatch):
    res = await _run_gate(monkeypatch, response_en="", rewrite_return="")
    assert res["response"]  # non-empty: the empty-generation fallback still applies

def _placeholder_text():
    from sage_poc.nodes.output_gate import _VETTED_FALLBACK_RESPONSE
    return _VETTED_FALLBACK_RESPONSE
```

- [ ] **Step 2: Run them — expect fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_output_gate_banned_opener.py -v -k "rewritten or passes_original or empty_response"`
Expected: FAIL (current code routes back to freeflow / substitutes canned).

- [ ] **Step 3: Replace the banned-opener block (`output_gate.py:409-446`)**

Replace the `if banned_match:` regen/fallback block with an inline rewrite + pass-through:

```python
    # ALLOWLIST (not blocklist): rewrite ONLY ordinary freeflow/skill turns. Scripted/safety
    # paths (scope_refusal, jailbreak) keep their clinician-authored copy; crisis never reaches
    # output_gate (routes to END). Keeps the four output-gate patterns distinct (T-11).
    opener_rewrite_audit = None
    # Defense-in-depth: allowlist by gate_path AND an in-node crisis guard, so the highest-stakes
    # case never depends on the upstream routing invariant alone (crisis_flags => is_safe=False =>
    # crisis route => END, so this is belt-and-suspenders).
    if gate_path in (None, "standard") and not state.get("crisis_flags") and response_en and not _response_en_is_arabic:
        banned_match = _BANNED_OPENER_RE.match(response_en.lstrip())
        if banned_match:
            opener = banned_match.group(0)
            _t0 = time.monotonic()  # `time` is already imported (used at output_gate.py:297)
            rewritten = await _rewrite_opener(response_en, opener, state.get("message_en", ""))
            _rw_ms = int((time.monotonic() - _t0) * 1000)
            # LOAD-BEARING deterministic re-check: the LLM proposes, _BANNED_OPENER_RE disposes.
            # MUST NOT be removed — it is what keeps Node 8 deterministic at the gate (ABSOLUTE RULE 1).
            if rewritten and not _BANNED_OPENER_RE.match(rewritten.lstrip()):
                response_en = rewritten
                path = path + ["output_gate_opener_rewritten"]
                opener_rewrite_audit = {"applied": True, "model": CLASSIFIER_MODEL, "opener": opener, "latency_ms": _rw_ms}
            else:
                # Rewrite unavailable/slow/still non-compliant: pass the model's REAL reply
                # through (a soft opener is the lesser evil) rather than a content-free
                # placeholder. Canned fallback is reserved for genuinely empty generations.
                path = path + ["output_gate_opener_passthrough"]
                banned_opener_violation = True
                opener_rewrite_audit = {"applied": False, "model": CLASSIFIER_MODEL, "opener": opener, "latency_ms": _rw_ms}
                _log.warning("[output_gate] opener rewrite unavailable; passing original reply through")
```

`CLASSIFIER_MODEL` is the model **name**; v7 §13.1 wants the served **version**. OpenRouter returns the resolved model in the response payload — if `get_classifier().ainvoke` surfaces it (e.g. `response_metadata["model_name"]`), capture it into `opener_rewrite["model_version"]`; otherwise log the name and open a follow-up to thread the served version through. Capturing `latency_ms` here doubles as the per-rewrite latency signal for the before/after in Task 5.
```

Add `from sage_poc.config import CLASSIFIER_MODEL` if absent. Thread `opener_rewrite_audit` into the `write_session_audit({**state, ...})` calls (add key `"opener_rewrite": opener_rewrite_audit`) so the rewrite is traceable, and include it in the node's returned dict. Delete the `banned_opener_retry_count` early-return branch and the `_VETTED_FALLBACK_RESPONSE` substitution that lived here. Leave the **empty-response** fallback path (the `_retry_count >= 1` empty-substitution earlier in the function and `_EMPTY_MONITORING_FALLBACK`) untouched — those handle a different failure (blank generation), not banned openers.

- [ ] **Step 3b: Persist the rewrite audit field (traceability)**

Add a nullable `opener_rewrite jsonb` column to `session_audit` via the repo's migration mechanism (mirror an existing JSONB column like `clinical_flags_detail`), and have `write_session_audit` write `state.get("opener_rewrite")` into it. This makes every rewritten/passed-through reply traceable to the model and the matched opener (v7 §13.1 / explainability). Add a test that a rewritten turn's audit payload carries `opener_rewrite.model` and `.opener`.

- [ ] **Step 4: Run — expect pass; then the whole module**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_output_gate_banned_opener.py -v && .venv/bin/python -m pytest tests/test_nodes.py -k "output_gate or banned" -q`
Expected: new tests PASS; existing output_gate tests pass, EXCEPT any that asserted the old regen/canned behavior — update those to the new contract (rewrite/pass-through), do not delete coverage.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_output_gate_banned_opener.py tests/test_nodes.py
git commit -m "feat(output_gate): inline opener rewrite + pass-through; drop canned-default for banned openers (#58)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Remove the graph re-entry (no more route-back-to-freeflow)

**Files:**
- Modify: `sage-poc/src/sage_poc/graph.py:244-249` and the `output_gate` conditional-edge map (`:296-298`)
- Modify: `sage-poc/src/sage_poc/prompts/composer.py:894-897` (delete the now-dead `[CORRECTION]` injection)
- Test: `sage-poc/tests/test_graph.py`

**Interfaces:**
- Consumes: the inline rewrite (Task 2) — there is no longer any banned-opener state that should route back to `freeflow_respond`.
- Produces: `_route_after_output_gate` returns only `END` (the banned-opener branch is gone).

- [ ] **Step 1: Write the failing test**

In `tests/test_graph.py`:

```python
def test_output_gate_never_reenters_freeflow_for_banned_opener():
    from sage_poc.graph import _route_after_output_gate
    # banned_opener_correction is no longer produced; even if present, no re-entry
    assert _route_after_output_gate({"banned_opener_correction": "x", "banned_opener_retry_count": 0}) != "freeflow_respond"
```

- [ ] **Step 2: Run — expect fail**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_graph.py::test_output_gate_never_reenters_freeflow_for_banned_opener -v`
Expected: FAIL (current code returns `"freeflow_respond"`).

- [ ] **Step 3: Implement**

In `graph.py`, simplify `_route_after_output_gate` to drop the banned-opener branch (`:248-249`):

```python
def _route_after_output_gate(state: SageState) -> str:
    return END
```

Remove `"freeflow_respond": "freeflow_respond"` from the `output_gate` conditional-edge map (`:296-298`) so the only edge is to `END`. In `composer.py`, delete the dead `[CORRECTION]` block (`:894-897`) and its `layers.append("banned_opener_correction")`.

- [ ] **Step 4: Run — expect pass; full graph suite (non-slow)**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest tests/test_graph.py -m "not slow" -q && .venv/bin/python -m pytest tests/test_nodes.py -k "composer or banned" -q`
Expected: PASS (update any test that asserted the old re-entry).

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/graph.py src/sage_poc/prompts/composer.py tests/test_graph.py
git commit -m "refactor(graph): drop banned-opener freeflow re-entry; rewrite is now inline (#58)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Full regression + a live one-shot check

- [ ] **Step 1: Full non-slow suite**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && .venv/bin/python -m pytest -m "not slow" -q`
Expected: green (modulo the known module-scope fixture flakes in `test_server.py` — re-run any flaky one in isolation).

- [ ] **Step 2: One live opener-rewrite sanity check (real gpt-4o-mini)**

Run a one-off that calls `_rewrite_opener` on the three review cases against real OpenRouter and prints input→output; confirm each output (a) no longer matches `_BANNED_OPENER_RE`, (b) keeps the trailing sentences, (c) reads warm. Paste into the sign-off doc as evidence.

---

## Task 5: Gate on sign-off, deploy, measure

- [ ] **Step 1: Confirm clinical sign-off returned** on the three Wave-0 items; swap the DRAFT `_OPENER_REWRITE_SYSTEM` for the signed-off copy if it changed; commit that copy change.

- [ ] **Step 2: Deploy via the master-worktree flow** (same as PR #54): branch off `origin/master`, PR, CI (`unit-gate`+`ferry-gate`), admin-merge, `railway up` from a clean master worktree. Record deploy timestamp `T`. **Migration ordering:** the additive nullable `opener_rewrite` column (Task 2 Step 3b) is backward-safe, but it MUST land before the code that writes it — run/confirm the migration on prod Supabase *before* the `railway up` that ships the writing code, or the first audit write with the new key fails.

- [ ] **Step 3: Measure before/after** with `scratchpad/banned_opener_rate.py` (the baseline query, windowed to `T`):

```python
# real-user node_path markers, windowed to deploy time
# expect: 'output_gate_banned_opener_retry' -> 0 (route removed),
#         'output_gate_fallback_substituted' -> ~0 (canned no longer default),
#         new: 'output_gate_opener_rewritten' rate ~= old 27% minus passthroughs.
```
Expected vs baseline (27.2% regen, 2.8% canned): regen marker gone, canned-for-openers gone, rewrite marker present; latency on opener turns down (~1s mini rewrite vs ~2-4s gpt-4o regen). Record in #58 and close it.

---

## Self-Review

**Spec coverage:** rewrite-with-context (Task 1), inline rewrite + pass-through + canned-only-for-empty (Task 2), remove graph re-entry + dead correction injection (Task 3), regression + live check (Task 4), sign-off gate + deploy + before/after (Wave 0 + Task 5). Issue #58's two refinements (context-rich rewrite on gpt-4o-mini; drop canned default) are both covered.

**Placeholder scan:** the only deliberate placeholder is the rewrite-instruction *copy*, explicitly marked DRAFT-pending-clinical-sign-off (the codebase's established pattern for the existing fallback) and gated at Task 5 Step 1. The baseline numbers are measured, not assumed.

**Type consistency:** `_rewrite_opener(response_en, opener, user_message_en) -> str` defined in Task 1, called in Task 2 with the same args; path markers `output_gate_opener_rewritten` / `output_gate_opener_passthrough` are the same in Task 2 code, Task 2 tests, and the Task 5 query; `_route_after_output_gate -> END` consistent between Task 3 code and test.

**Risk notes:** clinical sign-off is the gate (front-loaded in Wave 0). The rewrite adds a ~1s gpt-4o-mini call inside `output_gate` on the ~27% of turns that fire, but removes a ~2-4s gpt-4o regeneration round-trip — net latency win. Pass-through means a soft banned opener can occasionally reach the user (a clinical decision, signed off in Wave 0) — strictly better than the 2.8% content-free placeholder it replaces. Empty-generation fallback paths are untouched.

**Adjacent items (not in this plan, but sequenced):**
- **L0/L2 root-cause fix — sequence SOON, not "eventually."** 27.2% banned-opener rate means the persona/register isn't holding at source; this rewrite is a *mitigation on the symptom*. Every point shaved at the prompt removes a rewrite call from the critical path. File it as the next clinical/prompt-arch change immediately after this lands.
- **Arabic opener guard (pre-existing gap):** banned-opener detection is English-only (`not _response_en_is_arabic`); Khaleeji/Arabic replies have no equivalent guard. Not introduced here; track as its own item.
- The broader per-node latency instrumentation (separate infra task).
- **Crisis-audit divergence (verified, tracked separately — NOT a blocker for this fix):** v7 §6.5.1 frames output_gate as running on *every* response, but crisis responses bypass output_gate (→ END). Verified that audit coverage is preserved — `_crisis_response_node` writes its own `session_audit` row (`graph.py:26`, `create_task(write_session_audit(...))`), so the §13.1 audit point is met in the crisis node, not skipped. This fix now *leans on* the bypass for crisis safety, so the divergence ("output_gate is not literally universal; crisis audits in its own node") should be tracked as its own finding so the invariant stays true. The tracked finding must also confirm the crisis row is audited **equivalently, not just separately** — i.e. it captures the same §13.1 fields the gate row does (model version + crisis result specifically); if the crisis node's row is lighter, that's a content gap, not just a location gap.
