# Engagement Layer R1 + R3 + R5 Implementation Plan (v2, policy-as-data)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consent-gated skill entry with up to two offered options (R1), replace the general_chat scope wall with engage-then-bridge (R3), and cap word-count criteria holds per step (R5) — with every clinical policy parameter expressed as governed data, not Python constants.

**Architecture:** R1's matching policy (acute direct-entry list, intensity threshold, offer count, declined handling) lives in a new `skill_matching` category of the EXISTING Rules Service (`rules/engine.py` + `rules/data/`), evaluated first-match-wins by priority; `skill_select` consumes the fired rule's action and the fired `rule_id` goes into the audit path. The offer turn renders via a new `L2_skill_offer` template with bilingual-enveloped blurbs; `intent_route` classifies accept/decline/other; an accepted offer is promoted by a `skill_select` early-return. R3 is a content edit to `L2_general_chat`. R5 exposes `criteria_hold_count` as a step_policy signal and moves the budget into the skill schema (`criteria_hold_budget`, default null, per-skill opt-in), with the soft-advance instruction text in a governed content file. Crisis layer, post-crisis/psychotic auto-selects, and entry-screen gates are untouched; the budget can never fire on an `entry_screen` step (code invariant).

**Tech Stack:** Python 3.12, LangGraph, pytest (`uv run pytest`), Pydantic rule/skill/template schemas. Working dir for all commands: `/Users/knowledgebase/Documents/Sage/sage-poc`.

**Decisions locked with the user:**
- Offer for every Tier-1/Tier-2 match; direct entry only when `emotional_intensity >= 8` AND the match is in the acute somatic set — now expressed as the `acute_direct_entry` rule in data, with `ignore_declined: true` (acute entry bypasses the declined list; safety over preference).
- Up to TWO offered skills (`max_offered: 2` in data), plus "keep talking" always.
- Declined skills are not re-offered for the rest of the session (`declined_scope: "session"` in data; only literal implemented — unknown scopes fail at load, dead-signal guard). The 4h stale-gap reset clears `declined_skills`, deriving session semantics from this scope.
- R5 budget: `criteria_hold_budget` defaults to **null** in the schema; the 10 word-count-heuristic skills opt in with `criteria_hold_budget: 1` in their JSONs. LLM-criteria skills stay null (current behavior). NOTE: this corrects the review suggestion of a global default of 1, which would have silently budgeted all 16 LLM-criteria skills including post_crisis_check_in.
- Bilingual content contract from the first commit: blurbs are `{"en": ..., "ar": null}`; composer falls back to `en`.

**Governance:** New rule files, templates, and blurbs carry `status: draft-pending-review`, `approved_by: null`. The `criteria_hold_count` signal is a skill-schema extension requiring clinical sign-off (every future skill author can write rules against it) — flagged in the PR. Branch must not merge until Rule 1 engineering approval + clinical review. Em-dash rule: commas only in ALL content strings.

**Out of scope:** crisis_response behavior, entry_screen criteria, S1/S3/S7, L0 persona rewrite (R2, separate plan), Arabic blurb authoring (envelope ships now, content later), Cosmos/CMS/Supabase rule storage (the file contract is the interface; store swap is a loader swap).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/sage_poc/prompts/templates/L2_intents/general_chat.json` | Modify | R3 engage-then-bridge, v1.3.0 |
| `src/sage_poc/rules/schemas.py` | Modify | `SkillMatchingRule` model with load-time condition/action validation |
| `src/sage_poc/rules/loader.py` | Modify | register `skill_matching` category; unapproved-active warning |
| `src/sage_poc/rules/engine.py` | Modify | `_eval_skill_matching` (first-match-wins by priority) |
| `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json` | Create | acute_direct_entry + default_offer rules (draft-pending-review) |
| `src/sage_poc/rules/data/step_policy/soft_advance_instruction.json` | Create | R5 no-re-ask instruction text (out of Python, governed) |
| `src/sage_poc/skills/schema.py` | Modify | `criteria_hold_budget: int \| None = None` |
| `src/sage_poc/skills/conformance.py` | Modify | register `skill.criteria_hold_budget` as USED |
| `src/sage_poc/skills/<10 word-count skills>.json` | Modify | `criteria_hold_budget: 1` opt-in |
| `src/sage_poc/nodes/skill_executor.py` | Modify | `criteria_hold_count` signal, budget evaluation, entry_screen invariant |
| `src/sage_poc/state.py` | Modify | R1 offer fields + R5 hold-counter fields |
| `src/sage_poc/server_helpers.py` | Modify | per-turn resets; stale-gap clears offers AND declined list |
| `src/sage_poc/prompts/offer_descriptions.json` | Create | bilingual-enveloped blurbs (NOT under `templates/` — loader globs that tree as PromptTemplate) |
| `src/sage_poc/prompts/templates/L2_intents/skill_offer.json` | Create | L2 offer-turn template (draft-pending-review) |
| `src/sage_poc/prompts/composer.py` | Modify | `skill_offer` selector, `extra_variables`, lang-aware options block |
| `src/sage_poc/nodes/skill_select.py` | Modify | candidates → rules evaluation → offer/enter; accept promotion |
| `src/sage_poc/nodes/intent_route.py` | Modify | PENDING OFFER block + `offer_response` parsing |
| `src/sage_poc/graph.py` | Modify | accept routing branch; crisis clears offers |
| `tests/test_engagement_templates.py` | Create | R3 guard, blurb coverage, composer offer selection |
| `tests/test_skill_matching_rules.py` | Create | rules category contract tests |
| `tests/test_skill_select_offer.py` | Create | R1 node behavior against the rules contract |
| `tests/test_intent_route_node.py` | Modify | offer classification parsing |
| `tests/test_routing.py` | Modify | accept-branch routing |
| `tests/test_skill_executor.py` | Modify | R5 signal + budget tests |
| `tests/test_schema_conformance.py` | Modify | pinned count 15 → 16 |
| `docs/SageAI_architecture_current.md` | Modify | offer flow, skill_matching category, R5 signal (human sign-off flagged) |

---

### Task 0: Branch and baseline

- [ ] **Step 1: Create branch**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git checkout master && git pull && git checkout -b feat/engagement-r1-r3-r5
```

- [ ] **Step 2: Record baseline**

Run: `uv run pytest tests/ -q -m "not slow" 2>&1 | tail -3`
Expected: fully green. Record the count for the PR description.

---

### Task 1: R3 — engage-then-bridge in L2_general_chat

**Files:**
- Modify: `src/sage_poc/prompts/templates/L2_intents/general_chat.json`
- Test: `tests/test_engagement_templates.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/test_engagement_templates.py`:

```python
"""Content guards for the 2026-06-12 engagement-layer changes (R1 + R3).

Pins template content, blurb coverage, and composer offer selection so future
edits that silently regress engagement behavior fail CI instead of shipping.
"""
import json
from pathlib import Path

from sage_poc.prompts.loader import get_intent_template, reload_all

_PROMPTS_DIR = Path(__import__("sage_poc.prompts", fromlist=["__file__"]).__file__).parent


class TestR3GeneralChatEngageThenBridge:
    def test_deflection_clause_removed(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "rather than engaging with the topic itself" not in tmpl.content, (
            "R3 regression: the scope-wall deflection clause is back in L2_general_chat"
        )

    def test_engage_then_bridge_present_and_version_bumped(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "engage with the topic itself briefly" in tmpl.content
        assert "Never deflect" in tmpl.content
        assert tmpl.version == "1.3.0"

    def test_no_em_dash_in_content(self):
        reload_all()
        tmpl = get_intent_template("general_chat")
        assert "—" not in tmpl.content, "em dashes mirror into LLM output; use commas"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engagement_templates.py -v`
Expected: first two tests FAIL.

- [ ] **Step 3: Edit the template**

In `src/sage_poc/prompts/templates/L2_intents/general_chat.json`: `version` → `"1.3.0"`, `effective_date` → `"2026-06-12"`, `word_budget` → `130`, and replace the final sentence of `content`:

OLD: `You are a wellness companion. If the user raises a concern that is not about their own wellbeing, explore how they feel about it rather than engaging with the topic itself.`

NEW: `You are a wellness companion. If the user raises a topic that is not about their own wellbeing, engage with the topic itself briefly and substantively, one or two sentences, then connect it back to the user, how it affects them or what it means for them. Never deflect, refuse the topic, or answer a direct question with a feelings probe. Do not get pulled into extended technical or factual back-and-forth, after two turns on a side topic bring the focus gently back to the user.`

(Everything before that sentence, including the "Exception:" clause, stays verbatim.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_engagement_templates.py -v` — Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/prompts/templates/L2_intents/general_chat.json tests/test_engagement_templates.py
git commit -m "feat(R3): engage-then-bridge replaces scope-wall deflection in L2_general_chat v1.3.0"
```

---

### Task 2: skill_matching category in the existing Rules Service

**Files:**
- Modify: `src/sage_poc/rules/schemas.py`, `src/sage_poc/rules/loader.py`, `src/sage_poc/rules/engine.py`
- Create: `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json`
- Test: `tests/test_skill_matching_rules.py` (create)

**Design note:** This is NOT a new rules service. `rules/engine.py` + `rules/loader.py` already implement the v7 §5.5 contract (governance envelope, per-category Pydantic schemas, rule_id-returning EvalResult, cache + `reload_all()` hot-reload). This task adds the missing `skill_matching` category to it. Production storage swap (Cosmos/CMS/Supabase) remains a loader change behind `get_rules()`, unchanged by this task.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_matching_rules.py`:

```python
"""skill_matching rules category: first-match-wins by priority over named signals.
The fired rule's action drives skill_select's offer-vs-direct-entry decision;
the fired rule_id goes into the audit path."""
import pytest
from pydantic import ValidationError

from sage_poc.rules import engine as rules_engine
from sage_poc.rules.loader import reload_all
from sage_poc.rules.schemas import SkillMatchingRule


def _ctx(**overrides) -> dict:
    base = {"matched_skill_id": "cbt_thought_record", "emotional_intensity": 5}
    return {**base, **overrides}


class TestEvaluator:
    def setup_method(self):
        reload_all()

    def test_acute_match_high_intensity_fires_enter_direct(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="box_breathing", emotional_intensity=9))
        assert res.fired and res.fired[0].rule_id == "acute_direct_entry"
        assert res.fired[0].action["type"] == "enter_direct"
        assert res.fired[0].action["ignore_declined"] is True

    def test_acute_skill_low_intensity_falls_to_default_offer(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="box_breathing", emotional_intensity=4))
        assert res.fired and res.fired[0].rule_id == "default_offer"
        assert res.fired[0].action["type"] == "offer"
        assert res.fired[0].action["max_offered"] == 2
        assert res.fired[0].action["declined_scope"] == "session"

    def test_non_acute_skill_high_intensity_still_offers(self):
        res = rules_engine.evaluate("skill_matching", _ctx(
            matched_skill_id="cbt_thought_record", emotional_intensity=9))
        assert res.fired and res.fired[0].rule_id == "default_offer"

    def test_exactly_one_rule_fires(self):
        res = rules_engine.evaluate("skill_matching", _ctx())
        assert len(res.fired) == 1, "first-match-wins: exactly one rule fires"


class TestSchemaGuards:
    _BASE = dict(
        rule_id="x", category="skill_matching", effective_date="2026-06-12",
        action={"type": "offer", "max_offered": 2, "declined_scope": "session"},
    )

    def test_unknown_condition_key_rejected_at_load(self):
        with pytest.raises(ValidationError, match="dead-signal"):
            SkillMatchingRule.model_validate(
                {**self._BASE, "condition": {"moon_phase_gte": 3}})

    def test_unknown_action_type_rejected(self):
        with pytest.raises(ValidationError):
            SkillMatchingRule.model_validate(
                {**self._BASE, "action": {"type": "teleport"}})

    def test_unimplemented_declined_scope_rejected(self):
        with pytest.raises(ValidationError, match="session"):
            SkillMatchingRule.model_validate(
                {**self._BASE,
                 "action": {"type": "offer", "max_offered": 2, "declined_scope": "persistent"}})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_matching_rules.py -v`
Expected: ImportError (`SkillMatchingRule` missing) / `Unknown rule category`.

- [ ] **Step 3: Add the rule model**

In `src/sage_poc/rules/schemas.py`, after `CulturalOutputRule`:

```python
# Condition keys _eval_skill_matching resolves at runtime. Any key outside this set
# is spec-present-runtime-inert, the exact failure class behind the 21 dead
# step_policy signals. Reject at load, never skip silently.
_SKILL_MATCHING_CONDITION_KEYS = frozenset({"matched_skill_in", "emotional_intensity_gte"})


class SkillMatchingRule(BaseModel):
    rule_id: str
    version: str = "1.0.0"
    category: Literal["skill_matching"]
    authored_by: str = "sage_clinics"
    approved_by: str | None = None
    effective_date: str
    active: bool = True
    description: str = ""
    priority: int = 100          # ascending; first match wins
    condition: dict = Field(default_factory=dict)   # empty = always matches
    action: dict

    @field_validator("condition")
    @classmethod
    def known_condition_keys_only(cls, v):
        unknown = set(v) - _SKILL_MATCHING_CONDITION_KEYS
        if unknown:
            raise ValueError(
                f"skill_matching condition keys not resolvable at runtime: {sorted(unknown)}. "
                f"Known: {sorted(_SKILL_MATCHING_CONDITION_KEYS)} (dead-signal guard)."
            )
        return v

    @field_validator("action")
    @classmethod
    def implemented_actions_only(cls, v):
        if v.get("type") not in ("enter_direct", "offer"):
            raise ValueError(
                f"skill_matching action.type must be 'enter_direct' or 'offer', got {v.get('type')!r}"
            )
        if v.get("type") == "offer":
            if not isinstance(v.get("max_offered"), int) or v["max_offered"] < 1:
                raise ValueError("offer action requires integer max_offered >= 1")
            if v.get("declined_scope", "session") != "session":
                raise ValueError(
                    "declined_scope: only 'session' is implemented. Declaring other scopes "
                    "in data without runtime support recreates the dead-signal failure class."
                )
        return v
```

(`Field` and `field_validator` are already imported in this module for the other rule models; if not, add `from pydantic import Field, field_validator` to the existing import line.)

- [ ] **Step 4: Register in loader and engine**

In `src/sage_poc/rules/loader.py`: add `SkillMatchingRule` to the schemas import and to `_RULE_MODELS` (`"skill_matching": SkillMatchingRule`). In the `load_rules` active-rule loop, extend the unapproved-warning to cover it (control-layer rules deserve the same noise as safety rules):

```python
                if isinstance(rule, (SafetyRule, SkillMatchingRule)) and rule.approved_by is None:
```

(Replace the existing `isinstance(rule, SafetyRule) and rule.approved_by is None` check; the log message already prints the rule_id.)

In `src/sage_poc/rules/engine.py`: import `SkillMatchingRule`, add the evaluator, register `"skill_matching": _eval_skill_matching` in `_EVAL_DISPATCH`:

```python
def _eval_skill_matching(rules: list[SkillMatchingRule], context: dict) -> EvalResult:
    """
    Decide how a matched skill enters the conversation: direct entry or consent offer.
    First-match-wins by ascending priority; returns at most one fired rule.

    context keys:
      matched_skill_id (str)    — primary candidate from Tier 1/Tier 2 matching
      emotional_intensity (int) — current turn's intensity score (1-10)
    """
    matched_skill_id = context.get("matched_skill_id", "")
    intensity = int(context.get("emotional_intensity", 5))

    result = EvalResult()
    for rule in sorted(rules, key=lambda r: r.priority):
        cond = rule.condition
        if "matched_skill_in" in cond and matched_skill_id not in cond["matched_skill_in"]:
            continue
        if "emotional_intensity_gte" in cond and intensity < cond["emotional_intensity_gte"]:
            continue
        result.fired.append(FiredRule(
            rule_id=rule.rule_id, version=rule.version, action=rule.action,
        ))
        break
    return result
```

- [ ] **Step 5: Create the rules data file**

Create `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json`:

```json
{
  "category": "skill_matching",
  "description": "Controls how a matched therapeutic skill enters the conversation: immediate entry or a consent offer the user must accept. First-match-wins by ascending priority. Clinician-ownable: the acute skill list, intensity threshold, offer count, and declined handling are all data, not code.",
  "rules": [
    {
      "rule_id": "acute_direct_entry",
      "version": "0.1.0",
      "category": "skill_matching",
      "authored_by": "engineering",
      "approved_by": null,
      "effective_date": "2026-06-12",
      "active": true,
      "description": "At panic-level intensity a choice menu adds cognitive load; MI supports directiveness in acute distress. Enters the matched acute somatic skill immediately. ignore_declined: a prior decline does not block acute entry, safety over preference.",
      "priority": 1,
      "condition": {
        "matched_skill_in": ["box_breathing", "grounding_5_4_3_2_1", "stop_technique", "dbt_tipp"],
        "emotional_intensity_gte": 8
      },
      "action": {"type": "enter_direct", "ignore_declined": true}
    },
    {
      "rule_id": "default_offer",
      "version": "0.1.0",
      "category": "skill_matching",
      "authored_by": "engineering",
      "approved_by": null,
      "effective_date": "2026-06-12",
      "active": true,
      "description": "Default consent gate: every other match is offered, never imposed. Up to max_offered options plus the always-present choice to keep talking. declined_scope session: a declined skill is not re-offered for the rest of the session; the 4h stale-gap reset clears the declined list.",
      "priority": 99,
      "condition": {},
      "action": {"type": "offer", "max_offered": 2, "declined_scope": "session"}
    }
  ]
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_matching_rules.py -v` — Expected: all PASS.
Also run: `uv run pytest tests/ -q -m "not slow" -k "rules or engine" 2>&1 | tail -3` — Expected: no regressions in other categories.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/rules/schemas.py src/sage_poc/rules/loader.py src/sage_poc/rules/engine.py src/sage_poc/rules/data/skill_matching/ tests/test_skill_matching_rules.py
git commit -m "feat(R1): skill_matching category in Rules Service, acute_direct_entry + default_offer as governed data"
```

---

### Task 3: R5 — criteria_hold_count as step_policy signal, budget in skill schema

**Files:**
- Modify: `src/sage_poc/skills/schema.py`, `src/sage_poc/skills/conformance.py`, `src/sage_poc/state.py`, `src/sage_poc/nodes/skill_executor.py`
- Modify: 10 skill JSONs (budget opt-in)
- Create: `src/sage_poc/rules/data/step_policy/soft_advance_instruction.json`
- Test: `tests/test_skill_executor.py`, `tests/test_schema_conformance.py`

**Design note:** The executor computes signals; policy decides actions (v7 §4.1). `criteria_hold_count` becomes the seventh known step_policy signal — skill authors may write their own rules against it. The system default (advance when count >= budget) is evaluated at the criteria-blocked point so it can never fire over a turn whose criteria actually passed. Two invariants stay in code, not data: the budget never fires on `entry_screen` steps, and a null budget means no budget. Default is null — NOT 1 — so the 16 LLM-criteria skills (incl. post_crisis_check_in) are untouched unless a clinician deliberately opts one in.

- [ ] **Step 1: Schema + conformance + state**

(a) `src/sage_poc/skills/schema.py`, in `class Skill` after `cultural_overrides`:

```python
    criteria_hold_budget: int | None = Field(
        default=None, ge=1,
        description="Max consecutive criteria holds per step before soft advance. "
                    "null = no budget (hold indefinitely, current behavior). "
                    "Clinician-ownable per skill.",
    )
```

(`Field` is already imported in this module.)

(b) `src/sage_poc/skills/conformance.py`, add to `SCHEMA_CONFORMANCE` in the Skill-level section:

```python
    "skill.criteria_hold_budget": {
        "status": "USED",
        "injected_by": "skill_executor_node → evaluate_step_policy (criteria-blocked branch)",
        "note": (
            "Per-skill opt-in cap on consecutive word-count criteria holds at one step. "
            "null = no budget. Never applies to entry_screen steps (code invariant). "
            "Soft-advance instruction text lives in rules/data/step_policy/soft_advance_instruction.json."
        ),
    },
```

(c) `tests/test_schema_conformance.py`: update the pinned count test `test_total_field_count_is_15` → rename to `test_total_field_count_is_16`, assert `== 16`, and update the `summary.total == 15` assertion to 16.

(d) `src/sage_poc/state.py`, after `resistance_score`:

```python
    criteria_hold_count: int                 # R5: consecutive criteria holds at the current step; persists via LangGraph checkpoint
    criteria_hold_step_id: Optional[str]     # R5: step the hold counter belongs to; persists via LangGraph checkpoint
```

(Not added to `_build_state` — checkpoint-persisted, like `prev_step_id`.)

- [ ] **Step 2: Create the instruction content file**

Create `src/sage_poc/rules/data/step_policy/soft_advance_instruction.json` (same precedent as `rules/data/resistance_scoring/resistance_prompt.json`: engineering-loaded content with a governance envelope, NOT a rules category):

```json
{
  "content_id": "soft_advance_instruction",
  "version": "0.1.0",
  "status": "draft-pending-review",
  "authored_by": "engineering",
  "approved_by": null,
  "effective_date": "2026-06-12",
  "description": "Appended to the step instruction when criteria_hold_budget is exhausted. Therapeutic language must not live in .py files.",
  "instruction": "NOTE: The user answered briefly and was already asked once. Respond to what they said, move forward naturally, do not repeat the previous question. Invite more detail only as an option, never as a requirement."
}
```

- [ ] **Step 3: Write the failing tests**

Append to `tests/test_skill_executor.py`:

```python
# ── R5: criteria_hold_count signal + per-skill hold budget (2026-06-12) ───────

class TestR5CriteriaHoldBudget:
    """criteria_hold_count is a step_policy signal; the per-skill criteria_hold_budget
    (schema field, default null) converts the (budget+1)th consecutive criteria hold
    into a soft advance with a governed no-re-ask instruction. entry_screen steps are
    exempt by code invariant. Null budget = current behavior."""

    def _budgeted_skill(self, **kwargs):
        skill = _make_skill(**kwargs)
        skill.criteria_hold_budget = 1
        return skill

    async def test_first_short_answer_holds_and_arms_counter(self):
        state = _make_executor_state(message_en="ok")  # 1 word, heuristic fails
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=self._budgeted_skill()):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "step_1"
        assert result["criteria_hold_count"] == 1
        assert result["criteria_hold_step_id"] == "step_1"

    async def test_budget_exhausted_soft_advances_with_governed_note(self):
        state = _make_executor_state(
            message_en="ok", criteria_hold_count=1, criteria_hold_step_id="step_1")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=self._budgeted_skill()):
            result = await skill_executor_node(state)
        assert result["active_skill_id"] is None, "single-step skill: budget advance completes"
        assert result["rule_fired"] is True, (
            "soft advance must set rule_fired so compose_prompt uses the plain "
            "step_instruction and the appended note survives composition"
        )
        assert "do not repeat the previous question" in result["step_instruction"]
        assert result["criteria_hold_count"] == 0
        assert result["criteria_hold_step_id"] is None

    async def test_null_budget_holds_indefinitely(self):
        skill = _make_skill()  # criteria_hold_budget stays None
        state = _make_executor_state(
            message_en="ok", criteria_hold_count=7, criteria_hold_step_id="step_1")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "step_1", "null budget = no budget, current behavior"

    async def test_counter_resets_on_step_change(self):
        state = _make_executor_state(
            message_en="ok", criteria_hold_count=1, criteria_hold_step_id="some_previous_step")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=self._budgeted_skill()):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "step_1", "stale counter must not trigger soft advance"
        assert result["criteria_hold_count"] == 1
        assert result["criteria_hold_step_id"] == "step_1"

    async def test_entry_screen_never_soft_advances(self):
        """Code invariant: budget can never advance past an entry_screen safety gate,
        whatever the JSON says."""
        skill = self._budgeted_skill()
        skill.steps[0].step_id = "entry_screen"
        state = _make_executor_state(
            active_step_id="entry_screen",
            message_en="ok",
            criteria_hold_count=5,
            criteria_hold_step_id="entry_screen",
        )
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=skill), \
             patch(
                 "sage_poc.nodes.skill_executor.evaluate_completion_criteria",
                 new=AsyncMock(return_value=False),
             ):
            result = await skill_executor_node(state)
        assert result["active_step_id"] == "entry_screen"

    async def test_long_answer_never_arms_counter(self):
        state = _make_executor_state(
            message_en="I am breathing in slowly and holding it like you said")
        with patch("sage_poc.nodes.skill_executor.load_skill", return_value=self._budgeted_skill()):
            result = await skill_executor_node(state)
        assert result["criteria_hold_count"] == 0
        assert result["criteria_hold_step_id"] is None

    def test_criteria_hold_count_is_a_known_step_policy_signal(self):
        from sage_poc.nodes.skill_executor import _KNOWN_STEP_POLICY_SIGNALS
        assert "criteria_hold_count" in _KNOWN_STEP_POLICY_SIGNALS, (
            "skill authors must be able to write step_policy rules against the signal"
        )

    def test_skill_authored_rule_can_reference_signal(self):
        """A per-skill rule on criteria_hold_count fires in normal Phase 1 evaluation."""
        from sage_poc.skills.schema import StepPolicyRule, StepPolicyCondition
        skill = _make_skill()
        skill.step_policy.append(StepPolicyRule(
            condition=StepPolicyCondition(
                signal="criteria_hold_count", operator=">=", value=2, step="ANY"),
            action="offer_break",
            instruction="Would a short break help before we continue?",
            next_step_id="current",
        ))
        result = evaluate_step_policy(
            skill=skill, current_step_id="step_1", emotional_intensity=5,
            engagement=7, message_en="ok", criteria_hold_count=2,
        )
        assert result["action"] == "offer_break"

    async def test_word_count_production_skills_opted_in(self):
        """The 10 word-count-heuristic skills carry criteria_hold_budget: 1;
        LLM-criteria skills stay null."""
        from sage_poc.skills.schema import load_skill as real_load
        from sage_poc.nodes.skill_executor import _LLM_CRITERIA_SKILLS
        from sage_poc.skill_ids import SKILL_REGISTRY
        for sid in SKILL_REGISTRY:
            skill = real_load(sid)
            if sid in _LLM_CRITERIA_SKILLS or sid == "psychotic_referral":
                assert skill.criteria_hold_budget is None, (
                    f"{sid}: LLM-criteria/auto-select skills must not be silently budgeted"
                )
            elif sid == "post_crisis_check_in":
                assert skill.criteria_hold_budget is None
            else:
                assert skill.criteria_hold_budget == 1, (
                    f"{sid}: word-count skill missing criteria_hold_budget opt-in"
                )
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_executor.py -k "R5" -v`
Expected: FAIL (unknown schema field on `criteria_hold_budget=...`? No — Step 1 added the field, so failures are: signal unknown via `_KNOWN_STEP_POLICY_SIGNALS` assertion, `evaluate_step_policy` rejecting `criteria_hold_count` kwarg, counters absent from results, opt-in test failing on all 10 skills).

- [ ] **Step 5: Implement in skill_executor**

In `src/sage_poc/nodes/skill_executor.py`:

(a) Module level, after `_RESISTANCE_PROMPT_PATH`:

```python
_SOFT_ADVANCE_INSTRUCTION_PATH = (
    Path(__file__).parent.parent
    / "rules" / "data" / "step_policy" / "soft_advance_instruction.json"
)
try:
    _SOFT_ADVANCE_INSTRUCTION: str = json.loads(
        _SOFT_ADVANCE_INSTRUCTION_PATH.read_text(encoding="utf-8")
    )["instruction"]
except Exception:  # missing content file must not take the executor down
    _SOFT_ADVANCE_INSTRUCTION = (
        "NOTE: The user answered briefly and was already asked once. Move forward "
        "naturally and do not repeat the previous question."
    )
    logging.getLogger(__name__).warning(
        "[skill_executor] soft_advance_instruction.json unavailable; using fallback text"
    )
```

(b) Add `"criteria_hold_count"` to `_KNOWN_STEP_POLICY_SIGNALS`.

(c) `evaluate_step_policy`: add parameter `criteria_hold_count: int = 0`, add `"criteria_hold_count": criteria_hold_count` to the `signals` dict, and in the `if not met:` branch replace the plain stay-return with:

```python
    if not met:
        # System-default budget rule, overridable per skill via step_policy rules on
        # the criteria_hold_count signal. Evaluated only at the criteria-blocked point
        # so it can never fire over a turn whose criteria actually passed.
        # Code invariants the data cannot override: entry_screen steps are exempt;
        # null budget means no budget.
        if (
            skill.criteria_hold_budget is not None
            and current_step_id != "entry_screen"
            and criteria_hold_count >= skill.criteria_hold_budget
        ):
            step_ids = [s.step_id for s in skill.steps]
            current_idx = step_ids.index(current_step_id)
            next_id = step_ids[current_idx + 1] if current_idx + 1 < len(step_ids) else None
            return {
                "action":         "advance" if next_id else "complete",
                "instruction":    step_instruction + " " + _SOFT_ADVANCE_INSTRUCTION,
                "next_step_id":   next_id or current_step_id,
                "skill_complete": next_id is None,
                "_soft_advanced": True,
            }
        return {
            "action":            "stay",
            "instruction":       step_instruction,
            "next_step_id":      current_step_id,
            "skill_complete":    False,
            "_criteria_blocked": True,
        }
```

(d) `skill_executor_node`: compute the counter before `_base_policy_kwargs` and thread it:

```python
    criteria_hold_count = state.get("criteria_hold_count") or 0
    if state.get("criteria_hold_step_id") != step_id:
        criteria_hold_count = 0
```

add `"criteria_hold_count": criteria_hold_count,` to `_base_policy_kwargs`.

(e) Track the soft advance and counter updates. After `result = p1_result` (and keeping the existing `_criteria_blocked` pop flow), add:

```python
    soft_advanced = bool(result.pop("_soft_advanced", False))
```

immediately after the `p1_criteria_blocked = result.pop("_criteria_blocked", False)` line (both sentinels are popped before any downstream use). In the Phase 2 call, change `criteria_met=llm_criteria_met` to `criteria_met=True if soft_advanced else llm_criteria_met` (a non-safety resistance hold must not undo a budget advance; the existing precedence resolver then restores the soft-advance result, and `validate_only` safety holds still win).

(f) Compute the counter update just before the return dict:

```python
    if soft_advanced or result.get("action") in ("advance", "complete") or result.get("skill_complete"):
        criteria_hold_update = {"criteria_hold_count": 0, "criteria_hold_step_id": None}
    elif p1_criteria_blocked and llm_criteria_met is not True:
        criteria_hold_update = {
            "criteria_hold_count": criteria_hold_count + 1,
            "criteria_hold_step_id": step_id,
        }
    else:
        criteria_hold_update = {"criteria_hold_count": criteria_hold_count, "criteria_hold_step_id": state.get("criteria_hold_step_id")}
```

(g) In the final return dict: `"rule_fired": soft_advanced or result.get("action") not in ("advance", "complete", "stay", None),` and add `**criteria_hold_update,`. In the L1 early-return dict, add `"criteria_hold_count": 0, "criteria_hold_step_id": None,`.

- [ ] **Step 6: Opt in the 10 word-count skills**

Add `"criteria_hold_budget": 1` (top-level key, next to `cultural_overrides`) to exactly these skill JSONs in `src/sage_poc/skills/`:
`box_breathing.json`, `grounding_5_4_3_2_1.json`, `mi_readiness_ruler.json`, `mood_check_in.json`, `problem_solving_therapy.json`, `psychoed_anxiety.json`, `psychoed_depression.json`, `psychoed_stress.json`, `self_compassion_break.json`, `stop_technique.json`.

NOT `psychotic_referral.json` (auto-select referral, single step) and none of the 16 `_LLM_CRITERIA_SKILLS`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_skill_executor.py tests/test_schema_conformance.py -v`
Expected: all PASS, including every pre-existing executor test (precedence resolver, resistance, dead-signal pin — note `_get_dead_step_policy_signals` counts rules against `_KNOWN_STEP_POLICY_SIGNALS`, which now includes the new signal, so the pinned count stays 0).

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/skills/schema.py src/sage_poc/skills/conformance.py src/sage_poc/state.py src/sage_poc/nodes/skill_executor.py src/sage_poc/rules/data/step_policy/ src/sage_poc/skills/*.json tests/test_skill_executor.py tests/test_schema_conformance.py
git commit -m "feat(R5): criteria_hold_count step_policy signal; per-skill criteria_hold_budget (default null); governed soft-advance text"
```

---

### Task 4: R1 — offer state fields, resets, stale/crisis clearing

**Files:**
- Modify: `src/sage_poc/state.py`, `src/sage_poc/server_helpers.py`, `src/sage_poc/graph.py`

- [ ] **Step 1: SageState fields**

In `src/sage_poc/state.py`, after `semantic_score`:

```python
    offered_skill_ids: Optional[list[str]]  # R1: 1-2 skills offered, pending accept/decline; persists via checkpoint; cleared on accept (skill_select), decline/ignore (intent_route), crisis (crisis_response), stale gap
    offer_response: Optional[str]           # R1: "accept" | "decline" | "other"; per-turn, reset in _build_state
    offer_choice_skill_id: Optional[str]    # R1: skill chosen on accept; per-turn, reset in _build_state
    declined_skills: list[str]              # R1: skills declined this session; never re-offered (declined_scope "session" in skill_matching rules); persists via checkpoint; cleared at 4h stale gap
```

- [ ] **Step 2: Per-turn resets**

In `_build_state` (server_helpers.py), turn-level section:

```python
        "offer_response":          None,
        "offer_choice_skill_id":   None,
```

- [ ] **Step 3: Stale-gap clearing**

In `_stale_skill_overrides`: the `declined_scope: "session"` contract means a 4h+ gap (new-session semantics, same boundary that resets `crisis_state`) clears pending offers AND the declined list. Change the gate and overrides:

```python
    offered_pending = bool(checkpoint_values.get("offered_skill_ids"))
    declined_pending = bool(checkpoint_values.get("declined_skills"))
    if not last_turn_at or (
        not active_skill_id and not is_stale_crisis
        and not offered_pending and not declined_pending
    ):
        return {}
```

and inside `if gap_hours >= _SKILL_STALE_HOURS:` after the `overrides` dict creation:

```python
            if offered_pending:
                overrides["offered_skill_ids"] = None
            if declined_pending:
                overrides["declined_skills"] = []
```

- [ ] **Step 4: Crisis clears pending offers**

In `graph.py` `_crisis_response_node` return dict, after `"active_step_id": None,`:

```python
        "offered_skill_ids": None,
```

(`declined_skills` intentionally survives a crisis turn — it is preference state, not workflow position.)

- [ ] **Step 5: Verify no regressions**

Run: `uv run pytest tests/ -q -m "not slow" 2>&1 | tail -3` — Expected: baseline green.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/state.py src/sage_poc/server_helpers.py src/sage_poc/graph.py
git commit -m "feat(R1): offer state fields; stale gap clears offers and declined list per session scope"
```

---

### Task 5: R1 — bilingual offer descriptions

**Files:**
- Create: `src/sage_poc/prompts/offer_descriptions.json`
- Test: `tests/test_engagement_templates.py` (extend)

**Placement:** NOT under `templates/` (the template loader globs that tree as PromptTemplate and would crash). Bilingual envelope from the first commit: `{"en": ..., "ar": null}` — Arabic content later becomes a data drop, not a schema migration, and consistent Arabic display names can then be echoed into the PENDING OFFER classification block.

- [ ] **Step 1: Write the failing coverage test**

Append to `tests/test_engagement_templates.py`:

```python
class TestOfferDescriptionsCoverage:
    _PATH = _PROMPTS_DIR / "offer_descriptions.json"

    def _load(self) -> dict:
        return json.loads(self._PATH.read_text(encoding="utf-8"))["descriptions"]

    def test_every_offerable_skill_has_a_description(self):
        from sage_poc.skill_ids import SKILL_REGISTRY
        from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
        descs = self._load()
        offerable = [s for s in SKILL_REGISTRY if s not in KEYWORD_SEMANTIC_SKIP]
        missing = [s for s in offerable if s not in descs]
        assert not missing, (
            f"offer_descriptions.json missing blurbs for: {missing}. Every offerable "
            "skill needs one or its offers fall back to the bare skill_name."
        )

    def test_bilingual_envelope_and_clean_content(self):
        descs = self._load()
        for sid, entry in descs.items():
            for field in ("display_name", "description"):
                assert set(entry[field].keys()) == {"en", "ar"}, (
                    f"{sid}.{field}: bilingual envelope {{en, ar}} required"
                )
                en = entry[field]["en"]
                assert en and en.strip(), f"{sid}.{field}.en empty"
                assert "—" not in en, f"{sid}.{field}: em dash in content"
            assert len(entry["description"]["en"]) <= 160, f"{sid}: blurb too long for an offer line"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engagement_templates.py -k Coverage -v` — Expected: FileNotFoundError.

- [ ] **Step 3: Create the content file**

Create `src/sage_poc/prompts/offer_descriptions.json` (draft pending clinical review; `ar` keys null until Khaleeji content is authored):

```json
{
  "_meta": {
    "version": "0.2.0",
    "status": "draft-pending-review",
    "authored_by": "engineering",
    "approved_by": null,
    "purpose": "Plain-language descriptions used in R1 skill offers. Bilingual envelope: ar null falls back to en (output_gate translates the composed reply for Arabic sessions). When clinician-authored Khaleeji blurbs land, they become the verbatim display names echoed in offers and accept-classification.",
    "review_required": ["Clinical review of every display_name and description before production"]
  },
  "descriptions": {
    "box_breathing": {"display_name": {"en": "Box breathing", "ar": null}, "description": {"en": "a short guided breathing exercise, around five minutes, that helps your body settle when it feels wound up", "ar": null}},
    "grounding_5_4_3_2_1": {"display_name": {"en": "5-4-3-2-1 grounding", "ar": null}, "description": {"en": "a quick exercise using your five senses to come back to the present moment, takes a few minutes", "ar": null}},
    "stop_technique": {"display_name": {"en": "The STOP pause", "ar": null}, "description": {"en": "a one minute pause technique for catching yourself before reacting in a heated moment", "ar": null}},
    "dbt_tipp": {"display_name": {"en": "TIPP reset", "ar": null}, "description": {"en": "a fast physical reset using cold water and movement for very intense moments, about ten minutes", "ar": null}},
    "progressive_muscle_relaxation": {"display_name": {"en": "Muscle relaxation", "ar": null}, "description": {"en": "a guided exercise tensing and releasing muscle groups to let go of physical tension, ten to fifteen minutes", "ar": null}},
    "safe_place_visualization": {"display_name": {"en": "Safe place imagery", "ar": null}, "description": {"en": "a calming exercise where you picture a place that feels safe and settle into it, about ten minutes", "ar": null}},
    "mindfulness_body_scan": {"display_name": {"en": "Body scan", "ar": null}, "description": {"en": "a slow check-in through your body to notice and release tension, ten to fifteen minutes", "ar": null}},
    "cbt_thought_record": {"display_name": {"en": "Thought check", "ar": null}, "description": {"en": "a step by step way to take one heavy thought and test how true it really is, ten to fifteen minutes", "ar": null}},
    "cognitive_restructuring": {"display_name": {"en": "Reframing practice", "ar": null}, "description": {"en": "working through a stuck thought pattern and finding a fairer way to see it, ten to fifteen minutes", "ar": null}},
    "behavioral_activation": {"display_name": {"en": "Small steps plan", "ar": null}, "description": {"en": "picking one small doable activity to lift the week, planned together in about ten minutes", "ar": null}},
    "worry_time": {"display_name": {"en": "Worry time", "ar": null}, "description": {"en": "a way to contain spinning worries by giving them a fixed daily slot instead of the whole day, ten minutes to set up", "ar": null}},
    "problem_solving_therapy": {"display_name": {"en": "Problem solving", "ar": null}, "description": {"en": "breaking one real problem into options and a first step you choose, ten to fifteen minutes", "ar": null}},
    "sleep_hygiene": {"display_name": {"en": "Sleep reset", "ar": null}, "description": {"en": "going through what is disrupting your sleep and building a wind down routine that fits you, about ten minutes", "ar": null}},
    "mood_check_in": {"display_name": {"en": "Mood check-in", "ar": null}, "description": {"en": "a short guided check-in on how you are really doing, about five minutes", "ar": null}},
    "mi_readiness_ruler": {"display_name": {"en": "Readiness check", "ar": null}, "description": {"en": "a quick way to weigh how ready you feel for a change you have been considering, about five minutes", "ar": null}},
    "values_clarification": {"display_name": {"en": "What matters most", "ar": null}, "description": {"en": "exploring what you care about most so decisions get easier, ten to fifteen minutes", "ar": null}},
    "assertive_communication": {"display_name": {"en": "Speaking up practice", "ar": null}, "description": {"en": "preparing how to say a hard thing clearly and kindly, with practice, ten to fifteen minutes", "ar": null}},
    "interpersonal_effectiveness": {"display_name": {"en": "Asking for what you need", "ar": null}, "description": {"en": "a structured way to prepare a difficult ask or set a limit with someone, ten to fifteen minutes", "ar": null}},
    "self_compassion_break": {"display_name": {"en": "Self-kindness pause", "ar": null}, "description": {"en": "a short practice for being as kind to yourself as you would be to a friend, about five minutes", "ar": null}},
    "act_psychological_flexibility": {"display_name": {"en": "Unhooking from thoughts", "ar": null}, "description": {"en": "practicing how to notice difficult thoughts without being dragged around by them, about ten minutes", "ar": null}},
    "psychoed_anxiety": {"display_name": {"en": "Understanding anxiety", "ar": null}, "description": {"en": "a plain language walk through of how anxiety works in the body and what actually helps, about ten minutes", "ar": null}},
    "psychoed_depression": {"display_name": {"en": "Understanding low mood", "ar": null}, "description": {"en": "a plain language walk through of how low mood feeds itself and what helps break the loop, about ten minutes", "ar": null}},
    "psychoed_stress": {"display_name": {"en": "Understanding stress", "ar": null}, "description": {"en": "a plain language walk through of what stress does to you and practical ways to lower it, about ten minutes", "ar": null}},
    "financial_anxiety": {"display_name": {"en": "Money worry support", "ar": null}, "description": {"en": "working through money stress step by step and finding one thing in your control, ten to fifteen minutes", "ar": null}},
    "grief_loss": {"display_name": {"en": "Space for grief", "ar": null}, "description": {"en": "gentle guided space to be with a loss at your own pace, no fixing, about fifteen minutes", "ar": null}}
  }
}
```

- [ ] **Step 4: Run tests, then commit**

Run: `uv run pytest tests/test_engagement_templates.py -v` — Expected: all PASS. If coverage reports a registry skill missing (drift since plan authoring), author its blurb in the same style.

```bash
git add src/sage_poc/prompts/offer_descriptions.json tests/test_engagement_templates.py
git commit -m "feat(R1): bilingual-enveloped offer descriptions for all offerable skills (draft-pending-review)"
```

---

### Task 6: R1 — L2_skill_offer template + composer support

**Files:**
- Create: `src/sage_poc/prompts/templates/L2_intents/skill_offer.json`
- Modify: `src/sage_poc/prompts/composer.py`
- Test: `tests/test_engagement_templates.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_engagement_templates.py`:

```python
def _composer_state(**overrides) -> dict:
    base = {
        "raw_message": "I keep worrying about everything",
        "message_en": "I keep worrying about everything",
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "new_clinical_flags_turn": [],
        "third_party_crisis": False,
        "crisis_state": "none",
        "code_switching": False,
        "primary_intent": "new_skill",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 6,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "path": [],
        "turn_count": 1,
    }
    return {**base, **overrides}


class TestSkillOfferComposition:
    def test_offer_template_selected_when_offer_pending(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state(offered_skill_ids=["worry_time", "cognitive_restructuring"])
        system_str, user_str, layers = compose_prompt(state)
        assert "Worry time" in user_str, "en display_name from offer_descriptions must be injected"
        assert "Reframing practice" in user_str
        assert "Do not begin any exercise this turn" in user_str
        assert "continuing to talk" in user_str

    def test_unmatched_template_still_used_without_offer(self):
        from sage_poc.prompts.composer import compose_prompt
        state = _composer_state()
        system_str, user_str, layers = compose_prompt(state)
        assert "Do not begin any exercise this turn" not in user_str

    def test_offer_template_is_draft_and_clean(self):
        reload_all()
        tmpl = get_intent_template("skill_offer")
        assert tmpl is not None
        assert "—" not in tmpl.content
        assert set(tmpl.variables) == {"intensity", "intensity_guidance", "offer_options_block"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_engagement_templates.py -k Offer -v` — Expected: FAIL.

- [ ] **Step 3: Create the template**

Create `src/sage_poc/prompts/templates/L2_intents/skill_offer.json`:

```json
{
  "template_id": "L2_skill_offer",
  "version": "0.1.0",
  "status": "draft-pending-review",
  "authored_by": "engineering",
  "approved_by": null,
  "effective_date": "pending",
  "layer": "L2",
  "role": "user",
  "always_include": true,
  "word_budget": 170,
  "content": "INTENT: The user described something a short structured exercise could help with. A choice must be offered before any exercise begins. Emotional intensity: {intensity}/10. {intensity_guidance} First name the specific thing the user described, in one sentence. Then offer these options in plain everyday words, including roughly how long each takes:\n{offer_options_block}\nMake clear that simply continuing to talk is an equally good choice. Ask which they would prefer, as one short question. Do not begin any exercise this turn. Do not use clinical or technique jargon beyond the names given. Do not pressure, the user saying no is a complete answer. Keep the whole reply to 2-4 sentences plus the options.",
  "variables": ["intensity", "intensity_guidance", "offer_options_block"],
  "intent": "skill_offer",
  "_review_required": [
    "Rule 1 approval (new L2 selector in composer.py, control-layer change)",
    "Clinical review (offer framing, non-coercion wording)"
  ]
}
```

- [ ] **Step 4: Composer changes**

In `src/sage_poc/prompts/composer.py`:

(a) Imports (merge with existing): `import json as _json`, `from functools import lru_cache`, `from pathlib import Path`.

(b) Below `_INTENSITY_GUIDANCE`:

```python
_OFFER_DESCRIPTIONS_PATH = Path(__file__).parent / "offer_descriptions.json"


@lru_cache(maxsize=1)
def _offer_descriptions() -> dict:
    try:
        return _json.loads(_OFFER_DESCRIPTIONS_PATH.read_text(encoding="utf-8"))["descriptions"]
    except Exception as exc:
        _log.warning("offer_descriptions.json unavailable: %s", exc)
        return {}


def _bilingual(entry_field: dict, language: str) -> str:
    """Bilingual envelope accessor: ar falls back to en when null/absent."""
    return entry_field.get(language) or entry_field["en"]


def _build_offer_options_block(offered_skill_ids: list[str], language: str) -> str:
    """One numbered line per offered skill: display name plus plain blurb.
    Falls back to registry skill_name when a blurb is missing (coverage test
    in test_engagement_templates.py should make that unreachable)."""
    descs = _offer_descriptions()
    lines: list[str] = []
    for i, sid in enumerate(offered_skill_ids, 1):
        entry = descs.get(sid)
        if entry:
            name = _bilingual(entry["display_name"], language)
            desc = _bilingual(entry["description"], language)
            lines.append(f"{i}. {name}: {desc}")
        else:
            try:
                lines.append(f"{i}. {load_skill(sid).skill_name}")
            except Exception:
                _log.warning("offer options: unknown skill_id %s skipped", sid)
    return "\n".join(lines)
```

(c) Extend `_build_l2_intent_block` with `extra_variables: dict[str, str] | None = None` (last parameter) and merge into the variables dict:

```python
    variables: dict[str, str] = {
        "intensity": str(intensity),
        "intensity_guidance": guidance,
        **(extra_variables or {}),
    }
```

(d) In `compose_prompt`, replace the `_l2_intent` selector:

```python
    # R1 (2026-06-12): a pending skill offer overrides intent-based L2 selection.
    # State-driven because the offer is created by skill_select, not intent_route.
    _offer_ids = state.get("offered_skill_ids") or []
    if _offer_ids:
        _l2_intent = "skill_offer"
        _l2_extra = {"offer_options_block": _build_offer_options_block(_offer_ids, language)}
    else:
        _l2_intent = (
            "new_skill_unmatched"
            if primary_intent == "new_skill" and not state.get("active_skill_id")
            else primary_intent
        )
        _l2_extra = None
    l2_block = _build_l2_intent_block(_l2_intent, intensity, secondary_intent, extra_variables=_l2_extra)
```

- [ ] **Step 5: Run tests, then commit**

Run: `uv run pytest tests/test_engagement_templates.py tests/test_composer_intensity.py -v` — Expected: all PASS.

```bash
git add src/sage_poc/prompts/templates/L2_intents/skill_offer.json src/sage_poc/prompts/composer.py tests/test_engagement_templates.py
git commit -m "feat(R1): L2_skill_offer template; composer renders bilingual offer options (draft-pending-review)"
```

---

### Task 7: R1 — skill_select consumes the rules; accept promotion; routing

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`, `src/sage_poc/graph.py`
- Test: `tests/test_skill_select_offer.py` (create), `tests/test_routing.py` (extend)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_select_offer.py`:

```python
"""R1: consent-gated skill entry, driven by the skill_matching rules category.
skill_select collects candidates, asks the Rules Service how to proceed, and
either offers (offered_skill_ids) or enters directly. Fired rule_id is audited
in the path."""
import pytest

import sage_poc.nodes.skill_select as ss
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.skills.schema import load_skill


def make_state(**kwargs) -> dict:
    defaults = {
        "raw_message": kwargs.get("message_en", ""),
        "message_en": kwargs.get("message_en", ""),
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "new_skill",
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 6,
        "path": [],
        "therapeutic_profile": None,
        "offered_skill_ids": None,
        "offer_response": None,
        "offer_choice_skill_id": None,
        "declined_skills": [],
    }
    return {**defaults, **kwargs}


async def test_keyword_match_creates_offer_not_activation():
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(message_en=f"Lately {kw} and it will not stop")
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword_offer"
    assert "skill_offer_made" in result["path"]
    assert any(p.startswith("skill_matching_rule:") for p in result["path"]), (
        "fired rule_id must be audited in path"
    )


async def test_acute_somatic_high_intensity_enters_directly():
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(message_en=f"Help, {kw}", emotional_intensity=9)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing"
    assert not result.get("offered_skill_ids")
    assert result["skill_match_method"] == "keyword"


async def test_acute_direct_entry_ignores_declined():
    """ignore_declined in the acute rule: a prior decline must not block acute entry."""
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(
        message_en=f"Help, {kw}",
        emotional_intensity=9,
        declined_skills=["box_breathing"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "box_breathing", "safety over preference"


async def test_acute_somatic_low_intensity_still_offers():
    kw = load_skill("box_breathing").target_presentations[0]
    state = make_state(message_en=f"Sometimes {kw}", emotional_intensity=4)
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None
    assert result["offered_skill_ids"][0] == "box_breathing"


async def test_two_keyword_matches_offer_top_two_by_specificity():
    kw_a = load_skill("cbt_thought_record").target_presentations[0]
    kw_b = load_skill("worry_time").target_presentations[0]
    state = make_state(message_en=f"{kw_a} and also {kw_b} all day")
    result = await skill_select_node(state)
    offered = result["offered_skill_ids"]
    assert set(offered) == {"cbt_thought_record", "worry_time"}
    expected_first = "cbt_thought_record" if len(kw_a) >= len(kw_b) else "worry_time"
    assert offered[0] == expected_first


async def test_declined_skill_is_not_offered_again():
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(
        message_en=f"Lately {kw} and it will not stop",
        declined_skills=["cbt_thought_record"],
    )
    result = await skill_select_node(state)
    assert not result.get("offered_skill_ids") or \
        "cbt_thought_record" not in result["offered_skill_ids"]


async def test_accept_promotes_offered_skill():
    state = make_state(
        message_en="yes let us try it",
        offered_skill_ids=["worry_time", "cognitive_restructuring"],
        offer_response="accept",
        offer_choice_skill_id="cognitive_restructuring",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "cognitive_restructuring"
    assert result["active_step_id"] == load_skill("cognitive_restructuring").steps[0].step_id
    assert result["offered_skill_ids"] is None
    assert result["skill_match_method"] == "offer_accept"
    assert "offer_promoted" in result["path"]


async def test_accept_with_invalid_choice_falls_back_to_first():
    state = make_state(
        message_en="yes",
        offered_skill_ids=["worry_time"],
        offer_response="accept",
        offer_choice_skill_id="not_a_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "worry_time"


async def test_post_crisis_auto_select_bypasses_offer():
    state = make_state(message_en="I am okay I think", crisis_state="monitoring")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert not result.get("offered_skill_ids")


async def test_semantic_match_creates_offer(monkeypatch):
    # fully mocked semantic tier: no BGE load, no slow marker
    monkeypatch.setattr(
        ss, "_semantic_match_with_runner_up",
        lambda message_en, profile_context="": ("worry_time", 0.51, ("cognitive_restructuring", 0.49)),
    )
    state = make_state(message_en="everything spirals in my head at night and I cannot switch off")
    result = await skill_select_node(state)
    if result["skill_match_method"] in ("keyword", "keyword_offer"):
        pytest.skip("phrase unexpectedly keyword-matched; semantic path not exercised")
    assert result["offered_skill_ids"] == ["worry_time", "cognitive_restructuring"]
    assert result["skill_match_method"] == "semantic_offer"


async def test_enter_direct_without_ignore_declined_falls_back_to_offer_with_audit_marker(monkeypatch):
    """A clinician-authored enter_direct rule WITHOUT ignore_declined that matches a
    declined skill falls through to the consent path, and the audit trail records the
    divergence between the fired rule's action and the action taken."""
    from sage_poc.rules.schemas import EvalResult, FiredRule

    def fake_evaluate(category, context):
        assert category == "skill_matching"
        res = EvalResult()
        res.fired.append(FiredRule(
            rule_id="hypothetical_direct_rule",
            version="0.1.0",
            action={"type": "enter_direct"},   # no ignore_declined
        ))
        return res

    monkeypatch.setattr(ss.rules_engine, "evaluate", fake_evaluate)
    kw = load_skill("cbt_thought_record").target_presentations[0]
    state = make_state(
        message_en=f"Lately {kw} and it will not stop",
        declined_skills=["cbt_thought_record"],
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] is None, "consent fallback must win over a declined direct entry"
    assert "enter_direct_declined_fallback" in result["path"]
```

(If `EvalResult`/`FiredRule` live in a different module than `sage_poc.rules.schemas`, import them from where the engine does.)

Append to `tests/test_routing.py`:

```python
# ── R1: pending-offer routing ─────────────────────────────────────────────────

def test_offer_accept_routes_to_skill_select_bypassing_confidence():
    from sage_poc.graph import _route_after_intent
    state = {
        "primary_intent": "general_chat",
        "intent_confidence": 0.3,   # below gate; bare accepts are expected
        "crisis_state": "none",
        "offered_skill_ids": ["worry_time"],
        "offer_response": "accept",
        "active_skill_id": None,
    }
    assert _route_after_intent(state) == "skill_select"


def test_offer_decline_routes_normally():
    from sage_poc.graph import _route_after_intent
    state = {
        "primary_intent": "general_chat",
        "intent_confidence": 0.9,
        "crisis_state": "none",
        "offered_skill_ids": None,   # intent_route cleared it on decline
        "offer_response": "decline",
        "active_skill_id": None,
    }
    assert _route_after_intent(state) == "freeflow"


def test_crisis_still_beats_pending_offer():
    from sage_poc.graph import _route_after_intent
    state = {
        "primary_intent": "crisis",
        "intent_confidence": 0.9,
        "crisis_state": "none",
        "offered_skill_ids": ["worry_time"],
        "offer_response": "accept",
        "active_skill_id": None,
    }
    assert _route_after_intent(state) == "crisis"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_skill_select_offer.py tests/test_routing.py -m "not slow" -v`
Expected: offer tests FAIL (direct activation today); accept routing test FAILS (low_confidence).

- [ ] **Step 3: Implement skill_select**

In `src/sage_poc/nodes/skill_select.py`:

(a) Add import: `from sage_poc.rules import engine as rules_engine`. Remove nothing else.

(b) Add the resolution helper above `skill_select_node` (note: NO Python constants for the policy — list, threshold, count all come from the rules file):

```python
_FALLBACK_OFFER_ACTION = {"type": "offer", "max_offered": 2, "declined_scope": "session"}


def _resolve_entry(
    state: SageState,
    candidates: list[str],
    method: str,
    semantic_score: float | None,
) -> dict:
    """Ask the skill_matching rules how the primary candidate enters the
    conversation, then build the node result. candidates are ranked, NOT yet
    filtered by declined_skills — declined handling is the fired rule's decision
    (acute rule sets ignore_declined)."""
    primary = candidates[0]
    eval_result = rules_engine.evaluate("skill_matching", {
        "matched_skill_id": primary,
        "emotional_intensity": state.get("emotional_intensity", 5),
    })
    if eval_result.fired:
        fired = eval_result.fired[0]
        action, rule_id = fired.action, fired.rule_id
    else:
        # No rules loaded: consent is the fail-safe default, never silent entry.
        action, rule_id = _FALLBACK_OFFER_ACTION, "fallback_offer"
        logger.warning("[skill_select] no skill_matching rule fired; defaulting to offer")

    declined = set(state.get("declined_skills") or [])
    audit_markers = ["skill_select", f"skill_matching_rule:{rule_id}"]

    if action["type"] == "enter_direct":
        if action.get("ignore_declined") or primary not in declined:
            skill = _SKILLS[primary]
            return {
                "active_skill_id": primary,
                "active_step_id": skill.steps[0].step_id,
                "skill_match_method": method,
                "semantic_score": semantic_score,
                "path": state["path"] + audit_markers,
            }
        # A clinician-authored enter_direct rule without ignore_declined matched a
        # declined skill: consent fallback wins, and the audit trail must say so —
        # the fired rule's action and the action taken differ on this turn.
        audit_markers.append("enter_direct_declined_fallback")

    offerable = [sid for sid in candidates if sid not in declined]
    offerable = offerable[: int(action.get("max_offered", 2))]
    if not offerable:
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "path": state["path"] + audit_markers + ["all_candidates_declined"],
        }
    return {
        "active_skill_id": None,
        "active_step_id": None,
        "offered_skill_ids": offerable,
        "skill_match_method": f"{method}_offer",
        "semantic_score": semantic_score,
        "path": state["path"] + audit_markers + ["skill_offer_made"],
    }
```

Note: when an `enter_direct` rule falls through to the offer path, `max_offered` may be absent from its action; the `int(action.get("max_offered", 2))` default covers that.

(c) Accept promotion early-return, placed AFTER the psychotic auto-select block, BEFORE Tier 1 (all auto-select safety paths outrank a stale offer):

```python
    # R1: accepted offer promotion.
    offered = state.get("offered_skill_ids") or []
    if offered and state.get("offer_response") == "accept":
        chosen = state.get("offer_choice_skill_id")
        if chosen not in _SKILLS or chosen not in offered:
            chosen = offered[0]
        skill = _SKILLS[chosen]
        return {
            "active_skill_id": chosen,
            "active_step_id": skill.steps[0].step_id,
            "offered_skill_ids": None,
            "skill_match_method": "offer_accept",
            "semantic_score": None,
            "path": state["path"] + ["skill_select", "offer_promoted"],
        }
```

(d) Tier 1: collect ranked matches (no declined pre-filter — the rule decides), keep SF-1 best-match semantics (stable sort preserves registry order on ties):

```python
    kw_matches: dict[str, int] = {}   # skill_id -> longest matched keyword length
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            kw_lower = keyword.lower()
            if kw_lower in message_en or (detected_language == "ar" and kw_lower in raw_message):
                if len(kw_lower) > kw_matches.get(skill_id, 0):
                    kw_matches[skill_id] = len(kw_lower)

    if kw_matches:
        ranked_kw = sorted(kw_matches.items(), key=lambda x: x[1], reverse=True)
        candidates = [sid for sid, _ in ranked_kw]
        return _resolve_entry(state, candidates, method="keyword", semantic_score=None)
```

(e) Tier 2 runner-up: rename the body of `_semantic_match_sync` to `_semantic_match_with_runner_up` returning `tuple[str | None, float, tuple[str, float] | None]`. Inside, after `ranked` is built, add:

```python
    def _runner_up(best: str | None) -> tuple[str, float] | None:
        if best is None:
            return None
        for sid, sc in ranked:
            if sid != best and sc >= SEMANTIC_THRESHOLD:
                return (sid, sc)
        return None
```

Every existing `return X, Y` becomes `return X, Y, _runner_up(X)` (the early `return None, 0.0` becomes `return None, 0.0, None`; in the rerank branch capture `best_sid_r, best_score_r = rerank_candidates(...)` then `return best_sid_r, best_score_r, _runner_up(best_sid_r)`). Keep a 2-tuple back-compat wrapper (an existing test calls `_semantic_match_sync` directly):

```python
def _semantic_match_sync(message_en: str, profile_context: str = "") -> tuple[str | None, float]:
    best, score, _ = _semantic_match_with_runner_up(message_en, profile_context)
    return best, score
```

(f) Tier 2 call site: call `_semantic_match_with_runner_up` via `asyncio.to_thread`, then:

```python
    if semantic_skill is not None:
        candidates = [semantic_skill]
        if runner_up is not None and runner_up[0] != semantic_skill:
            candidates.append(runner_up[0])
        return _resolve_entry(state, candidates, method="semantic", semantic_score=round(score, 4))
```

(g) `graph.py` `_route_after_intent`: after the `crisis_state == "monitoring"` branch, before the confidence gate:

```python
    # R1: accept reply to a pending offer routes to skill_select for promotion.
    # Bypasses the confidence gate: bare accepts classify low-confidence by nature
    # (same precedent as post-crisis monitoring).
    if (state.get("offered_skill_ids") or []) and state.get("offer_response") == "accept":
        return "skill_select"
```

- [ ] **Step 4: Run tests; migrate existing assertions**

Run: `uv run pytest tests/test_skill_select_offer.py tests/test_routing.py tests/test_skill_select.py tests/test_skill_matching_rules.py -m "not slow" -v`

New tests PASS. **Pre-existing `test_skill_select.py` Tier-1/Tier-2 direct-activation assertions now FAIL by design** — migrate each to the offer contract: `result["offered_skill_ids"][0] == <skill>` + `result["active_skill_id"] is None` (default test intensity is 5, so the acute rule does not fire). SF-1 specificity assertions apply to `offered_skill_ids[0]`. Do NOT change assertions for info_request, post-crisis, or psychotic auto-select paths — if one of those fails, the implementation is wrong, not the test. Per the measurement-first principle, any harness (skill_ux_runner, wrong-skill suite) reading `active_skill_id` gets the same one-line mapping; clinical content is never edited to satisfy a harness.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py src/sage_poc/graph.py tests/test_skill_select_offer.py tests/test_routing.py tests/test_skill_select.py
git commit -m "feat(R1): skill_select consumes skill_matching rules; top-2 offers; accept promotion; rule_id audited in path"
```

---

### Task 8: R1 — intent_route offer classification

**Files:**
- Modify: `src/sage_poc/nodes/intent_route.py`
- Test: `tests/test_intent_route_node.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_intent_route_node.py`:

```python
# ── R1: pending-offer classification ─────────────────────────────────────────

_OFFER_STATE_KW = dict(
    offered_skill_ids=["box_breathing", "grounding_5_4_3_2_1"],
    declined_skills=[],
)


@pytest.mark.asyncio
async def test_offer_accept_parsed_with_choice():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.4, "emotional_intensity": 4, "engagement": 5, '
        '"offer_response": "accept", "offer_choice_skill_id": "grounding_5_4_3_2_1"}'
    )
    state = _base_state(message_en="the second one", **_OFFER_STATE_KW)
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_response"] == "accept"
    assert result["offer_choice_skill_id"] == "grounding_5_4_3_2_1"
    assert "offered_skill_ids" not in result, "accept must NOT clear the offer; skill_select promotes it"
    assert "offer_accepted" in result["path"]


@pytest.mark.asyncio
async def test_offer_accept_invalid_choice_defaults_to_first():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.5, "emotional_intensity": 4, "engagement": 5, '
        '"offer_response": "accept", "offer_choice_skill_id": "hallucinated_skill"}'
    )
    state = _base_state(message_en="yes", **_OFFER_STATE_KW)
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_choice_skill_id"] == "box_breathing"


@pytest.mark.asyncio
async def test_offer_decline_clears_offer_and_records_declines():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.8, "emotional_intensity": 4, "engagement": 5, '
        '"offer_response": "decline", "offer_choice_skill_id": null}'
    )
    state = _base_state(message_en="no, I would rather just talk", **_OFFER_STATE_KW)
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_response"] == "decline"
    assert result["offered_skill_ids"] is None
    assert result["declined_skills"] == ["box_breathing", "grounding_5_4_3_2_1"]
    assert "offer_declined" in result["path"]


@pytest.mark.asyncio
async def test_offer_other_clears_offer_without_declining():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 6, "engagement": 7, '
        '"offer_response": "other", "offer_choice_skill_id": null}'
    )
    state = _base_state(message_en="actually my real problem is I cannot sleep", **_OFFER_STATE_KW)
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offered_skill_ids"] is None
    assert "declined_skills" not in result, "ignoring an offer is not a decline; no cooldown"
    assert "offer_ignored" in result["path"]


@pytest.mark.asyncio
async def test_no_offer_pending_emits_no_offer_fields():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 3, "engagement": 5}'
    )
    state = _base_state(message_en="hello")
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert "offer_response" not in result


def test_prompt_contains_pending_offer_block_only_when_offered():
    from sage_poc.nodes.intent_route import build_intent_prompt
    with_offer = build_intent_prompt(_base_state(message_en="yes", **_OFFER_STATE_KW))
    without = build_intent_prompt(_base_state(message_en="yes"))
    assert "PENDING OFFER" in with_offer
    assert "box_breathing" in with_offer
    assert "the first one" in with_offer, "ordinal mapping instruction must be present"
    assert "PENDING OFFER" not in without


# Arabic-session offer classification: the node logic is language-blind (it reads
# message_en), but these pin the contract for Arabic sessions — the only fragile
# point in the Arabic offer path until authored Arabic display names land.
# (C-1/C-2 lesson: English-validated-only is how cultural gaps shipped before.)

@pytest.mark.asyncio
async def test_arabic_accept_with_positional_choice():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.5, "emotional_intensity": 4, "engagement": 5, '
        '"offer_response": "accept", "offer_choice_skill_id": "grounding_5_4_3_2_1"}'
    )
    state = _base_state(
        message_en="yes let's try the second one",
        detected_language="ar",
        **_OFFER_STATE_KW,
    )
    state["raw_message"] = "ايه يلا نجرب الثاني"
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_response"] == "accept"
    assert result["offer_choice_skill_id"] == "grounding_5_4_3_2_1", (
        "Arabic ordinal ('الثاني') must map to the second offered option"
    )
    assert "offer_accepted" in result["path"]


@pytest.mark.asyncio
async def test_arabic_decline_records_cooldown():
    from sage_poc.nodes.intent_route import intent_route_node
    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.7, "emotional_intensity": 4, "engagement": 4, '
        '"offer_response": "decline", "offer_choice_skill_id": null}'
    )
    state = _base_state(
        message_en="no I just want to talk",
        detected_language="ar",
        **_OFFER_STATE_KW,
    )
    state["raw_message"] = "لا بس ابي اتكلم"
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)
    assert result["offer_response"] == "decline"
    assert result["offered_skill_ids"] is None
    assert result["declined_skills"] == ["box_breathing", "grounding_5_4_3_2_1"]
    assert "offer_declined" in result["path"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_intent_route_node.py -k offer -v` — Expected: FAIL.

- [ ] **Step 3: Implement**

In `src/sage_poc/nodes/intent_route.py` — `INTENT_SYSTEM` is NOT touched (SPOF guard: the general_chat definition stays byte-identical):

(a) `build_intent_prompt` — add the conditional block before the final return:

```python
    offer_block = ""
    offered = state.get("offered_skill_ids") or []
    if offered:
        names = ", ".join(f'"{sid}"' for sid in offered)
        offer_block = (
            "\nPENDING OFFER: Last turn Sage offered the user a choice of these exercises: "
            f"[{names}]. Add two EXTRA fields to your JSON:\n"
            '- offer_response: "accept" if the user agrees to try an offered exercise, '
            '"decline" if they refuse the offer or prefer to keep talking, "other" if the '
            "message is about something else entirely (new topic, new symptom, a question).\n"
            "- offer_choice_skill_id: when offer_response is accept, the chosen exercise id "
            f"(one of [{names}]; if the user did not specify which, use the first), else null.\n"
            'A short bare agreement ("yes", "ok", "sure", "yalla", or Arabic equivalents) is accept. '
            'References like "the first one", "the second one", and their Arabic equivalents '
            '("الاول", "الثاني") map to the options by position. '
            "All other classification rules are unchanged; classify primary_intent as usual."
        )
    return f"{active}{history_block}{offer_block}\n\nUser message: {state['message_en']}"
```

(b) `intent_route_node` — after building `result`, before the gate_path lines:

```python
    offered = state.get("offered_skill_ids") or []
    if offered:
        offer_response = data.get("offer_response")
        if offer_response not in ("accept", "decline", "other"):
            offer_response = "other"
        result["offer_response"] = offer_response
        if offer_response == "accept":
            choice = data.get("offer_choice_skill_id")
            result["offer_choice_skill_id"] = choice if choice in offered else offered[0]
            result["path"] = result["path"] + ["offer_accepted"]
        elif offer_response == "decline":
            result["offered_skill_ids"] = None
            # dict.fromkeys: order-preserving dedup (clinical audit convention)
            result["declined_skills"] = list(dict.fromkeys(
                (state.get("declined_skills") or []) + list(offered)
            ))
            result["path"] = result["path"] + ["offer_declined"]
        else:
            result["offered_skill_ids"] = None
            result["path"] = result["path"] + ["offer_ignored"]
```

- [ ] **Step 4: Run tests, then commit**

Run: `uv run pytest tests/test_intent_route_node.py -v` — Expected: all PASS.

```bash
git add src/sage_poc/nodes/intent_route.py tests/test_intent_route_node.py
git commit -m "feat(R1): intent_route classifies pending-offer replies; decline records session-scoped declines"
```

---

### Task 9: Full-suite verification, guard tests, architecture doc

- [ ] **Step 1: Full not-slow suite**

Run: `uv run pytest tests/ -q -m "not slow" 2>&1 | tail -5`
Expected: 0 failures. Likely churn points: `test_graph.py` end-to-end skill activation flows (insert the offer turn: first invoke yields offer, second with accept yields activation) and `test_server.py` (mind the known module-scope fixture bleed — use per-test session_ids).

- [ ] **Step 2: Slow guard tests (LLM-dependent)**

Run: `uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m "slow" -v`
Expected: PASS — mandatory after any intent_route module change even though INTENT_SYSTEM is untouched.

Run: `uv run pytest tests/test_skill_select.py tests/test_skill_select_offer.py -m "slow" -q 2>&1 | tail -3`
Expected: PASS against the offer contract.

- [ ] **Step 3: Update the living architecture doc**

In `docs/SageAI_architecture_current.md`:
- §2.3 routing table: `offered_skill_ids set AND offer_response == "accept"` → skill_select (offer promotion, bypasses confidence gate); Tier 1/2 match → freeflow with `L2_skill_offer` unless `acute_direct_entry` fires.
- New Rules Service category: `skill_matching` (first-match-wins by priority; signals matched_skill_id + emotional_intensity; actions enter_direct/offer; rule_id audited in path). Document the declined-fallthrough interaction for rule authors: an `enter_direct` rule WITHOUT `ignore_declined` that matches a declined skill falls through to the consent path, and the turn's path carries `enter_direct_declined_fallback` so the audit trail explains the divergence between fired rule and action taken.
- §5.2: offer flow, early-return order (info_request → post-crisis → psychotic → offer promotion → Tier 1 → Tier 2), declined_skills session scope + stale-gap clearing, path markers and the acceptance-rate metric (count `offer_accepted` / count `skill_offer_made` in session_audit).
- §5.3/§5.5: `criteria_hold_budget` schema field (default null, per-skill opt-in), `criteria_hold_count` as seventh step_policy signal, entry_screen exemption invariant, soft-advance instruction content file.
- Header "Last updated" line.

```bash
git add docs/SageAI_architecture_current.md
git commit -m "docs: skill_matching rules category, offer flow, criteria_hold_budget in living architecture ref"
```

---

### Task 10: Manual smoke + PR

- [ ] **Step 1: Smoke conversation** (server up per project run conventions)

1. "I keep replaying one negative thought about myself" → offer turn: names the disclosure, up to 2 plain-language options with durations, keep-talking alternative, no exercise content.
2. "yes the first one" → cbt_thought_record step 1.
3. New session: same disclosure → "no, just want to talk" → graceful continuation; later matching turn in same session does NOT re-offer cbt_thought_record.
4. New session: "I can't breathe, my heart is racing right now, help" (high intensity) → DIRECT box_breathing entry, no menu.
5. "what do you think about the new traffic rules?" → brief substantive engagement, then bridge back.
6. In box_breathing (low intensity, accepted): two consecutive one-word answers → second one moves forward without re-asking.
7. Arabic session: "صار لي اسبوع ما اقدر انام وافكاري ما توقف" → offer turn rendered in Arabic (translated by output_gate), options named, keep-talking alternative present.
8. Khaleeji accept: "ايه يلا نجرب الاول" → first offered skill activates, step 1 delivered in Arabic.
9. Acute Gulf Arabic at high intensity: "ما اقدر اتنفس، قلبي يدق بسرعة، ساعدني" → DIRECT box_breathing entry, no menu (acute_direct_entry fires on the Arabic path; Tier 1 matches against raw_message for ar sessions).

- [ ] **Step 2: PR**

```bash
git push -u origin feat/engagement-r1-r3-r5
```

PR body: baseline vs final test counts; sign-off checklist — `skill_matching_rules.json`, `L2_skill_offer`, `offer_descriptions.json`, `soft_advance_instruction.json`, `L2_general_chat` v1.3.0 (Rule 1 + clinical); `criteria_hold_count` signal flagged as skill-schema extension needing clinical sign-off; architecture-doc diff flagged for human sign-off; acceptance-rate instrumentation note. Do NOT merge before sign-offs.

---

## Risks and explicit non-goals

- **Latency:** offer adds one conversational turn, zero extra LLM calls; the skill_matching evaluation is in-memory dict checks; Tier-2 runner-up reuses the same embedding pass.
- **Checkpoint compatibility:** all new state keys read via `.get(...)`; old checkpoints deserialize fine.
- **Fail-safe direction:** missing/empty skill_matching rules → offer (consent), never silent direct entry. Missing soft-advance content file → hardcoded fallback text + WARNING (response never silenced).
- **Existing-test churn is intentional and bounded:** Tier-1/Tier-2 direct-activation assertions → offer assertions. Auto-select assertions must not change.
- **Entry screens still run:** an accepted skill starts at its normal first step including entry_screen gates; consent does not bypass contraindication screening, and the R5 budget cannot advance past entry_screen (code invariant + null budgets on all LLM-criteria skills).
- **Store migration:** Cosmos/CMS (or interim Supabase rules table) replaces `rules/loader.py` file reads behind the same `get_rules()` interface; rule documents are the contract. No code in this plan binds to the file store beyond the loader.
