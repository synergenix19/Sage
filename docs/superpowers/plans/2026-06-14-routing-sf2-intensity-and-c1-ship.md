# Routing-SF-2 (intent-route intensity) + C1 ship Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make acute-distress turns that intent_route labels `general_chat` reach `skill_select` so the acute down-regulation skills (`dbt_tipp`, `grounding_5_4_3_2_1`) can match (Routing-SF-2), and ship the already-signed-off C1 + Task-3 routing fixes from the engagement branch to master via a clean sibling PR.

**Architecture:** Routing-SF-2 is a single new branch in `_route_after_intent` (graph.py) gated on the `emotional_intensity` signal that intent_route **already computes** but routing currently ignores. If no acute skill matches, `skill_select` falls through to `freeflow` as today, so the worst case is unchanged. C1 (the grounding-vs-dbt_tipp acute tiebreak) is already implemented, clinically signed off, and tested on the branch — its remaining work is extraction to master, not coding.

**Tech Stack:** Python 3.12, pytest, LangGraph `StateGraph`, `sage_poc.graph`, `sage_poc.nodes.intent_route`, `sage_poc.nodes.skill_select`.

> **LABEL DISAMBIGUATION — read before writing any test name or comment.** Two "SF-x" namespaces collide in this repo. This plan is the **skill-routing audit** namespace: **Routing-SF-2** = intent-route intensity blindness / dbt_tipp reachability (this plan). Do NOT confuse with the **Intelligence Evaluation** namespace: **IE-SF-2** = crisis-in-mid-skill (a separate safety item). Always prefix: `Routing-SF-2` in this work. The passive-SI detection escalation (`docs/superpowers/escalations/2026-06-14-passive-si-detection-gap-s3-empirical.md`, = IE-SF-1) outranks this plan and is tracked separately; this plan is routing, not detection, and must not be cited as mitigating it.

---

## Current behaviour (verified 2026-06-14)

`_route_after_intent` (`graph.py:151-185`) decides the post-classification route. Order today: `crisis` → `scope_refusal` → `jailbreak` → `monitoring` (bypasses confidence) → `psychotic_disclosure` (bypasses confidence) → `confidence < 0.6 → low_confidence` → `exit_skill` → `new_skill` → `info_request` → `skill_continuation` → **default `freeflow`**.

`intent_route` returns `emotional_intensity` (1-10, default 5) at `intent_route.py:77`. `_route_after_intent` never reads it. So a turn classified `general_chat` (the default intent) routes to `freeflow` regardless of intensity, and `skill_select` never runs — `dbt_tipp` / `grounding_5_4_3_2_1` are unreachable for an acutely distressed user who is not in crisis and did not phrase a `new_skill` request. That is the Routing-SF-2 gap (2026-06-07 audit, CRITICAL for dbt_tipp).

C1 (`skill_select.py:220-233`, commit `9ebf25c`, clinical sign-off 2026-06-13): when both `grounding_5_4_3_2_1` and `dbt_tipp` keyword-match, prefer grounding. Already implemented + tested; branch-only (not on master).

---

## File structure

| File | Change |
|------|--------|
| `src/sage_poc/graph.py` | Routing-SF-2: add `ACUTE_INTENSITY_FLOOR` constant + intensity branch in `_route_after_intent` |
| `tests/test_nodes.py` | Routing-SF-2: unit tests on `_route_after_intent` + guard tests; this file also needs adding to the master unit-gate (Task 3) |
| `tests/test_intent_route_integration.py` | Routing-SF-2: full-path integration test (acute general_chat → skill_select → acute skill) |

No change to `intent_route.py` (it already emits `emotional_intensity`). No change to `skill_select.py` for Routing-SF-2 (C1 already there).

---

## Task 1 — Routing-SF-2: intensity-aware route to skill_select

**What this fixes:** Acute-distress turns labelled `general_chat` bypass `skill_select`. Add a branch: high `emotional_intensity` + `general_chat` routes to `skill_select` so acute skills can match. Placed **before** the confidence gate, consistent with the existing monitoring/psychotic safety redirects (an acute redirect must not depend on classification confidence).

**Files:**
- Modify: `src/sage_poc/graph.py` (`_route_after_intent`, near line 151)
- Test: `tests/test_nodes.py`

- [ ] **Step 1: Write the failing unit tests**

  In `tests/test_nodes.py`, add:

  ```python
  def test_route_after_intent_acute_general_chat_reaches_skill_select():
      """Routing-SF-2: general_chat at high intensity must route to skill_select
      so acute down-regulation skills (dbt_tipp/grounding) can match. Without this,
      an acutely distressed non-crisis user never reaches skill_select."""
      from sage_poc.graph import _route_after_intent
      state = {
          "primary_intent": "general_chat",
          "intent_confidence": 1.0,
          "emotional_intensity": 9,
          "crisis_state": "none",
          "clinical_flags": [],
          "active_skill_id": None,
      }
      assert _route_after_intent(state) == "skill_select"

  def test_route_after_intent_calm_general_chat_still_freeflow():
      """Routing-SF-2 guard: low-intensity general_chat must STILL route to freeflow.
      The intensity branch must not capture ordinary conversation."""
      from sage_poc.graph import _route_after_intent
      state = {
          "primary_intent": "general_chat",
          "intent_confidence": 1.0,
          "emotional_intensity": 4,
          "crisis_state": "none",
          "clinical_flags": [],
          "active_skill_id": None,
      }
      assert _route_after_intent(state) == "freeflow"
  ```

- [ ] **Step 2: Run to verify they fail**

  Run: `.venv/bin/python -m pytest tests/test_nodes.py -k "route_after_intent_acute or calm_general_chat" -v`
  Expected: `test_..._acute_general_chat_reaches_skill_select` FAILS (returns `"freeflow"`); the calm guard PASSES already.

- [ ] **Step 3: Add the constant and the branch in `graph.py`**

  Near the top of `src/sage_poc/graph.py` (with the other module constants), add:

  ```python
  # Routing-SF-2: emotional_intensity at or above this floor makes a general_chat turn
  # reach skill_select (acute down-regulation skills). Matches the acute_direct_entry bar
  # in skill_matching_rules.json (emotional_intensity >= 8), the clinically-approved
  # threshold for acute handling. Adjust only with clinical sign-off.
  ACUTE_INTENSITY_FLOOR: int = 8
  ```

  In `_route_after_intent`, immediately AFTER the `psychotic_disclosure` block and BEFORE `if confidence < 0.6:`, insert:

  ```python
      # Routing-SF-2 (intent-route intensity): acute distress classified as general_chat
      # must still reach skill_select so the acute down-regulation skills (dbt_tipp,
      # grounding_5_4_3_2_1) can keyword-match. intent_route already computes
      # emotional_intensity; routing previously ignored it, sending high-intensity
      # general_chat to freeflow where no skill is ever offered. Placed before the
      # confidence gate (like monitoring/psychotic redirects): an acute redirect must not
      # depend on classification confidence. If no acute skill matches, skill_select falls
      # through to freeflow (_route_after_skill_select), so the worst case is unchanged.
      if (intent == "general_chat"
              and state.get("emotional_intensity", 5) >= ACUTE_INTENSITY_FLOOR):
          return "skill_select"
  ```

- [ ] **Step 4: Run to verify they pass**

  Run: `.venv/bin/python -m pytest tests/test_nodes.py -k "route_after_intent_acute or calm_general_chat" -v`
  Expected: both PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add src/sage_poc/graph.py tests/test_nodes.py
  git commit -m "feat(routing): Routing-SF-2 — acute general_chat reaches skill_select via intensity

  intent_route already emits emotional_intensity; _route_after_intent ignored it,
  so acutely-distressed non-crisis users classified general_chat never reached
  skill_select and dbt_tipp/grounding were unreachable (2026-06-07 audit, CRITICAL).

  Adds ACUTE_INTENSITY_FLOOR=8 (matches acute_direct_entry bar) and an intensity
  branch before the confidence gate, consistent with monitoring/psychotic redirects.
  Safe fallthrough: no acute keyword match -> skill_select -> freeflow as today.

  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

---

## Task 2 — Routing-SF-2 guard: safe-fallthrough + crisis-precedence

**What this proves:** (a) a high-intensity general_chat turn that matches NO skill still ends at freeflow (no spurious skill offer), and (b) the new branch does not perturb crisis precedence.

**Files:**
- Test: `tests/test_intent_route_integration.py`, `tests/test_nodes.py`

- [ ] **Step 1: Write the failing/holding tests**

  In `tests/test_intent_route_integration.py`, add:

  ```python
  @pytest.mark.asyncio
  async def test_acute_general_chat_no_keyword_falls_through_to_freeflow():
      """Routing-SF-2 safety: high-intensity general_chat with NO acute-skill keyword
      must reach skill_select and then fall through to freeflow (no spurious offer)."""
      from sage_poc.nodes.skill_select import skill_select_node
      from sage_poc.graph import _route_after_skill_select
      state = {
          "raw_message": "everything is just so much right now",
          "message_en": "everything is just so much right now",
          "detected_language": "en",
          "primary_intent": "general_chat",
          "emotional_intensity": 9,
          "crisis_state": "none",
          "clinical_flags": [],
          "active_skill_id": None,
          "active_step_id": None,
          "path": [],
          "therapeutic_profile": None,
      }
      result = await skill_select_node(state)
      merged = {**state, **result}
      # no acute keyword in the phrase -> no skill activated -> freeflow
      assert _route_after_skill_select(merged) == "freeflow"

  def test_crisis_intent_still_wins_over_intensity():
      """Routing-SF-2 guard: crisis intent must still route to crisis even at high intensity."""
      from sage_poc.graph import _route_after_intent
      state = {
          "primary_intent": "crisis",
          "intent_confidence": 1.0,
          "emotional_intensity": 10,
          "crisis_state": "none",
          "clinical_flags": [],
          "active_skill_id": None,
      }
      assert _route_after_intent(state) == "crisis"
  ```

- [ ] **Step 2: Run to verify**

  Run: `.venv/bin/python -m pytest tests/test_intent_route_integration.py -k "acute_general_chat_no_keyword or crisis_intent_still_wins" tests/test_nodes.py -k "crisis_intent_still_wins" -v`
  Expected: both PASS (crisis branch precedes the new branch; no-keyword phrase yields no skill). If the no-keyword test FAILS because some skill keyword-matched "everything is just so much," pick a phrase with no `target_presentations` substring and re-run.

- [ ] **Step 3: Commit**

  ```bash
  git add tests/test_intent_route_integration.py
  git commit -m "test(routing): Routing-SF-2 guards — safe freeflow fallthrough + crisis precedence

  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

---

## Task 3 — Ship signed routing fixes to master via a clean sibling PR

**What this does:** The Task-3 keyword ownership (`711f4f3`, signed 2026-06-10), the C1 acute tiebreak (`9ebf25c`, signed 2026-06-13), and this plan's Routing-SF-2 commits are all on `feat/engagement-r1-r3-r5` (PR #4), which is merge-gated on unrelated engagement sign-offs. They must reach master **without** PR #4 — the C1 governance doc states this explicitly ("a separate master PR, sibling of #6/#8, never inside PR #4"). This task extracts them onto a branch cut from master.

> This task mutates shared state (a new branch + PR toward master). Per the branch-mutation boundary, the cherry-pick/branch prep is do-and-report, but the actual merge to master is the human's call and must not be admin-bypassed. Flag if branch protection requires an override.

**Files:** git operations + `tests/` gate config. No source edits beyond cherry-pick.

- [ ] **Step 1: Cut a sibling branch from master**

  ```bash
  git fetch origin
  git checkout -b fix/routing-sf2-c1-ship origin/master
  ```

- [ ] **Step 2: Cherry-pick the signed routing commits in order**

  ```bash
  git cherry-pick 711f4f3   # Task 3 keyword ownership (worry_time -> cognitive_restructuring)
  git cherry-pick 9ebf25c   # C1 acute-overlap tiebreak (grounding for ambiguous overwhelm)
  # then the two Routing-SF-2 commits from Tasks 1-2 of this plan:
  git cherry-pick <task1_sha> <task2_sha>
  ```

  If a cherry-pick conflicts because the best-match/multi-vector machinery differs between branch and master: resolve by keeping master's machinery and re-applying only the C1 block and the SF-2 branch. Verify `skill_select.py:220-233` (C1) and the `_route_after_intent` intensity branch are both present after resolution.

- [ ] **Step 3: Add `test_nodes.py` to the master unit-gate**

  The C1 conflict doc (gate-coverage gap) notes `test_nodes.py` sat outside the curated unit-gate, which is why the overwhelm misroute was red-on-master invisibly. Add it to the gate config so this coverage is permanent. Locate the unit-gate test selection (search `.github/workflows/` and any `pytest.ini`/`pyproject.toml` gate marker or path list for the curated suite) and add `tests/test_nodes.py`.

  ```bash
  grep -rn "test_nodes\|unit-gate\|curated\|gate" .github/workflows/ pyproject.toml pytest.ini 2>/dev/null
  ```

  Edit the gate list to include `tests/test_nodes.py`. Commit:

  ```bash
  git add .github/workflows/ pyproject.toml pytest.ini  # whichever holds the gate list
  git commit -m "ci(gate): add test_nodes.py to unit-gate — permanent overwhelm-routing coverage (C1)

  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
  ```

- [ ] **Step 4: Run the full routing + node suite on the sibling branch**

  ```bash
  .venv/bin/python -m pytest tests/test_nodes.py tests/test_skill_select.py tests/test_intent_route_integration.py tests/test_wrong_skill_routing.py -p no:xdist -q
  ```

  Expected: all green (slow tests may need `-m slow` separately). Specifically confirm: the overwhelm grounding tests pass (C1), the Routing-SF-2 unit + guard tests pass, and no prior routing test regressed.

- [ ] **Step 5: Push and open the PR (do not self-merge)**

  ```bash
  git push -u origin fix/routing-sf2-c1-ship
  gh pr create --base master --title "Routing: ship Task-3 keyword ownership + C1 tiebreak + Routing-SF-2 intensity" \
    --body "$(cat <<'EOF'
Ships three signed/tested routing fixes to master, extracted from PR #4 (sibling, per C1 governance doc):
- Task 3 keyword ownership (catastrophizing -> cognitive_restructuring) — clinical sign-off 2026-06-10
- C1 acute-overlap tiebreak (grounding for ambiguous overwhelm) — clinical sign-off 2026-06-13
- Routing-SF-2: acute general_chat reaches skill_select via emotional_intensity (new; engineering)

Also adds test_nodes.py to the unit-gate (permanent C1 coverage).

Does NOT touch detection. The passive-SI detection gap (IE-SF-1) is tracked separately in
docs/superpowers/escalations/2026-06-14-passive-si-detection-gap-s3-empirical.md and is not mitigated by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
  ```

  Report the PR URL. The merge is the human's decision; if branch protection requires an admin override, flag it rather than bypassing.

---

## Open clinical confirmation (non-blocking for code, blocking for production)

- **Routing-SF-2 confidence-bypass:** the intensity branch is placed before the confidence gate, so an acute high-intensity turn reaches skill_select even at low classification confidence. This matches the monitoring/psychotic safety-redirect convention. Confirm with the clinical lead that acute-intensity reachability should not depend on classification confidence (recommended: yes). If the answer is no, move the branch to after `if confidence < 0.6:`.
- **ACUTE_INTENSITY_FLOOR = 8:** inherited from the clinically-approved `acute_direct_entry` bar. Confirm 8 is the intended reachability floor (a lower floor widens skill reach for moderate distress).

## Self-review notes

- Spec coverage: Routing-SF-2 (Task 1 impl + Task 2 guards), C1 ship (Task 3, no re-code — already `9ebf25c`), Task-3 keyword ship (Task 3 cherry-pick), gate-coverage gap (Task 3 Step 3). C1 is NOT re-implemented anywhere — confirmed it exists at `skill_select.py:220-233`.
- Detection vs routing kept separate: IE-SF-1 escalation referenced, never folded in.
- Label hygiene: every routing item prefixed `Routing-SF-2`; IE namespace called out in the header and the PR body.
