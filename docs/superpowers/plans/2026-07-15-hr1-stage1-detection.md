# HR-1 Stage 1 — High-Risk Detection Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Extend the existing rules engine so mania / dissociation / psychosis-variant presentations are detected and routed to the existing `psychotic_referral` terminal instead of being offered a contraindicated self-help skill. Detection only — the fixed-copy terminal is Stage 2.

**Architecture:** Reuse everything. New/extended keyword rules in `clinical_flag_patterns.json` (CF-006 family) set HR-class clinical flags; the live `psychotic_disclosure → psychotic_referral` route (graph.py:205, skill_select.py:619) is broadened to fire on any HR-class flag, gated behind a new flag so OFF is byte-identical to prod. No new node, no parallel detector, no precedence-resolver wiring.

**Tech Stack:** Python, pytest, JSON rule files, LangGraph.

## Global Constraints
- **Read against the document verbatim.** Trigger phrases are BOT BEHAVIOUR §HR.0 (bot_behaviour.txt L1509–1511), copied exactly + minimum word-order variants only. No invented clinical content.
- **Flag gate:** `HIGH_RISK_DETECTION_ENABLED` (env `SAGE_HIGH_RISK_DETECTION`, default `false`). OFF ⇒ only `psychotic_disclosure` routes (exactly as prod today). The existing psychotic path is NEVER gated off by this flag.
- **Route order is RATIFIED** `crisis > medical > hr > ipv` (safety_precedence.py:24). Do not reorder. SI always wins (crisis checked first in `_route_after_safety`).
- **No em dashes in rule `patterns`/action content** (mirrors into LLM output) — commas only.
- **Detection rules ship `active: false` + unsigned** at merge (inert, no loader warning, no active-implies-signed trip). Flip to `active: true` + `approved_by: clinical_lead` is the clinician-ratification step, done together with flipping `SAGE_HIGH_RISK_DETECTION` ON. Tests activate rules locally.
- Assert on behavior/flags, never on copy/log strings (required CI check).

## File Structure
- `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` — extend CF-006 patterns; add CF-007 (mania_disclosure), CF-008 (dissociation_disclosure). Ship `active:false`.
- `src/sage_poc/config.py` — add `HIGH_RISK_DETECTION_ENABLED`.
- `src/sage_poc/safety/hr_disclosure.py` (new) — `HR_DISCLOSURE_FLAGS` set + `hr_disclosure_present(clinical_flags, *, flag_enabled)` helper (single source of the "any HR flag, respecting the gate" rule).
- `src/sage_poc/graph.py` — broaden `_route_after_intent` L205 via the helper.
- `src/sage_poc/nodes/skill_select.py` — broaden auto-select L619 via the helper.
- `src/sage_poc/nodes/safety_precedence.py` — `_hr_fired` reads the broadened set (B2b expansion).
- Tests: `tests/test_rules_safety_hr.py` (new), `tests/test_hr_routing.py` (new), `tests/test_hr_crisis_precedence.py` (new, Stage 1.5), extend `tests/fixtures/bot_behaviour_audit/` with HR controls.

---

## Task 1: Detection rules — mania, dissociation, psychosis-variant expansion

**Files:**
- Modify: `src/sage_poc/rules/data/safety/clinical_flag_patterns.json` (CF-006 at L106–134; append CF-007, CF-008)
- Test: `tests/test_rules_safety_hr.py`

**Interfaces:**
- Produces: clinical flags `mania_disclosure`, `dissociation_disclosure`; extended `psychotic_disclosure` coverage. All three rules `active:false` at merge.

- [ ] **Step 1: Write failing rule-detection tests.** For EACH doc trigger phrase (psychosis 14 / mania 10 / dissociation 11, verbatim from spec §"Verbatim trigger sets"), assert the rules engine (with these rules force-activated in the fixture) fires the correct flag. For EACH must-NOT-fire control (spec §"Must-NOT-fire controls": grief "I feel numb since he died" / "nothing's felt real since the funeral"; panic-derealization "everything felt unreal during the panic attack"; idiom "this promotion doesn't feel real"; excitement "I'm so energized about this project" / "I have so much energy today after the gym"), assert NO HR flag fires. Load rules with `active` overridden true in the test fixture.

- [ ] **Step 2: Run — expect FAIL** (CF-007/CF-008 absent; controls may falsely fire on naive patterns — that is the signal to tighten).

- [ ] **Step 3: Author the rules.** Extend CF-006 `patterns` with the missing psychosis variants ("people are following me", "i think people are reading my thoughts", "i don't know what's real anymore", "the voices won't stop", etc.). Add CF-007 `flag_id: mania_disclosure` (mania 10) and CF-008 `flag_id: dissociation_disclosure` (dissociation 11), same JSON shape as CF-006, `match_type: keyword`, `active: false`, `approved_by` OMITTED (unsigned until ratification). Patterns are the doc phrases lowercased + minimum variants. **Tighten dissociation/mania patterns so the controls do not match** (e.g. require the dissociation phrase without a grief/panic co-token, or use longer anchored phrases like "nothing feels real" but rely on the control test to prove "nothing's felt real since the funeral" is excluded — if a pattern is a substring of a control, the pattern is too loose; prefer the doc's full phrase over a short fragment).

- [ ] **Step 4: Run — expect PASS** (all triggers fire, all controls excluded). If a control still fires, tighten the pattern; do NOT weaken the control.

- [ ] **Step 5: Commit** `feat(hr): add mania/dissociation detection rules + psychosis-variant expansion (inactive)`.

---

## Task 2: Config flag + HR-disclosure helper

**Files:**
- Modify: `src/sage_poc/config.py` (flag block ~L269–293)
- Create: `src/sage_poc/safety/hr_disclosure.py`
- Test: `tests/test_hr_routing.py` (helper unit tests)

**Interfaces:**
- Produces: `config.HIGH_RISK_DETECTION_ENABLED: bool`; `hr_disclosure.HR_DISCLOSURE_FLAGS: frozenset`; `hr_disclosure.hr_disclosure_present(clinical_flags, *, flag_enabled) -> bool`.

- [ ] **Step 1: Write failing helper tests.** `hr_disclosure_present(["psychotic_disclosure"], flag_enabled=False)` → True (psychotic always routes). `hr_disclosure_present(["mania_disclosure"], flag_enabled=False)` → False (gated off). `hr_disclosure_present(["mania_disclosure"], flag_enabled=True)` → True. `hr_disclosure_present(["dissociation_disclosure"], flag_enabled=True)` → True. `hr_disclosure_present([], flag_enabled=True)` → False.

- [ ] **Step 2: Run — expect FAIL** (module absent).

- [ ] **Step 3: Implement.** `HR_DISCLOSURE_FLAGS = frozenset({"psychotic_disclosure","mania_disclosure","dissociation_disclosure"})`. `hr_disclosure_present`: True if `psychotic_disclosure` in flags (always), OR (`flag_enabled` AND any of the mania/dissociation flags present). Add `HIGH_RISK_DETECTION_ENABLED: bool = os.getenv("SAGE_HIGH_RISK_DETECTION","false").lower()=="true"` in config.py using the exact idiom at config.py:271.

- [ ] **Step 4: Run — expect PASS.**

- [ ] **Step 5: Commit** `feat(hr): HIGH_RISK_DETECTION_ENABLED flag + hr_disclosure_present helper`.

---

## Task 3: Broaden the live HR route (gated)

**Files:**
- Modify: `src/sage_poc/graph.py` (`_route_after_intent` L205–207)
- Modify: `src/sage_poc/nodes/skill_select.py` (auto-select L619–631)
- Modify: `src/sage_poc/nodes/safety_precedence.py` (`_hr_fired` L37–39)
- Test: `tests/test_hr_routing.py`

**Interfaces:**
- Consumes: `hr_disclosure_present`, `config.HIGH_RISK_DETECTION_ENABLED`.

- [ ] **Step 1: Write failing routing tests.** With flag ON: state carrying `mania_disclosure` (not psychotic) → `_route_after_intent` returns `skill_select` AND `skill_select_node` auto-selects `psychotic_referral` (method `psychotic_disclosure_auto_select` — keep the method name in Stage 1; renamed in Stage 2). Same for `dissociation_disclosure`. With flag OFF: `mania_disclosure`-only state does NOT route to skill_select (falls through unchanged). With flag OFF or ON: `psychotic_disclosure` state routes (never gated off). `psychotic_referral_delivered=True` still suppresses re-selection for all three.

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement.** Replace the literal `"psychotic_disclosure" in (state.get("clinical_flags") or [])` at graph.py:205 and skill_select.py:619 with `hr_disclosure_present(state.get("clinical_flags") or [], flag_enabled=_cfg.HIGH_RISK_DETECTION_ENABLED)` (import `_cfg`/config as done nearby; import the helper). Update `_hr_fired` (safety_precedence.py:39) to `return hr_disclosure_present(state.get("clinical_flags") or [], flag_enabled=config.HIGH_RISK_DETECTION_ENABLED)` (call-time config read, matching apply_precedence). Preserve the `not psychotic_referral_delivered` guard exactly.

- [ ] **Step 4: Run — expect PASS.** Also run `tests/test_routing.py`, `tests/test_skill_select_psychotic.py`, `tests/test_safety_precedence.py` — must stay green (OFF is byte-identical).

- [ ] **Step 5: Run the static state-channel gate** `python scripts/check_state_channels.py` (no new channel added, but confirm clean).

- [ ] **Step 6: Commit** `feat(hr): route mania/dissociation disclosures to referral (flag-gated)`.

---

## Task 4: Stage 1.5 crisis co-check + full-graph red tests

**Files:**
- Test: `tests/test_hr_crisis_precedence.py` (new), `tests/test_hr_routing.py` (full-graph red block)

- [ ] **Step 1: Write the Stage 1.5 crisis-precedence test.** Full-graph `app.ainvoke`, flag ON, rules active: a message carrying BOTH SI and dissociation ("nothing feels real and I want to end it all") → `gate_path == "crisis"` (SI wins, per §5 + ratified order); a dissociation-only message → reaches `psychotic_referral` (referral, not a skill offer). This is the analogue of the crisis>medical verification.

- [ ] **Step 2: Write the full-graph red tests — the four missed drives verbatim.** flag ON, rules active, `app.ainvoke`: "People are following me and watching me" / "I haven't slept for days but I feel amazing and unstoppable" / "I think people are reading my thoughts" / "I feel completely detached from reality, nothing feels real" → each auto-selects `psychotic_referral` (assert `skill_match_method == "psychotic_disclosure_auto_select"`, NOT an `offered_skill_ids` skill). Assert the same four with flag OFF still get their current skill offer (proves the gate).

- [ ] **Step 3: Write the full-graph control block.** flag ON: the must-NOT-fire controls (grief/panic-derealization/idiom/excitement) do NOT reach `psychotic_referral`.

- [ ] **Step 4: Run — expect PASS** (Tasks 1–3 make these green). Any red drive that does not reach the referral is a pattern gap → back to Task 1 (tighten/extend patterns), not a test edit.

- [ ] **Step 5: Commit** `test(hr): Stage 1.5 crisis co-check + full-graph red/control drives`.

---

## Post-tasks (controller, not implementer)
- Final whole-branch review (most-capable model).
- Clinician packet (spec §"Clinician packet"): ratify §HR.0 table + variants + controls; the one dissociation-tier question. **Flip gate.**
- Flip step (post-ratification, separate PR): CF-006/007/008 `active:true` + `approved_by` + signed-fields reconciliation; `SAGE_HIGH_RISK_DETECTION=true` in prod; migration none (no new column in Stage 1); /health/version has no HR readback yet (add in Stage 2).
- AR: zero coverage stated; HR triggers → probe charter.
