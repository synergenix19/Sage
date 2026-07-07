# Make V2 Semantic Routing Live — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the already-built, already-gate-passed, already-once-deployed V2 semantic router (bi-encoder-with-exemplars → fp32 cross-encoder → global-τ route-or-ABSTAIN) from its stranded branch into production, correctly and durably, closing the three conditions the product owner set.

**Architecture:** V2 is NOT a rebuild. The reranker is wired via `skill_select._route_decision → _rerank_route → skill_rerank_model.score_pairs`, gated by env flags (`SKILL_ROUTING_V2` = exemplar/debias bi-encoder candidate set; `SKILL_RERANK_ENABLED` = cross-encoder selector + global-τ ABSTAIN). Flag-off is byte-identical V1 (CI-locked). The work is: reconcile the branch onto current master, close the gaps (ABSTAIN→Node 3 routing, **per-language fail-closed** so an uncalibrated language never loses its V1 abstain, keep anchors out), harden the deploy so a master `railway up` can't silently revert it again, then flip flags on for **English only** and measure V1→V2 in prod. **Arabic is decoupled by a deterministic code guarantee, not a runbook note:** Arabic ships on V2 only once its τ is calibrated (a separate follow-up plan, gated on native-review sign-off); until then every Arabic turn fails closed to the V1 path.

**Tech Stack:** Python 3.11 / LangGraph / BGE-M3 bi-encoder + `BAAI/bge-reranker-v2-m3` cross-encoder (fp32, revision-pinned) / pytest / Railway (manual `railway up`) / the `src/sage_poc/routing_eval` gate harness.

## Global Constraints

- **Cardinal Rule 5 (rules-first):** keyword Tier-1 evaluates before the reranker; the reranker is the semantic-fallback selector; a below-τ result is an explicit ABSTAIN that routes to Node 3 `low_confidence_respond` — never a silent no-op. Acceptance criterion on the wiring PR.
- **fp32 only in prod.** int8 is SAFETY-DISQUALIFIED (6/6 id_oos over-routes vs fp32). `SKILL_RERANK_PRECISION` must be unset/`fp32` on prod & staging. int8 stays selectable for latency probing ONLY.
- **Flag-off == V1 byte-identical**, CI-locked. Any change to the flag-off path is a regression and must fail CI.
- **Per-language fail-closed (deterministic guardrail).** The V2 reranker path is taken ONLY when `SKILL_RERANK_ENABLED=1` AND `_rerank_tau(lang)` is finite. A language with no calibrated τ takes the V1 decision path (its own threshold-gated ABSTAIN preserved) — NEVER the reranker at τ=−inf (which routes top-1 with no ABSTAIN). An uncalibrated gate fails closed, not open (Node 4 discipline).
- **Per-turn routing audit.** The skill_select audit row records the routing mode actually taken (`v2_reranked` / `v2_abstained` / `v1_fallback_uncalibrated_lang` / `v1`), the reranker revision, the τ used, and the score — so a fail-closed turn is never indistinguishable from a fired reranker (the same misreporting class Task 1 kills).
- **Reranker revision pinned** to `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (the exact snapshot every gate number was measured on). Do not float the revision.
- **`semantic_anchors` stays empty** in this PR. Populating it is a separate track gated on the passive-SI regression suite, per-skill, non-blanket (0/31 bleed into passive-SI). No anchor edits ride along here.
- **Arabic ABSTAIN is blocking for the bilingual pilot.** An uncalibrated AR-τ (`-inf`) routes top-1 with no ABSTAIN gate — do not declare the bilingual safety gate met until AR-τ is calibrated from native-reviewed cells.
- **No secrets in the repo.** Railway env is set via CLI, never committed.
- Master tip at planning time: `1209207` (PR #116). V2 branch: `reconcile/v2-onto-db8eb39` (94 ahead / 143 behind master).

---

## File Structure

- `src/sage_poc/nodes/skill_select.py` — the router. Holds `_route_decision`, `_rerank_route` (L261), `_keyword_rerank_veto` (L286), `_rerank_tau`/`_load_rerank_calibration` (L238–258), the ABSTAIN return (L357/L283). Modified in Task 6 (emit an ABSTAIN reason) and Task 7 (AR-τ).
- `src/sage_poc/graph.py` — `_route_after_skill_select` (L228–241) + skill_select conditional-edge map (L282–285). Modified in Task 6 (route ABSTAIN → `low_confidence`).
- `src/sage_poc/nodes/skill_rerank_model.py` — fp32 cross-encoder; `score_pairs`, `head_loaded_ok`, `active_precision`, pinned `_REVISION`. Read-only reference; consumed by Task 9.
- `src/sage_poc/nodes/rerank_calibration.json` — `{rerank_tau: {en: -6.0843}}`. AR key ADDED in Task 7.
- `src/sage_poc/server.py` — `/health/ready`. Modified in Task 1 (truthful routing-mode field) and Task 9 (live-path reranker-fired positive control) and Task 10 (deploy SHA).
- `src/sage_poc/routing_eval/` — gate harness (`gate_runner.py`, `calibration.py`, `cross_validation.py`, `baseline.py`, `fixtures.py`). Consumed by Tasks 2, 5, 7, 12.
- `tests/routing_eval/`, `tests/test_nodes.py`, `tests/test_graph_routing.py` — test homes.
- `docs/superpowers/plans/`, `docs/superpowers/governance/` — this plan + deploy runbook + sign-off records.

---

## Phase 0 — Truth & baseline (no V2 code; lands on master immediately)

### Task 1: Stop the flags lying + a truthful routing-mode health field

**Problem:** prod & staging run pure-V1 master, but `SKILL_ROUTING_V2=1`/`SKILL_RERANK_ENABLED=1` are set — an audit-trail integrity violation (env advertises a reranker the code doesn't run).

**Files:**
- Modify: `src/sage_poc/server.py` (`/health/ready` handler)
- Test: `tests/test_health_ready.py`

**Interfaces:**
- Produces: `/health/ready` JSON gains `"routing_mode": "v1" | "v2"` derived from **actual code capability**, not the raw env flag.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_health_ready.py
import os
from sage_poc.nodes.skill_select import _rerank_enabled

def test_routing_mode_reflects_code_capability(monkeypatch):
    # Flag set but if the code path doesn't exist/enabled, mode must not claim v2.
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    # routing_mode is "v2" only when the reranker path is actually reachable
    from sage_poc.server import compute_routing_mode
    assert compute_routing_mode() == ("v2" if _rerank_enabled() else "v1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc && uv run pytest tests/test_health_ready.py -v`
Expected: FAIL — `compute_routing_mode` not defined.

- [ ] **Step 3: Add the helper + wire into `/health/ready`**

```python
# server.py
def compute_routing_mode() -> str:
    """Truthful routing mode: 'v2' only if the reranker selector path is reachable AND enabled."""
    try:
        from sage_poc.nodes.skill_select import _rerank_enabled  # absent on pure-V1 master
    except ImportError:
        return "v1"
    return "v2" if _rerank_enabled() else "v1"
```
Add `"routing_mode": compute_routing_mode()` to the `/health/ready` payload.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_health_ready.py -v` → Expected: PASS.

- [ ] **Step 5: Set the running envs to the truth (ops, not code)**

Because master has no reranker path, set the inert flags to `0` on BOTH environments so nothing advertises a non-running reranker until V2 actually ships:

```bash
railway variables --service sage-api --environment production --set SKILL_ROUTING_V2=0 --set SKILL_RERANK_ENABLED=0
railway variables --service sage-api-staging --set SKILL_ROUTING_V2=0 --set SKILL_RERANK_ENABLED=0
```
Verify: `curl -s https://sage-api-production-3328.up.railway.app/health/ready` → `routing_mode` present (bare `{"status":"ready"}` = old build still live; redeploy needed to surface the field, acceptable — the env truth is corrected regardless).

- [ ] **Step 6: Commit**

```bash
git add tests/test_health_ready.py src/sage_poc/server.py
git commit -m "observability: truthful routing_mode on /health/ready; de-advertise inert V2 flags"
```

### Task 2: Freeze the V1 pre-wire prod comparator

**Why:** per the owner's sequencing correction, the "frozen baseline now" is the V1 snapshot that becomes the V1→V2 prod comparator (Task 12) and shakes out the harness. There is already a `2026-07-07-routing-baseline-11-failures.md` (pure-V1); this task pins it as the comparator artifact.

**Files:**
- Create: `docs/superpowers/governance/2026-07-07-v1-prewire-baseline-frozen.md`
- Use: `src/sage_poc/routing_eval/baseline.py`, the EN gate fixtures.

- [ ] **Step 1: Run the V1 baseline with the harness, FLAGS-OFF, on the V2 tree**

Note (corrected 2026-07-07): `routing_eval` does not exist on master — it ships with V2. Measure the V1 comparator with the *same* instrument by running it flags-off (flags-off == V1 byte-identical), from the V2 worktree, so V1 and V2 (Task 5) are apples-to-apples:

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc-phase0 && SKILL_ROUTING_V2=0 SKILL_RERANK_ENABLED=0 uv run python -m sage_poc.routing_eval.baseline --lang en --emit json > /tmp/v1_prewire_en.json`
Expected: per-stratum numbers (in_scope / id_oos / far_oos) near the known ~66% / 35% / 100% V1 profile. Label this "phase0-base V1"; the authoritative comparator is re-captured on the reconciled tree by the Task 5 flip gate (V1 and V2 on one tree).

- [ ] **Step 2: Record the frozen artifact**

Write `2026-07-07-v1-prewire-baseline-frozen.md` embedding the JSON, the fixture-set SHA, master SHA `1209207`, and the sentence: *"This is the V1 comparator for the V1→V2 prod measurement (Task 12). Do not re-measure V1 after V2 flags flip."*

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/governance/2026-07-07-v1-prewire-baseline-frozen.md
git commit -m "governance: freeze V1 pre-wire routing baseline as V1->V2 comparator"
```

---

## Phase 1 — Reconcile V2 onto current master

### Task 3: Reconcile `reconcile/v2-onto-db8eb39` onto master tip

**Context:** the branch is 143 behind master. A prior reconcile onto an older master (`408e8fe`) re-gated PASS — precedent exists. This redoes it against `1209207`.

**Files:** whole tree (183 files diverge). No app-logic changes here — conflict resolution only.

- [ ] **Step 1: Create a fresh integration branch off current origin/master (never a stale local ref)**

```bash
git -C /Users/knowledgebase/Documents/Sage/sage-poc fetch origin
git -C /Users/knowledgebase/Documents/Sage/sage-poc worktree add ../sage-poc-v2live -b feat/v2-live-reconcile origin/master
```

- [ ] **Step 2: Merge the V2 tree in, resolving conflicts toward master for infra and toward V2 for the routing core**

```bash
git -C ../sage-poc-v2live merge --no-ff origin/reconcile/v2-onto-db8eb39
```
Resolution rule: `src/sage_poc/nodes/skill_select.py`, `skill_rerank*.py`, `rerank_calibration.json`, `routing_eval/**` → take V2. Everything master shipped since (KB abstain gate, source cards, mm header, cosine-abstain `SAGE_COSINE_ABSTAIN_THRESHOLD`, migrations) → keep master. Where both touched a file, hand-merge.

- [ ] **Step 3: Verify it builds and imports**

Run: `uv run python -c "import sage_poc.graph, sage_poc.nodes.skill_select, sage_poc.nodes.skill_rerank_model"`
Expected: no ImportError.

- [ ] **Step 4: Commit the reconcile**

```bash
git -C ../sage-poc-v2live add -A
git -C ../sage-poc-v2live commit -m "reconcile: V2 semantic router onto master 1209207 (routing core=V2, infra=master)"
```

### Task 4: Prove flag-off == V1 byte-identical on the reconciled tree

**Files:** existing CI-locked test (from V2 commit "flag-off==V1 byte-identical proof, CI-locked").

- [ ] **Step 1: Run the byte-identical guard with flags OFF**

Run: `cd ../sage-poc-v2live && SKILL_ROUTING_V2=0 SKILL_RERANK_ENABLED=0 uv run pytest -k "byte_identical or flag_off_v1" -v`
Expected: PASS — flag-off routing decisions equal master V1 exactly.

- [ ] **Step 2: If it fails, the reconcile leaked a V2 default into the flag-off path — fix and re-run before proceeding.** Do not continue with a failing byte-identical guard.

- [ ] **Step 3: Commit any fix**

```bash
git -C ../sage-poc-v2live commit -am "fix(reconcile): restore flag-off==V1 byte-identical after master merge"
```

### Task 5: Re-gate EN on the reconciled tree

- [ ] **Step 1: Run the §5 flip gate (V2-vs-V1, per-stratum) on the reconciled tree**

Run: `SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 uv run python -m sage_poc.routing_eval.gate_runner --lang en`
Expected: clean per-stratum win, no cell below V1 — in_scope ≈60 (TIE), id_oos ≈86 (WIN, +45pp), far_oos 100 (TIE). Any cell below V1 is a STOP.

- [ ] **Step 2: Record the re-gate result**

Append the numbers + reconciled-tree SHA to `docs/superpowers/governance/2026-07-07-v2-live-regate.md`. Commit.

---

## Phase 2 — The three owner conditions

### Task 6 (Condition 1): Route V2 ABSTAIN → `low_confidence_respond` (Node 3), not freeflow

**Problem (verified):** `_rerank_route`/`_route_decision` return `(None, score, None)` on a below-τ ABSTAIN (`skill_select.py:283,357`), and `graph._route_after_skill_select` (L228–241) returns `"freeflow"` for a no-skill result. So a V2 ABSTAIN currently lands in `freeflow_respond`, violating Cardinal Rule 5 which requires Node 3.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (set an explicit reason on the state when the V2 reranker ABSTAINs)
- Modify: `src/sage_poc/graph.py` (`_route_after_skill_select` + skill_select conditional-edge map L282–285)
- Test: `tests/test_graph_routing.py`

**Interfaces:**
- Produces: state key `skill_select_abstained: bool` — True only when the reranker gate (`_rerank_route` or `_keyword_rerank_veto`) fired an ABSTAIN under `SKILL_RERANK_ENABLED`. `_route_after_skill_select` returns `"low_confidence"` when it is True, else its existing behavior (unchanged flag-off).

- [ ] **Step 1: Write the failing behavior test**

```python
# tests/test_graph_routing.py
import pytest

@pytest.mark.slow
def test_v2_abstain_routes_to_low_confidence(run_turn_v2):
    # An id_oos clinician-territory disclosure the reranker ABSTAINS on must reach Node 3,
    # not freeflow. run_turn_v2 runs the graph with SKILL_ROUTING_V2/SKILL_RERANK_ENABLED on.
    state = run_turn_v2("I keep needing to check the stove exactly seven times or something bad happens")
    assert state["node_path"][-1] == "low_confidence_respond"
    assert state["node_path"][-1] != "freeflow_respond"

@pytest.mark.slow
def test_flag_off_abstain_still_freeflow(run_turn_v1):
    # Byte-identical guard: with flags off, the no-match path is unchanged (freeflow).
    state = run_turn_v1("what time does the grocery store close today")
    assert state["node_path"][-1] == "freeflow_respond"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ../sage-poc-v2live && uv run pytest tests/test_graph_routing.py -k abstain -m slow -v`
Expected: FAIL — first test lands in `freeflow_respond`.

- [ ] **Step 3: Set the ABSTAIN reason in skill_select**

In the skill_select node body, where the `_route_decision` result is consumed, when the result is an ABSTAIN (`best is None`) AND `_rerank_enabled()` is True, set `state["skill_select_abstained"] = True`. (Flag-off ABSTAIN leaves it unset → preserves V1 freeflow.)

- [ ] **Step 4: Route it in graph.py**

```python
# graph.py _route_after_skill_select (around L228)
def _route_after_skill_select(state):
    if state.get("skill_select_abstained"):
        return "low_confidence"
    ...  # existing logic unchanged
    return "freeflow"
```
Add `"low_confidence": "low_confidence_respond"` to the skill_select conditional-edge map (L282–285) if absent (Node 3 node + its edge to `output_gate` already exist, L256/L277/L280).

- [ ] **Step 5: Run tests to verify both pass**

Run: `uv run pytest tests/test_graph_routing.py -k abstain -m slow -v` → Expected: PASS (both).
Then re-run the byte-identical guard (Task 4 Step 1) → Expected: still PASS.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat(routing): V2 reranker ABSTAIN routes to Node 3 low_confidence_respond (Cardinal Rule 5)"
```

### Task 6b (Condition 2, made real): Per-language fail-closed gate

**Problem (verified):** the flags are global. `_route_decision` (`skill_select.py:328`) takes the reranker path on `_rerank_enabled()` alone, and `_rerank_route` gates on `top_rr >= _rerank_tau(lang)` (L281). For AR, `_rerank_tau('ar')` = −inf → every AR turn routes top-1 with **no ABSTAIN**, removing the abstain V1 gives Arabic. Shipping EN-V2 with global flags therefore silently regresses AR safety unless the reranker is gated per-language. This is what actually makes the EN decouple safe (and makes Task 7 severable).

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (`_route_decision` L328 gate + the `_keyword_rerank_veto` call site)
- Test: `tests/test_graph_routing.py`

**Interfaces:**
- Produces: both reranker call sites (`_rerank_route` via `_route_decision`, and `_keyword_rerank_veto`) are entered ONLY when `_rerank_enabled() and math.isfinite(_rerank_tau(lang))`. An uncalibrated language falls through to the V1 decision path (cluster-argmax + absolute threshold gate + ABSTAIN, L331–357) exactly as flag-off.

- [ ] **Step 1: Write the failing test pair**

```python
# tests/test_graph_routing.py
import pytest

@pytest.mark.slow
def test_ar_fails_closed_to_v1_under_flags_on(run_turn_v2, route_v1):
    # AR clinician-territory disclosure, flags ON: decision must equal V1 (no top-1 over-route
    # through the reranker). route_v1 returns the flag-off V1 routing decision for the same input.
    msg = "أحتاج أتأكد من القفل عشر مرات وإلا يصير شي سيّئ"  # OCD-type checking, id_oos
    v2 = run_turn_v2(msg, lang="ar")
    assert v2["routing_decision"] == route_v1(msg, lang="ar")
    assert v2["routing_mode_taken"] == "v1_fallback_uncalibrated_lang"

@pytest.mark.slow
def test_en_reranker_still_fires_under_flags_on(run_turn_v2):
    # EN (calibrated τ): reranker must fire. Reuses Task 9's invocation counter.
    from sage_poc.nodes import skill_rerank_model as m
    before = m.invocation_count()
    run_turn_v2("my chest is tight and my heart is racing", lang="en")
    assert m.invocation_count() > before
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ../sage-poc-v2live && uv run pytest tests/test_graph_routing.py -k fails_closed -m slow -v`
Expected: FAIL — AR turn currently routes top-1 through the reranker.

- [ ] **Step 3: Gate both reranker call sites on a finite τ**

```python
# skill_select.py — top of file
import math
# in _route_decision (was: `if _rerank_enabled():`)
if _rerank_enabled() and math.isfinite(_rerank_tau(lang)):
    return _rerank_route(ranked, lang, message_en, _runner_up)
# guard the keyword veto identically at its call site:
if _rerank_enabled() and math.isfinite(_rerank_tau(lang)) and _keyword_rerank_veto(candidates, message_en, lang):
    ...  # existing veto handling
```
**Implementation note:** if the AR decision still diverges from V1 because the `include_exemplars` candidate pool (global, `SKILL_ROUTING_V2`) shifts AR bi-encoder scores, gate exemplar participation per-language too so an uncalibrated language scores on the V1 pool. The `test_ar_fails_closed_to_v1` assertion is the contract — it fails if any divergence remains.

- [ ] **Step 4: Run to verify both pass, then re-run the byte-identical guard**

Run: `uv run pytest tests/test_graph_routing.py -k "fails_closed or reranker_still_fires" -m slow -v` → Expected: PASS (both).
Run the Task 4 byte-identical guard → Expected: still PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(routing): per-language fail-closed — uncalibrated lang takes V1 path, never reranker at tau=-inf"
```

### Task 6c (audit trail): Log the routing mode actually taken

**Why:** an AR turn silently taking the V1 fallback must not be indistinguishable from a fired reranker in the audit — the same misreporting class Task 1 exists to kill.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (audit-record assembly at the decision site)
- Test: `tests/test_nodes.py`

**Interfaces:**
- Produces: skill_select audit fields — `routing_mode_taken` ∈ {`"v2_reranked"`, `"v2_abstained"`, `"v1_fallback_uncalibrated_lang"`, `"v1"`}, `reranker_revision` (from `skill_rerank_model._REVISION`), `rerank_tau_used` (float or `null`), `rerank_score` (float or `null`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_nodes.py
import pytest

@pytest.mark.slow
@pytest.mark.parametrize("msg,lang,expected", [
    ("my chest is tight and my heart is racing", "en", "v2_reranked"),
    ("what time does the grocery store close today", "en", "v2_abstained"),
    ("أحتاج أتأكد من القفل عشر مرات", "ar", "v1_fallback_uncalibrated_lang"),
])
def test_audit_records_routing_mode(run_turn_v2, msg, lang, expected):
    state = run_turn_v2(msg, lang=lang)
    assert state["session_audit"]["routing_mode_taken"] == expected
    assert state["session_audit"]["reranker_revision"]  # non-empty
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_nodes.py -k audit_records_routing_mode -m slow -v`
Expected: FAIL — field absent.

- [ ] **Step 3: Set the fields at the decision site**

At each terminal branch of the skill_select decision, set `routing_mode_taken` accordingly (reranked route / below-τ ABSTAIN / uncalibrated-lang fallback / flag-off V1), plus `reranker_revision = skill_rerank_model._REVISION`, `rerank_tau_used`, `rerank_score`. Include them in the persisted `session_audit` row.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_nodes.py -k audit_records_routing_mode -m slow -v` → Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(audit): record per-turn routing_mode_taken + reranker revision/tau/score in skill_select audit"
```

### Task 7 (Condition 2, Arabic τ) — MOVED to a separate follow-up plan

Arabic reranker-τ calibration is **out of scope for this EN deploy** and lives in `docs/superpowers/plans/2026-07-07-arabic-reranker-tau-followup.md`, gated on the native Khaleeji review sign-off (Lane 3 clinician clock). Its "BLOCKING" label is correct for the **bilingual pilot**, not for this deploy — Task 6b makes AR fail closed to V1 without it. The `test_ar_tau_present_and_gates_abstain` test lives in that follow-up PR, not this one.

### Task 8 (Condition 3): Guard that `semantic_anchors` stays empty in this PR

**Why:** the paraphrase robustness ships via `include_exemplars` (target_presentations as exemplar vectors), NOT anchors. Populating anchors bleeds into passive-SI (0/31) and is a separate, safety-gated track. This task is a *guard*, not a populate.

**Files:**
- Test: `tests/routing_eval/test_no_anchors_in_v2_pr.py`

- [ ] **Step 1: Write the guard test**

```python
# tests/routing_eval/test_no_anchors_in_v2_pr.py
import json, glob
def test_all_skills_have_empty_semantic_anchors():
    for p in glob.glob("src/sage_poc/skills/*.json"):
        data = json.load(open(p))
        assert not data.get("semantic_anchors"), f"{p} added anchors — belongs to the passive-SI-gated track, not this PR"
```

- [ ] **Step 2: Run to verify it passes now (all empty) and fails if anyone adds anchors**

Run: `uv run pytest tests/routing_eval/test_no_anchors_in_v2_pr.py -v` → Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/routing_eval/test_no_anchors_in_v2_pr.py
git commit -m "test: guard semantic_anchors stays empty in the V2-live PR (anchors are a separate passive-SI-gated track)"
```

---

## Phase 3 — Deploy hardening + live-path positive control

### Task 9: Live-path positive control — prove the reranker actually FIRES, not just loads

**Problem:** `head_loaded_ok()` proves the model *loads* and separates logits at startup. It does NOT prove the routing path *invokes* it. The whole "V2 deployed but behaved like V1" failure mode is a loaded-but-not-fired reranker. Add a control that fails readiness if a known route does not pass through `score_pairs`.

**Files:**
- Modify: `src/sage_poc/server.py` (`/health/ready`)
- Modify/Read: `src/sage_poc/nodes/skill_rerank_model.py` (expose an invocation counter)
- Test: `tests/test_health_ready.py`

**Interfaces:**
- Produces: `/health/ready` field `"reranker_fired": bool` — True only after a canary route has provably called `score_pairs` under flag-on.

- [ ] **Step 1: Write the failing test**

```python
def test_reranker_fires_on_canary_route(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1"); monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    from sage_poc.nodes import skill_rerank_model as m
    from sage_poc.nodes.skill_select import _route_decision
    before = m.invocation_count()
    _route_decision([("box_breathing", 0.61), ("grounding_5_4_3_2_1", 0.60)], "en", "my chest is tight and my heart is racing")
    assert m.invocation_count() > before
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_health_ready.py::test_reranker_fires_on_canary_route -v`
Expected: FAIL — `invocation_count` not defined.

- [ ] **Step 3: Add a module-level invocation counter to `score_pairs` and expose `invocation_count()`; gate `/health/ready` "reranker_fired" on a startup canary route under flag-on.**

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_health_ready.py -v` → Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -am "feat(health): live-path positive control — readiness requires the reranker to have fired on a canary route"
```

### Task 10: Deploy-provenance — make the deployed tree knowable and un-silently-revertible

**Problem:** `railway up` ships a local working tree with no SHA anywhere; a master `railway up` silently reverted V2 once, and on 2026-07-07 an unpinned deploy put clinically-unsigned `mindfulness_meditation` live in prod (see `2026-07-07-mm-registration-live-in-prod-escalation.md`). Make the deployed tree knowable and gate on it.

**Existing mechanism (reuse, do not duplicate):** master already exposes `build_sha` on **`/health/version`** (API-key gated) from the `SAGE_BUILD_SHA` env (`server.py`). Task 10 sets `SAGE_BUILD_SHA` on every deploy rather than adding a second field. Task 1 added `routing_mode` to `/health/ready`.

**Files:**
- Modify: `docs/superpowers/governance/2026-07-07-v2-deploy-runbook.md` (create), the Railway deploy env.

- [ ] **Step 1: Pin provenance on every deploy**

Set `SAGE_BUILD_SHA=<exact git SHA of the deployed tree>` as a Railway var on each `railway up`. `/health/version` then reports the running SHA (converting "unknown" → a knowable anchor). No code change — the field already exists.

- [ ] **Step 2: Write the runbook with the anti-revert rule + governance rules**

The runbook states, verbatim:
1. **Prod deploys pin to a named, audited SHA — never a branch tip.** `railway up` from a checkout at that SHA; record it.
2. **Two-endpoint hard gate before declaring a deploy good:** `/health/version` `build_sha` == the intended SHA, AND `/health/ready` `routing_mode` == the intended mode (and, once V2 ships, `reranker_fired: true`). The anti-revert check cannot half-pass — both endpoints, named explicitly.
3. **Clinically-unsigned skill content ships inert** (unregistered or flag-gated) until sign-off. "Merged to master" ≠ "routable in prod." Cite the 2026-07-07 mm incident.
4. Include the exact `railway up` command, the env-var sets, and the curl gate.

- [ ] **Step 3: Verify + commit**

Run: `curl -s <staging>/health/ready | jq '.deployed_sha, .routing_mode, .reranker_fired'` (after staging deploy in Task 11).

```bash
git add src/sage_poc/server.py docs/superpowers/governance/2026-07-07-v2-deploy-runbook.md
git commit -m "ops: surface deployed_sha on /health/ready + V2 deploy runbook with anti-revert health gate"
```

### Task 11: Staged deploy — staging → hard gate → prod

**Precondition:** Tasks 4, 5, 6, 6b, 6c, 8, 9, 10 green. AR-τ calibration is the separate follow-up plan and is **NOT** a precondition — Task 6b makes AR fail closed to V1 without it. Runbook states: **EN on V2, AR fail-closed to V1 (bilingual gate NOT met).**

- [ ] **Step 1: Deploy to staging with flags on**

```bash
cd ../sage-poc-v2live && railway up --service sage-api-staging
railway variables --service sage-api-staging --set SKILL_ROUTING_V2=1 --set SKILL_RERANK_ENABLED=1 --set SKILL_RERANK_PRECISION=fp32
```

- [ ] **Step 2: Hard health gate**

Run: `curl -s <staging>/health/ready | jq` → Expected: `status=ready`, `routing_mode=v2`, `reranker_head_control` passed, `reranker_fired=true`, `deployed_sha` == reconcile tree SHA. Any miss → STOP.

- [ ] **Step 3: Staging functional + latency check**

Run the EN gate against staging + a latency probe. Expected: id_oos win reproduced live; fp32 batch-1 p95 < 9.6s.

- [ ] **Step 4: Deploy to prod (same tree, same flags), then re-run the hard health gate against prod.**

```bash
railway up --service sage-api --environment production
railway variables --service sage-api --environment production --set SKILL_ROUTING_V2=1 --set SKILL_RERANK_ENABLED=1 --set SKILL_RERANK_PRECISION=fp32
```
Gate: prod `/health/ready` shows `routing_mode=v2`, `reranker_fired=true`, matching `deployed_sha`.

- [ ] **Step 5: Record the deploy** in the runbook (SHAs, timestamps, gate outputs). Commit.

---

## Phase 4 — Prove the win in prod

### Task 12: Measure V1→V2 in production against the frozen comparator

- [ ] **Step 1: Run the prod routing measurement** (the same fixture set as Task 2's frozen V1 baseline) against prod now on V2.

Run: `uv run python -m sage_poc.routing_eval.gate_runner --target prod --lang en`
Expected: id_oos over-route rate drops to the ~86 level measured offline; in_scope/far_oos not below the frozen V1 comparator.

- [ ] **Step 2: Record the realized V1→V2 prod delta** in `2026-07-07-v2-live-regate.md`. This is the artifact that closes "measure the baseline difference between V1 and V2" (English). Commit.

_(AR prod measurement moves to the Arabic follow-up plan, run after AR-τ ships.)_

---

## Downstream (OUT OF SCOPE of this plan — do not start here)

The bot-behaviour conformance audit (Layer 1 routing / Layer 2 flow fidelity / Layer 3 delivery) runs **after** V2 is live, on the improved matcher, with the spec's 600+ trigger phrases as the held-out generalization set for Layer 1. It gets its own plan.

---

## Self-Review

**Spec coverage vs the owner's decision + conditions (amended 2026-07-07 for the EN decouple):**
- Goal "make V2 live (EN)" → Phases 1–4. ✔
- Condition 1 (rules-first + ABSTAIN→Node 3, explicit acceptance criterion) → Global Constraints + Task 6. ✔
- Condition 2 (AR safety) → **converted from a runbook caveat to a deterministic guarantee: Task 6b per-language fail-closed** (uncalibrated lang → V1 path, never reranker at τ=−inf) + Task 6c audit of the mode taken. AR-τ calibration itself is the severed follow-up plan (native-review-gated), not a precondition of this deploy. ✔
- Condition 3 (anchors held behind passive-SI gate, non-blanket) → Global Constraints + Task 8 guard. ✔
- Sequencing correction (flags-truth immediate; V1 pre-wire snapshot = comparator; audit downstream) → Task 1, Task 2, Downstream. ✔
- fp32-only / int8-disqualified → Global Constraints + Task 11 precision pin. ✔
- The reversion root cause (no SHA / silent overwrite) → Task 10. ✔
- The loaded-but-not-fired failure mode → Task 9. ✔
- Misreporting-class defense extended to per-turn routing mode → Task 6c audit fields. ✔

**Placeholder scan:** no "TBD"/"handle edge cases" — each code task carries real test + impl; process tasks carry exact commands + expected output. Two tasks (3, 7) legitimately depend on external state (merge conflicts, native-review sign-off) and are written as gated STOPs rather than fabricated code — that is correct, not a placeholder.

**Type consistency:** `skill_select_abstained` (Task 6) is the single new state key, produced in skill_select, consumed in graph.py — names match. `routing_mode`/`reranker_fired`/`deployed_sha` (Tasks 1/9/10) are distinct `/health/ready` fields, no collision. `_rerank_tau`/`_load_rerank_calibration` referenced in Task 7 match `skill_select.py:238–258`.

**Open assumption to confirm at execution:** the exact skill_select node line where `state["skill_select_abstained"]` is set (Task 6 Step 3) — the router *decision* functions are verified (L261–357) but the node's state-assembly site was not read line-by-line; the behavior test (Task 6 Step 1) pins the requirement regardless of the internal site.
