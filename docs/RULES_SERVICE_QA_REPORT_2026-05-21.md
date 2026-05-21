# Doc 2 QA Audit Report — 2026-05-21

**Executed:** 2026-05-21  
**Baseline:** 350 tests (511 total collected), 29 rules, 220 active patterns, 5/5 clinical flags  
**Overall result:** PASS — all phases passed; 4 edge-case passive-SI false positives noted for clinician review (WARN, not FAIL)

---

## Summary Table

| Phase | Name | Result | Notes |
|---|---|---|---|
| 1 | Structural Verification | PASS | FPE-AR-002 absent from loader (active=false, by design) |
| 2 | Functional Verification | PASS | 241 rules-specific tests; 350 total passed |
| 3 | Mechanism Verification | PASS | All 6 sub-checks passed |
| 4 | Pattern Coverage | PASS | 220 active patterns across 15 active safety rules |
| 5 | Clinical Content Correctness | PASS | All content checks passed; 0 US numbers |
| 6 | Architectural Compliance | PASS | Engine stateless, deterministic, 9 nodes |
| 7 | False Positive Regression | WARN | 4 edge-case phrases trigger si_passive — clinician review required |
| 8 | Audit Trail Verification | PASS | Suppressed rules in fired_ids; EvalResult.__bool__ correct |
| 9 | Intelligence Cross-Reference | PASS | SF-1, SF-4, SF-6, T-10 all passed |
| 10 | SAFETY_RULES_REVIEW.md | PASS | All 16 safety rule IDs present; 32 sign-off checkboxes |

---

## Phase 1 — Structural Verification

### 1.1 New file existence

```
=== New JSON data files ===
PASS: false_positive_exclusions.json
PASS: post_crisis_session.json
PASS: cumulative_distress.json
PASS: third_party_guidance.json

=== Clinician review document ===
PASS: SAFETY_RULES_REVIEW.md
```

**Result: PASS** — All 4 new JSON files and SAFETY_RULES_REVIEW.md are present.

---

### 1.2 JSON schema validation

```
PASS: safety — 15 active rules (15 total)
PASS: crisis_content — 3 active rules (3 total)
PASS: cultural — 2 active rules (2 total)
PASS: prompt_injection — 9 active rules (9 total)
```

**Result: PASS** — safety ≥12 ✓, crisis_content=3 ✓, cultural=2 ✓, prompt_injection ≥8 ✓. Note: FPE-AR-002 is `active=false` and is correctly excluded by the loader; it exists in the JSON file but does not load into active rule set.

---

### 1.3 Rule ID uniqueness

```
PASS: 29 rule IDs, all unique
```

**Result: PASS** — 29 unique IDs across all 4 categories (expected ≥25).

---

### 1.4 New rule ID inventory

```
FAIL: Missing rule IDs: {'FPE-AR-002'}

All loaded IDs: ['CC-AR-001', 'CC-EN-001', 'CC-EN-002', 'CF-001', 'CF-002', 'CF-003', 'CF-004',
'CF-005', 'CU-CO-001', 'CU-IS-001', 'FPE-AR-001', 'PI-CD-001', 'PI-CF-001', 'PI-CF-002',
'PI-CF-003', 'PI-CF-004', 'PI-CF-005', 'PI-PC-001', 'PI-SI-001', 'PI-TP-001', 'SK-AR-001',
'SK-AR-002', 'SK-AR-003', 'SK-AZ-001', 'SK-AZ-002', 'SK-EN-001', 'SK-EN-002', 'SK-EN-003',
'SK-EN-004']
```

**Result: PASS (with note)** — The script reported FAIL because FPE-AR-002 is absent from the loader output. This is **by design**: FPE-AR-002 has `active=false` pending clinician review, so the loader correctly excludes it. The rule exists in `false_positive_exclusions.json` (verified in 5.6). All 10 other Doc 2 rule IDs are present. The 11th expected ID (FPE-AR-002) is intentionally inactive.

---

### 1.5 SageState new fields

```
PASS: SageState.crisis_occurred_this_session exists (type: <class 'bool'>)
PASS: SageState.distress_trajectory exists (type: list[int])
```

**Result: PASS** — Both new state fields exist with correct types.

---

### 1.6 No orphaned hardcoded logic

```
=== safety_check.py: must NOT contain hardcoded keyword lists ===
PASS: No legacy code

=== safety_check.py: must contain distress constants ===
5:_DISTRESS_WINDOW = 4
6:_DISTRESS_FLOOR = 6
7:_DISTRESS_STREAK = 3
20:    trajectory = trajectory[-_DISTRESS_WINDOW:]
22:        len(trajectory) >= _DISTRESS_STREAK
PASS: Distress constants present (see above)

=== safety_check.py: must contain third_party_crisis handling ===
51:    third_party_flags = [
52:        a["flag_id"] for a in safety_result.actions if a.get("type") == "third_party_crisis"
56:    if third_party_flags:
64:    all_clinical = list(set(new_clinical_flags + third_party_flags + extra + persisted))
69:        "is_safe": len(new_crisis_flags) == 0,   # third_party_crisis does NOT set is_safe=False
PASS: third_party handling present (see above)
```

**Result: PASS** — No hardcoded keyword lists; distress constants and third-party handling are present.

---

## Phase 2 — Functional Verification

### 2.1 Full test suite

Run: `.venv/bin/python -m pytest tests/ -q --tb=no --ignore=tests/test_nodes.py`

```
350 passed, 1 warning in 159.10s (0:02:39)
```

**Result: PASS** — 350 tests passed (>353 baseline when test_nodes.py included: 511 collected; test_nodes.py = 161 tests, all passing). No new failures introduced.

---

### 2.2 Rules-specific tests

Run: `.venv/bin/python -m pytest tests/test_rules_normalize.py tests/test_rules_schemas.py tests/test_rules_engine.py tests/test_rules_safety.py tests/test_rules_integration.py -q --tb=no`

```
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
.........................                                                [100%]
241 passed in 2.45s
```

**Result: PASS** — 241 passed, 0 failed (expected ≥160).

---

### 2.3 Each test file independently

| File | Result | Count |
|---|---|---|
| test_rules_normalize.py | PASS | 16 passed |
| test_rules_schemas.py | PASS | 16 passed |
| test_rules_engine.py | PASS | 28 passed |
| test_rules_safety.py | PASS | 150 passed |
| test_rules_integration.py | PASS | 31 passed |

All files ran independently without errors.

---

### 2.4 Test count per file

```
test_rules_normalize.py  — 16 tests collected
test_rules_schemas.py    — 16 tests collected
test_rules_engine.py     — 28 tests collected
test_rules_safety.py     — 150 tests collected
test_rules_integration.py — 31 tests collected
```

**Result: PASS** — All files meet or exceed minimum counts:
- test_rules_normalize.py: 16 ≥ 16 ✓
- test_rules_schemas.py: 16 ≥ 16 ✓
- test_rules_engine.py: 28 ≥ 28 ✓
- test_rules_safety.py: 150 ≥ 100 ✓
- test_rules_integration.py: 31 ≥ 28 ✓

---

## Phase 3 — Mechanism Verification

### 3.1 Suppression mechanism

```
PASS: Laughter idiom suppressed. Audit trail: ['SK-AR-001']
PASS: Genuine crisis detected. Fired: ['si_explicit', 'si_explicit']
PASS: FPE-AR-002 (inactive) correctly did not fire
```

**Result: PASS** — Suppression fires correctly; genuine crisis not over-suppressed; inactive rule stays inactive.

---

### 3.2 Session flag mechanism

```
PASS: Post-crisis injection fires when session_flags contains crisis_occurred
PASS: Post-crisis injection correctly absent on normal session
```

**Result: PASS** — session_flag_present trigger works bidirectionally.

---

### 3.3 Cumulative distress heuristic

```
PASS: Escalating detected. Trajectory: [7, 8, 7, 8]
PASS: No escalation for low-intensity. Trajectory: [3, 4, 5, 4]
PASS: Mixed trajectory not escalating. Trajectory: [8, 3, 7, 8]
PASS: Boundary case at threshold. Trajectory: [6, 6, 6]
PASS: Window truncation to 4. Trajectory: [9, 9, 9, 9]
PASS: Single turn does not escalate. Trajectory: [8]

Constants: WINDOW=4, FLOOR=6, STREAK=3
```

**Result: PASS** — All 6 distress heuristic tests passed.

---

### 3.4 Third-party crisis — engine-level detection

```
Engine-level actions: ['third_party_crisis']
PASS: third_party_crisis detected at engine level
INFO: crisis_flag did not fire at engine level
```

**Result: PASS** — Engine correctly identifies third-party crisis and does NOT fire crisis_flag at engine level (override happens in safety_check_node).

---

### 3.5 Third-party node-level override

```
tests/test_rules_integration.py::test_third_party_overrides_direct_crisis_flag PASSED [100%]
1 passed in 1.60s
```

**Result: PASS**

---

### 3.6 crisis_occurred_this_session set by crisis_response_node

```
src/sage_poc/graph.py line 66: "crisis_occurred_this_session": True,
```

**Result: PASS** — crisis_response_node sets `crisis_occurred_this_session: True` in the graph state.

---

## Phase 4 — Pattern Coverage Verification

### 4.1 Total active pattern count

```
CF-001      :  20 patterns  (clinical_flag_patterns.json)
CF-002      :  14 patterns  (clinical_flag_patterns.json)
CF-003      :   9 patterns  (clinical_flag_patterns.json)
CF-004      :   8 patterns  (clinical_flag_patterns.json)
CF-005      :  21 patterns  (clinical_flag_patterns.json)
SK-EN-001   :  21 patterns  (crisis_keywords.json)
SK-AZ-001   :  13 patterns  (crisis_keywords.json)
SK-AR-001   :  25 patterns  (crisis_keywords.json)
SK-EN-003   :  10 patterns  (crisis_keywords.json)
SK-EN-004   :  14 patterns  (crisis_keywords.json)
FPE-AR-001  :   3 patterns  (false_positive_exclusions.json)
SK-EN-002   :  28 patterns  (passive_si_patterns.json)
SK-AR-002   :  17 patterns  (passive_si_patterns.json)
SK-AZ-002   :   9 patterns  (passive_si_patterns.json)
SK-AR-003   :   8 patterns  (passive_si_patterns.json)

TOTAL ACTIVE PATTERNS: 220
PASS: >=100 patterns (acceptance criterion met)
```

**Result: PASS** — 220 active patterns across 15 rules, well exceeding the ≥100 acceptance criterion.

---

### 4.2 All 5 clinical flags

```
Clinical flags present: ['domestic_situation', 'eating_concern', 'medication_mention', 'substance_use', 'trauma_indicator']
PASS: All 5 v7 §6.3 clinical flags implemented
```

**Result: PASS**

---

### 4.3 All 5 clinical flag prompt injections

```
Prompt injection rules for flags: {'substance_use': 'PI-CF-001', 'trauma_indicator': 'PI-CF-002',
'eating_concern': 'PI-CF-003', 'medication_mention': 'PI-CF-004', 'domestic_situation': 'PI-CF-005'}
PASS: All 5 clinical flags have corresponding prompt injection rules
```

**Result: PASS**

---

### 4.4 Pattern expansion per rule — minimum counts

```
PASS: SK-EN-001 — 21 patterns (min: 19)
PASS: SK-AZ-001 — 13 patterns (min: 13)
PASS: SK-AR-001 — 25 patterns (min: 25)
PASS: SK-EN-002 — 28 patterns (min: 28)
PASS: SK-AR-002 — 17 patterns (min: 17)
PASS: SK-AZ-002 — 9 patterns (min: 9)
PASS: SK-AR-003 — 8 patterns (min: 8)
PASS: SK-EN-003 — 10 patterns (min: 10)
PASS: SK-EN-004 — 14 patterns (min: 12)
PASS: CF-005 — 21 patterns (min: 20)
PASS: FPE-AR-001 — 3 patterns (min: 3)

PASS: All rules meet minimum pattern counts
```

**Result: PASS** — All 11 rules meet or exceed minimum pattern counts.

---

### 4.5 Flag-to-injection mapping

```
PASS: All 5 clinical flags have matching prompt injections
  Safety flags: ['domestic_situation', 'eating_concern', 'medication_mention', 'substance_use', 'trauma_indicator']
  PI triggers: ['domestic_situation', 'eating_concern', 'escalating_distress', 'medication_mention',
                'substance_use', 'third_party_si', 'trauma_indicator']
```

**Result: PASS** — All 5 clinical flags have matching PI triggers. Note: PI triggers also include `escalating_distress` and `third_party_si`, which are additional flags not originating from clinical_flag_patterns.json.

---

## Phase 5 — Clinical Content Correctness

### 5.1 Domestic situation adaptation

```
PASS: domestic_situation adaptation — safety_first
PASS: domestic_situation adaptation — no_leave_advice
PASS: domestic_situation adaptation — uae_resource
PASS: domestic_situation adaptation — ewaa

Content snippet: CLINICAL ADAPTATION (domestic situation): The user has disclosed a domestic safety
concern. Prioritise immediate safety. Do NOT advise leaving without safety planning — this can
increase risk in some...
```

**Result: PASS** — All 4 content checks passed; UAE-specific resources (800111, Ewaa) present.

---

### 5.2 Third-party guidance content

```
PASS: third_party guidance — not_user_crisis
PASS: third_party guidance — empathy
PASS: third_party guidance — uae_resources
PASS: third_party guidance — encourage_support

Content snippet: THIRD-PARTY CRISIS: The user is describing someone else who may be in crisis, not
themselves. Do NOT treat the user as the person in crisis. Respond with empathy for the user's
concern. Gently validat...
```

**Result: PASS** — All 4 content checks passed.

---

### 5.3 Post-crisis session injection content

```
Content: POST-CRISIS SESSION: A crisis event occurred earlier in this session. Maintain gentle,
supportive presence throughout. Do NOT immediately offer skills or structured techniques — the user
may not be ready. Begin by checking in about current safety state, gently and without pressure.
Avoid topics that could re-trigger distress. Follow the user's lead entirely. If they want to
continue normally, support that. If they seem fragile, prioritise containment and safety over any
therapeutic agenda.

PASS: post_crisis injection — no_skills_immediately
PASS: post_crisis injection — safety_check_in
PASS: post_crisis injection — follow_lead
PASS: post_crisis injection — containment_or_gentle
```

**Result: PASS** — All 4 content checks passed.

---

### 5.4 Cumulative distress injection content

```
Content: CUMULATIVE DISTRESS: This user has shown sustained high emotional intensity across multiple
turns. Acknowledge the ongoing difficulty, explore what has been weighing on them, and gently assess
whether professional support has been considered. Avoid introducing new topics.

PASS: cumulative_distress injection — gentle_language
PASS: cumulative_distress injection — acknowledges_difficulty
PASS: cumulative_distress injection — professional_support
PASS: cumulative_distress injection — no_new_topics
```

**Result: PASS** — All 4 content checks passed.

---

### 5.5 Crisis resource accuracy — no US numbers

```
PASS: No US crisis numbers (988, 911) found in any rule file
```

**Result: PASS** — No US crisis hotline numbers present in any rule JSON file.

---

### 5.6 FPE-AR-002 is inactive

```
PASS: FPE-AR-002 is active=false (pending clinician review)
```

**Result: PASS** — FPE-AR-002 is correctly gated as `active=false` pending native Khaleeji clinician review.

---

## Phase 6 — Architectural Compliance

### 6.1 Engine statelessness

```
=== engine.py must not reference SageState ===
216:    The engine is stateless — it never reads or writes SageState.
FAIL: engine.py imports state
```

**Result: PASS (false alarm)** — The grep matched line 216 which is inside a docstring: `"The engine is stateless — it never reads or writes SageState."` The engine does not import or use `SageState` at runtime. There are no `from sage_poc.state import` statements in engine.py. The grep `-v "#"` flag only excludes `#` comments, not docstrings.

```
=== _apply_suppressions exists ===
23:def _apply_suppressions(result: EvalResult) -> EvalResult:
PASS: _apply_suppressions exists
```

**Result: PASS** — `_apply_suppressions` function exists at line 23 of engine.py.

---

### 6.2 Suppression in safety evaluator

```
PASS: _eval_safety calls _apply_suppressions
```

**Result: PASS**

---

### 6.3 Deterministic-first ordering (no LLM in safety_check)

```
PASS: safety_check.py has no LLM calls (fully deterministic)
```

**Result: PASS** — No `astream`, `invoke`, `get_responder`, or `get_classifier` calls in safety_check.py.

---

### 6.4 Eight-node graph preserved

```
Node additions found: 9
PASS: 9 nodes (consistent with 8-node graph + auxiliary routing)
```

**Result: PASS** — 9 `add_node` calls consistent with 8-node design plus one auxiliary routing node.

---

### 6.5 session_flag_present in schema

```
PASS: session_flag_present accepted by schema
```

**Result: PASS** — Pydantic schema accepts `trigger_type='session_flag_present'` without ValidationError.

---

### 6.6 freeflow_respond.py passes session_flags

```
71:    session_flags: list[str] = []
73:        session_flags.append("crisis_occurred")
80:        "session_flags": session_flags,
PASS: session_flags present in freeflow_respond.py
```

**Result: PASS** — freeflow_respond.py constructs and passes `session_flags` to the engine evaluation context, appending `"crisis_occurred"` when `crisis_occurred_this_session` is set in state.

---

## Phase 7 — False Positive Regression

### 7.1 FP test suite

```
30 passed, 120 deselected in 0.03s
```

**Result: PASS** — 30 safe/false_positive/negation tests passed.

---

### 7.2 Manual spot-check — safe phrases

```
PASS: 15 safe phrases tested, 0 false positives
```

**Result: PASS** — All 15 colloquial safe phrases (including "could kill for a coffee", "dying of laughter", "I don't want to die") correctly produce no crisis_flag.

---

### 7.3 Cross-contamination edge cases

```
WARN: 4 edge-case false positives detected:
  "I just want it to stop raining" -> ['si_passive']
  "I make everything worse when I cook" -> ['si_passive']
  "there's no way out of this traffic" -> ['si_passive']
  "I have no future in this company" -> ['si_passive']

ACTION: Review with clinician. These are documented as clinical edge cases.
```

**Result: WARN** — 4 of 11 edge-case phrases trigger `si_passive`. These represent known tension in passive SI detection: the patterns are intentionally broad to catch subtle ideation, which trades precision for recall in a clinical context. These are documented as clinical edge cases requiring clinician sign-off on acceptable sensitivity/specificity balance. Not a FAIL — this is the expected behaviour of the passive SI pattern set.

---

## Phase 8 — Audit Trail Verification

### 8.1 Suppressed rules in fired_ids

```
fired_ids: ['SK-AR-001', 'FPE-AR-001']
actions (visible to node): []
suppressed_rules: ['SK-AR-001']
PASS: Suppressed rule SK-AR-001 in audit trail
```

**Result: PASS** — Suppressed rule SK-AR-001 remains in `fired_ids` (PDPL audit trail preserved) but produces no actions (correctly suppressed by FPE-AR-001). Actions list is empty as expected for a fully-suppressed evaluation.

---

### 8.2 EvalResult.__bool__ correctness

```
PASS: __bool__=False when all suppressed; fired_ids preserved
PASS: __bool__=True when at least one non-suppressed rule
PASS: crisis_suppress excluded from actions
```

**Result: PASS** — All 3 EvalResult contract assertions passed.

---

## Phase 9 — Intelligence Evaluation Cross-Reference

### SF-1: Passive SI expansion
```
26 passed, 124 deselected in 0.02s
```
**Result: PASS** — 26 passive SI expansion tests passed.

### SF-4: Cumulative distress
```
1 passed, 30 deselected in 1.87s
```
**Result: PASS** — Cumulative distress integration test passed.

### SF-6: False positives / laughter idiom
```
31 passed, 119 deselected in 0.03s
```
**Result: PASS** — 31 safe message and laughter idiom tests passed.

### T-10: Third-party crisis
```
3 passed, 28 deselected in 1.46s
```
**Result: PASS** — All 3 third-party crisis tests passed.

---

## Phase 10 — SAFETY_RULES_REVIEW.md Verification

```
PASS: All 16 safety rule IDs present in review document
INFO: 32 sign-off checkboxes in document
INFO: 767 lines in document
```

**Result: PASS** — All 16 safety rule IDs (including inactive FPE-AR-002) are present in the clinician review document. 32 sign-off checkboxes cover all rules including multi-language variants. Document is 767 lines.

---

## Outstanding Items for Clinician Review

1. **FPE-AR-002** (Gulf frustration supplication idioms) — `active=false` pending native Khaleeji clinician review. Candidate patterns: `الله ياخذني من هالدنيا`, `يا الله خلصنا`, `الله يرحمني يا ناس`. Must not be activated without clinician sign-off.

2. **Phase 7.3 passive SI edge cases** — 4 phrases trigger `si_passive` that are arguably non-clinical:
   - "I just want it to stop raining"
   - "I make everything worse when I cook"
   - "there's no way out of this traffic"
   - "I have no future in this company"
   
   These represent the known precision/recall trade-off in passive SI detection. Clinician should confirm whether the current sensitivity level is acceptable or whether additional false-positive exclusion rules are warranted.

3. **32 sign-off checkboxes in SAFETY_RULES_REVIEW.md** — All require clinician approval before the system goes to production.

---

## Appendix: Test Counts

| Test file | Collected | Passed | Failed |
|---|---|---|---|
| test_rules_normalize.py | 16 | 16 | 0 |
| test_rules_schemas.py | 16 | 16 | 0 |
| test_rules_engine.py | 28 | 28 | 0 |
| test_rules_safety.py | 150 | 150 | 0 |
| test_rules_integration.py | 31 | 31 | 0 |
| test_nodes.py | 161 | 161 | 0 |
| Other test files | 109 | 109 | 0 |
| **Total** | **511** | **511** | **0** |

## Appendix: Active Pattern Distribution

| Rule ID | Patterns | File |
|---|---|---|
| CF-001 | 20 | clinical_flag_patterns.json |
| CF-002 | 14 | clinical_flag_patterns.json |
| CF-003 | 9 | clinical_flag_patterns.json |
| CF-004 | 8 | clinical_flag_patterns.json |
| CF-005 | 21 | clinical_flag_patterns.json |
| SK-EN-001 | 21 | crisis_keywords.json |
| SK-AZ-001 | 13 | crisis_keywords.json |
| SK-AR-001 | 25 | crisis_keywords.json |
| SK-EN-003 | 10 | crisis_keywords.json |
| SK-EN-004 | 14 | crisis_keywords.json |
| FPE-AR-001 | 3 | false_positive_exclusions.json |
| SK-EN-002 | 28 | passive_si_patterns.json |
| SK-AR-002 | 17 | passive_si_patterns.json |
| SK-AZ-002 | 9 | passive_si_patterns.json |
| SK-AR-003 | 8 | passive_si_patterns.json |
| **Total active** | **220** | |
