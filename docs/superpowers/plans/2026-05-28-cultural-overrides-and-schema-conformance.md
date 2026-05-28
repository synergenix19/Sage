# Cultural Overrides Wiring + Schema Conformance Visibility

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `cultural_overrides` from all 20 skill JSONs into the composer's system prompt, and make the full USED vs STORED_ONLY field conformance matrix visible via a startup log, a `/health/schema-conformance` endpoint, and a clinician dashboard panel.

**Architecture:** `cultural_overrides` (a `dict[str, str]` of named guidance strings) is injected into `compose_prompt()` immediately after the global cultural rules block, scoped to the active skill. A new `conformance.py` module declares the authoritative field-status registry; `server.py` logs it at startup and exposes it as a GET endpoint; the Next.js admin page fetches it server-side and renders a new `SchemaConformancePanel` section.

**Tech Stack:** Python / FastAPI / Pydantic (sage-poc); Next.js 14 server components + Tailwind + Vitest (cdai/apps/web).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/sage_poc/prompts/composer.py` | Modify | Inject skill `cultural_overrides` into system prompt |
| `src/sage_poc/skills/conformance.py` | Create | Authoritative USED/STORED_ONLY/PARTIAL registry + `get_conformance_report()` |
| `server.py` | Modify | Startup log + `GET /health/schema-conformance` endpoint |
| `tests/test_prompts_composer.py` | Modify | Tests for cultural_overrides injection |
| `tests/test_schema_conformance.py` | Create | Tests for conformance module + endpoint |
| `cdai/apps/web/components/admin/schema-conformance-panel.tsx` | Create | Dashboard panel component |
| `cdai/apps/web/app/admin/page.tsx` | Modify | Fetch conformance report server-side |
| `cdai/apps/web/components/admin/admin-dashboard.tsx` | Modify | Add SchemaConformancePanel section |

---

## Background — What you need to know

### Skill JSON structure (all 20 skills)

```python
# src/sage_poc/skills/schema.py
class SkillStep(BaseModel):
    step_id: str
    goal: str                        # USED — {step_goal} in L3_skill_wrapper
    technique: str                   # USED — {technique_name}
    technique_description: str = ""  # USED — {technique_description}
    tone: str                        # USED — {tone_instruction}
    examples: list[str]              # USED — {few_shot_block}
    contraindications: str = ""      # USED — {contraindication_block}
    completion_criteria: str = ""    # PARTIAL — LLM reads it for 4/20 skills

class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str                  # STORED_ONLY
    evidence_base: str               # STORED_ONLY
    self_evolution: Literal["manual_only"] = "manual_only"  # STORED_ONLY
    target_presentations: list[str]
    semantic_description: str = ""
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]  # L1 USED, L2-L4 STORED_ONLY
    cultural_overrides: dict = Field(default_factory=dict)  # STORED_ONLY → this plan makes it USED
```

### cultural_overrides actual data format (from post_crisis_check_in.json)

```json
{
  "islamic_relief_language": "If the user expresses relief in Islamic terms (الحمد لله على السلامة), mirror this warmly. Islamic spiritual expression is a genuine coping resource, not avoidance. Do not redirect away from it.",
  "shame_help_seeking": "Post-crisis, Gulf users, particularly male users, may feel ashamed of having reached a crisis point. Actively counter this: frame reaching out as courage and strength. Never treat the check-in as a clinical debrief."
}
```

All 20 skills have `cultural_overrides` (2-4 entries each).

### Where cultural rules land in compose_prompt

`compose_prompt()` in `src/sage_poc/prompts/composer.py` builds 6 layers. Cultural layer:
```python
# Lines 322–344
cultural_result = rules_engine.evaluate("cultural", {...})
cultural_actions = sorted([a for a in cultural_result.actions if a.get("target") == "system"],
                           key=lambda a: a.get("priority", 5))
word_count = 0
for action in cultural_actions:
    content = action["content"]
    words = count_words(content)
    if word_count + words <= _CULTURAL_BUDGET_WORDS or word_count == 0:
        system_parts.append(content)
        word_count += words
    else:
        break
if cultural_actions:
    layers.append("cultural")
```

`_CULTURAL_BUDGET_WORDS = 250` (line 295). Skill overrides go **immediately after** this block, before `injection_result`.

### Test pattern (from test_freeflow_respond.py)

```python
def _no_rules():
    r = MagicMock()
    r.actions = []
    return r

with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
    system_str, user_str, layers = compose_prompt(state)
```

### Admin page fetch pattern (admin/page.tsx)

`AdminPage` is an async Server Component — it already fetches from Supabase server-side. `SAGE_API_URL` is a server-side env var (`http://localhost:8000` in `.env.local`). `fetch()` in Next.js server components is natively supported.

---

## Task 1: Wire cultural_overrides into the composer

**Files:**
- Modify: `src/sage_poc/prompts/composer.py` (lines 293–344 area)
- Modify: `tests/test_prompts_composer.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_prompts_composer.py`:

```python
# ---- cultural_overrides injection tests ----

from unittest.mock import MagicMock, patch
from sage_poc.prompts.composer import compose_prompt
from sage_poc.skills.schema import Skill, SkillStep, StepPolicyRule


def _no_rules():
    r = MagicMock()
    r.actions = []
    return r


def _make_state(**overrides):
    base = {
        "raw_message": "I feel better now",
        "detected_language": "en",
        "message_en": "I feel better now",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "monitoring", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "code_switching": False,
        "primary_intent": "skill_continuation", "secondary_intent": None,
        "intent_confidence": 0.9, "emotional_intensity": 4, "engagement": 6,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None, "rule_fired": None,
        "stale_skill_id": None, "re_escalation_within_monitoring": None,
        "response_en": None, "response": None, "path": [],
        "turn_count": 1, "conversation_history": [],
        "prompt_layers": [], "token_usage": {},
        "knowledge_passages": None, "knowledge_abstain": False,
        "knowledge_source": None,
    }
    return {**base, **overrides}


def _make_skill(overrides: dict | None = None) -> Skill:
    return Skill(
        skill_id="post_crisis_check_in",
        skill_name="Post-Crisis Check-In",
        skill_type="check_in",
        evidence_base="Clinical protocol",
        target_presentations=["post_crisis"],
        semantic_description="",
        steps=[SkillStep(
            step_id="s1",
            goal="Confirm safety",
            technique="Open check-in",
            tone="warm",
            examples=["How are you feeling right now?"],
            contraindications="",
            completion_criteria="",
        )],
        step_policy=[],
        escalation_matrix={"L1": "Exit gracefully"},
        cultural_overrides=overrides if overrides is not None else {
            "islamic_relief_language": "Mirror Islamic relief expressions warmly.",
            "shame_help_seeking": "Frame help-seeking as courage, not weakness.",
        },
    )


def test_cultural_overrides_injected_into_system_when_skill_active():
    skill = _make_skill()
    state = _make_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" in system_str
    assert "Mirror Islamic relief expressions warmly." in system_str
    assert "Frame help-seeking as courage, not weakness." in system_str
    assert "cultural_skill_overrides" in layers


def test_cultural_overrides_not_injected_when_no_active_skill():
    state = _make_state(active_skill_id=None)
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str
    assert "cultural_skill_overrides" not in layers


def test_cultural_overrides_empty_dict_not_injected():
    skill = _make_skill(overrides={})
    state = _make_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()),
        patch("sage_poc.prompts.composer.load_skill", return_value=skill),
    ):
        system_str, _, layers = compose_prompt(state)

    assert "SKILL-SPECIFIC CULTURAL CONTEXT" not in system_str
    assert "cultural_skill_overrides" not in layers


def test_cultural_overrides_load_failure_does_not_crash_composer():
    state = _make_state(active_skill_id="post_crisis_check_in")
    with (
        patch("sage_poc.prompts.composer.rules_engine.evaluate", return_value=_no_rules()),
        patch("sage_poc.prompts.composer.load_skill", side_effect=FileNotFoundError("missing")),
    ):
        system_str, _, layers = compose_prompt(state)

    # Composer must not raise; cultural_skill_overrides simply absent
    assert "cultural_skill_overrides" not in layers
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
pytest tests/test_prompts_composer.py::test_cultural_overrides_injected_into_system_when_skill_active -v
```

Expected: `FAILED` — `AssertionError` (SKILL-SPECIFIC CULTURAL CONTEXT not in system_str)

- [ ] **Step 3: Add `_CULTURAL_OVERRIDE_BUDGET_WORDS` constant to composer.py**

In `src/sage_poc/prompts/composer.py`, find the existing constants block (around line 293–296):

```python
_CULTURAL_BUDGET_WORDS = 250
_TOTAL_WORD_BUDGET = 1100
```

Add the new constant immediately after:

```python
_CULTURAL_BUDGET_WORDS = 250
_CULTURAL_OVERRIDE_BUDGET_WORDS = 200  # per-skill cultural override budget
_TOTAL_WORD_BUDGET = 1100
```

- [ ] **Step 4: Inject cultural_overrides in compose_prompt**

In `src/sage_poc/prompts/composer.py`, find the end of the global cultural rules block (around line 344):

```python
    if cultural_actions:
        layers.append("cultural")
```

Add the skill-level injection immediately after (before the `injection_result` block):

```python
    if cultural_actions:
        layers.append("cultural")

    # Skill-specific cultural overrides — more specific than global rules; injected after them.
    _active_for_overrides = state.get("active_skill_id")
    if _active_for_overrides:
        try:
            _override_skill = load_skill(_active_for_overrides)
            if _override_skill.cultural_overrides:
                _override_lines = "\n".join(
                    f"- {v}" for v in _override_skill.cultural_overrides.values()
                )
                _override_block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{_override_lines}"
                if count_words(_override_block) <= _CULTURAL_OVERRIDE_BUDGET_WORDS:
                    system_parts.append(_override_block)
                    layers.append("cultural_skill_overrides")  # only when actually injected
                else:
                    _log.warning(
                        "cultural_overrides exceeds budget for %s", _active_for_overrides
                    )
                    # Block not injected; no layer tag — audit trail must reflect reality
        except Exception as exc:
            _log.warning("cultural_overrides load failed for %s: %s", _active_for_overrides, exc)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_prompts_composer.py -v
```

Expected: All tests PASS including the 4 new ones.

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
pytest tests/ -x -q 2>&1 | tail -20
```

Expected: All existing tests pass.

> **Budget note (Tier 3 work, not fixed here):** The 200-word sub-budget is a per-block cap but cultural_overrides words are not counted against `_TOTAL_WORD_BUDGET` (1,100 words). On turns where L0 (~150w) + L1 (~300w) + L2 (~50w) + L3 (~200w) + L4 (~300w) + cultural_overrides (~200w) are all active, total reaches ~1,200w. The existing L1 shrink-on-overflow logic in `compose_prompt()` handles the overflow, but cultural_overrides are not a candidate for shrinking — they would survive at the expense of L1. Acceptable for POC; consolidate in prompt budget Tier 3 work.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/prompts/composer.py tests/test_prompts_composer.py
git commit -m "feat(composer): inject cultural_overrides from active skill into system prompt

All 20 skills have cultural_overrides (2-4 entries each). This was the
highest-effort clinician-authored field with no runtime effect. It now
lands in the system prompt as SKILL-SPECIFIC CULTURAL CONTEXT, after
global cultural rules, within a 200-word budget."
```

---

## Task 2: Schema conformance registry module

**Files:**
- Create: `src/sage_poc/skills/conformance.py`
- Create: `tests/test_schema_conformance.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_schema_conformance.py`:

```python
"""Tests for the schema field conformance registry."""
import pytest
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE, get_conformance_report


VALID_STATUSES = {"USED", "STORED_ONLY", "PARTIAL"}
EXPECTED_FIELDS = {
    "step.goal",
    "step.technique",
    "step.technique_description",
    "step.tone",
    "step.examples",
    "step.contraindications",
    "step.completion_criteria",
    "skill.cultural_overrides",
    "skill.escalation_matrix.L1",
    "skill.escalation_matrix.L2",
    "skill.escalation_matrix.L3",
    "skill.escalation_matrix.L4",
    "skill.evidence_base",
    "skill.skill_type",
    "skill.self_evolution",
}


def test_all_expected_fields_present():
    assert EXPECTED_FIELDS <= set(SCHEMA_CONFORMANCE.keys()), (
        f"Missing: {EXPECTED_FIELDS - set(SCHEMA_CONFORMANCE.keys())}"
    )


def test_every_field_has_valid_status():
    for field, info in SCHEMA_CONFORMANCE.items():
        assert info["status"] in VALID_STATUSES, f"{field} has invalid status {info['status']!r}"


def test_every_field_has_note():
    for field, info in SCHEMA_CONFORMANCE.items():
        assert isinstance(info.get("note"), str) and info["note"], f"{field} missing note"


def test_cultural_overrides_is_used():
    """After Task 1, cultural_overrides must be USED."""
    assert SCHEMA_CONFORMANCE["skill.cultural_overrides"]["status"] == "USED"


def test_escalation_matrix_l1_is_used():
    assert SCHEMA_CONFORMANCE["skill.escalation_matrix.L1"]["status"] == "USED"


def test_stored_only_fields_have_no_injected_by():
    for field, info in SCHEMA_CONFORMANCE.items():
        if info["status"] == "STORED_ONLY":
            assert info.get("injected_by") is None, (
                f"{field} is STORED_ONLY but has injected_by: {info['injected_by']!r}"
            )


def test_get_conformance_report_structure():
    report = get_conformance_report()
    assert "summary" in report
    assert "fields" in report
    s = report["summary"]
    assert set(s.keys()) >= {"used", "partial", "stored_only", "total"}
    assert s["total"] == len(SCHEMA_CONFORMANCE)
    assert s["used"] + s["partial"] + s["stored_only"] == s["total"]


def test_get_conformance_report_is_json_serializable():
    import json
    report = get_conformance_report()
    # Must not raise
    serialized = json.dumps(report)
    assert len(serialized) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_schema_conformance.py -v
```

Expected: `ImportError: cannot import name 'SCHEMA_CONFORMANCE' from 'sage_poc.skills.conformance'`

- [ ] **Step 3: Create the conformance module**

Create `src/sage_poc/skills/conformance.py`:

```python
"""Schema field conformance registry.

Declares which fields in the Skill/SkillStep JSON schema are USED at runtime
vs STORED_ONLY. Surfaced at startup (log) and via GET /health/schema-conformance.
"""

SCHEMA_CONFORMANCE: dict[str, dict] = {
    # ---- SkillStep fields ----
    "step.goal": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({step_goal})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.technique": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({technique_name})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.technique_description": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({technique_description})",
        "note": "Optional. Appended to technique name when non-empty.",
    },
    "step.tone": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → L3_skill_wrapper ({tone_instruction})",
        "note": "Injected into user role on every skill turn.",
    },
    "step.examples": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block → _select_few_shot_examples ({few_shot_block})",
        "note": "Up to 2 examples selected; Arabic examples prioritised for ar-language users.",
    },
    "step.contraindications": {
        "status": "USED",
        "injected_by": "compose_prompt → _build_l3_skill_block ({contraindication_block})",
        "note": "Injected as 'Important: ...' block when non-empty.",
    },
    "step.completion_criteria": {
        "status": "PARTIAL",
        "injected_by": "skill_executor_node → evaluate_completion_criteria (LLM path only)",
        "note": (
            "LLM evaluator reads the criterion text for _LLM_CRITERIA_SKILLS "
            "(post_crisis_check_in, cbt_thought_record, behavioral_activation, assertive_communication). "
            "For all other skills, a word-count heuristic is used and this field text is ignored."
        ),
    },
    # ---- Skill-level fields ----
    "skill.cultural_overrides": {
        "status": "USED",
        "injected_by": "compose_prompt (system role, SKILL-SPECIFIC CULTURAL CONTEXT block)",
        "note": (
            "All key-value pairs injected into the system prompt after global cultural rules, "
            "within a 200-word budget. Active on every turn where active_skill_id is set."
        ),
    },
    "skill.escalation_matrix.L1": {
        "status": "USED",
        "injected_by": "skill_executor_node",
        "note": "Read as the exit instruction when primary_intent=exit_skill.",
    },
    "skill.escalation_matrix.L2": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.escalation_matrix.L3": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.escalation_matrix.L4": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not evaluated at runtime in this version.",
    },
    "skill.evidence_base": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not used in any prompt or gate.",
    },
    "skill.skill_type": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated. Not used in routing or prompt construction.",
    },
    "skill.self_evolution": {
        "status": "STORED_ONLY",
        "injected_by": None,
        "note": "Parsed and validated (enum: manual_only). Not evaluated at runtime.",
    },
}


def get_conformance_report() -> dict:
    """Return the schema conformance matrix as a JSON-serializable dict."""
    used = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "USED"]
    partial = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "PARTIAL"]
    stored_only = [k for k, v in SCHEMA_CONFORMANCE.items() if v["status"] == "STORED_ONLY"]
    return {
        "summary": {
            "used": len(used),
            "partial": len(partial),
            "stored_only": len(stored_only),
            "total": len(SCHEMA_CONFORMANCE),
        },
        "fields": SCHEMA_CONFORMANCE,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_schema_conformance.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/conformance.py tests/test_schema_conformance.py
git commit -m "feat(skills): add schema field conformance registry

Documents which of the 15 Skill/SkillStep fields are USED, PARTIAL, or
STORED_ONLY at runtime. Verified against code. Exposes get_conformance_report()
for the startup log and /health/schema-conformance endpoint."
```

---

## Task 3: Startup log + /health/schema-conformance endpoint

**Files:**
- Modify: `server.py`
- Modify: `tests/test_schema_conformance.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_schema_conformance.py`:

```python
# ---- endpoint tests ----

from fastapi.testclient import TestClient
from server import app


def test_schema_conformance_endpoint_returns_200():
    client = TestClient(app)
    response = client.get("/health/schema-conformance")
    assert response.status_code == 200


def test_schema_conformance_endpoint_returns_expected_shape():
    client = TestClient(app)
    data = client.get("/health/schema-conformance").json()
    assert "summary" in data
    assert "fields" in data
    assert data["summary"]["total"] == 15


def test_schema_conformance_endpoint_cultural_overrides_is_used():
    client = TestClient(app)
    data = client.get("/health/schema-conformance").json()
    assert data["fields"]["skill.cultural_overrides"]["status"] == "USED"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_schema_conformance.py::test_schema_conformance_endpoint_returns_200 -v
```

Expected: `FAILED` — 404 (route doesn't exist yet)

- [ ] **Step 3: Add import and startup log to server.py**

In `server.py`, find the existing imports block at the top. Add:

```python
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE, get_conformance_report
```

In the `lifespan` function, after the BGE-M3 warmup block (after line ~55, before the DATABASE_URL check):

```python
    # Schema conformance startup log
    for _field, _info in SCHEMA_CONFORMANCE.items():
        _log.info("[sage/startup] schema %-42s → %s", _field, _info["status"])
```

- [ ] **Step 4: Add the /health/schema-conformance endpoint**

In `server.py`, after the existing `@app.post("/name-session")` route definition (near the end of the file), add:

```python
@app.get("/health/schema-conformance")
async def health_schema_conformance():
    """Return the skill schema field conformance matrix.

    Lists which Skill/SkillStep fields are USED, PARTIAL, or STORED_ONLY
    at runtime. Intended for clinician dashboard and monitoring.
    """
    return get_conformance_report()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_schema_conformance.py -v
```

Expected: All 12 tests PASS.

- [ ] **Step 6: Manually verify the startup log**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python -c "
import asyncio, logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
from sage_poc.skills.conformance import SCHEMA_CONFORMANCE
for f, i in SCHEMA_CONFORMANCE.items():
    print(f'[sage/startup] schema {f:<42} → {i[\"status\"]}')
"
```

Expected: 15 lines, each with a field and status. `skill.cultural_overrides` should show `USED`.

- [ ] **Step 7: Commit**

```bash
git add server.py
git commit -m "feat(server): add schema conformance startup log and /health/schema-conformance endpoint

On every startup, logs USED/STORED_ONLY/PARTIAL status for all 15 Skill/SkillStep
fields. GET /health/schema-conformance returns the full matrix for dashboards and
monitoring integrations."
```

---

## Task 4: Clinician dashboard — Schema Conformance Panel

**Files:**
- Create: `cdai/apps/web/components/admin/schema-conformance-panel.tsx`
- Modify: `cdai/apps/web/app/admin/page.tsx`
- Modify: `cdai/apps/web/components/admin/admin-dashboard.tsx`

The panel is a server-rendered section. `admin/page.tsx` fetches the conformance report from `SAGE_API_URL` at render time (revalidated every hour since the data only changes on deploy). `AdminDashboard` receives it as a new `conformance` prop. `SchemaConformancePanel` renders a summary strip + scrollable field table.

- [ ] **Step 1: Create the panel component**

Create `cdai/apps/web/components/admin/schema-conformance-panel.tsx`:

```tsx
import { MetricCard } from './metric-card'

export interface FieldInfo {
  status: 'USED' | 'STORED_ONLY' | 'PARTIAL'
  injected_by: string | null
  note: string
}

export interface ConformanceReport {
  summary: {
    used: number
    partial: number
    stored_only: number
    total: number
  }
  fields: Record<string, FieldInfo>
}

interface Props {
  report: ConformanceReport | null
}

const STATUS_LABEL: Record<string, string> = {
  USED: 'USED',
  PARTIAL: 'PARTIAL',
  STORED_ONLY: 'STORED ONLY',
}

const STATUS_CLASS: Record<string, string> = {
  USED: 'bg-emerald-100 text-emerald-800',
  PARTIAL: 'bg-amber-100 text-amber-800',
  STORED_ONLY: 'bg-red-100 text-red-800',
}

export function SchemaConformancePanel({ report }: Props) {
  if (!report) {
    return (
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-5 py-4">
        <p className="text-sm text-[var(--color-text-secondary)]">
          Schema conformance data unavailable — sage-poc health endpoint did not respond.
        </p>
      </div>
    )
  }

  const { summary, fields } = report

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Fields Used"
          value={summary.used}
          subtext={`of ${summary.total} schema fields`}
        />
        <MetricCard
          label="Partial"
          value={summary.partial}
          subtext="LLM criteria (4/20 skills only)"
        />
        <MetricCard
          label="Stored Only"
          value={summary.stored_only}
          subtext="Not evaluated at runtime"
        />
        <MetricCard
          label="Total Fields"
          value={summary.total}
          subtext="Across Skill + SkillStep"
        />
      </div>

      <div className="rounded-2xl border border-[var(--color-border)] overflow-x-auto">
        <table className="w-full text-xs min-w-[600px]">
          <thead>
            <tr className="bg-[var(--color-bg-secondary)]">
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)] w-52">
                Schema Field
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)] w-28">
                Status
              </th>
              <th className="px-4 py-2.5 text-left font-medium text-[var(--color-text-secondary)]">
                Runtime Note
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {Object.entries(fields).map(([field, info]) => (
              <tr key={field} className="bg-[var(--color-bg-primary)] hover:bg-[var(--color-bg-secondary)] transition-colors">
                <td className="px-4 py-2.5 font-mono text-[var(--color-text-primary)]">
                  {field}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide ${
                      STATUS_CLASS[info.status] ?? 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {STATUS_LABEL[info.status] ?? info.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-[var(--color-text-secondary)] leading-relaxed">
                  {info.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-[var(--color-text-secondary)]">
        STORED ONLY fields are parsed and validated by Pydantic but not evaluated at runtime.
        Clinicians who author these fields should be informed their content is not yet enforced.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Fetch conformance in admin/page.tsx**

In `cdai/apps/web/app/admin/page.tsx`, add the `ConformanceReport` import and the fetch. The file currently ends with `return <AdminDashboard data={data} />`.

Replace the entire file content with:

```tsx
import { createAdminClient } from '@/lib/supabase/admin'
import { createClient } from '@/lib/supabase/server'
import { fetchAllAdminData } from '@/lib/admin-queries'
import { AdminDashboard } from '@/components/admin/admin-dashboard'
import type { ConformanceReport } from '@/components/admin/schema-conformance-panel'
import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/sign-in')

  const { data: profile, error: profileError } = await supabase
    .from('user_profiles')
    .select('is_admin')
    .eq('id', user.id)
    .single()

  if (profileError && profileError.code !== 'PGRST116') {
    console.error('[admin] profile fetch error:', profileError)
  }
  if (!profile?.is_admin) redirect('/chat')

  let data: Awaited<ReturnType<typeof fetchAllAdminData>>
  try {
    const admin = createAdminClient()
    data = await fetchAllAdminData(admin)
  } catch (err) {
    console.error('[admin] data fetch failed:', err)
    return (
      <div className="p-6">
        <p className="text-sm text-[var(--color-crisis)]">
          Admin data temporarily unavailable. Contact the platform team.
        </p>
      </div>
    )
  }

  const sageUrl = process.env.SAGE_API_URL ?? 'http://localhost:8000'
  let conformance: ConformanceReport | null = null
  try {
    const res = await fetch(`${sageUrl}/health/schema-conformance`, {
      next: { revalidate: 3600 },
    })
    if (res.ok) conformance = (await res.json()) as ConformanceReport
  } catch {
    // sage-poc offline — panel shows fallback state
  }

  return <AdminDashboard data={data} conformance={conformance} />
}
```

- [ ] **Step 3: Add SchemaConformancePanel to admin-dashboard.tsx**

In `cdai/apps/web/components/admin/admin-dashboard.tsx`, add the import and the `conformance` prop, then add the new section.

Find the current interface:
```tsx
interface Props {
  data: AdminData
}
```

Replace with:
```tsx
import { SchemaConformancePanel } from './schema-conformance-panel'
import type { ConformanceReport } from './schema-conformance-panel'

interface Props {
  data: AdminData
  conformance: ConformanceReport | null
}
```

Find the function signature:
```tsx
export function AdminDashboard({ data }: Props) {
```

Replace with:
```tsx
export function AdminDashboard({ data, conformance }: Props) {
```

Add the new section at the bottom of the returned JSX, after the population section and before the closing `</div>`:

```tsx
      <section id="schema-conformance">
        <h2 className="mb-4 text-lg font-semibold text-[var(--color-text-primary)]">
          Schema Conformance
          <span className="ml-2 text-xs font-normal text-[var(--color-text-secondary)]">
            which clinician-authored fields are enforced at runtime
          </span>
        </h2>
        <SchemaConformancePanel report={conformance} />
      </section>
```

- [ ] **Step 4: TypeScript check**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai/apps/web
npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 5: Verify dashboard renders**

With sage-poc running (`uvicorn server:app --reload` in sage-poc dir) and the Next.js dev server running (`pnpm dev` in cdai/apps/web):

1. Navigate to `http://localhost:3000/admin`
2. Scroll to the bottom — "Schema Conformance" section should appear
3. Verify:
   - Summary strip shows 9 USED, 1 PARTIAL, 5 STORED ONLY (out of 15 total)
   - `skill.cultural_overrides` row shows USED badge (green)
   - `step.completion_criteria` row shows PARTIAL badge (amber)
   - `skill.evidence_base`, `skill.skill_type`, `skill.self_evolution` rows show STORED ONLY badge (red)
4. Stop sage-poc and reload — panel should show the fallback "data unavailable" message

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/cdai
git add apps/web/components/admin/schema-conformance-panel.tsx \
        apps/web/app/admin/page.tsx \
        apps/web/components/admin/admin-dashboard.tsx
git commit -m "feat(admin): add Schema Conformance panel to clinician dashboard

Fetches /health/schema-conformance from sage-poc at render time (1h cache).
Shows USED/PARTIAL/STORED ONLY status for all 15 Skill/SkillStep fields
with runtime notes. Clinicians can now see which fields the system enforces."
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Task |
|-------------|------|
| Wire `cultural_overrides` into composer alongside global cultural rules | Task 1 ✓ |
| Inject into the prompt's cultural layer | Task 1 ✓ (system role, after global rules) |
| Startup log: USED vs STORED_ONLY per loaded skill field | Task 3 ✓ |
| `/health/schema-conformance` endpoint | Task 3 ✓ |
| Dashboard panel | Task 4 ✓ |

**Placeholder scan:** None.

**Type consistency:**
- `ConformanceReport` defined in `schema-conformance-panel.tsx` and imported in `admin/page.tsx` via named export. ✓
- `get_conformance_report()` return type matches `ConformanceReport` shape (both have `summary.{used, partial, stored_only, total}` and `fields`). ✓
- `SchemaConformancePanel({ report }: Props)` receives `ConformanceReport | null` from both `admin/page.tsx` and `admin-dashboard.tsx`. ✓
- `AdminDashboard({ data, conformance }: Props)` — `conformance` prop added to interface. ✓

**Edge cases handled:**
- Skill with empty `cultural_overrides: {}` → no injection, no layer tag (Task 1, test 3) ✓
- `load_skill` throws → warning log, composer continues (Task 1, test 4) ✓
- sage-poc offline → `SchemaConformancePanel` shows fallback message (Task 4, step 5 verification) ✓
- `cultural_overrides` values > 200 words → warning log, block not injected (guarded in Task 1 implementation) ✓
