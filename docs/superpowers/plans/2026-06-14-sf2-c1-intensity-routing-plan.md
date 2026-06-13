# SF-2 / C1 Intensity-Aware Acute Routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make acute-skill routing and dbt_tipp entry depend on `emotional_intensity` + gate
state rather than brittle keyword presence and code-hardcoded skill pairs — entirely in
rules-data (skill_matching + step_policy JSON), with **no graph change** and no deviation from
v7 (§2.3 routing rules, §4 intent, §5.2 matching, §5.3 step_policy).

**Architecture:** intent_route emits `emotional_intensity` (1–10) and `intent_confidence`
(§4). skill_select Tier-1/Tier-2 → `_resolve_entry()` → `rules_engine.evaluate("skill_matching",
{matched_skill_id, emotional_intensity})`, first-match-wins by priority (§5.2). `acute_direct_entry`
(priority 1) already gates the 4 acute skills at `emotional_intensity ≥ 8`. step_policy branches
steps inside `skill_executor.evaluate_step_policy` against `_KNOWN_STEP_POLICY_SIGNALS` (§5.3/§5.5).

**Tech stack:** Python rules engine; JSON rules-data; pytest.

**Status of inputs:** all three components below carry **clinical sign-off gates** (thresholds,
priority order, the dbt_tipp entry-branch logic, PMR content). Engineering implements the
mechanism; clinical authors/ratifies the values. Nothing ships to master without sign-off.

---

## Problem definitions (architecture/clinical to confirm — engineering's reading)

- **SF-2 (safety finding; distinct from Intelligence-Eval SF-2 "crisis-in-mid-skill").**
  Acute routing currently depends on a Tier-1 **keyword** hit. Tier-2 embeds `semantic_description`
  only and will not catch novel acute phrasings (§5.2 embedding note). So a user whom intent_route
  classifies as **acute / high `emotional_intensity`** but who uses no acute keyword falls through
  to freeflow — the most-activating safety-relevant population routed by the most brittle signal.
  **Proposed:** an intensity-driven acute **safety-net** — when no skill matches AND
  `emotional_intensity ≥ acute_net_threshold` AND not a crisis (crisis owns its own path), offer/enter
  the lowest-risk acute skill (grounding) rather than freeflow. Lower-risk default, never dbt_tipp via
  this net (cold-water risk; dbt_tipp stays keyword+screen only).

- **C1 (clinical-priority override).** The grounding-over-dbt_tipp tiebreak is currently a
  **code-hardcoded** pair check in `skill_select`. Generalize it into **data** (a clinical-priority
  ordering the rules consult), so future acute-overlap decisions are authored + signed, not edited in
  `.py`. No behavior change for the existing pair; it becomes the first entry in the data.

- **05c (dbt_tipp adaptive entry).** Replace "always temperature-first" with a step_policy branch in
  dbt_tipp's `entry_screen`: contraindication→redirect (exists); `emotional_intensity ≥ extreme_threshold`
  →temperature (fastest interrupt, gate cleared cold-water risk); else→paced_breathing/PMR (low-risk).

---

## File structure

- Modify: `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json` — add C1 priority data +
  (if approved) the SF-2 acute-safety-net rule.
- Modify: `src/sage_poc/nodes/skill_select.py` — replace the hardcoded grounding/dbt_tipp tiebreak with
  a data-driven clinical-priority lookup; wire the SF-2 net into the no-match path.
- Modify: `src/sage_poc/skills/dbt_tipp.json` — `entry_screen.step_policy` intensity branch (05c) +
  PMR step (05a, clinical-authored content).
- Tests: `tests/test_skill_select.py`, `tests/test_skill_executor.py`, `tests/test_routing.py`,
  extend `test_acute_cluster_bucket_lock`.

---

## Clinical sign-off gates (BLOCKING — author/ratify before the dependent tasks ship)

- [ ] **G1 — thresholds:** `acute_net_threshold` (SF-2) and `extreme_threshold` (05c). Default
  hypothesis `extreme_threshold = 8` to match the existing `acute_direct_entry ≥ 8`; `acute_net_threshold`
  TBD. Clinical confirms both.
- [ ] **G2 — clinical-priority order (C1):** the data list. Seed = `[grounding_5_4_3_2_1 ≻ dbt_tipp]`
  (existing decision). Clinical confirms whether other pairs belong.
- [ ] **G3 — PMR step content (05a):** goal/technique/technique_description/tone/examples
  (EN + AR, Arabic at position [0] per the example-ordering convention)/contraindications/completion_criteria.
- [ ] **G4 — 05c branch ratification:** confirm the contraindication→redirect / extreme→temperature /
  else→paced_breathing-or-PMR logic and which low-risk step is the default entry.

---

## Task 1 — C1: move the clinical-priority tiebreak from code to data

**Files:** `skill_matching_rules.json`, `skill_select.py`, `tests/test_skill_select.py`

- [ ] **Step 1 (test):** add `test_clinical_priority_is_data_driven` — assert the grounding≻dbt_tipp
  co-match still routes grounding (behavior unchanged) AND that the priority comes from the rules data
  (e.g. emptying the priority list reverts to longest-match). Run → fails.
- [ ] **Step 2 (impl):** add a `clinical_priority` array to `skill_matching_rules.json` (signed,
  G2); in `skill_select`, replace the hardcoded `{"grounding_5_4_3_2_1","dbt_tipp"}` check with a lookup
  over that array (when both members co-match and the lower-priority one is the longest-match winner,
  prefer the higher-priority one). Run → passes; `test_c1_tiebreak_*` and `test_acute_cluster_bucket_lock`
  still green.
- [ ] **Step 3 (commit).**

## Task 2 — 05c: dbt_tipp adaptive entry via step_policy

**Files:** `dbt_tipp.json`, `tests/test_skill_executor.py`

- [ ] **Step 1 (test):** `test_dbt_tipp_entry_branch_by_intensity` — at `emotional_intensity ≥
  extreme_threshold` entry advances to `temperature`; below it, to `paced_breathing` (or PMR once added);
  contraindication path still redirects. Run → fails.
- [ ] **Step 2 (impl):** add `step_policy` rules to `entry_screen` branching `next_step` on
  `emotional_intensity` (signed thresholds G1/G4). No graph change. Run → passes.
- [ ] **Step 3 (commit).** GATED on G1 + G4.

## Task 3 — 05a: add the PMR step (clinical-authored)

**Files:** `dbt_tipp.json`, `tests/test_schema_conformance.py`, `tests/test_skill_executor.py`

- [ ] **Step 1:** insert the clinical-authored PMR step (G3) into `dbt_tipp.steps` after
  `paced_breathing`; wire transitions (paced_breathing→PMR→check_in). Arabic example at [0].
- [ ] **Step 2 (test):** schema-conformance passes; a step-progression test reaches PMR; PMR has no
  cardiac/ED contraindication (lowest-risk).
- [ ] **Step 3 (commit).** GATED on G3.

## Task 4 — SF-2: intensity-driven acute safety-net (no-match path)

**Files:** `skill_matching_rules.json` / `skill_select.py`, `tests/test_routing.py`, `tests/test_skill_select.py`

- [ ] **Step 1 (test):** `test_acute_intensity_net_routes_low_risk` — no keyword match,
  `emotional_intensity ≥ acute_net_threshold`, non-crisis → grounding (offer or direct per the acute
  rule), NOT freeflow, NOT dbt_tipp. And a guard: below threshold → freeflow unchanged. Run → fails.
- [ ] **Step 2 (impl):** in the no-match branch of `skill_select`, consult intensity; if ≥
  `acute_net_threshold` and not crisis/monitoring, route to grounding via the existing acute machinery.
  Crisis path unchanged (safety owns it). Run → passes.
- [ ] **Step 3 (commit).** GATED on G1. **Safety review:** confirm this never shadows the crisis path
  and never routes to dbt_tipp via the net.

## Task 5 — extend the bucket-lock + regression

- [ ] Add the new decided behaviors (C1 data-driven, 05c entry branch, SF-2 net target) to the lock
  test / routing suite so they cannot silently drift. Run the full curated unit-gate suite green.

---

## Self-review checks
- No graph change anywhere (all rules-data + skill_select logic). ✔ design intent.
- dbt_tipp never reachable via the SF-2 net (cold-water risk) — only keyword + entry_screen. ✔ Task 4 guard.
- Crisis path precedence untouched (SF-2 net is non-crisis only). ✔ Task 4 safety review.
- Every clinical value (thresholds, priority order, PMR text, branch logic) behind a G-gate. ✔.
- `extreme_threshold` reconciled with the existing `acute_direct_entry ≥ 8` so the two intensity gates
  don't contradict. ✔ G1.
