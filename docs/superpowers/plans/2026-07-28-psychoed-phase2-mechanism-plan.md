# Psychoeducation Phase 2 — Mechanism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the flag-OFF psychoed serve mechanism — Node-4 resolver + classifiers, PSY-WEAVE-1 evaluator, declared state channel, deterministic no-LLM turn-1 serve, Node-8 audit + verbatim hash gate, and family-exposure carry-forward — with prod behavior byte-identical while `SAGE_PSYCHOED_PATHWAYS` is unset.

**Architecture:** All ratified copy is read from the Phase-1 content-as-code files (`data/psychoed/`) via one in-process store; the resolver and classifiers are pure modules integrated into `skill_select_node` ahead of the Mechanism-A consult block; serve composition is a no-LLM early path in `freeflow_respond_node` that still transits `output_gate` (Rider 1 — no bypass, unlike the crisis node). Spec: `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` §2–§6. Binding execution notes: `docs/superpowers/plans/2026-07-28-psychoed-phase2-handoff-notes.md`.

**Tech Stack:** Python 3, LangGraph (existing 9-node graph), `uv run pytest`, JSON data files, one SQL migration.

## Global Constraints

- **Flag-OFF = byte-identical.** With `SAGE_PSYCHOED_PATHWAYS` unset, every code path added here is unreachable; a regression test asserts current behavior unchanged (Task 12). Flag idiom: the strict inverted-default 3-statement block (config.py lines 170–178 pattern).
- **No new graph nodes.** One conditional-edge-map addition only (skill_select → existing `crisis_response`, required by spec §6.1 PSY-WEAVE-1 escalation; recorded as the single wiring delta — spec §2.1's "same edges" claim held for the serve path, not the weave escalation, and this plan documents the delta).
- **Never-disarm:** no upstream safety node (`safety_check`, `intent_route`) reads any `psychoed_*` key. Enforced by review + Task 3's channel test.
- **Ratified copy is served from the store only** (loaded from `data/psychoed/`, hash-guarded by `SOURCE_SHA` CI from Phase 1). No copy literals in code. `shared_scripts` values starting `"PENDING-CLINICIAN"` hard-fail at startup if their consuming path is enabled (handoff note 3).
- **State keys:** exactly the 10 spec §4.2 keys + `psychoed_family_exposures` (this plan adds it — see Task 9 rationale; schema-extension follow-up to spec §10 item 7). All declared in `SageState`; `scripts/check_state_channels.py` must stay green (CI: `.github/workflows/unit-gate.yml:80`).
- **Mechanism-A untouched in code.** Consult-set retirement happens per-category at Phase-4 flips, NOT here. Phase 2 only guarantees ordering: when the psychoed flag is ON for a category, the resolver returns before the consult block is reached (no double-claim).
- **Migration number 016 claimed in `migrations/MIGRATIONS.md` at branch creation** (ledger convention; note the ledger currently trails the files — reconcile the table to 015 in the same edit).
- **Branch:** `feat/psychoed-phase2-mechanism` off current master. One commit per task. No memory-directory writes.
- **Em-dash rule** applies to any string a user could see (there should be none in code — copy comes from the store).

## File Structure

```
src/sage_poc/psychoed/
  __init__.py
  store.py            # loads data/psychoed/** once; blocks/manifests/tables/collisions/shared/weave
  resolver.py         # trigger matching: exact, menu-context, subsumption-aware, collision winners
  classifiers.py      # Classifier A (acute distress) + Classifier B (framing) — pure functions
  weave.py            # PSY-WEAVE-1 evaluator — pure, driven by evaluation_semantics
  serve.py            # turn-1 composition (framing/block/weave/menu per delivery shape) + hashes
data/psychoed/
  classifier_a.en.json            # distress lexicon + structural thresholds (ENGINEERING PROPOSAL values)
  serve_templates.en.json         # composition templates (structure only, no clinical copy), versioned
src/sage_poc/prompts/templates/L2_intents/psychoed_continuation.json   # turns-2+ glue template
src/sage_poc/nodes/skill_select.py      # integration (ordered steps, spec §2.1)
src/sage_poc/nodes/knowledge_retrieve.py # outcome-1 store fetch + outcome-2 backstop + L4 quarantine
src/sage_poc/nodes/freeflow_respond.py  # no-LLM serve path
src/sage_poc/nodes/output_gate.py       # audit fields + verbatim hash gate + failure path
src/sage_poc/nodes/skill_executor.py    # rule-6 family-counter read
src/sage_poc/config.py                  # PSYCHOED_PATHWAYS_ENABLED + PSYCHOED_CATEGORIES
src/sage_poc/state.py                   # 11 new channels
src/sage_poc/graph.py                   # edge-map entry: skill_select → crisis_response
migrations/016_add_psychoed_to_session_audit.sql
server.py                               # per-turn reset of psychoed_serve
tests/test_psychoed_store.py, test_psychoed_resolver.py, test_psychoed_classifiers.py,
tests/test_psychoed_weave_eval.py, test_psychoed_serve.py, test_psychoed_skill_select.py,
tests/test_psychoed_gate.py, test_psychoed_flag_off.py, test_psychoed_carry_forward.py
```

---

### Task 1: Feature flags

**Files:**
- Modify: `src/sage_poc/config.py` (append after the `INFO_REQUEST_CONSULT` block, ~line 390)
- Test: `tests/test_psychoed_flag_off.py` (created here, extended in Task 12)

**Interfaces:**
- Produces: `config.PSYCHOED_PATHWAYS_ENABLED: bool`, `config.PSYCHOED_CATEGORIES: frozenset[str]` (empty when flag off; parsed from `SAGE_PSYCHOED_CATEGORIES`, comma-separated, validated against `{"1f","3c","4b","6d","7c","s2c"}`), `config.psychoed_enabled_for(category: str) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_flag_off.py
import importlib

def _reload_config(monkeypatch, **env):
    for k in ("SAGE_PSYCHOED_PATHWAYS", "SAGE_PSYCHOED_CATEGORIES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from sage_poc import config
    return importlib.reload(config)

def test_flag_default_off(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    assert cfg.PSYCHOED_CATEGORIES == frozenset()
    assert cfg.psychoed_enabled_for("1f") is False

def test_flag_on_with_categories(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,3c")
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is True
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f", "3c"})
    assert cfg.psychoed_enabled_for("1f") and not cfg.psychoed_enabled_for("s2c")

def test_invalid_category_rejected(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,bogus")
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f"})  # bogus dropped with a warning, never served
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_psychoed_flag_off.py -q` → FAIL (`AttributeError: PSYCHOED_PATHWAYS_ENABLED`).

- [ ] **Step 3: Implement in config.py** (strict inverted-default idiom, mirroring lines 170–178):

```python
# --- Psychoed pathways (Phase 2 mechanism; spec 2026-07-23 §7.3). Default OFF. ---
_psychoed_raw = os.getenv("SAGE_PSYCHOED_PATHWAYS")
PSYCHOED_PATHWAYS_ENABLED = (
    _psychoed_raw is not None and _psychoed_raw.strip().lower() == "true"
)
if _psychoed_raw is not None and _psychoed_raw.strip().lower() not in ("true", "false"):
    logging.getLogger(__name__).warning(
        "SAGE_PSYCHOED_PATHWAYS=%r is neither 'true' nor 'false'; treating as OFF", _psychoed_raw
    )

_PSYCHOED_VALID_CATEGORIES = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})
_categories_raw = os.getenv("SAGE_PSYCHOED_CATEGORIES", "")
_parsed = {c.strip().lower() for c in _categories_raw.split(",") if c.strip()}
for _bad in sorted(_parsed - _PSYCHOED_VALID_CATEGORIES):
    logging.getLogger(__name__).warning("SAGE_PSYCHOED_CATEGORIES: unknown category %r dropped", _bad)
PSYCHOED_CATEGORIES: frozenset[str] = (
    frozenset(_parsed & _PSYCHOED_VALID_CATEGORIES) if PSYCHOED_PATHWAYS_ENABLED else frozenset()
)

def psychoed_enabled_for(category: str) -> bool:
    return PSYCHOED_PATHWAYS_ENABLED and category in PSYCHOED_CATEGORIES
```

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_psychoed_flag_off.py -q` → 3 passed.
- [ ] **Step 5: Commit** — `git add src/sage_poc/config.py tests/test_psychoed_flag_off.py && git commit -m "feat(psychoed): SAGE_PSYCHOED_PATHWAYS + per-category enablement (default OFF)"`

---

### Task 2: The content store

**Files:**
- Create: `src/sage_poc/psychoed/__init__.py` (empty), `src/sage_poc/psychoed/store.py`
- Test: `tests/test_psychoed_store.py`

**Interfaces:**
- Consumes: `data/psychoed/**` (Phase-1 artifacts, shapes per `scripts/psychoed_ingest/schemas.py`).
- Produces (all later tasks depend on these exact names):
  - `store.get_block(block_id: str) -> dict | None`
  - `store.block_ids() -> frozenset[str]`
  - `store.manifest(category: str) -> dict`
  - `store.category_of(block_id: str) -> str`
  - `store.family_of_kb_ref(kb_ref: str) -> str | None` (kb_ref = article_family or block_id; returns article_family)
  - `store.trigger_rows() -> list[dict]` (each row: category, row_id, type, framing, route, row_provenance, phrases)
  - `store.collision_entries() -> dict` (raw collision_table.json)
  - `store.shared_script(name: str) -> str` (raises `PendingClinicianScript` if value startswith `"PENDING-CLINICIAN"`)
  - `store.weave_data() -> dict` (psy_weave_1.en.json)
  - `store.block_sha256(block_id: str) -> str` (hash of the block's `content` string, utf-8)
  - Module-level singleton loaded lazily on first access; `store.reload_for_tests()` for test isolation.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_store.py
import pytest
from sage_poc.psychoed import store

def test_all_40_blocks_load():
    assert len(store.block_ids()) == 40
    b = store.get_block("1f-b1")
    assert b["psychoed"]["category"] == "1f" and b["content"]

def test_manifests_and_categories():
    m = store.manifest("3c")
    assert m["safety_weave"] is True and m["delivery_shape"] == "answer_first"
    assert store.category_of("s2c-b8") == "s2c"

def test_family_of_kb_ref():
    assert store.family_of_kb_ref("understanding_anxiety") == "understanding_anxiety"
    assert store.family_of_kb_ref("1f-b2") == "understanding_anxiety"
    assert store.family_of_kb_ref("nope") is None

def test_pending_script_raises():
    with pytest.raises(store.PendingClinicianScript):
        store.shared_script("human_referral_close")
    assert store.shared_script("safety_weave_script")  # ratified-source script loads fine

def test_block_hash_stable():
    h = store.block_sha256("1f-b1")
    assert len(h) == 64 and h == store.block_sha256("1f-b1")
```

- [ ] **Step 2: Run to verify failure** — `uv run pytest tests/test_psychoed_store.py -q` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement `store.py`**

```python
"""In-process store for the Phase-1 psychoed content artifacts (data/psychoed/**).

The ONLY source of ratified psychoed copy at runtime (spec §3; Phase-2 handoff).
Loads once, lazily. Copy never appears as literals in code. The SOURCE_SHA CI
guard (tests/test_psychoed_content_integrity.py) pins these files to the doc.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[3] / "data" / "psychoed"

class PendingClinicianScript(RuntimeError):
    """Raised when a consuming path requests a shared script still awaiting clinical authorship."""

class _Store:
    def __init__(self) -> None:
        self._blocks: dict[str, dict] = {}
        for f in sorted((_DATA / "blocks" / "en").rglob("*.json")):
            d = json.loads(f.read_text())
            self._blocks[d["article_id"]] = d
        self._manifests = {
            f.stem: json.loads(f.read_text()) for f in sorted((_DATA / "manifests").glob("*.json"))
        }
        self._tables = [
            json.loads(f.read_text()) for f in sorted((_DATA / "trigger_tables" / "en").glob("*.json"))
        ]
        self._collisions = json.loads((_DATA / "collisions" / "collision_table.json").read_text())
        self._shared = json.loads((_DATA / "shared" / "shared_scripts.en.json").read_text())["scripts"]
        self._weave = json.loads((_DATA / "weave" / "psy_weave_1.en.json").read_text())

_instance: _Store | None = None

def _s() -> _Store:
    global _instance
    if _instance is None:
        _instance = _Store()
    return _instance

def reload_for_tests() -> None:
    global _instance
    _instance = None

def get_block(block_id: str) -> dict | None:
    return _s()._blocks.get(block_id)

def block_ids() -> frozenset[str]:
    return frozenset(_s()._blocks)

def manifest(category: str) -> dict:
    return _s()._manifests[category]

def category_of(block_id: str) -> str:
    return _s()._blocks[block_id]["psychoed"]["category"]

def family_of_kb_ref(kb_ref: str) -> str | None:
    blocks = _s()._blocks
    if kb_ref in blocks:
        return blocks[kb_ref]["psychoed"]["article_family"]
    families = {b["psychoed"]["article_family"] for b in blocks.values()}
    return kb_ref if kb_ref in families else None

def trigger_rows() -> list[dict]:
    rows: list[dict] = []
    for t in _s()._tables:
        for r in t["rows"]:
            rows.append({**r, "category": t["category"]})
    return rows

def collision_entries() -> dict:
    return _s()._collisions

def shared_script(name: str) -> str:
    v = _s()._shared[name]
    if v.startswith("PENDING-CLINICIAN"):
        raise PendingClinicianScript(name)
    return v

def weave_data() -> dict:
    return _s()._weave

def block_sha256(block_id: str) -> str:
    return hashlib.sha256(_s()._blocks[block_id]["content"].encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run to verify pass** — `uv run pytest tests/test_psychoed_store.py -q` → 5 passed.
- [ ] **Step 5: Commit** — `git add src/sage_poc/psychoed tests/test_psychoed_store.py && git commit -m "feat(psychoed): in-process content store over Phase-1 artifacts"`

---

### Task 3: State channels + per-turn reset

**Files:**
- Modify: `src/sage_poc/state.py` (append to `SageState`), `server.py` (`_build_state()` — add per-turn reset)
- Test: extend `tests/test_psychoed_flag_off.py`; CI check `scripts/check_state_channels.py` must stay green

**Interfaces:**
- Produces these `SageState` channels (exact names; spec §4.2 + one addition):
  - Per-turn (reset in `_build_state()`): `psychoed_serve: Optional[dict]`
  - Pathway-scoped: `psychoed_active_category: Optional[str]`, `psychoed_delivery_shape: Optional[str]`, `psychoed_blocks_served: list[str]`, `psychoed_menu_offered: bool`, `psychoed_weave_fired: bool`, `psychoed_weave_pending: bool`, `psychoed_matched_row_id: Optional[str]`, `psychoed_collision_path: Optional[str]`, `psychoed_framing: Optional[str]`
  - Session-scoped (this plan's addition, carry-forward): `psychoed_family_exposures: list[str]` (append-one-per-serve; counted by Task 9)

- [ ] **Step 1: Write the failing test** (append to `tests/test_psychoed_flag_off.py`):

```python
def test_psychoed_channels_declared():
    from sage_poc.state import SageState
    keys = SageState.__annotations__
    for k in ("psychoed_serve", "psychoed_active_category", "psychoed_delivery_shape",
              "psychoed_blocks_served", "psychoed_menu_offered", "psychoed_weave_fired",
              "psychoed_weave_pending", "psychoed_matched_row_id", "psychoed_collision_path",
              "psychoed_framing", "psychoed_family_exposures"):
        assert k in keys, f"undeclared channel: {k}"
```

- [ ] **Step 2: Run to verify failure** — FAIL (`undeclared channel: psychoed_serve`).
- [ ] **Step 3: Implement.** In `state.py`, append inside `SageState` (comment style matches existing keys):

```python
    # --- Psychoed pathway channel (spec 2026-07-23 §4.2; Phase 2). ---
    # psychoed_serve is PER-TURN: reset each turn in _build_state(). All others are
    # pathway-scoped (cleared on pathway exit by skill_select/output_gate, after audit
    # persist) except psychoed_family_exposures which is session-scoped (carry-forward,
    # schema-extension follow-up to spec §10 item 7).
    psychoed_serve: Optional[dict]
    psychoed_active_category: Optional[str]
    psychoed_delivery_shape: Optional[str]
    psychoed_blocks_served: list[str]
    psychoed_menu_offered: bool
    psychoed_weave_fired: bool
    psychoed_weave_pending: bool
    psychoed_matched_row_id: Optional[str]
    psychoed_collision_path: Optional[str]
    psychoed_framing: Optional[str]
    psychoed_family_exposures: list[str]
```

In `server.py` `_build_state()`, alongside the existing per-turn resets add `"psychoed_serve": None,` and defaults for the others when absent from the loaded session (`psychoed_blocks_served: []`, `psychoed_family_exposures: []`, booleans `False`, optionals `None` — carried forward from prior turn when present, matching how other pathway-scoped keys are handled there).

- [ ] **Step 4: Verify** — `uv run pytest tests/test_psychoed_flag_off.py -q` → pass; `uv run python scripts/check_state_channels.py` → exit 0.
- [ ] **Step 5: Commit** — `git commit -am "feat(psychoed): declare psychoed state channels + per-turn serve reset"`

---

### Task 4: PSY-WEAVE-1 evaluator (pure)

**Files:**
- Create: `src/sage_poc/psychoed/weave.py`
- Test: `tests/test_psychoed_weave_eval.py`

**Interfaces:**
- Produces: `weave.is_clear_negative(reply: str) -> bool` and `weave.evaluate(reply: str) -> str` returning `"proceed"` (clear negative) or `"crisis"` (everything else — fail-closed). Implementation MUST be driven by the data file's `evaluation_semantics` (order: contradiction markers first as substring on normalized reply, then clear-negative regex fullmatch; default fail-closed) — never hardcoded lists (handoff note 2).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_weave_eval.py
from sage_poc.psychoed import weave

OK = ["No", "no, nothing like that", "No, alhamdulillah", "no I haven't, why?", "no thank god"]
BAD = ["kind of", "sometimes", "not really but...", "no, but sometimes",
       "actually, what is anxiety?", "yes", "i don't know", ""]

def test_clear_negatives_proceed():
    for r in OK:
        assert weave.evaluate(r) == "proceed", r

def test_everything_else_fails_closed():
    for r in BAD:
        assert weave.evaluate(r) == "crisis", r

def test_driven_by_data_not_code():
    import inspect
    src = inspect.getsource(weave)
    assert "alhamdulillah" not in src  # patterns live in data, not code
```

- [ ] **Step 2: Run to verify failure** — FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `weave.py`**

```python
"""PSY-WEAVE-1 response evaluation (spec §6.1). Pure; driven entirely by
data/psychoed/weave/psy_weave_1.en.json's evaluation_semantics. Fail-closed:
anything not a clear negative routes toward crisis. Never-disarm: this module
never reads SageState; callers pass the raw reply text."""
from __future__ import annotations
import re
from sage_poc.psychoed import store

def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s']", "", text.lower()).strip()

def is_clear_negative(reply: str) -> bool:
    data = store.weave_data()
    sem = data["evaluation_semantics"]
    assert sem["default"] == "fail_closed_to_crisis"
    norm = _normalize(reply)
    if not norm:
        return False
    if any(m in norm for m in data["contradiction_markers"]):   # order[0]: markers first
        return False
    return any(re.fullmatch(p, norm) for p in data["clear_negative_patterns"])  # order[1]

def evaluate(reply: str) -> str:
    return "proceed" if is_clear_negative(reply) else "crisis"
```

- [ ] **Step 4: Verify pass**, then **Step 5: Commit** — `git commit -am "feat(psychoed): PSY-WEAVE-1 evaluator, data-driven, fail-closed"` (with the new test file added).

---

### Task 5: Classifier A data + classifiers module (pure)

**Files:**
- Create: `data/psychoed/classifier_a.en.json`, `src/sage_poc/psychoed/classifiers.py`
- Test: `tests/test_psychoed_classifiers.py`

**Interfaces:**
- Produces: `classifiers.acute_distress(state_like: dict, message_en: str) -> bool` (Classifier A: True = acute → psychoed is wrong tool now; inputs: safety-route state keys + lexicon + structural signals; ambiguity → True), `classifiers.framing_for_row(row: dict) -> str` (Classifier B outcome-1: reads `row["framing"]`), `classifiers.FRAMING_FALLBACK = "personal"` (outcome-2 fail-to-personal).

- [ ] **Step 1: Author the data file** (values are the packet ask-7 ENGINEERING PROPOSAL — clinician sets final):

```json
{
  "version": "0.1.0-draft",
  "status": "engineering-proposal-pending-clinician (packet ask 7)",
  "distress_markers": [
    "right now", "can't breathe", "cant breathe", "heart is racing", "heart racing",
    "panicking", "panic attack", "shaking", "can't calm down", "cant calm down",
    "help me now", "chest is tight"
  ],
  "structural": {
    "fragment_max_len": 12,
    "fragment_min_count": 3,
    "numeric_self_report_pattern": "\\b([7-9]|10)\\s*/\\s*10\\b"
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_psychoed_classifiers.py
from sage_poc.psychoed import classifiers

def test_lexical_distress_is_acute():
    assert classifiers.acute_distress({}, "what is anxiety? I can't breathe right now")

def test_numeric_self_report_is_acute():
    assert classifiers.acute_distress({}, "why do I feel like this, it's a 9/10")

def test_fragmented_message_is_acute():
    assert classifiers.acute_distress({}, "help. now. please. why")

def test_upstream_safety_state_is_acute():
    assert classifiers.acute_distress({"crisis_state": "monitoring"}, "what is anxiety?")

def test_calm_curiosity_is_not_acute():
    assert not classifiers.acute_distress({}, "What is anxiety? I have always wondered how it works.")

def test_framing_fallback_is_personal():
    assert classifiers.FRAMING_FALLBACK == "personal"
    assert classifiers.framing_for_row({"framing": "abstract"}) == "abstract"
```

- [ ] **Step 3: Run to verify failure**, then **Step 4: Implement `classifiers.py`**

```python
"""Psychoed classifiers (spec §5.3/§5.4). Pure functions; deterministic inputs only.
Classifier A fail direction: ambiguity -> acute (doc: 'default to the higher tier').
Classifier B data (row framing mappings, the fail-to-personal default) is
safety-rule governed (spec §5.4) — changes need clinical sign-off."""
from __future__ import annotations
import json, re
from pathlib import Path

_DATA = json.loads(
    (Path(__file__).resolve().parents[3] / "data" / "psychoed" / "classifier_a.en.json").read_text()
)
FRAMING_FALLBACK = "personal"

def acute_distress(state_like: dict, message_en: str) -> bool:
    if state_like.get("crisis_state") == "monitoring":
        return True
    if state_like.get("fired_safety_routes"):
        return True
    msg = message_en.lower()
    if any(m in msg for m in _DATA["distress_markers"]):
        return True
    s = _DATA["structural"]
    if re.search(s["numeric_self_report_pattern"], msg):
        return True
    frags = [f for f in re.split(r"[.!?\n]+", message_en) if f.strip()]
    short = [f for f in frags if len(f.strip()) <= s["fragment_max_len"]]
    return len(frags) >= s["fragment_min_count"] and len(short) == len(frags)

def framing_for_row(row: dict) -> str:
    return row.get("framing") or FRAMING_FALLBACK
```

- [ ] **Step 5: Verify pass; commit** — `git add data/psychoed/classifier_a.en.json src/sage_poc/psychoed/classifiers.py tests/test_psychoed_classifiers.py && git commit -m "feat(psychoed): Classifier A (fail-to-acute) + framing helpers"`

---

### Task 6: Trigger resolver (pure)

**Files:**
- Create: `src/sage_poc/psychoed/resolver.py`
- Test: `tests/test_psychoed_resolver.py`

**Interfaces:**
- Produces: `resolver.resolve(message_en: str, *, active_category: str | None, grief_context: bool, enabled_categories: frozenset[str]) -> dict | None`. Return shape on hit: `{"category", "row_id", "route", "framing", "block_id" (answer-first best block or None), "collision_path" (str|None), "menu_pick" (bool)}`. Behavior: normalized matching (same normalization as `weave._normalize`); **menu-context scoping first** (match against the active category's `menu_label`s when `active_category` set); then exact phrase match over trigger rows of ENABLED categories; cross-category ties resolved ONLY via the collision table (context signal → context_winner; else default/interim winner; **never similarity**); subsumption pairs resolved to the declared winner when the longer form matches; returns None on no hit. Answer-first `block_id`: the manifest's block whose `menu_label`/title row maps to the matched row's topic where the trigger table row declares one — otherwise the resolver returns the matched row and `serve.py` picks the block by row→block mapping in the manifest's ordered blocks (row_id → `blocks[i]` only where the trigger table's row carries `"block_id"`; rows without one get the category's first block per doc answer-first behavior of answering the SPECIFIC question — Phase-1 tables carry no block_id field, so v1 maps: match phrase → best block by exact `menu_label` containment in the phrase, else category block 1; this mapping choice is recorded in the module docstring and is fixture-pinned in Phase 3 F1).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_resolver.py
from sage_poc.psychoed import resolver

ALL = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})

def test_exact_hit_routes_category():
    r = resolver.resolve("What is anxiety?", active_category=None, grief_context=False,
                         enabled_categories=ALL)
    assert r and r["category"] == "1f"

def test_disabled_category_never_fires():
    r = resolver.resolve("What is anxiety?", active_category=None, grief_context=False,
                         enabled_categories=frozenset({"3c"}))
    assert r is None

def test_numb_collision_default_3c():
    r = resolver.resolve("Why do I feel numb?", active_category=None, grief_context=False,
                         enabled_categories=ALL)
    assert r["category"] == "3c" and r["collision_path"] == "default_winner"

def test_numb_collision_grief_context_s2c():
    r = resolver.resolve("Why do I feel numb?", active_category=None, grief_context=True,
                         enabled_categories=ALL)
    assert r["category"] == "s2c" and r["collision_path"] == "context_winner"

def test_subsumption_long_form_winner():
    r = resolver.resolve("Why do I feel like this for no reason?", active_category=None,
                         grief_context=False, enabled_categories=ALL)
    assert r["category"] == "3c"   # declared subsumption winner (weave-dominance)

def test_menu_context_scoped_first():
    r = resolver.resolve("the maintenance cycle one", active_category="1f",
                         grief_context=False, enabled_categories=ALL)
    assert r and r["category"] == "1f" and r["menu_pick"] is True

def test_bare_emotional_words_no_match():
    for msg in ("I'm stressed", "I feel depressed", "I feel sad"):
        assert resolver.resolve(msg, active_category=None, grief_context=False,
                                enabled_categories=ALL) is None
```

- [ ] **Step 2: Run to verify failure**, then **Step 3: Implement `resolver.py`**

```python
"""Node-4 psychoed trigger resolver (spec §2.1/§5.1/§5.2). Deterministic only:
normalized exact-phrase matching, menu-context scoping, collision-table winners.
NEVER similarity. Block mapping v1: matched phrase -> block whose menu_label's
normalized text is contained in the phrase, else the category's first block
(fixture-pinned in Phase 3 F1)."""
from __future__ import annotations
import re
from sage_poc.psychoed import store

def _norm(t: str) -> str:
    return re.sub(r"[^\w\s']", "", t.lower()).strip()

def _phrase_index(enabled: frozenset[str]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for row in store.trigger_rows():
        if row["category"] not in enabled:
            continue
        for ph in row["phrases"]:
            idx.setdefault(_norm(ph), []).append(row)
    return idx

def _collision_winner(phrase_norm: str, rows: list[dict], grief_context: bool) -> tuple[dict, str]:
    table = store.collision_entries()
    for e in table.get("collisions", []):
        if _norm(e["phrase"]) == phrase_norm:
            res = e["resolution"]
            if grief_context and res.get("context_winner"):
                win = res["context_winner"]; path = "context_winner"
            else:
                win = res.get("default_winner") or res.get("interim_default_winner"); path = "default_winner"
            return next(r for r in rows if r["category"] == win), path
    for e in table.get("subsumption_collisions", []):
        if _norm(e["phrase"]) in phrase_norm or phrase_norm in _norm(e["phrase"]):
            win = e["resolution"].get("winner") or e["resolution"].get("long_form_winner")
            cand = [r for r in rows if r["category"] == win]
            if cand:
                return cand[0], "subsumption_winner"
    return rows[0], "undeclared_first"  # unreachable if collision CI holds; audit will show it

def _pick_block(category: str, phrase_norm: str) -> str | None:
    man = store.manifest(category)
    if man["delivery_shape"] != "answer_first":
        return None
    for bid in man["blocks"]:
        label = _norm(store.get_block(bid)["psychoed"]["menu_label"])
        if label and label in phrase_norm:
            return bid
    return man["blocks"][0]

def resolve(message_en: str, *, active_category: str | None, grief_context: bool,
            enabled_categories: frozenset[str]) -> dict | None:
    if not enabled_categories:
        return None
    norm = _norm(message_en)
    if active_category and active_category in enabled_categories:
        for bid in store.manifest(active_category)["blocks"]:
            label = _norm(store.get_block(bid)["psychoed"]["menu_label"])
            if label and label in norm:
                return {"category": active_category, "row_id": "menu_pick", "route": "standard",
                        "framing": None, "block_id": bid, "collision_path": None, "menu_pick": True}
    idx = _phrase_index(enabled_categories)
    rows = idx.get(norm)
    if not rows:
        # subsumption: a declared longer-form phrase matching a contained shorter phrase's row
        for ph_norm, cand in idx.items():
            if ph_norm and ph_norm in norm and len(ph_norm) >= 12:
                rows = cand
                break
        if not rows:
            return None
    if len({r["category"] for r in rows}) > 1:
        row, path = _collision_winner(norm, rows, grief_context)
    else:
        row, path = rows[0], None
    return {"category": row["category"], "row_id": row["row_id"], "route": row["route"],
            "framing": row.get("framing"), "block_id": _pick_block(row["category"], norm),
            "collision_path": path, "menu_pick": False}
```

- [ ] **Step 4: Iterate until all 7 tests pass** (the subsumption/containment interplay is the fiddly part — the two declared long forms must land on their declared winners; add no similarity logic under any circumstances). **Step 5: Commit** — `git commit -am "feat(psychoed): deterministic trigger resolver (collision-table winners, menu scoping)"` (add new files).

---

### Task 7: Serve composition (pure) + continuation template

**Files:**
- Create: `data/psychoed/serve_templates.en.json`, `src/sage_poc/psychoed/serve.py`, `src/sage_poc/prompts/templates/L2_intents/psychoed_continuation.json`
- Test: `tests/test_psychoed_serve.py`

**Interfaces:**
- Produces: `serve.compose_turn1(payload: dict) -> dict` where payload is the `psychoed_serve` state dict (`{"category","block_id","route","framing","weave_due":bool,"template_version"}`) and the return is `{"text": str, "blocks_emitted": list[str], "weave_asked": bool, "menu_offered": bool, "template_version": str}`. Composition rules (spec §4.1): menu-first → framing + menu_offer; answer-first abstract → framing + block + menu_offer; answer-first personal+weave → framing + block + **weave question, STOP (no menu)**; `route == "formal_diagnosis"` → framing + diagnosis_guard_stage1 (weave-checked identically). Joins are `"\n\n"`. All copy comes from the store; `serve_templates.en.json` holds only ordering/version (`{"version":"1.0.0","order_menu_first":["framing","menu"],...}`) — no clinical text.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_psychoed_serve.py
from sage_poc.psychoed import serve, store

def test_menu_first_composition():
    out = serve.compose_turn1({"category": "1f", "block_id": None, "route": "standard",
                               "framing": "abstract", "weave_due": False})
    m = store.manifest("1f")
    assert out["text"] == m["framing_statement"] + "\n\n" + m["menu_offer"]
    assert out["menu_offered"] and not out["weave_asked"] and out["blocks_emitted"] == []

def test_answer_first_abstract():
    out = serve.compose_turn1({"category": "6d", "block_id": "6d-b1", "route": "standard",
                               "framing": "abstract", "weave_due": False})
    m = store.manifest("6d")
    b = store.get_block("6d-b1")["content"]
    assert out["text"] == m["framing_statement"] + "\n\n" + b + "\n\n" + m["menu_offer"]

def test_answer_first_personal_weave_stops_before_menu():
    out = serve.compose_turn1({"category": "3c", "block_id": "3c-b4", "route": "standard",
                               "framing": "personal", "weave_due": True})
    m = store.manifest("3c")
    assert out["text"].startswith(m["framing_statement"])
    assert store.get_block("3c-b4")["content"] in out["text"]
    assert store.shared_script("safety_weave_script") in out["text"]
    assert m["menu_offer"] not in out["text"]          # menu deferred behind the weave
    assert out["weave_asked"] and not out["menu_offered"]

def test_formal_diagnosis_serves_guard_script():
    out = serve.compose_turn1({"category": "3c", "block_id": None, "route": "formal_diagnosis",
                               "framing": "personal", "weave_due": False})
    assert store.shared_script("diagnosis_guard_stage1") in out["text"]
    assert out["blocks_emitted"] == []

def test_s2c_b8_block_guard_not_duplicated():
    out = serve.compose_turn1({"category": "s2c", "block_id": "s2c-b8", "route": "standard",
                               "framing": "abstract", "weave_due": False})
    note = store.get_block("s2c-b8")["psychoed"]["block_guard"]["note"]
    assert out["text"].count(note) == 1   # note is the block's own final sentence; never appended twice
```

- [ ] **Step 2: Run to verify failure**, then **Step 3: Implement.** `serve_templates.en.json`:

```json
{"version": "1.0.0", "join": "\n\n",
 "note": "Structure/version only. ALL clinical copy comes from the psychoed store."}
```

`serve.py`:

```python
"""Deterministic turn-1 psychoed composition (spec §4.1). No LLM. All copy from
the store. Weave turn-boundary rule: when the weave fires, the menu is deferred
to the following turn, contingent on a clear-negative (PSY-WEAVE-1)."""
from __future__ import annotations
import json
from pathlib import Path
from sage_poc.psychoed import store

_TPL = json.loads(
    (Path(__file__).resolve().parents[3] / "data" / "psychoed" / "serve_templates.en.json").read_text()
)

def compose_turn1(payload: dict) -> dict:
    cat = payload["category"]
    man = store.manifest(cat)
    join = _TPL["join"]
    parts: list[str] = [man["framing_statement"]]
    blocks: list[str] = []
    weave_asked = False
    menu_offered = False

    if payload.get("route") == "formal_diagnosis":
        parts.append(store.shared_script("diagnosis_guard_stage1"))
    elif man["delivery_shape"] == "menu_first":
        parts.append(man["menu_offer"])
        menu_offered = True
    else:  # answer_first
        bid = payload["block_id"]
        block = store.get_block(bid)
        parts.append(block["content"])
        blocks.append(bid)
        guard = block["psychoed"].get("block_guard")
        if guard and guard["note"] not in block["content"]:
            parts.append(guard["note"])   # single-sourcing: only if not already the final sentence
        if payload.get("weave_due"):
            parts.append(store.shared_script("safety_weave_script"))
            weave_asked = True            # menu deferred (spec §4.1)
        else:
            parts.append(man["menu_offer"])
            menu_offered = True

    if payload.get("weave_due") and payload.get("route") == "formal_diagnosis" and not weave_asked:
        parts.append(store.shared_script("safety_weave_script"))
        weave_asked = True

    return {"text": join.join(parts), "blocks_emitted": blocks, "weave_asked": weave_asked,
            "menu_offered": menu_offered, "template_version": _TPL["version"]}
```

`psychoed_continuation.json` (turns-2+ glue; mirrors the shape of `L2_intents/info_request.json` — copy that file's JSON envelope keys exactly, with `template_id: "L2_psychoed_continuation"` and an instruction body that: reads served topics from context, offers the remaining menu topics without re-serving content, presents bridge offers as optional-never-automatic, and never paraphrases block content — block re-serves go through the resolver).

- [ ] **Step 4: Verify pass** (5 tests), **Step 5: Commit** — `git commit -am "feat(psychoed): deterministic turn-1 serve composition + continuation template"` (add files).

---

### Task 8: skill_select integration + graph edge

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (new ordered block at the top of `skill_select_node`, currently line 632), `src/sage_poc/graph.py` (`_route_after_skill_select` lines 347–395 + edge map line 452)
- Test: `tests/test_psychoed_skill_select.py`

**Interfaces:**
- Consumes: `resolver.resolve`, `classifiers.acute_distress`, `weave.evaluate`, `config.psychoed_enabled_for`, `config.PSYCHOED_CATEGORIES`.
- Produces state writes: `psychoed_serve` payload `{"category","block_id","route","framing","weave_due","template_version","matched_row_id","collision_path"}` + `psychoed_active_category`, `psychoed_delivery_shape`, `psychoed_matched_row_id`, `psychoed_collision_path`, `psychoed_framing`, `psychoed_weave_pending` (set True when weave_due), `skill_match_method="psychoed_resolver"`, and on weave escalation `psychoed_weave_escalation=True` → route `"crisis_response"`. Routing: `_route_after_skill_select` returns `"knowledge_retrieve"` when `psychoed_serve` set; `"crisis_response"` when `psychoed_weave_escalation`.

Ordered integration at the TOP of `skill_select_node` (before the info_request bypass at line 649 — this guarantees the resolver wins before Mechanism-A's consult block, the no-double-claim property):

```python
    # --- Psychoed pathway (spec §2.1; flag-gated, default OFF). Order is binding. ---
    if config.PSYCHOED_PATHWAYS_ENABLED:
        from sage_poc.psychoed import resolver as psy_resolver, classifiers as psy_cls, weave as psy_weave

        # (1) PSY-WEAVE-1 precedence: evaluate BEFORE any matching on weave-pending turns.
        if state.get("psychoed_weave_pending"):
            verdict = psy_weave.evaluate(state.get("message_en") or "")
            if verdict == "crisis":
                return {"psychoed_weave_pending": False, "psychoed_weave_escalation": True,
                        "skill_match_method": "psychoed_weave_escalation", "path": ["skill_select"]}
            weave_cleared = True   # clear negative: proceed; menu re-offer handled by continuation
        else:
            weave_cleared = False

        # (2) Active-skill suppression stands.
        if not state.get("active_skill_id"):
            hit = psy_resolver.resolve(
                state.get("message_en") or "",
                active_category=state.get("psychoed_active_category"),
                grief_context=_psychoed_grief_context(state),
                enabled_categories=config.PSYCHOED_CATEGORIES,
            )
            # (3) hit + (4) Classifier A precedence
            if hit and psy_cls.acute_distress(state, state.get("message_en") or ""):
                hit = None   # acute: fall through to coping routes; offer deferred to check-in
            if hit:
                framing = hit["framing"] or psy_cls.FRAMING_FALLBACK
                weave_due = (framing == "personal"
                             and store_manifest_weave(hit["category"])
                             and not state.get("psychoed_weave_fired"))
                payload = {"category": hit["category"], "block_id": hit["block_id"],
                           "route": hit["route"], "framing": framing, "weave_due": weave_due,
                           "matched_row_id": hit["row_id"], "collision_path": hit["collision_path"]}
                return {"psychoed_serve": payload,
                        "psychoed_active_category": hit["category"],
                        "psychoed_delivery_shape": "menu_first" if hit["block_id"] is None else "answer_first",
                        "psychoed_matched_row_id": hit["row_id"],
                        "psychoed_collision_path": hit["collision_path"],
                        "psychoed_framing": framing,
                        "psychoed_weave_pending": bool(weave_due),
                        "psychoed_weave_fired": bool(weave_due) or state.get("psychoed_weave_fired", False),
                        "skill_match_method": "psychoed_resolver", "path": ["skill_select"]}
        if weave_cleared:
            # clear-negative reply, no new trigger: emit the deferred menu via continuation
            return {"psychoed_weave_pending": False, "skill_match_method": "psychoed_menu_after_weave",
                    "path": ["skill_select"]}
```

Helpers added in the same file: `_psychoed_grief_context(state) -> bool` (deterministic: `"grief" in (state.get("clinical_flags") or [])` OR `state.get("psychoed_active_category") == "s2c"` OR recent `grief_loss` in `offered_skill_ids`) and `store_manifest_weave(cat)` (reads `store.manifest(cat)["safety_weave"]`). `psychoed_weave_escalation: bool` becomes a declared channel (add to state.py in this task, keep channel-check green). Graph changes: `_route_after_skill_select` gains, at TOP priority, `if state.get("psychoed_weave_escalation"): return "crisis_response"` and, after the containment check, `if state.get("psychoed_serve") or state.get("skill_match_method") == "psychoed_menu_after_weave": return "knowledge_retrieve"`; edge map at graph.py:452 gains `"crisis_response": "crisis_response"`.

- [ ] **Step 1: Write the failing tests** — construct states per the local-`make_state()` convention (copy the pattern from `tests/test_skill_select.py`), monkeypatching `sage_poc.config.PSYCHOED_PATHWAYS_ENABLED=True` / `PSYCHOED_CATEGORIES=frozenset({"1f","3c"})`:
  - trigger hit → `psychoed_serve` set, `skill_match_method == "psychoed_resolver"`, consult block NOT reached (assert `skill_match_method != "info_request_skill_consult"` even with `primary_intent="info_request"` and a consult-set skill as top match)
  - weave-pending + "kind of" → `psychoed_weave_escalation` True; routing function returns `"crisis_response"`
  - weave-pending + "actually, what is anxiety?" → escalation (precedence BEFORE resolver)
  - weave-pending + "no, nothing like that" → `psychoed_weave_pending` False, method `psychoed_menu_after_weave`, routed to knowledge_retrieve
  - active skill set → resolver never fires (state unchanged on psychoed keys)
  - acute distress co-occurring ("what is anxiety? I can't breathe right now") → no serve, falls through to existing behavior
  - flag OFF → all psychoed keys absent from the node's return
- [ ] **Step 2: Run to verify failures**, **Step 3: implement** (code above + helpers + graph edits), **Step 4: full run** — `uv run pytest tests/test_psychoed_skill_select.py tests/test_psychoed_mechanism_a.py tests/test_skill_select.py -q` → all pass (Mechanism-A suite must stay green), plus `uv run python scripts/check_state_channels.py` → exit 0. **Step 5: Commit** — `git commit -am "feat(psychoed): Node-4 resolver integration, weave precedence, crisis edge"`.

---

### Task 9: Carry-forward (family exposures) — with the seam fix

**Context (binding finding):** `prior_exposure` is dead today — `skill_executor.py:557` counts `therapeutic_profile["techniques_used"]`, a key with NO writer anywhere and no DB column (`postgres_repository.py:16–40`). Phase 2 therefore implements exposure tracking in the declared session channel `psychoed_family_exposures` (Task 3), NOT via the broken profile key. The handoff's evaluation mechanic is preserved: the skip condition counts the family of the skill's `kb_ref` — `exposures.count(family_of(skill.kb_ref)) >= threshold` — never `prior_exposure[skill_id]`. Cross-session remains a declared dependency on the profile repair (do-NOT-wire guardrail respected). The seam finding itself goes back to the controller for the memory relay.

**Files:**
- Modify: `src/sage_poc/nodes/knowledge_retrieve.py` (append family on serve — Task 10 wires serve; the append lands there, this task provides the helper), `src/sage_poc/nodes/skill_executor.py` (family-counter read beside line 557)
- Test: `tests/test_psychoed_carry_forward.py`

**Interfaces:**
- Produces: in `skill_executor.py`, `_psychoed_family_exposure(state, skill) -> int` returning `state.get("psychoed_family_exposures", []).count(family)` where `family = store.family_of_kb_ref(skill.kb_ref)` (0 when the skill has no `kb_ref` — kb_ref additions to skill JSONs are packet-pending, ask 9; mechanism ships first). The existing `prior_exposure` computation at line 557 becomes `prior_exposure = max(techniques_used.count(skill_id), _psychoed_family_exposure(state, skill))` — additive, never lowers the current (always-0) value.

- [ ] **Step 1: Failing test** (fixture skill object with `kb_ref="understanding_anxiety"`; state with `psychoed_family_exposures=["understanding_anxiety"]*3` → `_psychoed_family_exposure` returns 3; skill without kb_ref → 0; integration: `evaluate_step_policy` skips psychoed step when threshold met — reuse the existing step-policy test pattern from `tests/test_skill_executor.py`).
- [ ] **Step 2–4: Red, implement, green** (also verify `uv run pytest tests/test_skill_executor.py -q` unchanged-green).
- [ ] **Step 5: Commit** — `git commit -am "feat(psychoed): family-exposure carry-forward via declared channel (rule-6 kb_ref-family mechanic; profile seam documented)"`

---

### Task 10: knowledge_retrieve — outcome-1 fetch, outcome-2 backstop, L4 quarantine

**Files:**
- Modify: `src/sage_poc/nodes/knowledge_retrieve.py` (node currently lines 24–52)
- Test: `tests/test_psychoed_knowledge_retrieve.py` (new; model on `tests/test_knowledge_retrieve_node.py` fakes)

**Interfaces:**
- Consumes: `psychoed_serve` payload; `store.get_block/block_ids/category_of`; `classifiers.FRAMING_FALLBACK`; manifests.
- Produces state writes: outcome-1 — `knowledge_passages=[]` untouched semantics preserved; adds `psychoed_serve` passthrough (payload enriched with `"content_hash": store.block_sha256(block_id)` when block_id set) and `psychoed_family_exposures` append (`store.manifest(cat)`'s `article_family` — derive via first block) and `psychoed_blocks_served` append. Outcome-2 — when NO `psychoed_serve` but flag ON and top RAG passage's `article_id ∈ store.block_ids()` and not abstained: build a backstop `psychoed_serve` with `category=store.category_of(article_id)`, `framing=FRAMING_FALLBACK` (fail-to-personal), `weave_due` per manifest weave, `route="standard"`, `collision_path="semantic_backstop"`. **L4 quarantine (both outcomes and always when flag ON): strip any passage whose `article_id ∈ store.block_ids()` from `knowledge_passages`** so psychoed copy can never enter LLM synthesis.

Behavior notes: outcome-1 skips the DB entirely (`retrieve()` not called — the store is authoritative and in-process). Outcome-2 only applies on the normal info_request path. Flag OFF → the node body is byte-identical to today (guard the whole addition with `config.PSYCHOED_PATHWAYS_ENABLED`).

- [ ] **Step 1: Failing tests** — (a) serve payload in state → no `repo.retrieve` call (assert via mock), hash present, exposures/blocks_served appended; (b) no payload + fake RAG result whose top passage `article_id="3c-b4"` → backstop payload with `framing="personal"`, `weave_due=True`; (c) quarantine: passages containing a block id are stripped from `knowledge_passages` while non-psychoed passages survive; (d) flag OFF → node output identical to a control run.
- [ ] **Steps 2–4: Red, implement, green** (also `uv run pytest tests/test_knowledge_retrieve_node.py -q` stays green).
- [ ] **Step 5: Commit** — `git commit -am "feat(psychoed): outcome-1 store fetch, outcome-2 fail-to-personal backstop, L4 quarantine"`

---

### Task 11: freeflow serve path + output_gate audit & hash gate + migration

**Files:**
- Modify: `src/sage_poc/nodes/freeflow_respond.py` (early path in node, line 240), `src/sage_poc/nodes/output_gate.py` (audit dict lines 933–969; new gate check near the HR gate call site lines 925–930), `src/sage_poc/audit.py` (`_build_session_audit_row` columns)
- Create: `migrations/016_add_psychoed_to_session_audit.sql`; update `migrations/MIGRATIONS.md` (claim 016; reconcile table through 015)
- Test: `tests/test_psychoed_gate.py`

**Interfaces:**
- freeflow: at the top of `freeflow_respond_node`, when `state.get("psychoed_serve")` → `out = serve.compose_turn1(payload)`; return `{"response_en": out["text"], "psychoed_menu_offered": out["menu_offered"], "psychoed_blocks_served": state.get("psychoed_blocks_served", []), "path": ["freeflow_respond"]}` with NO LLM call; when `skill_match_method == "psychoed_menu_after_weave"` → compose framing-less menu re-offer from the manifest (`menu_offer` verbatim) the same way. Every serve transits output_gate (unlike `_crisis_response_node` — do NOT copy its END-routing).
- output_gate: audit dict gains `psychoed_block_ids` (list), `psychoed_matched_row_id`, `psychoed_collision_path`, `psychoed_framing`, `psychoed_weave_state` (`"fired"/"pending"/"evaluated"/None`), `psychoed_template_version`. **Verbatim hash gate** (behavior-anchored, spec §6.2): when the turn carries a `psychoed_serve` with `block_id`, recompute `store.block_sha256(block_id)` and assert the block's `content` appears verbatim in `final_response`; on mismatch → BLOCK: recompose via `serve.compose_turn1` from the store (re-serve pinned); if the block_id is absent from the store (data corruption) → drop all psychoed copy, emit the normal freeflow path result is impossible post-hoc, so substitute the manifest's `check_in` question alone and log `psychoed_integrity_incident` with both hashes at ERROR. Never emit unverified psychoed copy. (Refinement of spec §6.2's "neutral referral template" recorded here: the store is in-process, fetch-fail ≈ data corruption; the fallback emits only already-pinned manifest copy, never composed text.)
- Migration 016: `ALTER TABLE session_audit ADD COLUMN psychoed_block_ids TEXT[], ADD COLUMN psychoed_matched_row_id TEXT, ADD COLUMN psychoed_collision_path TEXT, ADD COLUMN psychoed_framing TEXT, ADD COLUMN psychoed_weave_state TEXT, ADD COLUMN psychoed_template_version TEXT;` — one-row-per-turn model unchanged.

- [ ] **Step 1: Failing tests** — (a) serve payload → freeflow returns composed text with `make_mock_llm` asserting `.ainvoke` NEVER called; (b) gate pass-through: unaltered serve reaches `response` untouched, audit dict carries all six fields; (c) gate hash-mismatch (tamper `final_response` upstream of the gate in the test) → response replaced by the store recomposition, incident logged (caplog); (d) flag OFF → gate code unreached.
- [ ] **Steps 2–4: Red, implement, green** — plus `uv run pytest tests/test_freeflow_respond.py tests/test_output_gate_audit.py -q` (existing files) stays green.
- [ ] **Step 5: Commit** — `git commit -am "feat(psychoed): no-LLM serve transit, Node-8 audit columns + verbatim hash gate (migration 016)"`

---

### Task 12: Flag-OFF byte-identity + regression pins

**Files:**
- Modify: `tests/test_psychoed_flag_off.py`
- Test: same file

- [ ] **Step 1: Write the tests**
  - **Flag-OFF no-op:** with env unset, run `skill_select_node`, `knowledge_retrieve_node`, `freeflow_respond_node` on representative states (reuse local `make_state()` patterns from their existing test files) and assert their return dicts contain NO `psychoed_*` keys and equal a pre-recorded control (dict equality against the same call before this branch — practically: assert psychoed keys absent + `skill_match_method` values unchanged for the info_request consult case, the post-crisis case, and the two-tier case).
  - **Bare-emotional-words re-pin at the resolver surface** (spec §7.1 F8 seed, unit level): flag ON, `resolver.resolve("I'm stressed"/"I feel depressed"/"I feel sad")` → None (already in Task 6; here repeated THROUGH `skill_select_node` with flag ON to pin the integrated surface).
  - **Mechanism-A coexistence:** flag ON for `{"1f"}` only + info_request "What is grief?" (s2c NOT enabled) → consult path still fires (`info_request_skill_consult`), proving per-category coexistence until flip-time retirement.
- [ ] **Step 2–4: Red where applicable, implement nothing new (fix integration bugs these catch), green:** `uv run pytest tests/ -q -k "psychoed or skill_select or knowledge_retrieve or freeflow or output_gate" ` → all pass; `uv run python scripts/check_state_channels.py` → 0; full unit gate locally: `uv run pytest tests/test_psychoed_content_integrity.py -q` → 138 passed (untouched).
- [ ] **Step 5: Commit** — `git commit -am "test(psychoed): flag-OFF byte-identity, bare-affect re-pin, Mechanism-A coexistence"`

---

### Task 13: Graph test + docs

**Files:**
- Modify: `tests/test_graph.py` (or new `tests/test_psychoed_graph.py` following its pattern), `docs/superpowers/plans/2026-07-28-psychoed-phase2-handoff-notes.md` (append an "as-built" section)

- [ ] **Step 1:** Graph-level test (mocked LLM + no-DB fixture pattern from `tests/conftest.py::asgi_client`): flag ON `{"3c"}`, one full `app.ainvoke` turn with "Why do I feel numb?" → response text contains the 3c framing + 3c-b4 content + weave question, no menu; state carries `psychoed_weave_pending=True`; audit log dict (captured via caplog or the audit task patch pattern used in `tests/test_output_gate_audit.py`) carries `psychoed_matched_row_id="3c-t3"`. Second turn "kind of" → routed to `crisis_response` (assert `psychoed_weave_escalation` and the crisis card path fired).
- [ ] **Step 2:** Append to the handoff notes: the as-built deltas — `psychoed_family_exposures` channel (replaces the dead `techniques_used` read; seam finding), `psychoed_weave_escalation` channel + the one edge-map addition, the §6.2 fallback refinement (manifest `check_in` substitute, rationale), and the Mechanism-A coexistence semantics (per-category, retirement still flip-time).
- [ ] **Step 3:** Full suite: `uv run pytest tests/ -q -k "psychoed"` all green; `uv run pytest tests/test_graph.py -q` green. **Step 4: Commit** — `git commit -am "test(psychoed): full-graph serve + weave-escalation test; as-built handoff deltas"`

---

## Self-Review (performed at write time)

- **Spec coverage:** §2.1 order → Task 8 (steps 1–5 explicit, PSY-WEAVE-1 precedence first, active-skill guard, Classifier A, consult-block precedence); §2.2 outcome-2 + category-from-metadata + fail-to-personal → Task 10; §2.3 precedence-by-topology → untouched upstream nodes + Task 13 graph test; §3 content model → consumed read-only via Task 2 store; §4.1 compositions incl. weave turn-boundary + diagnosis guard → Task 7; §4.2 channels/lifetimes/audit-before-clear → Tasks 3, 11 (audit fields), pathway-clear on exit is exercised by the crisis-escalation graph test; §4.3 menu scoping/loop-back → Task 6 resolver + continuation template (Task 7); §4.4 carry-forward → Task 9 (with the seam finding and the channel substitution documented); §5.1–§5.2 → Task 6 (collision winners, never-similarity); §5.3–§5.4 → Task 5; §5.5 row split → Tasks 6–7 (`direct_diagnostic` rows flow answer-first by data — their `route` is `direct_diagnostic` and `serve.compose_turn1` treats only `formal_diagnosis` specially, which matches the ruling); §6.1 → Tasks 4, 8; §6.2 → Task 11; §6.4 CI → channel check green each task. Known deliberate exclusions: guard-script stage-2 (push-further) and the consented yes-branch are turns-2+ behaviors carried by the continuation template + resolver re-entry — their conformance fixtures are Phase 3 F10; scripted-clarify collision mechanism (spec §5.2 mechanism b) is not wired because no declared collision currently uses it (the pending entry uses interim default) — flagged in Task 13's as-built notes.
- **Placeholder scan:** clean — every code step carries the code; Task 7's continuation-template body is specified by contract with its envelope source named (`L2_intents/info_request.json`).
- **Type consistency:** `psychoed_serve` payload keys identical across Tasks 8/10/11 (`category, block_id, route, framing, weave_due, matched_row_id, collision_path`, + `content_hash` added in Task 10); `store` function names identical across Tasks 2/6/7/9/10/11; flag names identical across Tasks 1/8/10/11/12.
