# R1 — Acute Anchor-Space Regression (TIPP displacement) + fail-closed SG-2 gate (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> ## ⛔ WITHDRAWN 2026-07-14 — both premises false on master; DO NOT EXECUTE
> Re-baselined against `origin/master` `52cba81` (the original verification used prod `43b9b62`, 64 commits stale). **(1)** The "TIPP → box_breathing at ei=8" displacement **does not exist** — §1c High-anxiety routes to grounding/abstain, never box_breathing/dbt_tipp (v2 fixtures `0a58a7d` + warmed master run). The box_breathing routing is §3d **venting** (F6). **(2)** SG-2 is **already implemented + tested + enforced** (`dbt_tipp` entry_screen caveat + contraindications + gating completion_criteria; `test_dbt_tipp_safety_caveat` 3/3). Neither Tasks 1–3 (anchor repair) nor Task 4 (SG-2 caveat) has anything to build. **Residual → tickets:** `sg2_present()` runtime defense-in-depth gate; §1c under-reach (clinician blocker-with-default: doc says TIPP, routing gives grounding — ratify/amend); `embedding_timeout` → silent ABSTAIN (latent routing hazard). See spec §0 (re-baseline) + §4A. The tasks below are retained only as the historical record of a plan built on a stale tree.

**Goal (WITHDRAWN — premise false):** Restore TIPP reachability at High intensity — a drive at `ei=8` currently resolves to `box_breathing`, not `dbt_tipp` — and couple that restoration **fail-closed** to the SG-2 cardiac/pregnancy caveat, so TIPP is not routable unless the contraindication screen is present.

**Architecture:** The acute match resolves in `skill_select` by max-pooled BGE-M3 cosine over each skill's `semantic_description` + `semantic_anchors` (+ `target_presentations` exemplars under V2). The §1e anchor-widening let a `box_breathing` anchor out-pool TIPP's High-band exemplars. R1 makes the **smallest** anchor-space change that flips the High-band probe back to `dbt_tipp`, recalibrates the semantic threshold, verifies no other acute skill was re-displaced, then wires a structural precondition: `dbt_tipp` is excluded from acute routing (fails closed to a substitute) unless its SG-2 caveat mechanism is present.

**Tech Stack:** Python 3.12, BGE-M3 (`sentence_transformers`), `scripts/calibrate_threshold.py`, LangGraph, `pytest`.

**Parent spec:** `docs/superpowers/specs/2026-07-14-bot-behaviour-routing-conformance-design.md` §4A (R1) + §R1.4 (SG-2 fail-closed gate) + §6 (permanent acute-band reachability control). **Depends on nothing in the B1 plan;** they are independent not-frozen fast-starts.

## Global Constraints

- **NOT frozen.** R1 edits the anchor space in `skill_select` (`semantic_description` / `semantic_anchors` / `target_presentations`); it does **not** touch `acute_direct_entry` (the frozen, signed rule). Build live-shippable pre-Gitex.
- **This is a defect from a shipped change, not unmeasured drift** — in scope by the spec's §1 carve-out. Do not "log and defer" it.
- **The fix is empirical.** Which anchor displaced TIPP must be *measured* (Task 2), not guessed. Task 3's exact edit is chosen from that measurement.
- **Recalibration is mandatory.** Any `semantic_description` / anchor / `target_presentations` edit requires `scripts/calibrate_threshold.py` + a determinism check (per `skill_select.py:41`). No silent anchor edits.
- **Re-verify no re-displacement.** The fix must not knock a *different* acute skill (`grounding_5_4_3_2_1`, `stop_technique`) off its own reachability. Prefer the smallest, lowest-governance change.
- **Governance ceiling depends on the field edited:** a *pinned* `semantic_description` (see `signed_clinical_fields.json`) → sign-off + manifest update in the same PR; `target_presentations` are unpinned-but-governance-sensitive (the unaudited-keyword gap) — record the edit for retroactive review.
- **SG-2 gate is structural and fail-closed** (§R1.4): TIPP not routable unless the caveat mechanism is present. Absence → unreachable, never silently reachable-without-screen. A sequencing note does not fail closed.
- **Assert on behaviour markers** (`active_skill_id`, resolved skill id, routability), never on prose.
- Code verified against deploy SHA `113bb09`.

---

### Task 1: Reproduce the regression as a red test (the permanent reachability control)

**Files:**
- Test: `tests/test_acute_band_reachability.py`

**Interfaces:**
- Produces: `test_high_band_resolves_to_tipp` — asserts a High-band (`ei≥8`) drive resolves to `dbt_tipp`. Red today on `113bb09`. This test is **permanent** (the spec §6 acute-band reachability control), not a throwaway repro.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_acute_band_reachability.py
import pytest
from sage_poc.nodes.skill_select import skill_select_node

# High-band presentation the doc routes to TIPP: "breathing isn't working, need
# something stronger" at panic intensity. dbt_tipp carries these exemplars.
HIGH_BAND_DRIVE = "I can't calm down, breathing isn't working, I need something stronger, I'm losing it"

def _high_band_state(msg: str) -> dict:
    return {"raw_message": msg, "message_en": msg, "detected_language": "en",
            "emotional_intensity": 8, "engagement": 6, "path": [],
            "offered_skill_ids": None, "declined_skills": [], "crisis_state": "none",
            "primary_intent": "new_skill"}

@pytest.mark.asyncio
async def test_high_band_resolves_to_tipp():
    out = await skill_select_node(_high_band_state(HIGH_BAND_DRIVE))
    # Behaviour marker: the acute match at ei>=8 must land on dbt_tipp, not box_breathing.
    assert out.get("active_skill_id") == "dbt_tipp", out.get("active_skill_id")
```

- [ ] **Step 2: Run — confirm it is RED on the current tree**

Run: `cd /Users/knowledgebase/Documents/Sage/sage-poc-spec-wt && uv run pytest tests/test_acute_band_reachability.py -v`
Expected: FAIL — resolves to `box_breathing` (or offers), NOT `dbt_tipp`. **Record this red run** — it is R1's exhibit and the register-gap evidence (the §1e widening shipped with no test asserting this).

- [ ] **Step 3: Commit the red test (regression captured before fix)**

```bash
git add tests/test_acute_band_reachability.py
git commit -m "test(routing): red — High band (ei=8) must resolve to dbt_tipp (R1 regression)"
```

---

### Task 2: Diagnose the displacement (measurement — method, not a guess)

**Files:**
- Create: `scripts/diagnose_tipp_displacement.py`

**Interfaces:**
- Produces: a ranked per-skill max-pooled cosine table for `HIGH_BAND_DRIVE`, naming the `box_breathing` anchor/exemplar that out-pools TIPP's best exemplar.

- [ ] **Step 1: Write the diagnostic script**

```python
# scripts/diagnose_tipp_displacement.py
"""R1 diagnosis: for the High-band drive, print the max-pooled cosine per acute skill
and the single anchor pair that wins for box_breathing vs dbt_tipp. Read-only; no edits."""
import numpy as np
from sage_poc.nodes.skill_select import build_anchor_pairs, _ensure_semantic_ready, _embed_model
from sage_poc.skills.schema import load_all_skills  # adjust to the actual loader in skill_select
from sage_poc import config as _cfg

DRIVE = "I can't calm down, breathing isn't working, I need something stronger, I'm losing it"
ACUTE = {"box_breathing", "dbt_tipp", "grounding_5_4_3_2_1", "stop_technique"}

def main():
    _ensure_semantic_ready()
    skills = load_all_skills()
    pairs = build_anchor_pairs(skills, include_exemplars=_cfg.SKILL_ROUTING_V2 if hasattr(_cfg, "SKILL_ROUTING_V2") else False)
    model = _embed_model
    q = model.encode([DRIVE], normalize_embeddings=True)[0]
    texts = [t for _, t in pairs]
    embs = model.encode(texts, normalize_embeddings=True)
    scored = [(sid, texts[i], float(np.dot(q, embs[i]))) for i, (sid, _) in enumerate(pairs)]
    # max-over-anchors per skill
    best = {}
    for sid, text, s in scored:
        if sid not in best or s > best[sid][1]:
            best[sid] = (text, s)
    print("=== max-pooled cosine per acute skill (High-band drive) ===")
    for sid in sorted(ACUTE, key=lambda s: -best.get(s, ("", -1))[1]):
        text, s = best.get(sid, ("<no anchor>", -1))
        print(f"  {s:.4f}  {sid:24}  <- {text!r}")
    print("\nDISPLACEMENT:", "box_breathing OUTPOOLS dbt_tipp" if best.get('box_breathing',('',-1))[1] > best.get('dbt_tipp',('',-1))[1] else "no displacement reproduced")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and capture the ranking**

Run: `uv run python scripts/diagnose_tipp_displacement.py`
Expected: `box_breathing` max-pooled cosine `>` `dbt_tipp`, and the printed `box_breathing` anchor text is the §1e-added anchor that over-captures the High band. **Record the winning anchor string** — Task 3 targets exactly it. If displacement does NOT reproduce here, the regression is not pure anchor-space (escalate: it may be threshold or keyword-tier); do not proceed to Task 3 blind.

- [ ] **Step 3: Commit the diagnostic (kept for the register)**

```bash
git add scripts/diagnose_tipp_displacement.py
git commit -m "chore(routing): R1 displacement diagnostic (read-only measurement)"
```

---

### Task 3: Minimal anchor repair + recalibrate + re-verify no re-displacement

**Files:**
- Modify: the anchor of the displacing skill identified in Task 2 — one of `src/sage_poc/skills/box_breathing.json` (`semantic_anchors` / `target_presentations`) **or** `src/sage_poc/skills/dbt_tipp.json` (strengthen a High-band exemplar). Choose the **smallest** change that flips the probe.
- Modify: `src/sage_poc/nodes/skill_select.py:42` recalibration comment / `SEMANTIC_THRESHOLD` if recalibration moves it.
- Test: `tests/test_acute_band_reachability.py`

**Interfaces:**
- Consumes: Task 2's named displacing anchor.
- Produces: `test_high_band_resolves_to_tipp` green; `grounding`/`stop` reachability unchanged.

- [ ] **Step 1: Add the no-re-displacement guard tests (write BEFORE the fix)**

```python
GROUNDING_DRIVE = "I feel unreal and detached, help me get grounded, name things around me"
STOP_DRIVE = "I'm about to do something impulsive, I need to stop and step back right now"

@pytest.mark.asyncio
async def test_grounding_still_reachable():
    out = await skill_select_node(_high_band_state(GROUNDING_DRIVE))
    assert out.get("active_skill_id") == "grounding_5_4_3_2_1", out.get("active_skill_id")

@pytest.mark.asyncio
async def test_stop_still_reachable():
    out = await skill_select_node(_high_band_state(STOP_DRIVE) | {"emotional_intensity": 7})
    assert out.get("active_skill_id") == "stop_technique", out.get("active_skill_id")
```

- [ ] **Step 2: Run — grounding/stop should PASS now (they are the baseline the fix must not break)**

Run: `uv run pytest tests/test_acute_band_reachability.py -k "grounding_still or stop_still" -v`
Expected: PASS (pre-fix baseline). If either already fails, the anchor space is more broadly displaced — widen Task 2's diagnosis before editing.

- [ ] **Step 3: Make the minimal anchor edit (targets Task 2's named anchor)**

Apply the smallest change that flips the High-band probe. Two candidate shapes — pick per Task 2's finding:
- **(a) Narrow the over-capturing `box_breathing` anchor** — the §1e-added phrase that pulls "breathing isn't working / need something stronger" into box_breathing is exactly wrong (those phrasings mean *breathing is insufficient* → escalate to TIPP). Remove or tighten that specific anchor/exemplar in `box_breathing.json`.
- **(b) Strengthen `dbt_tipp` High-band exemplars** — if TIPP's margin is thin, add the drive's discriminating phrasing to `dbt_tipp.json` `target_presentations` (it already carries "breathing isn't working", "need something stronger than breathing" — verify they survived and are indexed).

Record which field changed and its governance class (pinned `semantic_description` → sign-off; `target_presentations` → unpinned, log for retroactive review).

- [ ] **Step 4: Recalibrate the semantic threshold (mandatory)**

Run: `uv run python scripts/calibrate_threshold.py`
Then update `SEMANTIC_THRESHOLD` + the recalibration-date comment in `skill_select.py` if it moved. Do NOT skip — an anchor edit without recalibration is a silent threshold drift.

- [ ] **Step 5: Run the full reachability suite — TIPP green, grounding/stop still green**

Run: `uv run pytest tests/test_acute_band_reachability.py -v`
Expected: PASS on all — `dbt_tipp` restored, `grounding`/`stop` un-displaced.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/skills/*.json src/sage_poc/nodes/skill_select.py tests/test_acute_band_reachability.py
git commit -m "fix(routing): restore TIPP reachability at ei>=8 (R1 anchor repair + recalibrate)"
```

---

### Task 4: SG-2 cardiac/pregnancy caveat mechanism on TIPP

**Files:**
- Modify: `src/sage_poc/skills/dbt_tipp.json` (`contraindications` field + a caveat rendered before the `temperature` and `intense_exercise` steps)
- Test: `tests/test_dbt_tipp_safety_caveat.py` (exists — extend it)

**Interfaces:**
- Produces: the temperature + intense-exercise steps carry the SG-2 caveat; `contraindications` is non-empty and specific.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_dbt_tipp_safety_caveat.py (extend)
import json
def _tipp():
    return json.load(open("src/sage_poc/skills/dbt_tipp.json"))

def test_sg2_caveat_present_on_physiological_steps():
    d = _tipp()
    steps = {s["step_id"]: s for s in d["steps"]}
    caveat_terms = ("heart", "irregular", "pregnan")
    # The caveat must appear at/before the temperature and intense_exercise steps.
    blob = json.dumps(steps.get("temperature", {})) + json.dumps(steps.get("intense_exercise", {})) + d.get("contraindications", "")
    for term in caveat_terms:
        assert term in blob.lower(), f"SG-2 caveat missing term: {term}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_dbt_tipp_safety_caveat.py -k "sg2_caveat_present" -v`
Expected: FAIL — no cardiac/pregnancy caveat today (`#298` red baseline).

- [ ] **Step 3: Add the caveat (verbatim from the doc's TIPP requirement)**

In `dbt_tipp.json`, set `contraindications` and prepend the caveat to the `temperature` and `intense_exercise` step instructions:

```json
"contraindications": "Before the temperature step (which can slow the heart rate suddenly) and the intense-exercise step (which raises it quickly): if the person has a heart condition, an irregular heartbeat, or is pregnant, tell them to skip those two steps or check with a doctor first. Use paced breathing and progressive muscle relaxation only."
```

And in each of the `temperature` and `intense_exercise` steps, lead the instruction with a one-line caveat (no em dashes in rule/instruction content — use commas): *"First, a quick check: if you have a heart condition, an irregular heartbeat, or are pregnant, skip this step or check with a doctor, and we'll use the breathing and muscle steps instead."*

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_dbt_tipp_safety_caveat.py -k "sg2_caveat_present" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/dbt_tipp.json tests/test_dbt_tipp_safety_caveat.py
git commit -m "feat(safety): SG-2 cardiac/pregnancy caveat on TIPP temperature+exercise steps (#298)"
```

---

### Task 5: Fail-closed SG-2 gate — TIPP not routable unless the caveat is present

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py` (add a routability precondition that drops `dbt_tipp` from the acute candidate set when its SG-2 caveat is absent)
- Test: `tests/test_acute_band_reachability.py`

**Interfaces:**
- Consumes: `dbt_tipp` `contraindications` + step caveat (Task 4).
- Produces: `sg2_present(skill) -> bool`; when False, `dbt_tipp` is excluded from acute routing and the acute substitution path (grounding-first) takes over — never a silent TIPP-without-screen.

- [ ] **Step 1: Write the failing tests (both directions)**

```python
from sage_poc.nodes import skill_select as ss

@pytest.mark.asyncio
async def test_tipp_routable_when_sg2_present(monkeypatch):
    # SG-2 present (Task 4 landed): High-band resolves to dbt_tipp.
    out = await skill_select_node(_high_band_state(HIGH_BAND_DRIVE))
    assert out.get("active_skill_id") == "dbt_tipp"

@pytest.mark.asyncio
async def test_tipp_fails_closed_when_sg2_absent(monkeypatch):
    # Simulate the caveat being missing (revert/regression): TIPP must become
    # UNREACHABLE, not silently routed without the screen.
    monkeypatch.setattr(ss, "sg2_present", lambda skill: False)
    out = await skill_select_node(_high_band_state(HIGH_BAND_DRIVE))
    assert out.get("active_skill_id") != "dbt_tipp", "TIPP must fail closed without SG-2"
```

- [ ] **Step 2: Run to verify the fail-closed test fails**

Run: `uv run pytest tests/test_acute_band_reachability.py -k "routable_when_sg2 or fails_closed_when_sg2" -v`
Expected: `fails_closed` FAILS (no gate yet — TIPP routes regardless of caveat).

- [ ] **Step 3: Implement the fail-closed precondition**

In `skill_select.py`, add:

```python
def sg2_present(skill) -> bool:
    """SG-2 fail-closed gate: dbt_tipp is only routable if its cardiac/pregnancy caveat
    mechanism is present. Structural, not a sequencing note — absence => unreachable.
    Checks the contraindications field carries the cardiac/pregnancy terms."""
    contra = (getattr(skill, "contraindications", "") or "").lower()
    return all(term in contra for term in ("heart", "irregular", "pregnan"))
```

Where the acute candidate set is assembled (before the semantic match resolves the winner / before `acute_direct_entry` sees `dbt_tipp`), drop `dbt_tipp` when the gate is closed:

```python
    # SG-2 fail-closed gate (spec §R1.4): TIPP cannot be routed without its
    # cardiac/pregnancy caveat. Excluding it here makes the acute substitution
    # pool (grounding-first) take over — never a silent TIPP-without-screen.
    if not sg2_present(skills.get("dbt_tipp")):
        candidates = [c for c in candidates if c != "dbt_tipp"]
```

(Adapt `candidates` to the actual variable holding the ranked acute matches in `skill_select_node`.)

- [ ] **Step 4: Run — both directions green**

Run: `uv run pytest tests/test_acute_band_reachability.py -v`
Expected: PASS — TIPP routable with SG-2, unreachable without it.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py tests/test_acute_band_reachability.py
git commit -m "feat(routing): fail-closed SG-2 gate — TIPP unroutable without cardiac caveat (R1)"
```

---

### Task 6: End-to-end + coupling invariant

**Files:**
- Test: `tests/test_acute_band_reachability.py`

- [ ] **Step 1: Write the end-to-end + coupling tests**

```python
from sage_poc.graph import build_graph

@pytest.mark.asyncio
async def test_e2e_high_band_lands_on_tipp_with_caveat():
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": HIGH_BAND_DRIVE, "emotional_intensity": 8, "path": []},
        config={"configurable": {"thread_id": "r1-e2e"}},
    )
    assert result.get("active_skill_id") == "dbt_tipp"

@pytest.mark.asyncio
async def test_coupling_invariant_holds_through_the_fix(monkeypatch):
    # The wrong order must be impossible: with SG-2 removed, TIPP is not routable
    # even after R1's reachability restoration. This test must stay green permanently.
    from sage_poc.nodes import skill_select as ss
    monkeypatch.setattr(ss, "sg2_present", lambda skill: False)
    out = await skill_select_node(_high_band_state(HIGH_BAND_DRIVE))
    assert out.get("active_skill_id") != "dbt_tipp"
```

- [ ] **Step 2: Run the full suite + adjacent routing regressions**

Run: `uv run pytest tests/test_acute_band_reachability.py tests/test_routing.py tests/test_dbt_tipp_safety_caveat.py -v`
Expected: PASS across all.

- [ ] **Step 3: Commit**

```bash
git add tests/test_acute_band_reachability.py
git commit -m "test(routing): R1 end-to-end + SG-2 coupling invariant (permanent guard)"
```

---

## Sequencing note (within R1)

Tasks 4 (SG-2 caveat) and 5 (fail-closed gate) **must land before** Task 3's reachability restoration is flipped live — otherwise TIPP becomes reachable-without-screen for the window between them. In execution order the tests enforce this: Task 5's `fails_closed` test and Task 6's coupling invariant are the structural proof that the wrong order cannot ship. If executing incrementally with the guard behind a flag, keep TIPP excluded until Tasks 4+5 are both green.

## Self-Review

**Spec coverage (§4A, §R1.4, §6):** regression reproduced as a permanent reachability control (Task 1) ✓; empirical diagnosis, not a guess (Task 2) ✓; minimal anchor repair + mandatory recalibrate + no-re-displacement guard (Task 3) ✓; SG-2 caveat mechanism, verbatim (Task 4) ✓; **fail-closed structural gate** — TIPP unroutable without the caveat, both directions tested (Task 5) ✓; coupling invariant permanent (Task 6) ✓; not-frozen / governance-per-field noted (Global Constraints) ✓. **Out of scope:** the full E3 medical detector (B1 plan); F5's tier logic (F5 plan) — R1 only restores the High-band *target*, F5 builds the tier behaviour on top.

**Placeholder scan:** the one intentionally empirical step (Task 3's exact edit) is chosen from Task 2's measured output — the method, acceptance, and both candidate shapes are specified; that is correct fidelity for a data-dependent fix, not a placeholder.

**Type consistency:** `sg2_present(skill)->bool`, `active_skill_id`, `HIGH_BAND_DRIVE`, `dbt_tipp` used identically across Tasks 1–6.
