# Native-Arabic (Khaleeji) Shadow-Measure — Tier 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Review status:** Structurally approved 2026-07-07 with 5 amendments (3 blocking) folded into this revision. Amendment map at the end.

**Goal:** Measure — without changing what any user is served — whether GPT-4o generating Gulf Arabic (Khaleeji) *directly* clears the register ≥4.0/5.0 KPI, and by how much latency differs from the shipped English-then-translate path, producing three numbers (register delta, latency delta, gate-fire rate) for the deferred Tier 1 native-generation decision brief.

**Architecture:** On Arabic turns, behind a default-OFF flag, `freeflow_respond` runs a **second, native-Khaleeji generation concurrently** with the normal English generation. The shadow output **never enters `SageState`** — `freeflow_respond` writes it directly to a dedicated restricted table (`shadow_register_eval`) via its own writer and returns nothing shadow-related in the node dict. Because it never joins durable state, it cannot reach the LangGraph checkpointer or the API response payload (containment by construction). The served path is byte-identical: `output_gate` translates-out the English response exactly as today, so every deterministic English gate keeps running unchanged. Register scoring (blinded, dual-arm, Gulf-native rater) and gate-fire replay both run **offline** over the eval table.

**Tech Stack:** Python 3, LangGraph (`SageState`), pytest, Supabase Postgres (numbered SQL migrations), OpenRouter GPT-4o via `get_responder()`.

## Global Constraints

- **Option 3 (ship native) is OUT OF SCOPE and non-approvable here.** All deterministic gates run on English `response_en` PRE-translate (cultural blocklist fires English-only — `"pork"`, `"happy hour"`; banned-opener English regex; one-question; format). Serving native Arabic silently no-ops them. Those gates are protocol-mandatory ("cultural rules at output_gate — not optional") and are **not** covered by the POC carve-out (carve-out waives *sovereignty*, not deterministic safety/cultural gating). Native serving is gated on a clinician-signed Arabic gate-port that Tier 0 *measures* but does not build.
- **Containment by construction (Blocking #1).** The shadow payload MUST NOT be added to `SageState`, returned from any node, or written anywhere the served turn or client can read it. It goes only to `shadow_register_eval`. Enforced by Task 8 (behavioral sentinel + state-channel absence tests), which MUST merge before the Task 7 migration lands (containment guarantee exists before any shadow text is persisted).
- **Flag OFF ⇒ byte-identical behaviour.** No new `SageState` keys; served `response`, `path`, and `session_audit` row unchanged when `SAGE_NATIVE_ARABIC_SHADOW=false`.
- **Fail-open.** Any shadow error returns `None`; a timeout is recorded as a *censored* eval row (Blocking #2), never affecting the served turn. Shadow gen is wrapped in `asyncio.wait_for` (8s).
- **Served-latency impact under flag ON is real, not "one free call" (Amendment #4).** `asyncio.gather` makes served latency ≈ **max(English arm, shadow arm)**, bounded at +8s worst case (typically small — shadow hides under the English tool-loop on tool turns; on zero-tool turns both are ~1–2.5s). Pilot-cohort Arabic p95 may degrade against the <3s KPI. This is an **explicitly accepted, time-boxed** impact; the pre-registration (Task 11) states it and commits a flag-off date. (Fire-and-forget `create_task` was rejected: request/graph teardown can cancel the task and drop the eval write.)
- **Offline-seed gate.** Phase 3 (rubric calibration on the seed set + pre-registered analysis plan, incl. the zero-tool primary comparison and timeout-censoring rule) MUST be merged and signed before the flag is enabled on any live cohort (Phase 4).
- **Exemplars are clinician-governed content (Amendment #5).** Khaleeji few-shot exemplars shape therapeutic tone → Cardinal Rule 2. Repo JSON is acceptable for a measurement instrument, but Phase 4 preconditions require **clinician review alongside Gulf-native authoring**; if exemplars survive into serving, the Tier 1 brief must note CMS migration.
- **Flag convention:** env `SAGE_<NAME>` → constant `<NAME>_ENABLED`.
- **PDPL:** `shadow_register_eval` holds clinical response text (restricted class, as `original_response_text`); apply restricted retention; DPO ack recorded in Task 11.
- **Carried deviations (context for the brief, NOT changed here):** (1) end-state ≠ "zero hops" — translate-**in** stays for routing until `target_presentations`/`semantic_anchors` are Arabic-native; dropping translate-out frees only generation. (2) GPT-4o-mini classify/route contradicts the v7 model table (Falcon-3B, Nodes 2/5/8; GPT-4o fallback only) — tracked POC deviation, not target.

---

## File Structure

- `src/sage_poc/config.py` — `NATIVE_ARABIC_SHADOW_ENABLED` flag.
- `src/sage_poc/prompts/khaleeji_shadow_exemplars.json` — **new**; versioned native-authored few-shot exemplars.
- `src/sage_poc/prompts/loader.py` — `load_khaleeji_shadow_exemplars()`.
- `src/sage_poc/prompts/composer.py` — `shadow_arabic: bool = False` kwarg on `compose_prompt`.
- `src/sage_poc/shadow_arabic.py` — **new**; `generate_shadow_arabic(state, llm)` (native gen, gen-only timing, fail-open). Imported by NO serving/gate path.
- `src/sage_poc/shadow_eval.py` — **new**; `write_shadow_eval_row(...)` → inserts into `shadow_register_eval`. The ONLY sink for shadow data.
- `src/sage_poc/nodes/freeflow_respond.py` — concurrent shadow arm; capture tool-loop iterations; write eval row; return NOTHING shadow-related.
- `migrations/008_add_shadow_register_eval.sql` — **new**; dedicated restricted table.
- `scripts/register_eval/seed_inputs.json`, `rating_harness.py`, `replay_gates.py` — **new**; offline instruments.
- `docs/superpowers/specs/2026-07-07-native-arabic-register-preregistration.md` — **new**; rubric, blinding, zero-tool primary comparison, timeout censoring, accepted-latency impact, DPO ack.
- Tests under `sage-poc/tests/`.

> **Note:** there is **no** `SageState` field and **no** `session_audit` change in this plan — that is the containment fix. `state.py` and `audit.py` are untouched.

---

## Phase 1 — Flag, prompt variant, shadow generator

### Task 1: Feature flag

**Files:** Modify `src/sage_poc/config.py` (after `D5_ACUITY_GATE_ENABLED`, ~line 99); Test `tests/test_config_native_arabic_shadow.py`

**Interfaces:** Produces `sage_poc.config.NATIVE_ARABIC_SHADOW_ENABLED: bool`

- [ ] **Step 1: Failing test**
```python
# tests/test_config_native_arabic_shadow.py
import importlib

def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("SAGE_NATIVE_ARABIC_SHADOW", raising=False)
    import sage_poc.config as cfg; importlib.reload(cfg)
    assert cfg.NATIVE_ARABIC_SHADOW_ENABLED is False

def test_flag_on_when_true(monkeypatch):
    monkeypatch.setenv("SAGE_NATIVE_ARABIC_SHADOW", "true")
    import sage_poc.config as cfg; importlib.reload(cfg)
    assert cfg.NATIVE_ARABIC_SHADOW_ENABLED is True
```
- [ ] **Step 2: Verify fail** — `cd sage-poc && uv run pytest tests/test_config_native_arabic_shadow.py -v` → FAIL (AttributeError)
- [ ] **Step 3: Add flag**
```python
# src/sage_poc/config.py (after D5_ACUITY_GATE_ENABLED)
# Tier 0 native-Arabic register measurement. Ships INERT: when on, generates a
# second native-Khaleeji response written ONLY to shadow_register_eval and NEVER
# served or placed in SageState. See docs/superpowers/plans/2026-07-07-native-arabic-shadow-measure.md
NATIVE_ARABIC_SHADOW_ENABLED: bool = os.getenv("SAGE_NATIVE_ARABIC_SHADOW", "false").lower() == "true"
```
- [ ] **Step 4: Verify pass** — same command → PASS (2)
- [ ] **Step 5: Commit** — `git add src/sage_poc/config.py tests/test_config_native_arabic_shadow.py && git commit -m "feat(config): add SAGE_NATIVE_ARABIC_SHADOW flag (default off)"`

---

### Task 2: Khaleeji few-shot exemplars + loader

**Files:** Create `src/sage_poc/prompts/khaleeji_shadow_exemplars.json`; Modify `src/sage_poc/prompts/loader.py`; Test `tests/test_khaleeji_exemplars_loader.py`

**Interfaces:** Produces `load_khaleeji_shadow_exemplars() -> tuple[str, str]` = `(version, block_text)`.

**Content note:** `ar` values + `version` are Gulf-native-authored **and clinician-reviewed** before Phase 4 (Amendment #5). This task lands schema + loader + English source lines; ships with two seed entries so the loader is testable.

- [ ] **Step 1: Create the file**
```json
{
  "version": "0.1.0-draft",
  "note": "ar fields require Gulf-native authoring AND clinician review before Phase 4 deploy (Cardinal Rule 2); bump version on every content change.",
  "exemplars": [
    {"en": "That sounds really heavy, and it makes sense you're tired. You don't have to sort it all out tonight.", "ar": "TODO_NATIVE_AUTHOR"},
    {"en": "I'm here with you. Take it one breath at a time — what feels like the hardest part right now?", "ar": "TODO_NATIVE_AUTHOR"}
  ]
}
```
- [ ] **Step 2: Failing test**
```python
# tests/test_khaleeji_exemplars_loader.py
from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars

def test_loader_returns_version_and_block():
    version, block = load_khaleeji_shadow_exemplars()
    assert isinstance(version, str) and version
    assert "KHALEEJI EXEMPLARS" in block
    assert "one breath at a time" in block
```
- [ ] **Step 3: Verify fail** — `cd sage-poc && uv run pytest tests/test_khaleeji_exemplars_loader.py -v` → FAIL (ImportError)
- [ ] **Step 4: Add loader**
```python
# src/sage_poc/prompts/loader.py (append)
import json as _json
from pathlib import Path as _Path
from functools import lru_cache as _lru_cache

_KHALEEJI_EXEMPLARS_PATH = _Path(__file__).parent / "khaleeji_shadow_exemplars.json"

@_lru_cache(maxsize=1)
def load_khaleeji_shadow_exemplars() -> tuple[str, str]:
    data = _json.loads(_KHALEEJI_EXEMPLARS_PATH.read_text(encoding="utf-8"))
    lines = ["KHALEEJI EXEMPLARS (style reference, do not quote verbatim):"]
    for ex in data.get("exemplars", []):
        ar = ex.get("ar", "")
        lines.append(f"- {ex['en']}\n  → {ar}" if ar and ar != "TODO_NATIVE_AUTHOR" else f"- {ex['en']}")
    return data.get("version", "unknown"), "\n".join(lines)
```
- [ ] **Step 5: Verify pass** — PASS
- [ ] **Step 6: Commit** — `git add src/sage_poc/prompts/khaleeji_shadow_exemplars.json src/sage_poc/prompts/loader.py tests/test_khaleeji_exemplars_loader.py && git commit -m "feat(prompts): Khaleeji shadow exemplars + loader (ar pending native+clinical authoring)"`

---

### Task 3: `compose_prompt` shadow-Arabic mode

**Files:** Modify `src/sage_poc/prompts/composer.py:636` (signature) and `:661-668`; Test `tests/test_composer_shadow_arabic.py`

**Interfaces:** Consumes `load_khaleeji_shadow_exemplars()`; Produces `compose_prompt(state, *, shadow_arabic: bool = False)`. Default returns today's output byte-for-byte.

- [ ] **Step 1: Failing tests**
```python
# tests/test_composer_shadow_arabic.py
from sage_poc.prompts.composer import compose_prompt

def _ar_state():
    return {"detected_language": "ar", "raw_message": "تعبت من كل شي", "message_en": "I'm tired of everything"}

def test_default_is_english_first_unchanged():
    sys_default, _, layers = compose_prompt(_ar_state())
    assert "Generate in English" in sys_default and "Do not write in Arabic" in sys_default
    assert "arabic_register" in layers

def test_shadow_mode_swaps_to_khaleeji_direct():
    sys_shadow, _, layers = compose_prompt(_ar_state(), shadow_arabic=True)
    assert "Generate your reply directly in warm, informal Gulf Arabic" in sys_shadow
    assert "Do not write in Arabic" not in sys_shadow
    assert "KHALEEJI EXEMPLARS" in sys_shadow and "arabic_native_shadow" in layers

def test_shadow_mode_noop_for_english_session():
    sys_en, _, _ = compose_prompt({"detected_language": "en", "raw_message": "hi", "message_en": "hi"}, shadow_arabic=True)
    assert "KHALEEJI EXEMPLARS" not in sys_en
```
- [ ] **Step 2: Verify fail** — `cd sage-poc && uv run pytest tests/test_composer_shadow_arabic.py -v` → FAIL (unexpected kwarg)
- [ ] **Step 3: Change signature** — replace `composer.py:636` `def compose_prompt(state: SageState) -> tuple[str, str, list[str]]:` with `def compose_prompt(state: SageState, *, shadow_arabic: bool = False) -> tuple[str, str, list[str]]:`
- [ ] **Step 4: Swap the ARABIC SESSION block** — replace `composer.py:661-668` with:
```python
    if language == "ar":
        if shadow_arabic:
            from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars  # noqa: PLC0415
            _ex_version, _ex_block = load_khaleeji_shadow_exemplars()
            system_parts.append(
                "ARABIC SESSION (native generation): This user writes in Arabic. "
                "Generate your reply directly in warm, informal Gulf Arabic (Khaleeji "
                "dialect), not Modern Standard Arabic and not clinical or formal "
                "phrasing. Mirror the user's dialect and level of formality.\n" + _ex_block
            )
            layers.append("arabic_native_shadow")
        else:
            system_parts.append(
                "ARABIC SESSION: This user writes in Arabic. Your response will be "
                "translated to Khaleeji Arabic by the delivery layer. Generate in English "
                "with warmth and conversational rhythm that translates naturally to Gulf "
                "Arabic, not clinical or formal phrasing. Do not write in Arabic."
            )
            layers.append("arabic_register")
```
- [ ] **Step 5: Verify pass** — PASS (3)
- [ ] **Step 6: Regression** — `cd sage-poc && uv run pytest tests/test_composer_intensity.py tests/test_composer_d5_acuity_gate.py -q` → PASS
- [ ] **Step 7: Commit** — `git add src/sage_poc/prompts/composer.py tests/test_composer_shadow_arabic.py && git commit -m "feat(composer): add shadow_arabic mode (Khaleeji-direct, off by default)"`

---

### Task 4: `generate_shadow_arabic` (native gen, fail-open)

**Files:** Create `src/sage_poc/shadow_arabic.py`; Test `tests/test_shadow_arabic.py`

**Interfaces:** Produces `async generate_shadow_arabic(state, llm=None) -> dict | None` → `{"text","prompt_hash","exemplar_version","generation_language":"ar_native","gen_latency_ms"}`; `None` for non-AR or any error.

- [ ] **Step 1: Failing tests**
```python
# tests/test_shadow_arabic.py
import asyncio
from sage_poc.shadow_arabic import generate_shadow_arabic

class _FakeResp:
    def __init__(self, c): self.content = c
class _FakeLLM:
    def __init__(self, c="مرحبا", raises=False): self._c, self._r = c, raises
    async def ainvoke(self, m):
        if self._r: raise RuntimeError("boom")
        return _FakeResp(self._c)

def _ar(): return {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired"}

def test_none_for_english():
    assert asyncio.run(generate_shadow_arabic({"detected_language": "en"}, _FakeLLM())) is None

def test_payload_for_arabic():
    out = asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM("مرحبا")))
    assert out["text"] == "مرحبا" and out["generation_language"] == "ar_native"
    assert len(out["prompt_hash"]) == 16 and out["exemplar_version"]
    assert isinstance(out["gen_latency_ms"], int) and out["gen_latency_ms"] >= 0

def test_fail_open():
    assert asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM(raises=True))) is None
```
- [ ] **Step 2: Verify fail** — FAIL (ModuleNotFound)
- [ ] **Step 3: Implement**
```python
# src/sage_poc/shadow_arabic.py
"""Tier 0 native-Khaleeji shadow generation — MEASUREMENT ONLY.
Output is NEVER served and NEVER enters SageState. Fail-open: any error → None."""
from __future__ import annotations
import hashlib, logging, time
from sage_poc.prompts.composer import compose_prompt
from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars

_log = logging.getLogger(__name__)

async def generate_shadow_arabic(state: dict, llm=None) -> dict | None:
    if state.get("detected_language") != "ar":
        return None
    try:
        if llm is None:
            from sage_poc.llm import get_responder  # noqa: PLC0415
            llm = get_responder()
        system_str, user_str, _ = compose_prompt(state, shadow_arabic=True)
        messages = [{"role": "system", "content": system_str}, {"role": "user", "content": user_str}]
        prompt_hash = hashlib.sha256(system_str.encode("utf-8")).hexdigest()[:16]
        exemplar_version, _blk = load_khaleeji_shadow_exemplars()
        t0 = time.monotonic()
        resp = await llm.ainvoke(messages)
        gen_latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "text": getattr(resp, "content", None) or str(resp),
            "prompt_hash": prompt_hash,
            "exemplar_version": exemplar_version,
            "generation_language": "ar_native",
            "gen_latency_ms": gen_latency_ms,
        }
    except Exception as exc:
        _log.warning("[shadow_arabic] generation failed (fail-open): %s", exc)
        return None
```
- [ ] **Step 4: Verify pass** — PASS (3)
- [ ] **Step 5: Commit** — `git add src/sage_poc/shadow_arabic.py tests/test_shadow_arabic.py && git commit -m "feat(shadow): native-Khaleeji generator (measurement-only, fail-open)"`

---

## Phase 2 — Containment guard, then the eval sink

### Task 5: Never-served / never-in-state guard (MERGE BEFORE Task 7) — Blocking #1

**Files:** Test `tests/test_shadow_never_served.py` (+ extend one existing `output_gate` Arabic test and one end-to-end server test)

**Interfaces:** none — protective tests enforcing containment.

- [ ] **Step 1: Static + state-channel absence tests**
```python
# tests/test_shadow_never_served.py
import inspect
import sage_poc.nodes.output_gate as og
import sage_poc.state as state_mod
import sage_poc.nodes.freeflow_respond as fr

def test_output_gate_never_references_shadow():
    assert "shadow_arabic" not in inspect.getsource(og)

def test_shadow_is_not_a_sagestate_channel():
    # Containment by construction: shadow must never travel in durable state
    assert "shadow_arabic" not in getattr(state_mod.SageState, "__annotations__", {})

def test_freeflow_return_excludes_shadow_keys():
    # freeflow_respond_node must not return any shadow_* key into state
    src = inspect.getsource(fr.freeflow_respond_node)
    # the node writes shadow to the eval table, never returns it
    assert "\"shadow_arabic\"" not in src and "'shadow_arabic'" not in src
```
> **Architect sign-off 2026-07-07 (Checkpoint 1):** the **behavioral sentinel test + API-payload assertion are RELOCATED to Task 7** (they require the freeflow wiring to exist) and are a **hard merge gate there** — Task 7 does not merge with that test absent, skipped, or red. Task 5 lands the three static, by-construction invariants that provide the containment guarantee *before* persistence: `output_gate` source-absence, `SageState` channel-absence, `freeflow` return-shape. Keep all three together.

- [ ] **Step 2: Serializer + checkpointer confirmation audit (Blocking #1b)** — grep the API/response layer and checkpointer for full-state passthrough; document that no code returns raw `SageState` to the client (the response DTO whitelists fields). Record findings in a one-paragraph note at the top of Task 11's pre-registration doc. Since shadow never enters state, this is a confirmation, not a patch — but if the audit finds any raw-state dump to client or logs, add an explicit exclusion and a test.

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && grep -rnE "\.dict\(\)|model_dump|jsonify\(state|return .*state\b" src/sage_poc/server.py src/sage_poc/**/*.py | grep -iv test`
- [ ] **Step 3: Verify** — `cd sage-poc && uv run pytest tests/test_shadow_never_served.py -v` → PASS (three static guards green; will fail loudly if anyone ever routes shadow into state/serving)
- [ ] **Step 4: Commit** — `git add tests/test_shadow_never_served.py && git commit -m "test(shadow): containment static guards — never a state channel, output_gate/freeflow return-shape absence"`

---

### Task 6: Eval table migration + writer — Blocking #2 & #3

**Files:** Create `migrations/008_add_shadow_register_eval.sql`; Create `src/sage_poc/shadow_eval.py`; Test `tests/test_shadow_eval_row.py`

**Interfaces:** Produces `build_shadow_eval_row(state, payload, tool_loop_iterations, timed_out) -> dict` (pure, unit-tested) and `async write_shadow_eval_row(state, payload, *, tool_loop_iterations, timed_out)` (thin Supabase insert). Consumes `state["message_en"]`, `state["clinical_flags"]`, `state["session_id"]`, `state["turn_number"]`.

- [ ] **Step 1: Migration (dedicated restricted table)**
```sql
-- migrations/008_add_shadow_register_eval.sql
-- Tier 0 native-Arabic shadow measurement. Isolated restricted table (clinical text,
-- same class as identity-substitution audit). Populated only when SAGE_NATIVE_ARABIC_SHADOW on.
-- message_en + clinical_flags stored so offline gate-replay evaluates mirroring rules on the
-- REAL user message (Blocking #3). tool_loop_iterations + shadow_timed_out support the zero-tool
-- primary comparison and timeout-censoring (Blocking #2). Served (shipped) Arabic is joined
-- offline from the messages store by (session_id, turn_number) — not duplicated here.
CREATE TABLE IF NOT EXISTS shadow_register_eval (
  id                       bigint generated always as identity primary key,
  session_id               text    not null,
  turn_number              integer not null,
  message_en               text,
  clinical_flags           text[],
  shadow_arabic_text       text,
  shadow_prompt_hash       text,
  shadow_exemplar_version  text,
  generation_language      text,
  shadow_gen_latency_ms    integer,
  tool_loop_iterations     integer,
  shadow_timed_out         boolean default false,
  created_at               timestamptz default now(),
  unique (session_id, turn_number)
);
```
- [ ] **Step 2: Failing test (pure row builder)**
```python
# tests/test_shadow_eval_row.py
from sage_poc.shadow_eval import build_shadow_eval_row

def _state():
    return {"session_id": "s1", "turn_number": 4, "message_en": "I'm tired",
            "clinical_flags": ["substance"]}

def test_row_from_payload():
    p = {"text": "هلا والله", "prompt_hash": "d"*16, "exemplar_version": "0.1.0-draft",
         "generation_language": "ar_native", "gen_latency_ms": 812}
    row = build_shadow_eval_row(_state(), p, tool_loop_iterations=0, timed_out=False)
    assert row["session_id"] == "s1" and row["turn_number"] == 4
    assert row["message_en"] == "I'm tired" and row["clinical_flags"] == ["substance"]
    assert row["shadow_arabic_text"] == "هلا والله"
    assert row["tool_loop_iterations"] == 0 and row["shadow_timed_out"] is False

def test_censored_row_on_timeout():
    row = build_shadow_eval_row(_state(), None, tool_loop_iterations=2, timed_out=True)
    assert row["shadow_timed_out"] is True
    assert row["shadow_arabic_text"] is None and row["shadow_gen_latency_ms"] is None
    assert row["tool_loop_iterations"] == 2  # censored obs still records the English-arm tool count
```
- [ ] **Step 3: Verify fail** — FAIL (ModuleNotFound)
- [ ] **Step 4: Implement**
```python
# src/sage_poc/shadow_eval.py
"""The ONLY sink for native-Arabic shadow data. Writes to shadow_register_eval.
Never returns data into SageState. Restricted-retention clinical text."""
from __future__ import annotations
import logging
_log = logging.getLogger(__name__)

def build_shadow_eval_row(state: dict, payload: dict | None, *, tool_loop_iterations: int, timed_out: bool) -> dict:
    p = payload or {}
    return {
        "session_id":              state.get("session_id", ""),
        "turn_number":             state.get("turn_number", 0),
        "message_en":              state.get("message_en"),
        "clinical_flags":          state.get("clinical_flags") or [],
        "shadow_arabic_text":      p.get("text"),
        "shadow_prompt_hash":      p.get("prompt_hash"),
        "shadow_exemplar_version": p.get("exemplar_version"),
        "generation_language":     p.get("generation_language"),
        "shadow_gen_latency_ms":   p.get("gen_latency_ms"),
        "tool_loop_iterations":    tool_loop_iterations,
        "shadow_timed_out":        timed_out,
    }

async def write_shadow_eval_row(state: dict, payload: dict | None, *, tool_loop_iterations: int, timed_out: bool) -> None:
    """Thin insert; fail-open (measurement must never break the served turn)."""
    try:
        row = build_shadow_eval_row(state, payload, tool_loop_iterations=tool_loop_iterations, timed_out=timed_out)
        from sage_poc.audit import _supabase_insert  # reuse the project's REST insert helper  # noqa: PLC0415
        await _supabase_insert("shadow_register_eval", row)
    except Exception as exc:
        _log.warning("[shadow_eval] write failed (fail-open): %s", exc)
```
> If `audit.py` has no reusable async insert helper, add a minimal one there mirroring `_write_session_audit_row` (same `{_URL}/rest/v1/<table>` POST, service key) and import it. Confirm the exact helper name during implementation.
- [ ] **Step 5: Verify pass (row builder)** — `cd sage-poc && uv run pytest tests/test_shadow_eval_row.py -v` → PASS (2)
- [ ] **Step 6: Apply migration** (staging first); record in `migrations/MIGRATIONS.md`.
- [ ] **Step 7: Commit** — `git add migrations/008_add_shadow_register_eval.sql src/sage_poc/shadow_eval.py tests/test_shadow_eval_row.py migrations/MIGRATIONS.md && git commit -m "feat(shadow): shadow_register_eval table + writer (message_en, tool count, timeout censoring)"`

---

### Task 7: Wire concurrent shadow into `freeflow_respond` (writes eval row, returns nothing shadow)

**Files:** Modify `src/sage_poc/nodes/freeflow_respond.py:264-297`; Modify `src/sage_poc/shadow_arabic.py` (empty-content fix, below); Test `tests/test_freeflow_shadow_wiring.py`; Test `tests/test_shadow_never_served.py` (add relocated sentinel + API-payload assertion)

**Interfaces:** Consumes `NATIVE_ARABIC_SHADOW_ENABLED`, `generate_shadow_arabic`, `write_shadow_eval_row`. Produces: node result dict is **unchanged** (no shadow keys); side-effect is one `shadow_register_eval` row on Arabic turns when flag on.

> **MERGE GATE (architect sign-off 2026-07-07, Checkpoint 1) — Task 7 does NOT merge unless all hold:**
> - **(a) Behavioral sentinel test present, green, not skipped** (relocated from Task 5): drive an Arabic turn flag-ON with a monkeypatched shadow generator returning a distinctive sentinel; assert the sentinel appears in NEITHER the served `response`/node result NOR the serialized API payload. Both the node-level test AND the API-layer assertion (in the e2e server test) are required.
> - **(b) Empty-content semantics fixed** in `generate_shadow_arabic` (carried Minor): an empty-string LLM `content` is a FAILED generation → return `None` (fail-open, logged) — never a stored empty row, never the object repr. A repr entering `shadow_register_eval` silently poisons the register sample with non-responses. Required test: empty content → `None`.
> - **(c) The V1/V2/V3 verification items** (write fail-open+bounded, pairing key, retention parity) tracked in the Amendment Map — V1 lands here (write is bounded + swallowed; `test_eval_write_failure_does_not_break_served_turn`).

- [ ] **Step 1: Failing tests**
```python
# tests/test_freeflow_shadow_wiring.py
import asyncio
from unittest.mock import patch, AsyncMock
import sage_poc.nodes.freeflow_respond as fr

def _ar():
    return {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired",
            "path": [], "user_id": None, "session_id": "s1", "turn_number": 1}

def test_writes_eval_row_when_flag_on(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": "مرحبا", "prompt_hash": "a"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 4}
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_awaited_once()
    kwargs = writer.await_args.kwargs
    assert kwargs["timed_out"] is False and "tool_loop_iterations" in kwargs
    assert "shadow_arabic" not in out and "response_en" in out  # nothing shadow leaks into state

def test_timeout_writes_censored_row(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.01)
    async def _hang(*a, **k):
        await asyncio.sleep(10)
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=_hang), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    assert writer.await_args.kwargs["timed_out"] is True

def test_no_shadow_when_flag_off(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", False)
    writer = AsyncMock()
    with patch.object(fr, "write_shadow_eval_row", new=writer):
        asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_not_called()

def test_generation_failure_writes_nothing(monkeypatch):
    # Clarification #1: non-timeout generation failure (shadow returns None, not timed out)
    # must NOT write a row — an invalid measurement must not pollute the sample. Distinct from
    # timeout (which DOES write a censored row per test_timeout_writes_censored_row).
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 5.0)  # not a timeout; generator just returns None
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=None)), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_not_called()          # generation failure → no row
    assert "response_en" in out          # served turn unaffected

def test_eval_write_failure_does_not_break_served_turn(monkeypatch):
    # Verification #1: a write raising/timing out must be swallowed; served turn intact.
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": "مرحبا", "prompt_hash": "a"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 4}
    async def _boom(*a, **k):
        raise RuntimeError("supabase down")
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=_boom):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    assert "response_en" in out  # served turn completed despite write failure
```

- [ ] **Step 1b: Merge-gate tests (architect sign-off) — empty-content + relocated sentinel**

Empty-content → None, in `tests/test_shadow_arabic.py` (fixes the carried Minor at the semantic level):
```python
def test_empty_content_is_treated_as_failed_generation():
    # empty string content = failed generation → None (never a stored empty row / repr)
    import asyncio as _a
    out = _a.run(generate_shadow_arabic(_ar(), _FakeLLM("")))
    assert out is None
def test_whitespace_only_content_is_failed_generation():
    import asyncio as _a
    assert _a.run(generate_shadow_arabic(_ar(), _FakeLLM("   \n "))) is None
```
Relocated behavioral sentinel + API-payload assertion, in `tests/test_shadow_never_served.py`:
```python
import asyncio
from unittest.mock import patch, AsyncMock
import sage_poc.nodes.freeflow_respond as fr
_SENTINEL = "ZZZ_SHADOW_SENTINEL_ﷺ_NEVER_SERVE"

def test_sentinel_never_in_served_response(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": _SENTINEL, "prompt_hash": "x"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 3}
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=AsyncMock()):
        out = asyncio.run(fr.freeflow_respond_node(
            {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired",
             "path": [], "user_id": None, "session_id": "s1", "turn_number": 1},
            llm=fr_stub_llm()))
    assert _SENTINEL not in str(out)                         # not in node result / state
    assert out.get("response_en") and _SENTINEL not in out["response_en"]
```
> Plus the API-layer assertion in the e2e server test (`tests/test_server.py` / `tests/test_e2e_*`): one Arabic turn flag-ON with the sentinel monkeypatch → assert `_SENTINEL not in <http payload text>`. `fr_stub_llm()` reuses the fake LLM in `tests/test_freeflow_respond.py`.

- [ ] **Step 1c: Apply the empty-content fix** in `src/sage_poc/shadow_arabic.py` — after computing `text`, treat empty/whitespace as failure:
```python
        text = getattr(resp, "content", None)
        if text is None:
            text = str(resp)
        if not text.strip():
            _log.warning("[shadow_arabic] empty generation content; treating as failed (None)")
            return None
```
(replaces the `text = getattr(resp, "content", None) or str(resp)` line; preserves fail-open and never returns a repr/empty as `text`.)

- [ ] **Step 2: Verify fail** — FAIL (missing symbols)
- [ ] **Step 3: Imports + constants** (top of `freeflow_respond.py`; ensure `import asyncio` and a module `_log` are present)
```python
from sage_poc.config import NATIVE_ARABIC_SHADOW_ENABLED
from sage_poc.shadow_arabic import generate_shadow_arabic
from sage_poc.shadow_eval import write_shadow_eval_row

_SHADOW_TIMEOUT_S = 8.0        # bound on the shadow generation arm
_SHADOW_WRITE_TIMEOUT_S = 2.0  # bound on the eval-row DB write (Verification #1)
```
- [ ] **Step 4: Concurrent arms + eval write** — replace `freeflow_respond.py:266-277` with:
```python
    tool_ai_messages: list = []
    token_usage: dict = {}

    async def _english_arm():
        return await _invoke_with_tool_loop(
            llm, messages, llm_tools, node="freeflow_respond",
            language=state.get("detected_language", "en"), fallback_llm=fallback_llm,
            _tool_messages=tool_ai_messages, _usage=token_usage,
        )

    if NATIVE_ARABIC_SHADOW_ENABLED and state.get("detected_language") == "ar":
        _timed_out = False
        async def _shadow_arm():
            nonlocal _timed_out
            try:
                return await asyncio.wait_for(generate_shadow_arabic(state, llm), timeout=_SHADOW_TIMEOUT_S)
            except asyncio.TimeoutError:
                _timed_out = True
                return None
            except Exception:
                return None
        response, shadow_payload = await asyncio.gather(_english_arm(), _shadow_arm())
        # tool_loop_iterations proxy = number of tool round-trips the English arm took;
        # the pre-registered PRIMARY comparison uses tool_loop_iterations == 0 turns only (Blocking #2).
        #
        # Write policy (Amendment #2 / Checkpoint-2 clarification #1):
        #   TIMEOUT  → write a CENSORED row (shadow_timed_out=True) — a right-censored observation;
        #              dropping it would bias the latency delta optimistic by discarding the slowest gens.
        #   SUCCESS  → write the row with the payload.
        #   GENERATION FAILURE (payload None, NOT timed out — e.g. LLM error, empty content) → write NOTHING;
        #              it is not a valid measurement and must not pollute the register/latency sample.
        if _timed_out or shadow_payload is not None:
            # Verification #1: the eval write is fail-open AND bounded — a Supabase timeout/error
            # must never delay or break the served turn. Bounded + swallowed = "logged, discarded".
            try:
                await asyncio.wait_for(
                    write_shadow_eval_row(
                        state, shadow_payload,
                        tool_loop_iterations=len(tool_ai_messages),
                        timed_out=_timed_out,
                    ),
                    timeout=_SHADOW_WRITE_TIMEOUT_S,
                )
            except Exception:
                _log.warning("[freeflow] shadow eval write failed/timed out (discarded)")
    else:
        response = await _english_arm()
```
> Do NOT add any shadow key to the node's return dict. The eval row is the only sink.
- [ ] **Step 5: Verify pass** — `cd sage-poc && uv run pytest tests/test_freeflow_shadow_wiring.py -v` → PASS (3)
- [ ] **Step 6: Regression** — `cd sage-poc && uv run pytest tests/test_freeflow_respond.py tests/test_shadow_never_served.py -q` → PASS
- [ ] **Step 7: Commit** — `git add src/sage_poc/nodes/freeflow_respond.py tests/test_freeflow_shadow_wiring.py && git commit -m "feat(freeflow): concurrent native-Khaleeji shadow → eval table (flag-gated, censored on timeout, never in state)"`

---

## Phase 3 — Offline instruments (rubric-first; gates Phase 4)

### Task 8: Offline seed set (IE C-1/C-3/C-4)

**Files:** Create `scripts/register_eval/seed_inputs.json`

- [ ] **Step 1: Locate the IE findings** — `cd /Users/knowledgebase/Documents/Sage && grep -rilE "C-1|C-3|C-4|dialect realism|Intelligence Evaluation" --include=*.md . | head`; read matches; pull the dialect-realism inputs (code-switch, Arabizi, 2am fragments).
- [ ] **Step 2: Author the seed file** (20–30; extracted + native augmentation)
```json
{
  "version": "1.0.0",
  "provenance": "IE findings C-1/C-3/C-4 dialect-realism cases + Gulf-native augmentation",
  "note": "Inputs only — calibrates the RATER rubric, not a pass/fail oracle.",
  "inputs": [
    {"id": "seed-001", "source": "IE-C1", "lang_profile": "khaleeji", "text": "والله تعبت من كل شي، ما عاد فيني"},
    {"id": "seed-002", "source": "IE-C3", "lang_profile": "code_switch", "text": "i can't sleep, راسي مو طايق"},
    {"id": "seed-003", "source": "IE-C4", "lang_profile": "arabizi", "text": "ta3ban mn kl shy w mafi amal"}
  ]
}
```
> Expand under Gulf-native review; keep `source`/`lang_profile` tags — the report is stratified by `lang_profile`.
- [ ] **Step 3: Commit** — `git add scripts/register_eval/seed_inputs.json && git commit -m "feat(register-eval): seed inputs from IE C-1/C-3/C-4"`

---

### Task 9: Blinded dual-arm rating harness + IRR

**Files:** Create `scripts/register_eval/rating_harness.py`; Test `tests/test_rating_harness.py`

**Interfaces:** `build_blinded_sheet(pairs, seed)`, `compute_irr(scores_by_rater)`, `register_delta(unblinded)`. The shipped arm is joined from the messages store by `(session_id, turn_number)`; the shadow arm from `shadow_register_eval`.

- [ ] **Step 1: Failing tests**
```python
# tests/test_rating_harness.py
from scripts.register_eval.rating_harness import build_blinded_sheet, compute_irr, register_delta

def test_blinding_hides_arm_identity():
    sheet = build_blinded_sheet([{"turn_id": "t1", "shipped": "خ1", "shadow": "خ2"}], seed=7)
    row = sheet[0]
    assert set(row["arms"].keys()) == {"A", "B"}
    assert "shipped" not in row and "shadow" not in row
    assert build_blinded_sheet([{"turn_id": "t1", "shipped": "خ1", "shadow": "خ2"}], seed=7)[0]["arms"] == row["arms"]

def test_irr_perfect_is_one():
    assert compute_irr({"r1": [4, 5, 3], "r2": [4, 5, 3]}) == 1.0

def test_register_delta():
    d = register_delta([{"turn_id":"t1","shipped_score":3.0,"shadow_score":4.0},
                        {"turn_id":"t2","shipped_score":3.5,"shadow_score":4.5}])
    assert d["shadow_mean"] == 4.25 and d["shipped_mean"] == 3.25 and d["delta"] == 1.0
    assert d["shadow_meets_kpi"] is True

def test_pairs_joined_by_session_and_turn():
    # Verification #2: table split — shadow (shadow_register_eval) must pair with the
    # served Arabic (messages/session_audit) on (session_id, turn_number), NOT assume one row.
    from scripts.register_eval.rating_harness import pair_by_turn
    shadow_rows = [{"session_id": "s1", "turn_number": 2, "shadow_arabic_text": "خ_shadow"}]
    shipped_rows = [{"session_id": "s1", "turn_number": 2, "arabic_text": "خ_shipped"},
                    {"session_id": "s1", "turn_number": 9, "arabic_text": "خ_other"}]
    pairs = pair_by_turn(shadow_rows, shipped_rows)
    assert len(pairs) == 1
    assert pairs[0]["turn_id"] == "s1:2"
    assert pairs[0]["shadow"] == "خ_shadow" and pairs[0]["shipped"] == "خ_shipped"
```
- [ ] **Step 2: Verify fail** — FAIL
- [ ] **Step 3: Implement** (as previously specified: `REGISTER_KPI=4.0`, deterministic seeded A/B randomization with `_map` withheld from the rater view, simplified ordinal IRR, means/delta/KPI). Include a `fetch_pairs()` docstring noting the messages-join for the shipped arm and the `tool_loop_iterations == 0` filter for the primary set.
```python
# scripts/register_eval/rating_harness.py
from __future__ import annotations
import random
REGISTER_KPI = 4.0  # v7 §16.1

def build_blinded_sheet(pairs: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed); sheet = []
    for p in pairs:
        flip = rng.random() < 0.5
        a, b = (p["shipped"], p["shadow"]) if flip else (p["shadow"], p["shipped"])
        sheet.append({"turn_id": p["turn_id"], "arms": {"A": a, "B": b},
                      "_map": {"A": "shipped" if flip else "shadow", "B": "shadow" if flip else "shipped"}})
    return sheet

def compute_irr(scores_by_rater: dict[str, list[int]]) -> float:
    rs = list(scores_by_rater.values())
    if len(rs) < 2 or len(rs[0]) != len(rs[1]) or not rs[0]:
        return float("nan")
    dis = sum(abs(x - y) for x, y in zip(rs[0], rs[1])) / len(rs[0])
    return round(1.0 - dis / 4.0, 4)

def register_delta(unblinded: list[dict]) -> dict:
    n = len(unblinded)
    sh = sum(r["shadow_score"] for r in unblinded) / n
    sp = sum(r["shipped_score"] for r in unblinded) / n
    return {"n": n, "shadow_mean": round(sh, 4), "shipped_mean": round(sp, 4),
            "delta": round(sh - sp, 4), "shadow_meets_kpi": sh >= REGISTER_KPI}

def pair_by_turn(shadow_rows: list[dict], shipped_rows: list[dict]) -> list[dict]:
    """Verification #2: join the two-table split explicitly on (session_id, turn_number).
    shadow_rows from shadow_register_eval; shipped_rows = served Arabic joined from the
    messages store (or session_audit). Turns without both arms are dropped (logged by caller)."""
    shipped_by_key = {(r["session_id"], r["turn_number"]): r["arabic_text"] for r in shipped_rows}
    pairs = []
    for s in shadow_rows:
        key = (s["session_id"], s["turn_number"])
        if key in shipped_by_key and s.get("shadow_arabic_text"):
            pairs.append({"turn_id": f"{key[0]}:{key[1]}",
                          "shadow": s["shadow_arabic_text"], "shipped": shipped_by_key[key]})
    return pairs
```
> `fetch_pairs()` (the live read) calls `pair_by_turn(<shadow_register_eval rows>, <served-Arabic rows>)` and applies the `tool_loop_iterations == 0` filter to the shadow rows for the primary set. The shipped arm is NOT stored in `shadow_register_eval` — it is joined from the messages store by `(session_id, turn_number)`.
- [ ] **Step 4: Verify pass** — PASS (3)
- [ ] **Step 5: Commit** — `git add scripts/register_eval/rating_harness.py tests/test_rating_harness.py && git commit -m "feat(register-eval): blinded dual-arm rating + IRR + delta"`

---

### Task 10: Offline gate-fire replay on the REAL user message — Blocking #3

**Files:** Create `scripts/register_eval/replay_gates.py`; Test `tests/test_replay_gates.py`

**Interfaces:** `async replay_gates_on_row(row) -> dict` (uses `row["shadow_arabic_text"]`, `row["message_en"]`, `row["clinical_flags"]`); `gate_fire_summary(rows) -> dict`.

- [ ] **Step 1: Failing test (summary)**
```python
# tests/test_replay_gates.py
from scripts.register_eval.replay_gates import gate_fire_summary

def test_summary_counts_and_rate():
    rows = [{"cultural_fired": ["general_cultural"], "banned_opener": False, "format_tokens": []},
            {"cultural_fired": [], "banned_opener": True, "format_tokens": ["*"]},
            {"cultural_fired": [], "banned_opener": False, "format_tokens": []}]
    s = gate_fire_summary(rows)
    assert s["n"] == 3 and s["cultural_fires"] == 1 and s["banned_opener_fires"] == 1
    assert s["any_gate_fire_rate"] == round(2/3, 4)
```
- [ ] **Step 2: Verify fail** — FAIL
- [ ] **Step 3: Implement** — replay back-translates the shadow text and runs the gates with the ACTUAL `message_en` + `clinical_flags` from the eval row (Blocking #3), not empty strings.
```python
# scripts/register_eval/replay_gates.py
"""Offline: estimate which English deterministic gates WOULD fire on native Khaleeji
shadow output. Runs over shadow_register_eval rows (NOT the live turn). Uses the REAL
message_en + clinical_flags per row so message-conditioned mirroring rules fire correctly
(Blocking #3). Back-translation is an approximation; rater spot-check adjudicates borderline."""
from __future__ import annotations

async def replay_gates_on_row(row: dict) -> dict:
    from sage_poc.language import async_translate_to_english  # noqa: PLC0415
    from sage_poc.rules import rules_engine  # noqa: PLC0415
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE, _FORMAT_VIOLATIONS  # noqa: PLC0415
    text = row.get("shadow_arabic_text") or ""
    back_en = await async_translate_to_english(text) if text else ""
    cultural = rules_engine.evaluate("cultural_output", {
        "response_text": back_en,
        "message_en": row.get("message_en") or "",        # REAL user message, per Blocking #3
        "clinical_flags": row.get("clinical_flags") or [],
    })
    return {"back_en": back_en,
            "cultural_fired": [r.rule_id for r in cultural.fired],
            "banned_opener": bool(_BANNED_OPENER_RE.search(back_en)),
            "format_tokens": _FORMAT_VIOLATIONS.findall(back_en)}

def gate_fire_summary(rows: list[dict]) -> dict:
    n = len(rows) or 1
    any_fire = sum(1 for r in rows if r["cultural_fired"] or r["banned_opener"] or r["format_tokens"])
    return {"n": len(rows),
            "cultural_fires": sum(1 for r in rows if r["cultural_fired"]),
            "banned_opener_fires": sum(1 for r in rows if r["banned_opener"]),
            "format_fires": sum(1 for r in rows if r["format_tokens"]),
            "any_gate_fire_rate": round(any_fire / n, 4)}
```
> `_BANNED_OPENER_RE`/`_FORMAT_VIOLATIONS` are module-private in `output_gate.py`; if not importable, lift them into a shared module first. Confirm during implementation.
- [ ] **Step 4: Verify pass** — PASS
- [ ] **Step 5: Commit** — `git add scripts/register_eval/replay_gates.py tests/test_replay_gates.py && git commit -m "feat(register-eval): gate-fire replay on real message_en (sizes Tier 1 port)"`

---

### Task 11: Pre-registration doc (the Phase-4 gate) — folds Amendments #2 and #4

**Files:** Create `docs/superpowers/specs/2026-07-07-native-arabic-register-preregistration.md`

- [ ] **Step 1: Author, fixed-before-data:**
  - **Serializer/checkpointer confirmation note** (from Task 5 Step 3) at the top.
  - **Primary comparison (Blocking #2):** register AND latency computed on **`tool_loop_iterations == 0` (zero-tool) turns only** — the only turns where the shadow single-`ainvoke` is comparable to the served arm in both latency and content. Tool turns (`>0`) reported as a **stratified secondary**, explicitly labelled non-comparable (shadow lacks the retrieved evidence the served reply used).
  - **Latency definition:** shadow `shadow_gen_latency_ms` vs served (English `freeflow` gen time + `output_gate` translate-out time) from existing stage timers; p50/p95 on Railway.
  - **Timeout censoring (Blocking #2):** `shadow_timed_out=true` rows are **right-censored observations** — report the count/rate and treat as censored in the latency distribution; do NOT silently drop (dropping biases the delta optimistic).
  - **Accepted served-latency impact (Amendment #4):** state that flag-ON served latency ≈ max(English, shadow) bounded +8s, pilot AR p95 may exceed the <3s KPI during the window; **commit a flag-off date**.
  - **Register rubric (1–5)** with anchors (5 native Khaleeji … 1 wrong dialect/broken); KPI = 4.0. **≥2 Gulf-native raters, blinded**; IRR target α ≥ 0.6, re-adjudicate below.
  - **Stratification** by `lang_profile` (khaleeji/code_switch/arabizi) and turn type.
  - **Calibration-first rule:** rubric/blinding/IRR settled on the Task 8 seed set before the flag goes live.
  - **PDPL/DPO ack line (Verification #3 — retention parity):** the ack MUST name the table where the text actually lives — **`shadow_register_eval`** (restricted retention, same class as `original_response_text`) — NOT `session_audit` columns. The table split relocated the restricted text; the ack must point at the real location or the retention guarantee is misfiled.
- [ ] **Step 2: Commit** — `git add docs/superpowers/specs/2026-07-07-native-arabic-register-preregistration.md && git commit -m "docs(register-eval): pre-registration — zero-tool primary, timeout censoring, accepted-latency, DPO ack"`

---

## Phase 4 — Enablement (gated)

### Task 12: Enable on pilot cohort after sign-off

**Preconditions (ALL true):**
- Task 5 static containment guards + the Task 7 behavioral sentinel/API-payload assertion merged and green.
- Task 11 pre-registration merged; rubric/blinding/KPI signed; DPO ack recorded (names `shadow_register_eval` with the RLS posture below); flag-off date committed.
- Task 2 exemplar `ar` fields **native-authored AND clinician-reviewed** (Amendment #5); `version` bumped from `-draft`.
- Migration `009` (table) **and** migration `010` (RLS) applied to the **prod** DB. **Migration 010 posture (architect sign-off 2026-07-07): `ALTER TABLE shadow_register_eval ENABLE ROW LEVEL SECURITY; ALTER TABLE ... FORCE ROW LEVEL SECURITY; REVOKE ALL ON shadow_register_eval FROM anon, authenticated;`** — service-role-only, owner-exemption removed, grants revoked so no future policy can silently re-open client access. **Hard precondition: RLS verified ON the prod DB before the flag flips.**
- `session_audit` RLS/grant posture verified (forced adjacent audit) — if it was exposed, its remediation migration is applied to prod (this is independent of Phase 4 and higher priority, since it already takes prod writes).
- `tests/test_shadow_never_served.py` green on the deploy SHA — **specifically the behavioral sentinel + API-payload assertion** (architect sign-off 2026-07-07: re-verified at the only point the flag ever turns on, not just at Task 7 merge).

- [ ] **Step 1:** `SAGE_NATIVE_ARABIC_SHADOW=true` on the pilot service only (Railway; deploys are manual — `railway up`).
- [ ] **Step 2:** Verify one Arabic turn writes a `shadow_register_eval` row (with `message_en`, `tool_loop_iterations`, `shadow_timed_out`) AND that the served `response` is unchanged translate-out; grep the client payload for the sentinel to confirm containment in prod.
- [ ] **Step 3:** Collect to target N; run Task 9 rating + Task 10 replay; disable the flag on the committed date.
- [ ] **Step 4:** Hand register delta / latency delta (zero-tool primary) / gate-fire rate to the deferred decision brief (a).

---

## Amendment Map (2026-07-07 review)

- **#1 (blocking) containment:** shadow removed from `SageState` entirely → written only to `shadow_register_eval` (Tasks 6–7); mandatory behavioral sentinel + state-channel-absence tests + serializer/checkpointer confirmation (Task 5, merges before the migration).
- **#2 (blocking) latency validity:** `tool_loop_iterations` captured per turn (Task 7); pre-registered zero-tool primary comparison + tool-turn stratified secondary; `shadow_timed_out` recorded and treated as right-censored (Tasks 6, 11).
- **#3 (blocking) replay context:** `message_en` + `clinical_flags` stored per row and used in gate replay (Tasks 6, 10).
- **#4 (non-blocking) served-latency honesty:** Global Constraints corrected to max(English, shadow) bounded +8s; accepted-impact + flag-off date in pre-registration (Task 11).
- **#5 (non-blocking) exemplar governance:** clinician review added to Phase 4 preconditions; CMS-migration note flagged for the Tier 1 brief (Tasks 2, 12).

**Wiring-checkpoint verification items (relocated side-effect of the by-construction fix — reviewer MUST confirm all three at the Task 7 review pause):**
- **V1 write fail-open + bounded:** the direct DB write from inside the graph node is wrapped in `asyncio.wait_for(_SHADOW_WRITE_TIMEOUT_S)` + swallowed; a Supabase timeout/error never delays or breaks the served turn (Task 6 writer + Task 7 wiring + `test_eval_write_failure_does_not_break_served_turn`).
- **V2 pairing key across table split:** the rating harness pairs shadow (`shadow_register_eval`) to served Arabic (messages store) explicitly on `(session_id, turn_number)` via `pair_by_turn`, not single-row columns (Task 9 + `test_pairs_joined_by_session_and_turn`).
- **V3 retention parity:** the DPO ack names `shadow_register_eval` as the restricted-text location, not `session_audit` (Task 11).

## Self-Review

- Containment (#1) → Tasks 5/6/7; no `SageState`/`audit.py`/serializer path carries shadow. ✓
- Latency comparability + censoring (#2) → `tool_loop_iterations`, `shadow_timed_out`, zero-tool primary. ✓
- Replay uses real message (#3) → eval-table `message_en`/`clinical_flags`. ✓
- Served-latency honesty (#4) + exemplar clinical sign-off (#5) → constraints + Task 11/12. ✓
- Type consistency: `generate_shadow_arabic` keys → `build_shadow_eval_row` payload reads → `shadow_register_eval` columns all align; `compose_prompt(..., shadow_arabic=bool)` matches call sites. ✓
- Placeholder scan: only genuine native/clinical content (exemplar `ar`, seed set >3) is deferred, gated with explicit authoring + version bump. ✓
