# SageAI Architecture POC — Graph Routing & Skill Execution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the 8-node LangGraph architecture works end-to-end — Arabic/English input → language detection → node routing → skill step_policy execution → Therapist layer response → translated output.

**Architecture:** 7 of the 8 production nodes (`knowledge_retrieve` deferred — requires a populated vector index). All LLM calls go through OpenRouter. Arabic translation uses a local Ollama model. One real CBT skill (3 steps + step_policy) exercises the executor fully. In-memory state only — no DB.

> **Why Node 6 is deferred and Node 3 is not:** `knowledge_retrieve` (Node 6) requires a live vector index with loaded documents — infrastructure that defeats the "lightweight" goal. `low_confidence_respond` (Node 3) requires nothing but an LLM call and tests a real routing path (what happens when the classifier is uncertain). Omitting Node 3 leaves confidence-threshold routing completely untestable.

**Tech Stack:** Python 3.11+, `langgraph`, `langchain-openai` (OpenRouter via `base_url`), `ollama` Python SDK, `langdetect`, `pydantic` v2, `pytest`

---

## File Map

| File | Responsibility |
|------|---------------|
| `sage-poc/pyproject.toml` | Project deps |
| `sage-poc/.env.example` | Env var template |
| `sage-poc/src/sage_poc/state.py` | LangGraph TypedDict state — single source of truth |
| `sage-poc/src/sage_poc/config.py` | Model names, env loading |
| `sage-poc/src/sage_poc/language.py` | langdetect + Ollama translation |
| `sage-poc/src/sage_poc/llm.py` | OpenRouter client factory |
| `sage-poc/src/sage_poc/knowledge.py` | 10-entry in-memory knowledge dict for L4-lite injection |
| `sage-poc/src/sage_poc/skills/schema.py` | Pydantic skill schema |
| `sage-poc/src/sage_poc/skills/cbt_thought_record.json` | Sample skill (3 steps + step_policy) |
| `sage-poc/src/sage_poc/nodes/safety_check.py` | Node 1: keyword lexicon + language detection |
| `sage-poc/src/sage_poc/nodes/intent_route.py` | Node 2: OpenRouter intent + emotional intensity + engagement |
| `sage-poc/src/sage_poc/nodes/low_confidence_respond.py` | Node 3: empathic clarification when confidence < 0.6 |
| `sage-poc/src/sage_poc/nodes/skill_select.py` | Node 4: rule-based keyword → skill ID |
| `sage-poc/src/sage_poc/nodes/skill_executor.py` | Node 5: load skill JSON, evaluate step_policy |
| `sage-poc/src/sage_poc/nodes/freeflow_respond.py` | Node 7: OpenRouter response with skill instruction |
| `sage-poc/src/sage_poc/nodes/output_gate.py` | Node 8: translate back + audit log |
| `sage-poc/src/sage_poc/graph.py` | LangGraph assembly + conditional edges |
| `sage-poc/run.py` | Interactive multi-turn CLI |
| `sage-poc/tests/test_language.py` | Language detection + translation unit tests |
| `sage-poc/tests/test_nodes.py` | Node unit tests (mocked LLM) |
| `sage-poc/tests/test_graph.py` | E2E integration: 3 scenarios |

---

## Task 1: Project Setup

**Files:**
- Create: `sage-poc/pyproject.toml`
- Create: `sage-poc/.env.example`
- Create: `sage-poc/src/sage_poc/__init__.py`
- Create: `sage-poc/src/sage_poc/nodes/__init__.py`
- Create: `sage-poc/src/sage_poc/skills/__init__.py`

- [ ] **Step 1: Create directory tree**

```bash
cd /Users/knowledgebase/Documents/Sage
mkdir -p sage-poc/src/sage_poc/nodes
mkdir -p sage-poc/src/sage_poc/skills
mkdir -p sage-poc/tests
touch sage-poc/src/sage_poc/__init__.py
touch sage-poc/src/sage_poc/nodes/__init__.py
touch sage-poc/src/sage_poc/skills/__init__.py
touch sage-poc/tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sage-poc"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-openai>=0.2.0",
    "langchain-core>=0.3.0",
    "ollama>=0.3.0",
    "langdetect>=1.0.9",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]

[tool.hatch.build.targets.wheel]
packages = ["src/sage_poc"]
```

- [ ] **Step 3: Write `.env.example`**

```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_CLASSIFIER_MODEL=openai/gpt-4o-mini
OPENROUTER_RESPONSE_MODEL=anthropic/claude-3-5-sonnet
OLLAMA_TRANSLATION_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```

- [ ] **Step 4: Install dependencies**

```bash
cd sage-poc
pip install -e ".[dev]"
```

Expected: `Successfully installed sage-poc-0.1.0` plus all deps.

- [ ] **Step 5: Verify Ollama model is available**

```bash
ollama pull qwen2.5:7b
```

> **Note on translation model size:** `qwen2.5:7b` is 4.7GB and handles Arabic well. Lighter alternative: `qwen2.5:3b` (1.9GB) — weaker Arabic but faster. If you need stronger Arabic quality and have the RAM: `qwen2.5:14b` (9GB). Do NOT use a model under 3B for Arabic translation — quality degrades sharply.

- [ ] **Step 6: Commit**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
git init
git add pyproject.toml .env.example src/
git commit -m "feat: project scaffold for SageAI graph routing POC"
```

---

## Task 2: State Schema

**Files:**
- Create: `sage-poc/src/sage_poc/state.py`
- Create: `sage-poc/tests/test_state.py`

The state is the shared data structure passed between all nodes. Every field that a node reads OR writes must live here.

- [ ] **Step 1: Write failing test**

```python
# tests/test_state.py
from sage_poc.state import SageState

def test_state_has_required_fields():
    state: SageState = {
        "raw_message": "hello",
        "detected_language": "en",
        "message_en": "hello",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    assert state["raw_message"] == "hello"
    assert state["path"] == []
    assert state["clinical_flags"] == []

def test_state_path_is_list():
    state: SageState = {
        "raw_message": "test",
        "detected_language": "en",
        "message_en": "test",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": ["substance_use"],
        "primary_intent": "general_chat",
        "intent_confidence": 0.9,
        "emotional_intensity": 3,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": "identify_thought",
        "step_instruction": None,
        "escalation_triggered": {"level": "L2", "reason": "substance detected"},
        "response_en": "I'm here for you.",
        "response": "I'm here for you.",
        "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        "turn_count": 1,
        "conversation_history": [{"role": "user", "content": "test"}],
    }
    assert len(state["path"]) == 4
    assert "intent_route" in state["path"]
    assert state["clinical_flags"] == ["substance_use"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sage-poc
pytest tests/test_state.py -v
```

Expected: `ImportError: No module named 'sage_poc.state'`

- [ ] **Step 3: Write `state.py`**

```python
# src/sage_poc/state.py
from typing import TypedDict, Optional, Literal

Intent = Literal[
    "skill_continuation", "new_skill", "general_chat",
    "crisis", "info_request", "exit_skill",
]

class SageState(TypedDict):
    raw_message: str
    detected_language: str
    message_en: str

    is_safe: bool
    crisis_flags: list[str]
    clinical_flags: list[str]   # substance_use, trauma_indicator, eating_concern, medication_mention

    primary_intent: Optional[Intent]
    secondary_intent: Optional[Intent]  # blended intent — e.g. "info_request" alongside "new_skill"
    intent_confidence: float
    emotional_intensity: int   # 1–10
    engagement: int            # 1–10

    active_skill_id: Optional[str]
    active_step_id: Optional[str]      # step the NEXT turn will start from
    executed_step_id: Optional[str]    # step whose instruction was used THIS turn (for audit)
    step_instruction: Optional[str]
    escalation_triggered: Optional[dict]  # {"level": "L1"|"L2", "reason": str, "action": str}

    response_en: Optional[str]
    response: Optional[str]

    path: list[str]
    turn_count: int
    conversation_history: list[dict]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_state.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/state.py tests/test_state.py
git commit -m "feat: LangGraph state schema for SageAI POC"
```

---

## Task 3: Config Module

**Files:**
- Create: `sage-poc/src/sage_poc/config.py`

- [ ] **Step 1: Write `config.py`**

```python
# src/sage_poc/config.py
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLASSIFIER_MODEL = os.getenv("OPENROUTER_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
RESPONSE_MODEL = os.getenv("OPENROUTER_RESPONSE_MODEL", "anthropic/claude-3-5-sonnet")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TRANSLATION_MODEL = os.getenv("OLLAMA_TRANSLATION_MODEL", "qwen2.5:7b")
```

No test needed — this is pure config. Failures surface immediately when a node tries to use a missing key.

- [ ] **Step 2: Create `.env` from example**

```bash
cp .env.example .env
# Then edit .env and fill in your OPENROUTER_API_KEY
```

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/config.py
git commit -m "feat: config loader for OpenRouter and Ollama settings"
```

---

## Task 4: Language Module (Detection + Translation)

**Files:**
- Create: `sage-poc/src/sage_poc/language.py`
- Create: `sage-poc/tests/test_language.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_language.py
from sage_poc.language import detect_language, translate_to_english, translate_to_arabic

def test_detect_english():
    assert detect_language("I feel really sad today") == "en"

def test_detect_arabic():
    lang = detect_language("أشعر بالحزن الشديد اليوم")
    assert lang in ("ar", "fa")  # langdetect sometimes confuses ar/fa

def test_detect_mixed():
    # Arabic Unicode chars override langdetect — code-switched message classified as Arabic
    lang = detect_language("I feel بخير today, maybe things will get better")
    assert lang == "ar"

# NOTE: These two tests make real Ollama calls — skip with: pytest -m "not slow"
import pytest

@pytest.mark.slow
def test_translate_arabic_to_english():
    result = translate_to_english("أنا أشعر بالخوف الشديد")
    assert isinstance(result, str)
    assert len(result) > 5
    # Should contain fear-related words
    result_lower = result.lower()
    assert any(word in result_lower for word in ["fear", "scared", "afraid", "anxious", "intense"])

@pytest.mark.slow
def test_translate_english_to_arabic():
    result = translate_to_arabic("I am here to support you.")
    assert isinstance(result, str)
    # Arabic text contains Arabic Unicode chars
    assert any('؀' <= c <= 'ۿ' for c in result)
```

- [ ] **Step 2: Run fast tests to verify they fail**

```bash
pytest tests/test_language.py -v -m "not slow"
```

Expected: `ImportError: No module named 'sage_poc.language'`

- [ ] **Step 3: Write `language.py`**

```python
# src/sage_poc/language.py
import re
import ollama
from langdetect import detect, LangDetectException
from sage_poc.config import TRANSLATION_MODEL, OLLAMA_BASE_URL


def detect_language(text: str) -> str:
    # Arabic Unicode block presence overrides langdetect for code-switching
    if re.search(r'[؀-ۿ]', text):
        return "ar"
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def translate_to_english(text: str) -> str:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(
        model=TRANSLATION_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Translate the following text to English. "
                "Return ONLY the translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
    )
    return response["message"]["content"].strip()


def translate_to_arabic(text: str) -> str:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(
        model=TRANSLATION_MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Translate the following text to Modern Standard Arabic. "
                "Return ONLY the Arabic translation, nothing else:\n\n"
                f"{text}"
            ),
        }],
    )
    return response["message"]["content"].strip()
```

- [ ] **Step 4: Run fast tests to verify they pass**

```bash
pytest tests/test_language.py -v -m "not slow"
```

Expected: `3 passed`

- [ ] **Step 5: Run Ollama translation tests (requires Ollama running)**

```bash
pytest tests/test_language.py -v -m "slow"
```

Expected: `2 passed` (may take 10–30 seconds per test on first run)

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/language.py tests/test_language.py
git commit -m "feat: language detection and Ollama-based translation"
```

---

## Task 5: OpenRouter LLM Client

**Files:**
- Create: `sage-poc/src/sage_poc/llm.py`

- [ ] **Step 1: Write `llm.py`**

```python
# src/sage_poc/llm.py
from langchain_openai import ChatOpenAI
from sage_poc.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    CLASSIFIER_MODEL,
    RESPONSE_MODEL,
)


def get_classifier() -> ChatOpenAI:
    """Fast, low-temperature model for intent classification and safety routing."""
    return ChatOpenAI(
        model=CLASSIFIER_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0,
        max_tokens=512,
        default_headers={
            "HTTP-Referer": "https://sage.ai",
            "X-Title": "SageAI POC",
        },
    )


def get_responder() -> ChatOpenAI:
    """Higher-quality model for therapeutic response generation."""
    return ChatOpenAI(
        model=RESPONSE_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        temperature=0.7,
        max_tokens=1024,
        default_headers={
            "HTTP-Referer": "https://sage.ai",
            "X-Title": "SageAI POC",
        },
    )
```

No unit test — this is a thin factory. Integration is tested at the node level.

- [ ] **Step 2: Verify OpenRouter connection**

```bash
python - <<'EOF'
from sage_poc.llm import get_classifier
llm = get_classifier()
result = llm.invoke("Say 'OK' and nothing else.")
print(result.content)
EOF
```

Expected: `OK` (or similar)

- [ ] **Step 3: Commit**

```bash
git add src/sage_poc/llm.py
git commit -m "feat: OpenRouter LLM client factory (classifier + responder)"
```

---

## Task 6: Skill Schema + Sample CBT Skill

**Files:**
- Create: `sage-poc/src/sage_poc/skills/schema.py`
- Create: `sage-poc/src/sage_poc/skills/cbt_thought_record.json`
- Create: `sage-poc/tests/test_skill_schema.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_skill_schema.py
import json
from pathlib import Path
from sage_poc.skills.schema import Skill, load_skill

def test_load_cbt_skill():
    skill = load_skill("cbt_thought_record")
    assert skill.skill_id == "cbt_thought_record"
    assert skill.skill_type == "structured"
    assert len(skill.steps) == 3
    assert len(skill.step_policy) >= 2

def test_skill_step_has_required_fields():
    skill = load_skill("cbt_thought_record")
    for step in skill.steps:
        assert step.step_id
        assert step.goal
        assert step.technique
        assert step.tone
        assert len(step.examples) >= 2

def test_skill_policy_rule_structure():
    skill = load_skill("cbt_thought_record")
    for rule in skill.step_policy:
        assert "signal" in rule.condition
        assert "operator" in rule.condition
        assert "value" in rule.condition
        assert rule.action
        assert rule.instruction
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_skill_schema.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `schema.py`**

```python
# src/sage_poc/skills/schema.py
import json
from pathlib import Path
from pydantic import BaseModel

SKILLS_DIR = Path(__file__).parent


class StepPolicyCondition(BaseModel):
    signal: str       # "emotional_intensity" | "engagement" | etc.
    operator: str     # ">" | "<" | ">=" | "<=" | "=="
    value: int | float
    step: str         # "ANY" or a specific step_id


class StepPolicyRule(BaseModel):
    condition: StepPolicyCondition
    action: str
    instruction: str
    next_step_id: str = "current"


class SkillStep(BaseModel):
    step_id: str
    goal: str
    technique: str
    tone: str
    examples: list[str]


class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    evidence_base: str
    target_presentations: list[str]
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]


def load_skill(skill_id: str) -> Skill:
    path = SKILLS_DIR / f"{skill_id}.json"
    data = json.loads(path.read_text())
    return Skill.model_validate(data)
```

- [ ] **Step 4: Write `cbt_thought_record.json`**

```json
{
  "skill_id": "cbt_thought_record",
  "skill_name": "CBT Thought Record",
  "skill_type": "structured",
  "evidence_base": "Beck (1979); NICE CG159",
  "target_presentations": [
    "negative thoughts", "self-blame", "cognitive distortions",
    "catastrophizing", "failure", "worthless", "always my fault"
  ],
  "steps": [
    {
      "step_id": "identify_thought",
      "goal": "Help the user identify and clearly articulate the specific negative thought",
      "technique": "Socratic questioning",
      "tone": "warm, curious, non-judgmental",
      "examples": [
        "What specific thought is going through your mind right now?",
        "When you say you feel like a failure, what exactly are you telling yourself?",
        "Can you put that thought into one sentence — what is the thought saying about you?"
      ]
    },
    {
      "step_id": "explore_distortion",
      "goal": "Gently explore the evidence for and against the negative thought",
      "technique": "Thought challenging",
      "tone": "warm, collaborative, curious",
      "examples": [
        "What evidence do you have that supports this thought? And what evidence goes against it?",
        "If a close friend told you this about themselves, what would you say to them?",
        "Is there another way to look at this situation?"
      ]
    },
    {
      "step_id": "balanced_thought",
      "goal": "Help the user construct a more balanced, realistic perspective",
      "technique": "Cognitive restructuring",
      "tone": "encouraging, collaborative, hopeful",
      "examples": [
        "Taking all of this into account, what would be a more balanced way of looking at this?",
        "What would be a fairer, more realistic thought to replace the original one?",
        "How does this new perspective feel compared to the original thought?"
      ]
    }
  ],
  "step_policy": [
    {
      "condition": {
        "signal": "emotional_intensity",
        "operator": ">",
        "value": 7,
        "step": "ANY"
      },
      "action": "validate_only",
      "instruction": "The user is highly distressed. Validate their emotion fully and do NOT challenge the thought yet. Stay warm and present. Return to normal step next turn.",
      "next_step_id": "current"
    },
    {
      "condition": {
        "signal": "engagement",
        "operator": "<",
        "value": 3,
        "step": "ANY"
      },
      "action": "check_in",
      "instruction": "The user seems disengaged. Gently check in — ask if they'd like to continue, take a different approach, or simply talk.",
      "next_step_id": "current"
    }
  ],
  "escalation_matrix": {
    "L1": "Exit skill gracefully if user requests to stop",
    "L2": "Add clinician_review flag if trauma or substance mention detected",
    "L3": "Exit immediately to crisis protocol if any crisis signal",
    "L4": "Trigger human handoff if 3+ crises detected in last 30 days"
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_skill_schema.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/skills/ tests/test_skill_schema.py
git commit -m "feat: skill schema and CBT thought record sample skill"
```

---

## Task 7: Node 1 — safety_check

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/safety_check.py`
- Modify: `sage-poc/tests/test_nodes.py` (create if not exists)

This node detects language, translates Arabic to English for internal processing, and checks for crisis keywords. All deterministic — no LLM.

- [ ] **Step 1: Write failing test**

```python
# tests/test_nodes.py
import pytest
from sage_poc.nodes.safety_check import safety_check_node, CRISIS_KEYWORDS

def make_state(**kwargs):
    defaults = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    return {**defaults, **kwargs}

def test_safe_english_message():
    state = make_state(raw_message="I feel sad today")
    result = safety_check_node(state)
    assert result["is_safe"] is True
    assert result["detected_language"] == "en"
    assert result["message_en"] == "I feel sad today"
    assert result["clinical_flags"] == []
    assert "safety_check" in result["path"]

def test_crisis_english_message():
    state = make_state(raw_message="I want to kill myself")
    result = safety_check_node(state)
    assert result["is_safe"] is False
    assert len(result["crisis_flags"]) > 0

def test_crisis_keywords_list_not_empty():
    assert len(CRISIS_KEYWORDS) >= 5

def test_clinical_flag_substance_use():
    state = make_state(raw_message="I've been drinking heavily every night to cope")
    result = safety_check_node(state)
    assert result["is_safe"] is True  # not a crisis
    assert "substance_use" in result["clinical_flags"]
    assert result["crisis_flags"] == []

def test_clinical_flag_trauma():
    state = make_state(raw_message="Someone hurt me and I can't stop thinking about it")
    result = safety_check_node(state)
    assert "trauma_indicator" in result["clinical_flags"]

def test_clinical_flag_medication():
    state = make_state(raw_message="I'm on antidepressants but I don't know the right dosage")
    result = safety_check_node(state)
    assert "medication_mention" in result["clinical_flags"]

def test_no_clinical_flags_for_general_message():
    state = make_state(raw_message="I feel really sad and hopeless today")
    result = safety_check_node(state)
    assert result["clinical_flags"] == []

# Requires Ollama — tests Arabic crisis detection path
@pytest.mark.slow
def test_crisis_arabic_message():
    state = make_state(raw_message="أريد الموت الآن")
    result = safety_check_node(state)
    assert result["is_safe"] is False
    assert result["detected_language"] == "ar"
    assert len(result["crisis_flags"]) > 0

@pytest.mark.slow
def test_araglish_code_switching():
    """Araglish message: Arabic Unicode override classifies as Arabic even mid-English sentence."""
    state = make_state(raw_message="I feel بخير today, maybe things will get better")
    result = safety_check_node(state)
    assert result["detected_language"] == "ar"
    assert result["is_safe"] is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_nodes.py::test_safe_english_message -v
pytest tests/test_nodes.py::test_crisis_english_message -v
pytest tests/test_nodes.py::test_crisis_keywords_list_not_empty -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `safety_check.py`**

```python
# src/sage_poc/nodes/safety_check.py
import re
from sage_poc.state import SageState
from sage_poc.language import detect_language, translate_to_english

CRISIS_KEYWORDS = [
    "kill myself", "want to die", "end my life", "suicide", "suicidal",
    "hurt myself", "self-harm", "cut myself", "overdose", "no reason to live",
    "better off dead", "can't go on", "not worth living",
    "أريد الموت", "انتحار", "أنهي حياتي", "أؤذي نفسي",
]

CLINICAL_KEYWORD_SETS: dict[str, list[str]] = {
    "substance_use": [
        "drinking", "drunk", "alcohol", "alcoholism", "liquor", "beer", "wine",
        "drugs", "drug use", "cocaine", "heroin", "marijuana", "weed",
        "using pills", "numb the pain", "cope with drink",
        "كحول", "مخدرات", "حبوب مخدرة", "مدمن",
    ],
    "trauma_indicator": [
        "abuse", "abused", "assault", "assaulted", "attacked", "violence",
        "hurt me", "hit me", "rape", "molested", "trauma",
        "إساءة", "اعتداء", "عنف",
    ],
    "eating_concern": [
        "purging", "binge eating", "starving myself", "not eating",
        "eating disorder", "anorexia", "bulimia",
        "لا آكل", "أتجوع",
    ],
    "medication_mention": [
        "medication", "antidepressant", "dosage", "prescribed", "prescription",
        "دواء", "مضادات الاكتئاب", "جرعة",
    ],
}


def _contains_crisis(text: str) -> list[str]:
    text_lower = text.lower()
    return [kw for kw in CRISIS_KEYWORDS if kw.lower() in text_lower]


def _detect_clinical_flags(text: str) -> list[str]:
    text_lower = text.lower()
    return [
        flag_type
        for flag_type, keywords in CLINICAL_KEYWORD_SETS.items()
        if any(kw.lower() in text_lower for kw in keywords)
    ]


def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    lang = detect_language(raw)

    if lang == "ar":
        arabic_crisis = _contains_crisis(raw)
        arabic_clinical = _detect_clinical_flags(raw)
        message_en = translate_to_english(raw)
    else:
        arabic_crisis = []
        arabic_clinical = []
        message_en = raw

    english_crisis = _contains_crisis(message_en)
    english_clinical = _detect_clinical_flags(message_en)

    all_crisis = list(set(arabic_crisis + english_crisis))
    all_clinical = list(set(arabic_clinical + english_clinical))

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(all_crisis) == 0,
        "crisis_flags": all_crisis,
        "clinical_flags": all_clinical,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_nodes.py::test_safe_english_message tests/test_nodes.py::test_crisis_english_message tests/test_nodes.py::test_crisis_keywords_list_not_empty tests/test_nodes.py::test_clinical_flag_substance_use tests/test_nodes.py::test_clinical_flag_trauma tests/test_nodes.py::test_clinical_flag_medication tests/test_nodes.py::test_no_clinical_flags_for_general_message -v
```

Expected: `7 passed` (Ollama-dependent tests are `@pytest.mark.slow` — run separately with `pytest tests/test_nodes.py -v -m slow`; this covers `test_crisis_arabic_message` and `test_araglish_code_switching`)

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/safety_check.py tests/test_nodes.py
git commit -m "feat: safety_check node with crisis lexicon and language detection"
```

---

## Task 8: Node 2 — intent_route

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/intent_route.py` (create)
- Modify: `sage-poc/tests/test_nodes.py`

This node calls OpenRouter (classifier model) to determine: intent, emotional_intensity, intent_confidence. Returns structured JSON.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from unittest.mock import patch, MagicMock
from sage_poc.nodes.intent_route import intent_route_node, build_intent_prompt

def test_intent_prompt_contains_message():
    state = make_state(message_en="I feel like everything is my fault, always", active_skill_id=None)
    prompt = build_intent_prompt(state)
    assert "everything is my fault" in prompt
    assert "active_skill_id" in prompt.lower() or "no active skill" in prompt.lower()

def test_intent_route_with_mocked_llm():
    state = make_state(
        message_en="I keep thinking I'm a failure",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "new_skill", "emotional_intensity": 7, "engagement": 6, "intent_confidence": 0.9}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "new_skill"
    assert result["emotional_intensity"] == 7
    assert result["engagement"] == 6
    assert result["intent_confidence"] == 0.9
    assert "intent_route" in result["path"]

def test_intent_route_skill_continuation():
    state = make_state(
        message_en="Hmm, I think maybe it was partly my fault but not entirely",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        conversation_history=[{"role": "assistant", "content": "What thought is going through your mind?"}],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "skill_continuation", "emotional_intensity": 5, "engagement": 7, "intent_confidence": 0.85}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "skill_continuation"
    assert result["engagement"] == 7

def test_intent_route_classifies_exit_skill():
    state = make_state(
        message_en="I don't want to do this anymore, can we stop?",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "exit_skill", "emotional_intensity": 4, "engagement": 3, "intent_confidence": 0.88}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "exit_skill"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_intent_prompt_contains_message tests/test_nodes.py::test_intent_route_with_mocked_llm tests/test_nodes.py::test_intent_route_skill_continuation -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `intent_route.py`**

```python
# src/sage_poc/nodes/intent_route.py
import json
import re
from sage_poc.state import SageState
from sage_poc.llm import get_classifier

INTENT_SYSTEM = """You are a routing classifier for a mental health assistant.
Analyse the user's message and return ONLY valid JSON with these fields:
- primary_intent: one of "skill_continuation" | "new_skill" | "general_chat" | "crisis" | "info_request" | "exit_skill"
- secondary_intent: the SECOND intent if two are present, or null if only one. Example: user expresses distress AND asks a factual question → primary "new_skill", secondary "info_request".
- emotional_intensity: integer 1-10 (1=calm, 10=extremely distressed)
- engagement: integer 1-10 (1=one-word/dismissive, 10=elaborating/open)
- intent_confidence: float 0.0-1.0

Rules:
- skill_continuation: user is responding to an active therapeutic skill session
- new_skill: user expresses distress, negative thoughts, or needs a therapeutic technique
- general_chat: greeting, small talk, or unrelated question
- crisis: ANY mention of self-harm, suicide, or immediate danger (redundant safety net)
- info_request: user asks a factual question about mental health
- exit_skill: user explicitly asks to stop, leave, or change topic away from the current skill

Return ONLY the JSON object. No explanation."""


def build_intent_prompt(state: SageState) -> str:
    active = f"Active skill: {state['active_skill_id']}" if state["active_skill_id"] else "No active skill."
    history_lines = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in state["conversation_history"][-3:]
    )
    history_block = f"\nRecent history:\n{history_lines}" if history_lines else ""
    return f"{active}{history_block}\n\nUser message: {state['message_en']}"


def intent_route_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_classifier()

    messages = [
        {"role": "system", "content": INTENT_SYSTEM},
        {"role": "user", "content": build_intent_prompt(state)},
    ]
    raw = llm.invoke(messages).content.strip()

    # Extract JSON — handle models that wrap in markdown fences
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    data = json.loads(match.group(0)) if match else {}

    return {
        "primary_intent": data.get("primary_intent", "general_chat"),
        "secondary_intent": data.get("secondary_intent"),
        "intent_confidence": float(data.get("intent_confidence", 0.5)),
        "emotional_intensity": int(data.get("emotional_intensity", 5)),
        "engagement": int(data.get("engagement", 5)),
        "path": state["path"] + ["intent_route"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_intent_prompt_contains_message tests/test_nodes.py::test_intent_route_with_mocked_llm tests/test_nodes.py::test_intent_route_skill_continuation -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/intent_route.py tests/test_nodes.py
git commit -m "feat: intent_route node with OpenRouter classification"
```

---

## Task 9: Node 4 — skill_select

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/skill_select.py`
- Modify: `sage-poc/tests/test_nodes.py`

Rule-based matching of user message to a skill. For POC we have one skill, so this is simple. The rules map target_presentations keywords from each skill's JSON to the skill_id.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from sage_poc.nodes.skill_select import skill_select_node

def test_selects_cbt_for_negative_thought():
    state = make_state(
        message_en="I keep thinking I'm a failure, it's always my fault",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["active_step_id"] == "identify_thought"
    assert "skill_select" in result["path"]

def test_no_skill_for_general_chat():
    state = make_state(
        message_en="What is the weather like?",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_selects_cbt_for_negative_thought tests/test_nodes.py::test_no_skill_for_general_chat -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `skill_select.py`**

```python
# src/sage_poc/nodes/skill_select.py
from sage_poc.state import SageState
from sage_poc.skills.schema import load_skill

# All available skills — in production this comes from the CMS
SKILL_REGISTRY = ["cbt_thought_record"]

# Pre-load skills at module init so we're not reading JSON on every request
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}


def skill_select_node(state: SageState) -> dict:
    message = state["message_en"].lower()

    for skill_id, skill in _SKILLS.items():
        for keyword in skill.target_presentations:
            if keyword.lower() in message:
                return {
                    "active_skill_id": skill_id,
                    "active_step_id": skill.steps[0].step_id,
                    "path": state["path"] + ["skill_select"],
                }

    return {
        "active_skill_id": None,
        "active_step_id": None,
        "path": state["path"] + ["skill_select"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_selects_cbt_for_negative_thought tests/test_nodes.py::test_no_skill_for_general_chat -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py tests/test_nodes.py
git commit -m "feat: skill_select node with keyword matching"
```

---

## Task 10: Node 5 — guided_skill_executor

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/skill_executor.py`
- Modify: `sage-poc/tests/test_nodes.py`

This is the architectural heart of the POC. It loads the skill, evaluates step_policy rules deterministically, and produces a `step_instruction` that freeflow_respond uses.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from sage_poc.nodes.skill_executor import skill_executor_node, evaluate_step_policy

def test_evaluate_step_policy_high_intensity_triggers_validate_only():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=9,
        engagement=6,
    )
    assert action["action"] == "validate_only"
    assert "validate" in action["instruction"].lower() or "distress" in action["instruction"].lower()

def test_evaluate_step_policy_normal_intensity_advances_to_next_step():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=5,
        engagement=6,
    )
    assert action["action"] == "advance"
    assert "goal" in action["instruction"].lower()
    assert action["next_step_id"] == "explore_distortion"
    assert not action.get("skill_complete")

def test_evaluate_step_policy_last_step_marks_skill_complete():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="balanced_thought",
        emotional_intensity=5,
        engagement=7,
    )
    assert action["action"] == "complete"
    assert action["skill_complete"] is True

def test_recovery_from_validate_only_override():
    """High intensity pauses progression; normal intensity resumes on the SAME step."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")

    # Turn N: intensity 9 → validate_only fires, step stays at identify_thought
    high = evaluate_step_policy(
        skill=skill, current_step_id="identify_thought",
        emotional_intensity=9, engagement=7,
    )
    assert high["action"] == "validate_only"
    assert high["next_step_id"] == "identify_thought"  # held in place

    # Turn N+1: intensity drops to 5 → no rule fires, advance to explore_distortion
    normal = evaluate_step_policy(
        skill=skill, current_step_id="identify_thought",
        emotional_intensity=5, engagement=7,
    )
    assert normal["action"] == "advance"
    assert normal["next_step_id"] == "explore_distortion"  # resumes

def test_evaluate_step_policy_low_engagement_triggers_check_in():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="explore_distortion",
        emotional_intensity=4,
        engagement=2,
    )
    assert action["action"] == "check_in"

def test_skill_executor_node_produces_instruction():
    # message_en must be > 10 words for completion_criteria to allow advancement
    state = make_state(
        message_en="I don't know what to do, everything is always my fault.",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=6,
        engagement=7,
    )
    result = skill_executor_node(state)
    assert result["step_instruction"] is not None
    assert len(result["step_instruction"]) > 20
    assert result["executed_step_id"] == "identify_thought"
    assert result["active_step_id"] == "explore_distortion"
    assert result["escalation_triggered"] is None
    assert "skill_executor" in result["path"]

def test_completion_criteria_short_response_holds_step():
    """Short user response (≤ 10 words) holds the step — proves the hook exists."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=5,
        engagement=7,
        message_en="okay",  # 1 word — too short to advance
    )
    assert action["action"] == "stay"
    assert action["next_step_id"] == "identify_thought"  # held in place
    assert not action["skill_complete"]

def test_skill_executor_l1_exit_when_user_wants_to_stop():
    state = make_state(
        message_en="I don't want to do this anymore, let's stop.",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=5,
        engagement=3,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result["escalation_triggered"]["level"] == "L1"
    assert result["active_skill_id"] is None  # skill exited
    assert result["executed_step_id"] == "explore_distortion"

def test_skill_executor_l2_flag_on_clinical_signal():
    state = make_state(
        message_en="I've been drinking every night to cope",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=6,
        engagement=6,
        clinical_flags=["substance_use"],
    )
    result = skill_executor_node(state)
    assert result["escalation_triggered"]["level"] == "L2"
    # Skill stays active for L2 (flag only, not exit)
    assert result["active_skill_id"] == "cbt_thought_record"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_evaluate_step_policy_high_intensity_triggers_validate_only tests/test_nodes.py::test_evaluate_step_policy_normal_intensity_advances_to_next_step tests/test_nodes.py::test_evaluate_step_policy_last_step_marks_skill_complete tests/test_nodes.py::test_evaluate_step_policy_low_engagement_triggers_check_in tests/test_nodes.py::test_skill_executor_node_produces_instruction tests/test_nodes.py::test_completion_criteria_short_response_holds_step -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `skill_executor.py`**

```python
# src/sage_poc/nodes/skill_executor.py
from sage_poc.state import SageState
from sage_poc.skills.schema import Skill, load_skill

_OPERATOR_MAP = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

# L1 escalation: user wants to stop the skill
L1_EXIT_PHRASES = [
    "stop", "quit", "don't want to", "enough", "leave", "exit",
    "not doing this", "change the subject", "talk about something else",
    "let's stop", "i want to stop",
]


def check_escalation(message_en: str, clinical_flags: list[str]) -> dict | None:
    """Evaluates escalation matrix before step_policy. Returns escalation dict or None."""
    message_lower = message_en.lower()

    # L1: user requests to stop
    if any(phrase in message_lower for phrase in L1_EXIT_PHRASES):
        return {
            "level": "L1",
            "reason": "User requested to stop the skill",
            "action": "exit_skill",
        }

    # L2: clinical flag detected (substance, trauma, eating, medication)
    if clinical_flags:
        return {
            "level": "L2",
            "reason": f"Clinical flags detected: {', '.join(clinical_flags)}",
            "action": "flag_clinician",
        }

    return None


def _meets_completion_criteria(message_en: str) -> bool:
    """Heuristic: > 10 words signals the user engaged with the step. Empty string → skip check."""
    if not message_en:
        return True
    return len(message_en.split()) > 10


def evaluate_step_policy(
    skill: Skill,
    current_step_id: str,
    emotional_intensity: int,
    engagement: int,
    message_en: str = "",
) -> dict:
    signals = {
        "emotional_intensity": emotional_intensity,
        "engagement": engagement,
    }

    for rule in skill.step_policy:
        cond = rule.condition
        if cond.step not in ("ANY", current_step_id):
            continue
        signal_value = signals.get(cond.signal)
        if signal_value is None:
            continue
        op_fn = _OPERATOR_MAP.get(cond.operator)
        if op_fn and op_fn(signal_value, cond.value):
            return {
                "action": rule.action,
                "instruction": rule.instruction,
                "next_step_id": current_step_id if rule.next_step_id == "current" else rule.next_step_id,
                "skill_complete": False,
            }

    # No rule fired — check completion_criteria before advancing
    step = next(s for s in skill.steps if s.step_id == current_step_id)
    step_instruction = (
        f"Goal: {step.goal}. "
        f"Technique: {step.technique}. "
        f"Tone: {step.tone}. "
        f"Example approaches: {'; '.join(step.examples[:2])}"
    )

    if not _meets_completion_criteria(message_en):
        return {
            "action": "stay",
            "instruction": step_instruction,
            "next_step_id": current_step_id,
            "skill_complete": False,
        }

    # Criteria met — advance to next step in sequence
    step_ids = [s.step_id for s in skill.steps]
    current_idx = step_ids.index(current_step_id)
    next_id = step_ids[current_idx + 1] if current_idx + 1 < len(step_ids) else None

    return {
        "action": "advance" if next_id else "complete",
        "instruction": step_instruction,
        "next_step_id": next_id or current_step_id,
        "skill_complete": next_id is None,
    }


def skill_executor_node(state: SageState) -> dict:
    skill_id = state["active_skill_id"]
    step_id = state["active_step_id"]
    skill = load_skill(skill_id)

    # Evaluate escalation matrix BEFORE step_policy (per architecture spec §9.3)
    escalation = check_escalation(
        message_en=state["message_en"],
        clinical_flags=state.get("clinical_flags", []),
    )
    if escalation:
        matrix_instruction = skill.escalation_matrix.get(
            escalation["level"], "Follow escalation protocol."
        )
        return {
            "step_instruction": f"[{escalation['level']}] {matrix_instruction}",
            "executed_step_id": step_id,
            "active_step_id": step_id,
            "active_skill_id": None if escalation["action"] == "exit_skill" else skill_id,
            "escalation_triggered": escalation,
            "path": state["path"] + ["skill_executor"],
        }

    result = evaluate_step_policy(
        skill=skill,
        current_step_id=step_id,
        emotional_intensity=state["emotional_intensity"],
        engagement=state["engagement"],
        message_en=state["message_en"],
    )

    return {
        "step_instruction": result["instruction"],
        "executed_step_id": step_id,           # which step's instruction was used THIS turn
        "active_step_id": result["next_step_id"],  # where NEXT turn starts from
        "active_skill_id": None if result.get("skill_complete") else skill_id,
        "escalation_triggered": None,
        "path": state["path"] + ["skill_executor"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_evaluate_step_policy_high_intensity_triggers_validate_only tests/test_nodes.py::test_evaluate_step_policy_normal_intensity_advances_to_next_step tests/test_nodes.py::test_evaluate_step_policy_last_step_marks_skill_complete tests/test_nodes.py::test_evaluate_step_policy_low_engagement_triggers_check_in tests/test_nodes.py::test_skill_executor_node_produces_instruction tests/test_nodes.py::test_skill_executor_l1_exit_when_user_wants_to_stop tests/test_nodes.py::test_skill_executor_l2_flag_on_clinical_signal tests/test_nodes.py::test_completion_criteria_short_response_holds_step -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/skill_executor.py tests/test_nodes.py
git commit -m "feat: guided_skill_executor with step_policy evaluation and completion_criteria hook"
```

---

## Task 11: Node 7 — freeflow_respond

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/freeflow_respond.py`
- Modify: `sage-poc/tests/test_nodes.py`

Composes the final LLM prompt from the 6-layer prompt architecture (simplified for POC to L0 + L1 + L2 + L3 only) and calls OpenRouter.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from unittest.mock import patch, MagicMock
from sage_poc.nodes.freeflow_respond import freeflow_respond_node, compose_prompt

def test_compose_prompt_with_skill_instruction():
    state = make_state(
        message_en="I don't know... everything is my fault.",
        primary_intent="new_skill",
        step_instruction="Goal: identify thought. Technique: Socratic questioning. Tone: warm.",
        conversation_history=[],
        emotional_intensity=6,
    )
    prompt = compose_prompt(state)
    assert "wellness" in prompt.lower() or "companion" in prompt.lower()  # L0
    assert "socratic" in prompt.lower() or "identify thought" in prompt.lower()  # L3
    assert "everything is my fault" in prompt

def test_compose_prompt_without_skill_instruction():
    state = make_state(
        message_en="Hello, how are you?",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=3,
    )
    prompt = compose_prompt(state)
    assert "wellness" in prompt.lower() or "companion" in prompt.lower()

def test_compose_prompt_blended_intent_injects_knowledge():
    state = make_state(
        message_en="I feel hopeless. Also, what is CBT?",
        primary_intent="new_skill",
        secondary_intent="info_request",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
    )
    prompt = compose_prompt(state)
    assert "blended" in prompt.lower() or "info_request" in prompt.lower()
    assert "cognitive behavioral" in prompt.lower()  # knowledge snippet injected

def test_compose_prompt_clinical_flag_injects_adaptation():
    state = make_state(
        message_en="I've been drinking to cope",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
        clinical_flags=["substance_use"],
    )
    prompt = compose_prompt(state)
    assert "motivational interviewing" in prompt.lower()
    assert "judge" in prompt.lower()  # "do not judge"

def test_freeflow_respond_with_mocked_llm():
    state = make_state(
        message_en="I keep thinking I'm a failure.",
        step_instruction="Goal: identify the thought. Technique: Socratic questioning.",
        conversation_history=[],
        emotional_intensity=6,
        engagement=7,
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="That sounds really hard. When you say you feel like a failure, what specifically are you telling yourself?")
    result = freeflow_respond_node(state, llm=mock_llm)
    assert result["response_en"] is not None
    assert "freeflow_respond" in result["path"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_compose_prompt_with_skill_instruction tests/test_nodes.py::test_compose_prompt_without_skill_instruction tests/test_nodes.py::test_freeflow_respond_with_mocked_llm -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `freeflow_respond.py`**

```python
# src/sage_poc/nodes/freeflow_respond.py
from sage_poc.state import SageState
from sage_poc.llm import get_responder
from sage_poc.knowledge import lookup_knowledge

# L0: Base persona — always included
PERSONA = """You are Sage, a warm and empathetic wellness companion. You provide emotional support grounded in evidence-based approaches (CBT, DBT, motivational interviewing). You are conversational, never clinical or cold. You listen deeply, reflect back what you hear, and gently guide users toward insight.

You do NOT diagnose, prescribe, or replace professional mental health care. If someone is in crisis, your only role is to express care and provide emergency resources.

Keep responses concise (2–4 sentences unless the user needs more). Match the user's energy and register. Be present before being helpful."""

# Clinical flag adaptations — injected when flags are present
_CLINICAL_ADAPTATIONS = {
    "substance_use": (
        "The user has disclosed substance use. Use motivational interviewing language. "
        "Do NOT judge or suggest immediate cessation. Explore ambivalence gently."
    ),
    "trauma_indicator": (
        "The user has disclosed trauma. Use trauma-sensitive language. "
        "Do NOT push for details. Prioritise emotional safety and containment."
    ),
    "eating_concern": (
        "The user has disclosed eating concerns. Avoid all body or weight comments. "
        "Be sensitive. Gently encourage professional support if appropriate."
    ),
    "medication_mention": (
        "The user mentioned medication. Do NOT advise on dosage or medication changes. "
        "Encourage speaking with their prescriber for any medication questions."
    ),
}


def compose_prompt(state: SageState) -> str:
    parts = [f"SYSTEM: {PERSONA}"]

    # L1: Conversation history (last 4 turns)
    if state["conversation_history"]:
        history = state["conversation_history"][-4:]
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
        parts.append(f"\nCONVERSATION HISTORY:\n{history_text}")

    # L2: Intent instruction
    intent = state.get("primary_intent") or "general_chat"
    secondary = state.get("secondary_intent")
    intensity = state.get("emotional_intensity", 5)
    intent_line = f"INTENT: {intent}"
    if secondary:
        intent_line += f" + {secondary} (blended)"
    parts.append(f"\n{intent_line} | Emotional intensity: {intensity}/10")

    # L3: Skill instruction (only when active)
    if state.get("step_instruction"):
        parts.append(f"\nSKILL INSTRUCTION:\n{state['step_instruction']}")

    # L4-lite: knowledge snippet if secondary_intent is info_request (no vector DB needed)
    if state.get("secondary_intent") == "info_request":
        snippet = lookup_knowledge(state["message_en"])
        if snippet:
            parts.append(
                f"\nKNOWLEDGE (weave naturally into your response if relevant):\n{snippet}"
            )

    # L5-lite: clinical flag adaptations (only when flags present)
    clinical = state.get("clinical_flags", [])
    if clinical:
        adaptations = [_CLINICAL_ADAPTATIONS[f] for f in clinical if f in _CLINICAL_ADAPTATIONS]
        if adaptations:
            parts.append(
                "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
                + "\n".join(f"- {a}" for a in adaptations)
            )

    parts.append(f"\nUSER: {state['message_en']}\n\nSAGE:")
    return "\n".join(parts)


def freeflow_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    prompt = compose_prompt(state)
    response = llm.invoke(prompt).content.strip()

    return {
        "response_en": response,
        "path": state["path"] + ["freeflow_respond"],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_compose_prompt_with_skill_instruction tests/test_nodes.py::test_compose_prompt_without_skill_instruction tests/test_nodes.py::test_freeflow_respond_with_mocked_llm -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/freeflow_respond.py tests/test_nodes.py
git commit -m "feat: freeflow_respond node with 4-layer prompt composition"
```

---

## Task 12: Node 8 — output_gate

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/output_gate.py`
- Modify: `sage-poc/tests/test_nodes.py`

Translates English response back to Arabic if the original input was Arabic, appends the audit path to state, and prints the audit log.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from sage_poc.nodes.output_gate import output_gate_node

def test_output_gate_english_passthrough():
    state = make_state(
        detected_language="en",
        response_en="That sounds really difficult. What thought is coming up for you?",
        path=["safety_check", "intent_route", "skill_select", "skill_executor", "freeflow_respond"],
    )
    result = output_gate_node(state)
    assert result["response"] == "That sounds really difficult. What thought is coming up for you?"
    assert "output_gate" in result["path"]

def test_output_gate_arabic_response_is_translated():
    # We mock the translation to avoid Ollama dependency in unit tests
    state = make_state(
        detected_language="ar",
        response_en="I hear you. That sounds incredibly hard.",
        path=["safety_check", "intent_route"],
    )
    with patch("sage_poc.nodes.output_gate.translate_to_arabic") as mock_translate:
        mock_translate.return_value = "أسمعك. يبدو هذا صعباً للغاية."
        result = output_gate_node(state)
    assert result["response"] == "أسمعك. يبدو هذا صعباً للغاية."
    mock_translate.assert_called_once_with("I hear you. That sounds incredibly hard.")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_output_gate_english_passthrough tests/test_nodes.py::test_output_gate_arabic_response_is_translated -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `output_gate.py`**

```python
# src/sage_poc/nodes/output_gate.py
import json
from datetime import datetime
from sage_poc.state import SageState
from sage_poc.language import translate_to_arabic


def output_gate_node(state: SageState) -> dict:
    response_en = state["response_en"] or ""
    lang = state["detected_language"]

    if lang == "ar":
        final_response = translate_to_arabic(response_en)
    else:
        final_response = response_en

    path = state["path"] + ["output_gate"]

    # Audit log — in production this writes to Cosmos DB
    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "turn": state["turn_count"],
        "path": path,
        "detected_language": lang,
        "primary_intent": state.get("primary_intent"),
        "active_skill": state.get("active_skill_id"),
        "executed_step": state.get("executed_step_id"),   # step used THIS turn
        "next_step": state.get("active_step_id"),          # step NEXT turn starts from
        "emotional_intensity": state.get("emotional_intensity"),
        "engagement": state.get("engagement"),
        "is_safe": state.get("is_safe"),
        "clinical_flags": state.get("clinical_flags", []),
        "escalation": state.get("escalation_triggered"),
    }
    print(f"\n[AUDIT] {json.dumps(audit, indent=2)}")

    # CLI-visible flag for demo visibility
    if state.get("clinical_flags"):
        print(f"\n[CLINICAL FLAGS] {', '.join(state['clinical_flags'])}")
    if state.get("escalation_triggered"):
        esc = state["escalation_triggered"]
        print(f"\n[ESCALATION {esc['level']}] {esc['reason']}")

    return {
        "response": final_response,
        "path": path,
        "turn_count": state["turn_count"] + 1,
        "conversation_history": state["conversation_history"] + [
            {"role": "user", "content": state["message_en"]},
            {"role": "assistant", "content": response_en},
        ],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_output_gate_english_passthrough tests/test_nodes.py::test_output_gate_arabic_response_is_translated -v
```

Expected: `2 passed`

- [ ] **Step 5: Run all node tests**

```bash
pytest tests/test_nodes.py -v -m "not slow"
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/nodes/output_gate.py tests/test_nodes.py
git commit -m "feat: output_gate node with back-translation and audit logging"
```

---

## Task 12A: In-Memory Knowledge Module (L4-lite)

**Files:**
- Create: `sage-poc/src/sage_poc/knowledge.py`
- Modify: `sage-poc/tests/test_nodes.py`

No vector DB. A Python dict with 10 FAQ answers keyed by query phrase. `freeflow_respond` calls `lookup_knowledge()` when `secondary_intent == "info_request"`. This proves blended intent works — the LLM gets both a skill instruction (L3) and a knowledge snippet (L4-lite) and weaves them together.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from sage_poc.knowledge import lookup_knowledge

def test_knowledge_lookup_exact_phrase():
    result = lookup_knowledge("what is anxiety")
    assert result is not None
    assert len(result) > 20

def test_knowledge_lookup_embedded_phrase():
    result = lookup_knowledge("Can you tell me what is CBT and how does it work?")
    assert result is not None

def test_knowledge_lookup_no_match_returns_none():
    result = lookup_knowledge("I feel sad today")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nodes.py::test_knowledge_lookup_exact_phrase tests/test_nodes.py::test_knowledge_lookup_embedded_phrase tests/test_nodes.py::test_knowledge_lookup_no_match_returns_none -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `knowledge.py`**

```python
# src/sage_poc/knowledge.py

KNOWLEDGE_DICT: dict[str, str] = {
    "what is anxiety": (
        "Anxiety is a normal stress response — feelings of worry, nervousness, or unease. "
        "When persistent and interfering with daily life, it may indicate an anxiety disorder. "
        "Evidence-based treatments include CBT, mindfulness, and sometimes medication."
    ),
    "what is depression": (
        "Depression is a mood disorder characterised by persistent low mood, loss of interest, "
        "and reduced energy. It affects how a person feels, thinks, and manages daily activities. "
        "CBT, DBT, and antidepressant medication are commonly effective treatments."
    ),
    "what is cbt": (
        "Cognitive Behavioral Therapy (CBT) is an evidence-based approach that helps identify "
        "and challenge unhelpful thought patterns and behaviours. It's structured, goal-oriented, "
        "and one of the most research-supported therapies for anxiety and depression."
    ),
    "what is dbt": (
        "Dialectical Behavior Therapy (DBT) combines CBT with mindfulness and acceptance strategies. "
        "It was developed for emotional dysregulation and is highly effective for managing "
        "intense emotions, interpersonal difficulties, and self-destructive behaviours."
    ),
    "what is mindfulness": (
        "Mindfulness is the practice of paying intentional, non-judgmental attention to the present moment. "
        "Research shows it reduces stress, anxiety, and depression. "
        "It can be practiced through breathing exercises, body scans, or everyday awareness."
    ),
    "what is burnout": (
        "Burnout is a state of chronic stress that leads to physical and emotional exhaustion, "
        "cynicism, and feelings of ineffectiveness. It's especially common in demanding work or caregiving roles. "
        "Recovery typically involves rest, boundary-setting, and addressing root stressors."
    ),
    "what is trauma": (
        "Trauma is an emotional response to a deeply distressing event. "
        "Effects can include flashbacks, avoidance, emotional numbness, and hypervigilance. "
        "Evidence-based treatments include EMDR and trauma-focused CBT."
    ),
    "what is self-care": (
        "Self-care refers to intentional practices that maintain and restore physical and emotional wellbeing. "
        "It includes sleep, nutrition, movement, social connection, and activities that restore energy. "
        "Effective self-care is personalised — what works varies between people."
    ),
    "what is stress": (
        "Stress is the body's response to perceived demands or threats. "
        "Short-term stress can be motivating; chronic stress harms physical and mental health. "
        "Management strategies include time management, relaxation techniques, and social support."
    ),
    "what is motivational interviewing": (
        "Motivational Interviewing (MI) is a person-centred counselling approach that explores ambivalence "
        "about change. It uses empathic listening, open questions, and affirmation to strengthen "
        "a person's own motivation and commitment to change."
    ),
}


def lookup_knowledge(query: str) -> str | None:
    query_lower = query.lower()
    for phrase, answer in KNOWLEDGE_DICT.items():
        if phrase in query_lower:
            return answer
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nodes.py::test_knowledge_lookup_exact_phrase tests/test_nodes.py::test_knowledge_lookup_embedded_phrase tests/test_nodes.py::test_knowledge_lookup_no_match_returns_none -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/knowledge.py tests/test_nodes.py
git commit -m "feat: in-memory knowledge dict for L4-lite blended intent injection"
```

---

## Task 12B: Node 3 — low_confidence_respond

**Files:**
- Create: `sage-poc/src/sage_poc/nodes/low_confidence_respond.py`
- Modify: `sage-poc/tests/test_nodes.py`

Fires when `intent_route` returns `intent_confidence < 0.6`. Returns an empathic clarifying question. No external dependencies — just an LLM call. Routes to `output_gate` like all terminal nodes.

- [ ] **Step 1: Add test to `test_nodes.py`**

```python
# Add to tests/test_nodes.py
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node

def test_low_confidence_respond_with_mocked_llm():
    state = make_state(
        message_en="I don't know... maybe",
        primary_intent="general_chat",
        intent_confidence=0.4,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content="I want to make sure I understand — could you tell me a bit more about what's on your mind?"
    )
    result = low_confidence_respond_node(state, llm=mock_llm)
    assert result["response_en"] is not None
    assert "low_confidence_respond" in result["path"]
    # Should NOT contain a skill instruction or therapeutic technique
    assert result.get("step_instruction") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_nodes.py::test_low_confidence_respond_with_mocked_llm -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `low_confidence_respond.py`**

```python
# src/sage_poc/nodes/low_confidence_respond.py
from sage_poc.state import SageState
from sage_poc.llm import get_responder

_SYSTEM = (
    "You are Sage, a warm wellness companion. "
    "The user's message was ambiguous and you are not sure what they need. "
    "Ask ONE gentle, open-ended clarifying question to understand better. "
    "Be warm and non-judgmental. Maximum 2 sentences."
)


def low_confidence_respond_node(state: SageState, llm=None) -> dict:
    if llm is None:
        llm = get_responder()

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": state["message_en"]},
    ]
    response = llm.invoke(messages).content.strip()

    return {
        "response_en": response,
        "path": state["path"] + ["low_confidence_respond"],
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_nodes.py::test_low_confidence_respond_with_mocked_llm -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/nodes/low_confidence_respond.py tests/test_nodes.py
git commit -m "feat: low_confidence_respond node (Node 3) for ambiguous intent"
```

---

## Task 13: Graph Assembly

**Files:**
- Create: `sage-poc/src/sage_poc/graph.py`
- Create: `sage-poc/tests/test_graph.py`

Wire all 7 nodes into a LangGraph `StateGraph` with conditional edges for routing.

- [ ] **Step 1: Write failing integration test**

```python
# tests/test_graph.py
import pytest
from unittest.mock import patch, MagicMock

def make_e2e_state(raw_message: str, **overrides) -> dict:
    base = {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": "",
        "is_safe": False,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    return {**base, **overrides}

@pytest.mark.slow
def test_english_general_chat_e2e():
    """English general chat: safety → intent → freeflow → output. No skill."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("Hello, I just wanted to check in."))
    assert result["is_safe"] is True
    assert result["response"] is not None
    assert "safety_check" in result["path"]
    assert "output_gate" in result["path"]

@pytest.mark.slow
def test_english_crisis_message_stops_at_safety():
    """Crisis message: safety_check fires, graph ends, no LLM called."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I want to kill myself tonight"))
    assert result["is_safe"] is False
    assert "safety_check" in result["path"]
    assert "intent_route" not in result["path"]
    assert result["response"] is not None
    assert "crisis" in result["response"].lower() or "help" in result["response"].lower()

@pytest.mark.slow
def test_english_skill_routing_e2e():
    """New skill intent: routes through skill_select → executor → respond."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I keep thinking everything is my fault, always", emotional_intensity=6))
    assert result["is_safe"] is True
    assert "skill_select" in result["path"]
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["executed_step_id"] == "identify_thought"
    assert result["active_step_id"] == "explore_distortion"
    assert result["step_instruction"] is not None
    assert result["response"] is not None
    print(f"\n[TEST] Path: {result['path']}")
    print(f"[TEST] Step used: {result['executed_step_id']} → next: {result['active_step_id']}")
    print(f"[TEST] Response: {result['response']}")

@pytest.mark.slow
def test_cbt_full_3_step_progression_e2e():
    """Full CBT thought record: 3 turns, advances through all steps, skill clears on completion."""
    from sage_poc.graph import build_graph
    graph = build_graph()

    # Turn 1: trigger skill (message > 10 words so completion_criteria allows advancement)
    r1 = graph.invoke(make_e2e_state(
        "I keep thinking that everything is my fault, always, and I cannot escape it",
        emotional_intensity=6,
    ))
    assert r1["active_skill_id"] == "cbt_thought_record"
    assert r1["executed_step_id"] == "identify_thought"
    assert r1["active_step_id"] == "explore_distortion"

    # Turn 2: skill_continuation → explore_distortion step
    r2 = graph.invoke(make_e2e_state(
        "I tell myself I'm worthless and that nothing will ever change",
        active_skill_id=r1["active_skill_id"],
        active_step_id=r1["active_step_id"],
        conversation_history=r1["conversation_history"],
        emotional_intensity=r1.get("emotional_intensity", 6),
        engagement=r1.get("engagement", 7),
    ))
    assert r2["executed_step_id"] == "explore_distortion"
    assert r2["active_step_id"] == "balanced_thought"

    # Turn 3: balanced_thought → skill complete
    r3 = graph.invoke(make_e2e_state(
        "My friend said something kind yesterday... maybe I'm not totally worthless",
        active_skill_id=r2["active_skill_id"],
        active_step_id=r2["active_step_id"],
        conversation_history=r2["conversation_history"],
        emotional_intensity=r2.get("emotional_intensity", 5),
        engagement=r2.get("engagement", 7),
    ))
    assert r3["executed_step_id"] == "balanced_thought"
    assert r3["active_skill_id"] is None  # skill complete, cleared
    print(f"\n[TEST] Full CBT path T3: {r3['path']}")

@pytest.mark.slow
def test_clinical_flag_detected_in_e2e():
    """Substance use message passes crisis check but sets clinical_flags."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I've been drinking heavily every night to cope with the stress"))
    assert result["is_safe"] is True
    assert "substance_use" in result.get("clinical_flags", [])
    assert result["response"] is not None

@pytest.mark.slow
def test_escalation_l1_exit_mid_skill():
    """User says stop mid-skill: executor L1 fires, skill clears, graceful close generated."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state(
        "I don't want to do this anymore, can we stop please",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=5,
    ))
    assert result["active_skill_id"] is None
    assert result.get("escalation_triggered", {}).get("level") == "L1"
    assert result["response"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_graph.py -v -m "slow"
```

Expected: `ImportError: No module named 'sage_poc.graph'`

- [ ] **Step 3: Write `graph.py`**

```python
# src/sage_poc/graph.py
from langgraph.graph import StateGraph, END
from sage_poc.state import SageState
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.nodes.intent_route import intent_route_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node
from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.nodes.skill_executor import skill_executor_node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.output_gate import output_gate_node

CRISIS_RESPONSE = (
    "I'm really concerned about what you've shared. "
    "Please reach out to a crisis line immediately — "
    "in the UAE: Tawazun 800-HOPE (4673), or international: 988 (US). "
    "You don't have to face this alone."
)


def _crisis_response_node(state: SageState) -> dict:
    return {
        "is_safe": False,
        "response": CRISIS_RESPONSE,
        "response_en": CRISIS_RESPONSE,
        "path": state["path"] + ["crisis_response"],
    }


def _route_after_safety(state: SageState) -> str:
    return "safe" if state["is_safe"] else "crisis"


def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
    if confidence < 0.6:
        return "low_confidence"
    if intent == "exit_skill":
        # Route to skill_executor so L1 escalation fires and clears active_skill_id
        # If no active skill, treat as general_chat
        return "skill_executor" if state.get("active_skill_id") else "freeflow"
    if intent == "new_skill":
        # Always re-run skill_select — even mid-skill, user may need a different one
        return "skill_select"
    if intent == "skill_continuation" and state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"


def _route_after_skill_select(state: SageState) -> str:
    return "skill_executor" if state.get("active_skill_id") else "freeflow"


def build_graph() -> StateGraph:
    graph = StateGraph(SageState)

    graph.add_node("safety_check", safety_check_node)
    graph.add_node("intent_route", intent_route_node)
    graph.add_node("low_confidence_respond", low_confidence_respond_node)
    graph.add_node("skill_select", skill_select_node)
    graph.add_node("skill_executor", skill_executor_node)
    graph.add_node("freeflow_respond", freeflow_respond_node)
    graph.add_node("output_gate", output_gate_node)
    graph.add_node("crisis_response", _crisis_response_node)

    graph.set_entry_point("safety_check")

    graph.add_conditional_edges("safety_check", _route_after_safety, {
        "safe": "intent_route",
        "crisis": "crisis_response",
    })
    graph.add_edge("crisis_response", END)

    graph.add_conditional_edges("intent_route", _route_after_intent, {
        "skill_select": "skill_select",
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
        "crisis": "crisis_response",
        "low_confidence": "low_confidence_respond",
    })
    graph.add_edge("low_confidence_respond", "output_gate")

    graph.add_conditional_edges("skill_select", _route_after_skill_select, {
        "skill_executor": "skill_executor",
        "freeflow": "freeflow_respond",
    })

    graph.add_edge("skill_executor", "freeflow_respond")
    graph.add_edge("freeflow_respond", "output_gate")
    graph.add_edge("output_gate", END)

    return graph.compile()
```

- [ ] **Step 4: Run all 3 integration tests**

```bash
pytest tests/test_graph.py -v -m "slow" -s
```

Expected: `6 passed`. You will see real LLM responses and audit logs printed. This is the POC validation.

Verify manually:
- Test 1 (general chat): path = `safety_check → intent_route → freeflow_respond → output_gate`
- Test 2 (crisis): path stops at `safety_check → crisis_response`; `intent_route` NOT in path
- Test 3 (skill routing): `executed_step_id=="identify_thought"`, `active_step_id=="explore_distortion"`
- Test 4 (3-step CBT): 3 turns, each step advances; `active_skill_id` clears on turn 3
- Test 5 (clinical flag): `substance_use` appears in `clinical_flags`; `is_safe==True`
- Test 6 (L1 exit): `active_skill_id` clears; `escalation_triggered.level=="L1"`

Note: the session lifecycle test is in Task 15.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/graph.py tests/test_graph.py
git commit -m "feat: LangGraph graph assembly with conditional routing for all 7 nodes"
```

---

## Task 14: Interactive CLI Runner

**Files:**
- Create: `sage-poc/run.py`

Multi-turn CLI that lets you test the full loop interactively, including Arabic input.

- [ ] **Step 1: Write `run.py`**

```python
#!/usr/bin/env python3
# run.py — Interactive multi-turn SageAI POC runner
import sys
from sage_poc.graph import build_graph
from sage_poc.state import SageState

def make_initial_state() -> SageState:
    return {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


def main():
    print("\n=== SageAI Graph Routing POC ===")
    print("Type your message (Arabic or English). 'quit' to exit.\n")

    graph = build_graph()
    state = make_initial_state()

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        state["raw_message"] = user_input

        result = graph.invoke(state)

        print(f"\nSage: {result['response']}")
        print(f"[Path: {' → '.join(result['path'])}]")

        # Skill status
        if result.get("active_skill_id"):
            print(f"[Skill: {result['active_skill_id']} | Used: {result.get('executed_step_id')} → Next: {result.get('active_step_id')}]")

        # Blended intent
        if result.get("secondary_intent"):
            print(f"[Blended intent: {result.get('primary_intent')} + {result.get('secondary_intent')}]")

        # Clinical flags (visible during demo)
        if result.get("clinical_flags"):
            print(f"[CLINICAL FLAGS: {', '.join(result['clinical_flags'])}]")

        # Escalation
        if result.get("escalation_triggered"):
            esc = result["escalation_triggered"]
            print(f"[ESCALATION {esc['level']}] {esc['reason']}")

        print()

        # Carry forward persistent state for multi-turn
        state = {
            **make_initial_state(),
            "active_skill_id": result.get("active_skill_id"),
            "active_step_id": result.get("active_step_id"),
            "conversation_history": result.get("conversation_history", []),
            "turn_count": result.get("turn_count", 0),
            "engagement": result.get("engagement", 7),
            "emotional_intensity": result.get("emotional_intensity", 5),
        }


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the CLI and test manually**

```bash
cd sage-poc
python run.py
```

Test these inputs in order to exercise all routing paths. Start a fresh session for each numbered block:

**Block A — Full CBT progression:**
1. `Hello` → general_chat → freeflow, no skill
2. `I keep thinking everything is my fault, always` → new_skill → skill_select → executor (identify_thought), output shows `Used: identify_thought → Next: explore_distortion`
3. `I tell myself I'm worthless and nothing will change` → skill_continuation → executor (explore_distortion), advances to balanced_thought
4. `My friend said something nice... maybe I'm not all bad` → skill_continuation → executor (balanced_thought, skill complete), `active_skill_id` clears
5. `I feel better, thanks` → general_chat → freeflow (back to open conversation)

**Block B — Clinical flags + escalation:**
6. `I've been drinking heavily every night to cope` → `[CLINICAL FLAGS: substance_use]` visible in output; response uses motivational interviewing tone
7. `I don't want to do this anymore, can we stop?` (while in a skill) → `[ESCALATION L1]` visible; skill clears

**Block C — Blended intent (knowledge injection):**
8. `I feel hopeless and what is CBT anyway?` → `[Blended intent: new_skill + info_request]`; response weaves therapeutic support AND a CBT explanation

**Block D — Arabic + crisis:**
9. `أشعر أن كل شيء خطئي دائماً` → Arabic detected, translated, CBT routing, Arabic response
10. `I want to kill myself` → stops at crisis_response; no LLM called; path shows only `safety_check → crisis_response`

- [ ] **Step 3: Commit**

```bash
git add run.py
git commit -m "feat: interactive multi-turn CLI runner for POC validation"
```

---

## Task 15: Session Lifecycle E2E Test

**Files:**
- Modify: `sage-poc/tests/test_graph.py`

Demonstrates the full demo journey as one connected flow: greeting → skill trigger → 3-step CBT → skill complete → freeflow → goodbye. Proves the graph handles an entire user session, not just isolated turns.

- [ ] **Step 1: Add test to `test_graph.py`**

```python
# Add to tests/test_graph.py

@pytest.mark.slow
def test_session_full_lifecycle_e2e():
    """Full session: greeting → CBT skill (3 steps) → completion → freeflow. One connected flow."""
    from sage_poc.graph import build_graph
    graph = build_graph()

    # Turn 1: Greeting — general chat, no skill
    r1 = graph.invoke(make_e2e_state("Hello, I have been feeling really overwhelmed lately"))
    assert r1["is_safe"] is True
    assert r1["active_skill_id"] is None
    assert r1["response"] is not None
    print(f"\n[LIFECYCLE] Turn 1 (greeting) path: {r1['path']}")

    # Turn 2: Skill trigger — message > 10 words so completion_criteria allows first step to advance
    r2 = graph.invoke(make_e2e_state(
        "I keep thinking that everything is my fault, always, and I cannot shake it",
        conversation_history=r1["conversation_history"],
        emotional_intensity=6, engagement=7,
    ))
    assert r2["active_skill_id"] == "cbt_thought_record"
    assert r2["executed_step_id"] == "identify_thought"
    assert r2["active_step_id"] == "explore_distortion"
    print(f"[LIFECYCLE] Turn 2 (skill start) executed: {r2['executed_step_id']} → next: {r2['active_step_id']}")

    # Turn 3: User responds to identify_thought prompt (> 10 words → advances)
    r3 = graph.invoke(make_e2e_state(
        "I tell myself that I am worthless and that nothing good will ever happen to me",
        active_skill_id=r2["active_skill_id"],
        active_step_id=r2["active_step_id"],
        conversation_history=r2["conversation_history"],
        emotional_intensity=r2.get("emotional_intensity", 6),
        engagement=r2.get("engagement", 7),
    ))
    assert r3["executed_step_id"] == "explore_distortion"
    assert r3["active_step_id"] == "balanced_thought"
    print(f"[LIFECYCLE] Turn 3 (step 2) executed: {r3['executed_step_id']} → next: {r3['active_step_id']}")

    # Turn 4: User responds to explore_distortion → skill complete
    r4 = graph.invoke(make_e2e_state(
        "My friend said something kind to me yesterday and maybe I am not all bad after all",
        active_skill_id=r3["active_skill_id"],
        active_step_id=r3["active_step_id"],
        conversation_history=r3["conversation_history"],
        emotional_intensity=r3.get("emotional_intensity", 5),
        engagement=r3.get("engagement", 7),
    ))
    assert r4["executed_step_id"] == "balanced_thought"
    assert r4["active_skill_id"] is None  # skill complete, cleared
    print(f"[LIFECYCLE] Turn 4 (skill complete) path: {r4['path']}")

    # Turn 5: Back to freeflow — no active skill
    r5 = graph.invoke(make_e2e_state(
        "Thank you so much, that really helped me think differently about things",
        conversation_history=r4["conversation_history"],
        emotional_intensity=r4.get("emotional_intensity", 4),
        engagement=r4.get("engagement", 7),
    ))
    assert r5["active_skill_id"] is None
    assert r5["response"] is not None
    assert "skill_select" not in r5["path"]
    print(f"[LIFECYCLE] Turn 5 (freeflow close) path: {r5['path']}")
    print("\n[LIFECYCLE] Full session lifecycle confirmed.")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_graph.py::test_session_full_lifecycle_e2e -v -m "slow" -s
```

Expected: `ImportError: No module named 'sage_poc.graph'` (if Task 13 not done) or `1 passed` after Task 13 is complete.

- [ ] **Step 3: Run test after Task 13 is complete**

```bash
pytest tests/test_graph.py::test_session_full_lifecycle_e2e -v -m "slow" -s
```

Expected: `1 passed`. Observe printed output showing the full 5-turn path and step progression.

Verify manually in the output:
- Turn 1: no `skill_select` or `skill_executor` in path
- Turn 2: `executed_step_id=="identify_thought"`, `active_step_id=="explore_distortion"`
- Turn 3: `executed_step_id=="explore_distortion"`, `active_step_id=="balanced_thought"`
- Turn 4: `executed_step_id=="balanced_thought"`, `active_skill_id` is None
- Turn 5: general chat path, no skill nodes

- [ ] **Step 4: Commit**

```bash
git add tests/test_graph.py
git commit -m "test: session lifecycle E2E covering greeting → skill → completion → freeflow"
```

---

## Self-Review

**Spec coverage:**
- ✅ Language detection + Arabic→English translation at Node 1
- ✅ Arabic Unicode override for code-switching (detect_language fast-paths on Arabic chars)
- ✅ Clinical flag detection (substance_use, trauma_indicator, eating_concern, medication_mention)
- ✅ Intent routing (new_skill / skill_continuation / general_chat / crisis / exit_skill / low_confidence)
- ✅ Low-confidence fallback (Node 3) — empathic clarification when classifier confidence < 0.6
- ✅ Skill selection (rule-based keyword matching)
- ✅ step_policy evaluation (deterministic, numeric thresholds, high-intensity + low-engagement rules)
- ✅ Policy override recovery — validate_only holds step; normal intensity on next turn resumes
- ✅ Step advancement (identify_thought → explore_distortion → balanced_thought → skill complete)
- ✅ Skill completion — `active_skill_id` clears when last step executes
- ✅ Escalation matrix — L1 (exit on stop request), L2 (clinical flag, skill stays active)
- ✅ Graceful L1 exit — user "stop" request clears skill, generates warm closing
- ✅ Engagement tracking — computed per-turn by `intent_route`, carried across turns
- ✅ Secondary intent (blended) — `intent_route` returns both primary + secondary
- ✅ Prompt composition (6 layers: L0 persona + L1 history + L2 intent + L3 skill + L4-lite knowledge + L5-lite clinical)
- ✅ Knowledge injection (L4-lite) — 10-entry in-memory dict injected when secondary_intent="info_request"
- ✅ Clinical flag prompt adaptation (L5-lite) — motivational interviewing, trauma-sensitive language, etc.
- ✅ Response generation via OpenRouter
- ✅ English→Arabic back-translation at output_gate
- ✅ Audit trail (path, executed_step, next_step, clinical_flags, escalation logged per turn)
- ✅ Crisis short-circuit (graph terminates before any LLM call)
- ✅ Multi-turn state (skill_id + step_id + history + emotional_intensity + engagement carried across turns)
- ✅ Completion_criteria heuristic (> 10 words) — proves the production hook; gates step advancement before advancing
- ✅ Araglish code-switching — Arabic Unicode override classifies code-switched messages as Arabic in detect_language
- ✅ Session lifecycle E2E — greeting → CBT skill (3 steps) → completion → freeflow (one connected test flow)

**Intentionally omitted (out of POC scope):**
- Node 6 (knowledge_retrieve / RAG): requires a populated vector index — defeats the lightweight goal
- Secondary intent routing changes: secondary_intent informs prompt only — primary intent drives routing
- LLM tools (knowledge_lookup, check_user_history, etc.): Full Build
- User therapeutic profile + active issues list: Full Build
- LangGraph MemorySaver (Cosmos DB): Full Build
- Engagement scoring + blended intent: Full Build

**Placeholder scan:** None found. All code blocks are complete.

**Type consistency:** `SageState` fields are used consistently across all nodes. `skill_executor_node` reads `active_skill_id`/`active_step_id` — same field names written by `skill_select_node`. `output_gate_node` reads `response_en` — same field written by `freeflow_respond_node`.

---

## Ollama Model Reference

| Model | Size | Arabic Quality | Best For |
|-------|------|---------------|---------|
| `qwen2.5:3b` | 1.9GB | Adequate | Quick testing, low RAM |
| `qwen2.5:7b` | 4.7GB | Good ✅ (recommended) | POC standard |
| `qwen2.5:14b` | 9.0GB | Very good | Higher quality translation |
| `aya-expanse:8b` | 4.7GB | Good (multilingual-first) | Alternative to qwen2.5:7b |

If translation quality is poor with `qwen2.5:7b`, upgrade to `qwen2.5:14b`. Do not go below 3B parameters for Arabic — smaller models produce incoherent Arabic output.

---
