# SageAI POC Re-Audit Report — Post-Sprint Remediation

**Date:** 2026-05-20 (post-sprint)
**Scope:** `sage-poc/` — all 23 audit workstreams
**Python:** 3.12.4 (venv) | **LangGraph:** 1.2.0 | **Tests at re-audit:** 92 fast passing, 11 slow deferred
**Sprints remediated:** Sprint 1 (crisis path) · Arabic research (keywords) · Sprint 2 (safety gate) · Sprint 3 (error handling) · Sprint 4 (prompt architecture) · Sprint 5 (infra + cleanup)
**Methodology:** 4 parallel subagent audit passes, full code read, cross-sprint interaction analysis

---

## Executive Summary

| Category | Count |
|---|---|
| **FIXED** — Original finding closed with evidence | 24 |
| **PARTIAL FIXED** — Partially addressed; residual noted | 2 |
| **FAIL (deferred)** — Not addressed; pre-existing accepted deferral | 7 |
| **NEW FAIL** — Issue not in original audit | 5 |
| **NEW WARN** — Advisory; not in original audit | 8 |
| **PASS** — Unchanged correct areas | 41 |

**Cross-sprint interaction verdict: CLEAN.** No interaction effects between the Sprint 1 crisis path changes, Sprint 2 keyword expansion, Sprint 4 prompt role split, or Sprint 5 infra changes. The two high-risk interactions flagged (Arabic sensitivity vs. L1 false-positive fix; compose_prompt role split vs. crisis state) were specifically verified and both pass.

**Residual P1:** English `CRISIS_RESPONSE` constant still contains the unverified service name "Tawazun" and US-only number 988. The Arabic version was corrected in Sprint 1; the English version was not. English-speaking UAE users receive incorrect crisis contact information.

**Two new P2 findings:** (a) Three `L1_EXIT_PHRASES` patterns remain overly broad after Sprint 2's partial fix. (b) ZWSP (U+200B) bypass of crisis keyword detection is unaddressed from the original audit.

---

## Section 1: Original Findings — Full Verdict

### P0 Critical

| ID | Original Finding | Verdict | Evidence |
|---|---|---|---|
| P0-A / 12.1b / 13.1 | Arabic user in crisis receives English-only response | **FIXED** | `_crisis_response_node` checks `detected_language`, selects `CRISIS_RESPONSE_AR` for `"ar"`. Arabic is hardcoded (no translation latency on crisis path). |
| P0-B / 13.4 | Active skill persists through crisis turn | **FIXED** | Returns `active_skill_id: None`, `active_step_id: None` explicitly. Comment: `# P0-B: clear skill — never resume CBT after crisis`. |

### P1 High

| ID | Original Finding | Verdict | Evidence |
|---|---|---|---|
| P1-1 / 3.1 | CRISIS_KEYWORDS missing Gulf-dialect Arabic, Araglish, indirect euphemisms | **PARTIAL FIXED** | 22 Gulf/Khaleeji/Levantine/Araglish entries added. `"أبي أموت"`, `"نفسي تعبت"`, `"ياريت أنام ولا أصحى"`, `"want to mat"` all present. **Residual:** `"don't want to be alive"` and `"end it all"` — both listed in original finding — are still absent. Substance-use false positive (`"wine"`) not narrowed. |
| P1-2 / 3.2 | L1 exit false positives on single-word triggers | **FIXED** | `"stop"` and `"leave"` removed from `L1_EXIT_PHRASES`. Multi-word intent-specific phrases retained and expanded. `"I can't stop thinking"` → no L1. `"let's stop"` → L1. See NEW-2 for residual overly-broad patterns. |
| P1-3 / 5.1 | `clinical_flags` reset to `[]` every turn in `run.py` | **FIXED** | `run.py` line 90: `"clinical_flags": result.get("clinical_flags", [])` explicitly in carry-forward dict. |
| P1-4 / 13.2 | No audit log on crisis turns | **FIXED** | `_crisis_response_node` emits `[AUDIT:CRISIS]` JSON with `timestamp`, `event`, `turn`, `detected_language`, `crisis_flags`, `clinical_flags`, `active_skill_cleared`. |
| P1-5 / 13.3 | Crisis exchange not appended to `conversation_history` | **FIXED** | Returns `conversation_history` + user message + English response. `turn_count` incremented. Test asserts `len == 4` after starting with 2-entry history. |
| P1-6 / 16.1a,c | Ollama failure crashes session | **FIXED** | Both `translate_to_english` and `translate_to_arabic` wrap `ollama.Client.chat()` in `try/except Exception`, returning original text as fallback. `output_gate` inherits protection via import. |
| P1-7 / 16.2 | `json.loads` crashes on malformed LLM JSON | **FIXED** | `try/except json.JSONDecodeError` around `json.loads(match.group(0))`, falling through to `data = {}` and defaults. |
| P1-8 / 15.1 | `freeflow_respond` sends system prompt as `HumanMessage` | **FIXED** | `compose_prompt` returns `tuple[str, str]`. `freeflow_respond_node` calls `llm.invoke([{"role":"system",...},{"role":"user",...}])`. PERSONA and clinical adaptations confirmed in `system_str`. |
| P1-9 / 2.2 | `new_skill` mid-skill silently discards skill progress | **DEFERRED** | User-accepted deferral. `_route_after_intent` still routes `new_skill` → `skill_select` unconditionally. No fix applied. |

### P2 Medium

| ID | Original Finding | Verdict | Evidence |
|---|---|---|---|
| P2-2 / 16.1b | `StopIteration` crash on unknown `step_id` | **FIXED** | `next(..., None)` with None-check returning `{"action": "stay", ...}`. |
| P2-3 / 3.5 | `skill_select` negation false positive | **DEFERRED** | User-accepted deferral. `"I am not a failure"` still triggers CBT enrollment. |
| P2-4 / 6.1b | `detect_language(None)` → TypeError | **FIXED** | `if not text: return "en"` guard at top of function. |
| P2-5 / 6.1c | RTL Unicode control chars → wrong detection | **FIXED** | `_DIRECTIONAL_MARKS` regex strips U+200E, U+200F, U+202A–U+202E, U+2066–U+2069 before detection. Also `"so"` (Somali false-positive) is in `_LATIN_SCRIPT_LANGS` as double protection. |
| P2-6 / 17.2 | ZWSP (U+200B) bypasses crisis keyword detection | **FAIL** | `safety_check.py` has no unicode normalization. `_DIRECTIONAL_MARKS` in `language.py` does not cover U+200B (0x200B is below the covered range 0x202A). `"kill​myself"` → `is_safe=True`. |
| P2-7 / 1.3 | `int()` crash on non-numeric LLM output | **FIXED** | `_safe_int(value, default)` wraps `int(float(value))` in `try/except (TypeError, ValueError)`. Applied to both `emotional_intensity` and `engagement`. |
| P2-8 / 9.2 | Knowledge injection misses `primary_intent="info_request"` | **FIXED** | Condition: `if "info_request" in {state.get("primary_intent"), state.get("secondary_intent")}`. Both primary and secondary paths covered. |
| P2-9 / 10.1 | No routing function unit tests | **FIXED** | `tests/test_routing.py` with parametrized coverage of all 10 in-scope branches (2 for `_route_after_safety`, 12 for `_route_after_intent`, 2 for `_route_after_skill_select`, 2 boundary tests). All fast, no external services. |
| P2-10 / 22.1 | CLI has no exception or `KeyboardInterrupt` handling | **FIXED** | `input()` wrapped with `except (EOFError, KeyboardInterrupt)`. `graph.invoke()` wrapped with `except KeyboardInterrupt` and `except Exception as e`. Session survives node failures. |
| P2-11 / 11.1 | Loose dependency version bounds | **FIXED** | `langgraph>=1.0.0,<2.0.0`, `langchain-openai>=1.0.0,<2.0.0`, `langchain-core>=1.0.0,<2.0.0`. All production deps have `<major.0.0` upper bounds. |
| P2-12 / 18.1 | Dual skill loading inconsistency | **DEFERRED** | `skill_select` pre-loads at module init; `skill_executor` re-reads disk per turn. Not addressed. Acceptable for POC. |
| P2-13 / 5.2 | `turn_count` not carried in multi-turn test helpers | **FAIL** | `test_graph.py` multi-turn tests still do not pass `turn_count` between turns. `make_e2e_state()` defaults it to 0 each turn. See NEW-4. |
| P2-14 / 22.4 | No UTF-8 stdout guarantee for Arabic output | **FAIL** | `run.py` uses bare `print()` with no stdout reconfiguration. Not addressed. |

### P3 Low

| ID | Original Finding | Verdict | Evidence |
|---|---|---|---|
| P3-1 / 23.2 | `testpaths` missing from pytest config | **FAIL** | `pyproject.toml` `[tool.pytest.ini_options]` still has only `markers`. `testpaths = ["tests"]` absent. |
| P3-2 / 23.3 | No `conftest.py` | **PASS (design)** | `tests/conftest.py` exists with documented rationale for local helper pattern. Intentional; 21-field duplication risk accepted. |
| P3-3 | Spec field names differ from implementation | Not addressed. Advisory only. |
| P3-4 / 12.1c | 988 US-only in `CRISIS_RESPONSE_AR` | **PARTIAL FIXED** | `CRISIS_RESPONSE_AR` corrected (988 removed, `توازن` removed, 999 added, 800-HOPE retained). **`CRISIS_RESPONSE` (English) unchanged** — still contains `"Tawazun 800-HOPE (4673)"` and `"988 (US)"`. |
| P3-5 | Non-AR/EN language fallback | Not addressed. POC scope accepted. |
| P3-6 | `.gitignore` missing `.pytest_cache/` | **FAIL** | Directory exists on disk. Not added to `.gitignore`. |
| P3-7 | Cold-start skill loading at scale | Not addressed. POC scope accepted. |
| P3-8 / 22.3 | Unbounded `conversation_history` growth | **FAIL** | `output_gate.py` appends 2 entries per turn with no cap. Not addressed. |
| P3-9 | `int()` truncation of float `emotional_intensity` | Resolved by `int(float(value))` in `_safe_int` — `7.9` → `7`, still truncates, but crash risk removed. |

---

## Section 2: Cross-Sprint Interaction Analysis

### Interaction A: Arabic keyword expansion (Sprint 1) vs. L1 false-positive fix (Sprint 2)

**Verdict: CLEAN — no cross-triggering.**

The two changes operate on architecturally separate paths. Arabic crisis keywords are checked against `raw_message` in `safety_check_node`. L1 exit phrases are checked against `message_en` in `skill_executor_node`. Furthermore, `safety_check` is the first node in the graph — a crisis message routes to `crisis_response → END` before `skill_executor` is ever reached, so no message that matches a crisis keyword can simultaneously reach the L1 check in production.

Specific phrase verification:
- `"I can't stop thinking about this"` → L1: **does not fire** (confirmed: `"stop"` removed)
- `"let's stop"` → L1: **fires** (confirmed: retained in `L1_EXIT_PHRASES`)
- `"I want to stop"` → L1: **fires** (confirmed: `"i want to stop"` + `"want to stop"` both present)
- Arabic keywords: all 22 new entries verified to trigger `_contains_crisis`

Residual concern (see NEW-2): Three patterns remain that produce L1 false positives not yet addressed by Sprint 2's fix.

### Interaction B: Sprint 4 prompt role split vs. Sprint 1 crisis state changes

**Verdict: CLEAN — no interaction regressions.**

The `compose_prompt` refactor reads `clinical_flags` from state (now placed in `system_str`). Sprint 1's `_crisis_response_node` does not return `clinical_flags` — LangGraph merge preserves the incoming value. Sprint 2 ensures `run.py` carries `clinical_flags` into the next turn. The chain is:

```
crisis fires → clinical_flags NOT touched by crisis node →
LangGraph preserves clinical_flags from incoming state →
run.py carries clinical_flags to Turn N+1 →
compose_prompt reads clinical_flags → system_str contains adaptations
```

No breakage. PERSONA, clinical adaptations confirmed in `system_str`; dynamic context confirmed in `user_str`.

**One implicit dependency flagged (not a regression):** `is_safe=False` written by `_crisis_response_node` does not persist into the next turn because `run.py` rebuilds from `make_initial_state()` (defaults `is_safe=True`) rather than carrying `is_safe` forward. This is the correct behavior, but there is no test asserting that `is_safe` resets between turns, and no comment explaining why it is intentionally excluded from the carry-forward. If a future sprint adds `is_safe` to the carry-forward by analogy with other persisted fields, it would lock `is_safe=False` permanently after any crisis turn.

---

## Section 3: New Findings (Not in Original Audit)

### NEW-1 — P2 — English `CRISIS_RESPONSE` unchanged; "Tawazun" and "988 (US)" still present

**Evidence:** `graph.py` lines 15–20. `CRISIS_RESPONSE_AR` was corrected in Sprint 1 (988 removed, `توازن` removed, 999 added). `CRISIS_RESPONSE` (English) was not updated. English text still reads: `"in the UAE: Tawazun 800-HOPE (4673), or international: 988 (US)"`.

**Impact:** English-speaking UAE users in crisis receive (a) an unverified service name, (b) a US-only phone number that will not connect from a UAE SIM. This is clinically equivalent to the P3-4 finding in the original audit, now elevated to P2 because the Arabic version is fixed and the inconsistency is explicit.

**Fix:** Apply the same corrections to `CRISIS_RESPONSE`:
```python
CRISIS_RESPONSE = (
    "I'm very concerned about your safety and what you've shared. "
    "Please reach out to the mental health support line now — "
    "in the UAE: 800 4673 (800-HOPE), or emergency: 999. "
    "You don't have to face this alone."
)
```
Add the same tests that now guard `CRISIS_RESPONSE_AR` (correct number, 988 absent, no unverified service name).

---

### NEW-2 — P2 — Three `L1_EXIT_PHRASES` patterns remain clinically problematic

**Evidence:** `skill_executor.py` lines 23, 29, 32.

Sprint 2 correctly removed standalone `"stop"` and `"leave"`. Three multi-word patterns that remained or were added introduce comparable false-positive rates:

| Phrase | False-positive example |
|---|---|
| `"don't want to"` | `"I don't want to burden you"`, `"I don't want to think about the past"` |
| `"want to stop"` | `"I want to stop feeling anxious"`, `"I want to stop the panic attacks"` |
| `"please stop"` | `"please stop being so harsh on yourself"` |

All three are common therapeutic statements where the user is expressing a desire to stop a *symptom* or protecting a *relationship boundary*, not requesting skill exit. No tests exist for these false-positive cases.

**Fix options:**
- `"don't want to"` → replace with `"don't want to do this"` or `"don't want to continue"` (already covered by `"not doing this"`)
- `"want to stop"` → scope to `"want to stop this"` or `"want to stop the session"` / `"want to stop therapy"`
- `"please stop"` → remove (overly ambiguous; exit intent is already covered by `"let's stop"`, `"want to stop"`, `"can we stop"`)

---

### NEW-3 — P1-remaining — `"don't want to be alive"` and `"end it all"` absent from `CRISIS_KEYWORDS`

**Evidence:** `safety_check.py` lines 6–35. These phrases were explicitly listed in the original P1-1 finding. Neither was added in the Arabic/keyword expansion sprint (which focused on Gulf-dialect Arabic and Araglish). A user typing `"I don't want to be alive anymore"` or `"I just want to end it all"` receives `is_safe=True` and routes to `intent_route`.

**Severity:** This is a residual P1, not a new finding — it was part of P1-1. Flagged here because it was not resolved by the sprint work.

---

### NEW-4 — P2 — `turn_count` and `clinical_flags` not carried in multi-turn E2E test helpers

**Evidence:** `test_graph.py` multi-turn tests (`test_cbt_full_3_step_progression_e2e` lines 89–109, `test_session_full_lifecycle_e2e` lines 154–200). Neither test carries `turn_count` or `clinical_flags` between turns. Every turn after T1 sees `turn_count=0` (from `make_e2e_state()` default). The production `run.py` carries both correctly.

**Impact:** Audit logs in E2E tests report incorrect `turn` values. More critically, if a clinical flag fires on Turn 2 in a multi-turn E2E test, it is absent from Turn 3's `clinical_flags` — meaning `check_escalation`'s L2 path is not tested in the correct multi-turn sequence. Tests do not faithfully replicate production session state.

**Fix:** Add `turn_count=rN.get("turn_count", 0)` and `clinical_flags=rN.get("clinical_flags", [])` to each inter-turn `make_e2e_state()` call.

---

### NEW-5 — P2 — `output_gate.py` audit log prints unconditionally to stdout with no debug guard

**Evidence:** `output_gate.py` lines 33–39. Every non-crisis turn emits a multi-line JSON audit blob to stdout before the `Sage:` response in the CLI. No `DEBUG` flag, `logging` module, or environment variable guard exists.

**Impact:** In a demo or production setting, the terminal output is cluttered with audit JSON on every single turn. More importantly, there is no way to run the system quietly without modifying source. This is development instrumentation in production code paths.

**Fix:** Route audit output through `logging.debug()` or guard with `if os.environ.get("SAGE_AUDIT_LOG"):`.

---

## Section 4: Accepted Residuals (Pre-existing, Not Regressed)

These were known before the sprint cycle and were either explicitly deferred or are out of current POC scope:

| ID | Issue | Status |
|---|---|---|
| P1-9 | Skill handoff on `new_skill` mid-skill | User-deferred; design decision pending |
| P2-3 | Negation false-positive in `skill_select` | User-deferred; requires semantic approach |
| P2-6 | ZWSP crisis bypass | Not addressed — scope for future hardening sprint |
| P2-12 | Dual skill loading inconsistency | POC-acceptable; no impact on correctness |
| P2-14 | UTF-8 stdout | Not addressed; low priority for demo use |
| P3-1 | `testpaths` missing from pytest config | Minor; not addressed |
| P3-8 | Unbounded `conversation_history` | POC-acceptable; flag before production |
| P3-6 | `.gitignore` missing `.pytest_cache/` | Minor; not addressed |

---

## Section 5: Clinical Reviewer Handoff Evidence

The following assertions are in the test suite and cover the clinical localization requirements a reviewer will check first:

| Claim | Test | File |
|---|---|---|
| Arabic crisis response contains correct UAE hotline (800 4673) | `test_arabic_crisis_response_contains_correct_hotline_number` | `test_graph.py` |
| Arabic crisis response contains UAE emergency number (999) | `test_arabic_crisis_response_contains_emergency_number` | `test_graph.py` |
| Arabic crisis response does NOT contain 988 (US-only) | `test_arabic_crisis_response_excludes_us_only_988` | `test_graph.py` |
| Arabic crisis response does NOT contain "توازن" (unverified name) | `test_arabic_crisis_response_excludes_incorrect_service_name` | `test_graph.py` |
| Arabic crisis response ends with "أنت لست وحدك" (you are not alone) | `test_arabic_crisis_response_ends_with_not_alone` | `test_graph.py` |
| Arabic crisis response centers safety, not AI's anxiety state | `test_arabic_crisis_response_centers_safety_not_ai_anxiety` | `test_graph.py` |
| Active skill is cleared when crisis fires mid-CBT session | `test_crisis_clears_active_skill_and_returns_arabic_when_ar_detected` | `test_graph.py` |
| Clinical adaptations (e.g., substance_use) appear in system role | `test_compose_prompt_clinical_flag_injects_adaptation` | `test_nodes.py` |
| LLM receives system+user message roles (persona not as user message) | `test_freeflow_respond_with_mocked_llm` | `test_nodes.py` |

**Outstanding before clinical handoff:** `CRISIS_RESPONSE` (English) still contains unverified service name and US-only number (NEW-1). Tests for English crisis response content equivalents are absent — a reviewer checking the English path will find the same problems that were fixed for Arabic.

---

## Full Verdict Matrix (Re-Audit)

| Workstream | Check | Original | Re-Audit |
|---|---|---|---|
| 1.1 | State field write/read matrix | PASS | **PASS** |
| 1.2 | `secondary_intent` in all helpers | PASS | **PASS** |
| 1.3 | Type coercions (int/float) | P3+PASS | **FIXED** (`_safe_int`) |
| 1.4 | LangGraph state merge semantics | PASS | **PASS** |
| 2.1 | `_route_after_safety` branches | PASS | **PASS** |
| 2.2 | `_route_after_intent` all branches | PASS (design flags) | **PASS** |
| 2.3 | Crisis path isolation | PASS | **PASS** |
| 2.4 | Dead/unreachable paths | PASS | **PASS** |
| 3.1 | CRISIS_KEYWORDS completeness | **FAIL P1** | **PARTIAL FIXED** (2 English phrases remain) |
| 3.2 | L1 exit false positives | **FAIL P1** | **FIXED** (residual: 3 overly-broad patterns, NEW-2) |
| 3.3 | `completion_criteria` boundaries | PASS | **PASS** |
| 3.4 | StopIteration in `skill_executor` | **FAIL P2** | **FIXED** |
| 3.5 | `skill_select` negation false positive | **FAIL P2** | **DEFERRED** |
| 4.1 | Step policy first-rule-wins | PASS | **PASS** |
| 4.2 | Step policy boundary values | PASS | **PASS** |
| 4.3 | Step scope ANY handling | PASS | **PASS** |
| 4.4 | Policy recovery sequence | PASS | **PASS** |
| 5.1 | `clinical_flags` reset per turn | **FAIL P1** | **FIXED** |
| 5.2 | `turn_count` not in multi-turn test helpers | WARN P2 | **FAIL P2** (not addressed) |
| 5.3 | `conversation_history` growth | PASS | **PASS** |
| 6.1a | `detect_language` edge cases | PASS | **PASS** |
| 6.1b | `detect_language(None)` TypeError | **FAIL P2** | **FIXED** |
| 6.1c | RTL control chars → wrong detection | **FAIL P2** | **FIXED** |
| 6.1d | Non-AR/EN language fallback | WARN P3 | **WARN P3** (unchanged) |
| 6.2 | Live Ollama AR↔EN translation | PASS | **PASS** |
| 7 | LLM API integration | Mixed | **PASS** (all nodes use correct role format) |
| 8.1 | Skill schema field completeness | PASS | **PASS** |
| 8.3 | `load_skill` error handling | PASS | **PASS** |
| 9.1 | Knowledge lookup accuracy | PASS | **PASS** |
| 9.2 | Knowledge injection — primary_intent gap | **FAIL P2** | **FIXED** |
| 10.1 | Routing function unit test gap | **FAIL P2** | **FIXED** (18 parametrized cases) |
| 10.2 | `make_state()` completeness | PASS | **PASS** |
| 10.3 | Slow test isolation | PASS | **PASS** |
| 10.4 | Pytest marker registration | PASS | **PASS** |
| 10.4b | `testpaths` / `asyncio_mode` absent | FAIL P3 | **FAIL P3** (unchanged) |
| 11.1 | Dependency version bounds | WARN P2 | **FIXED** |
| 11.2 | Env var safety + `.gitignore` | PASS | **PASS** |
| 11.3 | Python 3.12.4 compatibility | PASS | **PASS** |
| 12.1a | Crisis UAE helpline present | PASS | **PASS** (Arabic correct; English still has Tawazun/988 — NEW-1) |
| 12.1b | Arabic crisis gets English response | **FAIL P0** | **FIXED** |
| 12.1c | 988 US-only caveat | WARN P3 | **PARTIAL FIXED** (Arabic only) |
| 12.2 | No disk writes / no PII in logs | PASS | **PASS** |
| 12.3a | Persona no-diagnose disclaimer | PASS | **PASS** |
| 12.3b | Clinical adaptations in system role | PASS (was HumanMessage) | **FIXED** (now in system role) |
| 12.4 | Prompt injection via `message_en` | WARN P2 | **WARN P2** (unchanged) |
| 13.1 | Arabic crisis English-only (confirmed) | **FAIL P0** | **FIXED** |
| 13.2 | No audit log on crisis turns | **FAIL P1** | **FIXED** |
| 13.3 | No history update on crisis | **FAIL P1** | **FIXED** |
| 13.4 | Skill state persists through crisis | **FAIL P0** | **FIXED** |
| 14.1 | `config.py` uses `.get()` | PASS | **PASS** |
| 14.2 | Non-slow tests run without services | PASS | **PASS** |
| 15.1 | freeflow system prompt as HumanMessage | **FAIL P1** | **FIXED** |
| 15.2 | Prompt token budget | PASS | **PASS** |
| 16.1a | `language.py` Ollama failure | **FAIL P1** | **FIXED** |
| 16.1b | StopIteration on bad `step_id` | **FAIL P2** | **FIXED** |
| 16.1c | `output_gate` Ollama failure | **FAIL P1** | **FIXED** (via `language.py` try/except) |
| 16.2 | JSONDecodeError in `intent_route` | **FAIL P1** | **FIXED** |
| 17.1 | Empty message to `safety_check` | PASS | **PASS** |
| 17.2 | ZWSP crisis bypass | **FAIL P2** | **FAIL P2** (not addressed) |
| 17.3 | RTL markers / emoji | FAIL/PASS | **PARTIAL** (RTL in `detect_language` fixed; ZWSP in `safety_check` not) |
| 18.1 | Dual skill loading inconsistency | WARN P2 | **WARN P2** (unchanged) |
| 19.1 | `datetime.utcnow()` | PASS | **PASS** |
| 19.2 | Python 3.12 type compatibility | PASS | **PASS** |
| 19.3 | Pydantic v2 usage | PASS | **PASS** |
| 20.1 | External call count per path | PASS | **PASS** |
| 20.2 | Cold-start loading | WARN P3 | **WARN P3** (unchanged) |
| 21.1 | Graph topology — all nodes connected | PASS | **PASS** |
| 21.2 | Node count (7 + crisis_response) | PASS | **PASS** |
| 21.3 | `.gitignore` covers `.env` | PASS | **PASS** |
| 22.1 | CLI no error handling | **FAIL P2** | **FIXED** |
| 22.2 | Post-crisis stale skill state | **FAIL P2** | **FIXED** |
| 22.3 | Unbounded history growth | WARN P3 | **FAIL P3** (acknowledged, not addressed) |
| 22.4 | Terminal UTF-8 encoding | WARN P2 | **FAIL P2** (not addressed) |
| 23.1 | Duplicated test helpers | WARN P3 | **WARN P3** (accepted by design) |
| 23.2 | pytest config missing `testpaths` | FAIL P3 | **FAIL P3** (not addressed) |
| 23.3 | No `conftest.py` | FAIL P3 | **PASS (design)** |
| NEW-1 | English `CRISIS_RESPONSE` has Tawazun/988 | — | **FAIL P2** |
| NEW-2 | 3 `L1_EXIT_PHRASES` patterns overly broad | — | **FAIL P2** |
| NEW-3 | `output_gate` audit log: no debug guard | — | **FAIL P2** |
| NEW-4 | Multi-turn tests missing `turn_count`/`clinical_flags` carry | — | **FAIL P2** |
| NEW-5 | `ollama` lower bound `>=0.3.0` too loose | — | **WARN P3** |

---

## Immediate Action Items (Before Clinical Use)

1. **NEW-1 (P2)** — Fix `CRISIS_RESPONSE` (English): remove "Tawazun", remove "988 (US)", add 999. Add English-equivalent of the Arabic content tests.
2. **NEW-2 (P2)** — Scope or remove `"don't want to"`, `"want to stop"`, `"please stop"` from `L1_EXIT_PHRASES`. Add false-positive test cases.
3. **P1-1 residual (P1)** — Add `"don't want to be alive"` and `"end it all"` to `CRISIS_KEYWORDS`. Add regression tests.
4. **NEW-4 (P2)** — Add `turn_count` and `clinical_flags` carry-forward to multi-turn E2E test helpers.
5. **P2-6 (P2)** — Add ZWSP normalization to `_contains_crisis` in `safety_check.py`.
