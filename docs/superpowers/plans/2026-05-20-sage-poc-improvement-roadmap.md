# Sage POC Improvement Roadmap — Post-Abby Benchmark

**Date:** 2026-05-20
**Status:** Living planning artifact — update after each sprint completion
**Purpose:** Translate competitive benchmark findings and residual bug inventory into a prioritised, actionable roadmap for taking the Sage POC from proof-of-concept to CDAi Gitex pilot readiness. This document is the authoritative source for sprint sequencing decisions.

---

## 1. Benchmark Summary

Abby.gg is a consumer-grade AI therapy companion built on a single GPT-4o instance with custom clinical system prompts, a server-side user profile memory service, and a live web-search backend for its "7,000+ articles" Discover feature. It is a polished B2C product with a clear freemium-to-subscription conversion funnel — its Roadmap feature is a four-step conversion mechanism dressed as a care plan, not a clinical tool. Its voice feature is browser Web Speech API input-to-text with no server-side audio processing; it has no vocal biomarker capability. Architecturally, Abby is a single-agent application with message-injection tooling, not an orchestrated multi-node graph. Its "knowledge base" is live web search with UTM tracking, confirmed by `?utm_source=abby.gg` parameters appended to every returned URL.

The benchmark surfaced three categories of competitive gap. First, safety protocol failures: Abby passes no crisis response for passive hopelessness ("nothing matters") or passive suicidal ideation ("everyone would be better off without me"), fires a single catch-all one-sentence template for explicit crisis, jailbreak attempts, and scope refusals interchangeably, and lists only US crisis resources (988, 741741) with zero UAE or MENA coverage by default. Second, cultural and linguistic gaps: Abby's Arabic classification engine runs in English only, its religious framing is Christian-biased by training data, and it pathologises collectivist family values by defaulting to Western individualist framing. Third, memory architecture risks: cross-session memory injection is attribution-free and surfaces previously crisis-flagged content in non-crisis contexts without re-triggering safety protocol — a clinical liability that Abby's architecture cannot safely patch without a graph-level safety gate.

The benchmark also confirmed Sage's structural advantages. The 8-node LangGraph separation of concerns means safety re-checks can be composed at the graph level rather than prompt-engineered around. The step_policy-driven skill executor gives Sage a genuine clinical architecture that Abby cannot replicate conversationally. The `secondary_intent` field exists in `SageState` and is already surfaced in the intent block of `freeflow_respond.py` — it just is not yet used to drive response behaviour. The UAE crisis resources in `graph.py` are already correct following prior sprint remediation. The foundation is sound.

---

## 2. Immediate Fixes — Blockers Before Any Feature Work

These are not sprint items. They are pre-conditions for any further development. Each fix is small and isolated. The 92 passing tests must remain green after each change.

### BUG NEW-1 — English CRISIS_RESPONSE Has Incorrect Contacts

**File:** `sage-poc/src/sage_poc/graph.py`

The Arabic `CRISIS_RESPONSE_AR` is correct (800 4673, 999, no 988, no Tawazun). The English `CRISIS_RESPONSE` constant must match: "in the UAE: 800 4673 (800-HOPE), or emergency: 999" with no US-only lines. Verify, fix, and add a parallel test `test_english_crisis_response_excludes_us_only_988` in `tests/test_graph.py` matching the existing Arabic-path tests.

### BUG NEW-2 — Three L1_EXIT_PHRASES Remain Overly Broad

**File:** `sage-poc/src/sage_poc/nodes/skill_executor.py`

Three phrases cause false-positive skill exits. Replace:
- `"want to quit"` → `"i want to quit this exercise"`
- `"can we stop"` → `"can we stop this exercise"`
- `"i'm done with this"` → `"i'm done with this exercise"` and `"i'm done with this skill"`

Add parametrized regression tests in `tests/test_nodes.py` asserting no false exit when these phrases appear in a clearly non-exit context.

### BUG P1-1 — Missing Crisis Keyword Phrases

**File:** `sage-poc/src/sage_poc/nodes/safety_check.py`

Verify `"don't want to be alive"` and `"end it all"` are present in `CRISIS_KEYWORDS`. Add if absent. Add explicit single-phrase tests for both in `tests/test_nodes.py` asserting `is_safe is False`.

### BUG P2-6 — ZWSP Bypass: Normalise Unicode Before Matching

**File:** `sage-poc/src/sage_poc/nodes/safety_check.py`

The `_contains_crisis` normalisation must explicitly strip invisible Unicode characters using escape sequences, not literal copy-pasted characters. Change to:

```python
text_lower = re.sub(r'[​‌‍﻿]', '', text).lower()
```

Add a test asserting `"kill​myself"` triggers crisis detection.

### BUG NEW-4 — Multi-Turn Test Helpers Missing State Carry-Forward

**File:** `sage-poc/tests/test_graph.py`

Add `carry_state(prev_result: dict, raw_message: str, **overrides) -> dict` that automatically carries forward `turn_count`, `clinical_flags`, `conversation_history`, `active_skill_id`, `active_step_id`, `emotional_intensity`, and `engagement` from the previous turn's result. Update multi-turn E2E tests to use it. Add a test asserting `clinical_flags` from turn 1 propagate to turn 2.

### BUG NEW-5 — Audit JSON Prints Unconditionally to Stdout

**Files:** `sage-poc/src/sage_poc/nodes/output_gate.py`, `sage-poc/src/sage_poc/graph.py`

In `config.py`, add:
```python
AUDIT_LOG_ENABLED = os.getenv("SAGE_AUDIT_LOG", "false").lower() == "true"
```

Guard every audit `print` call with `if AUDIT_LOG_ENABLED:`. Set `SAGE_AUDIT_LOG=true` in `.env.example`. Add a test using `capsys` asserting suppression when disabled.

---

## 3. LLM Stack Migration — Anthropic API Direct (Claude Sonnet + Haiku)

Remove OpenRouter. Remove Ollama. All LLM calls go directly to the Anthropic API.

**Model assignment:**

| Call site | File | Model |
|---|---|---|
| Intent classification | `intent_route.py` | `claude-haiku-4-5-20251001` |
| Skill semantic matching (Sprint B) | `skill_select.py` | `claude-haiku-4-5-20251001` |
| Arabic ↔ English translation | `language.py` | `claude-haiku-4-5-20251001` |
| Session summarisation (Sprint A) | new `memory.py` | `claude-haiku-4-5-20251001` |
| Session naming (Sprint C) | `run.py` | `claude-haiku-4-5-20251001` |
| Therapeutic response generation | `freeflow_respond.py` | `claude-sonnet-4-6` |
| Low-confidence clarification | `low_confidence_respond.py` | `claude-sonnet-4-6` |

### Changes to `config.py`

Replace all `OPENROUTER_*` constants:

```python
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLASSIFIER_MODEL = os.getenv("SAGE_CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")
RESPONDER_MODEL = os.getenv("SAGE_RESPONDER_MODEL", "claude-sonnet-4-6")
TRANSLATOR_MODEL = os.getenv("SAGE_TRANSLATOR_MODEL", "claude-haiku-4-5-20251001")
```

Update `.env.example`: remove `OPENROUTER_API_KEY` and Ollama variables. Add `ANTHROPIC_API_KEY=sk-ant-...`.

### Changes to `llm.py`

Replace `langchain_openai.ChatOpenAI` with `langchain_anthropic.ChatAnthropic`:

```python
from langchain_anthropic import ChatAnthropic
from sage_poc.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL, RESPONDER_MODEL, TRANSLATOR_MODEL

def get_classifier():
    return ChatAnthropic(model=CLASSIFIER_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0, max_tokens=512)

def get_responder():
    return ChatAnthropic(model=RESPONDER_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.7, max_tokens=1024)

def get_translator():
    return ChatAnthropic(model=TRANSLATOR_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0, max_tokens=1024)
```

### Changes to `language.py`

Change `translate_to_english` and `translate_to_arabic` to call `get_translator()` instead of `get_responder()`. Import change only — function signatures and callers are unchanged.

### Changes to `pyproject.toml`

Remove `langchain-openai`. Add `langchain-anthropic>=0.3.0` and `anthropic>=0.40.0`.

### Test impact

All 92 mocked-LLM fast tests are model-agnostic and require no changes. Add `@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="requires Anthropic API key")` to all slow E2E tests.

---

## 4. Feature Roadmap

### Sprint A — Session Memory + Output Gate + Secondary Intent

Sprint A is the highest-impact sprint. It directly addresses the two most clinically significant gaps from the benchmark: absence of cross-session continuity and the single catch-all output gate.

#### A1 — Session Memory Architecture

**New file: `sage-poc/src/sage_poc/memory.py`**

Three responsibilities: post-session summarisation, profile persistence, and context injection.

`summarise_session(history: list[dict], user_id: str) -> dict`
Calls `get_translator()` (Haiku, fast and cost-appropriate for extraction) with a structured extraction prompt. Returns JSON with fields:
- `themes: list[str]` — emotional and situational themes
- `disclosed_topics: list[str]` — specific topics explicitly discussed
- `techniques_used: list[str]` — skills or exercises the user engaged with
- `safety_flags: list[str]` — any SI language, crisis disclosures, or harm-adjacent content. **This field gates injection.**
- `emotional_range: str` — overall emotional pattern of the session

`load_profile(user_id: str) -> dict`
Reads from `sage-poc/data/profiles/{user_id}.json` in POC (MongoDB in production). Returns empty dict if no profile exists.

`save_profile(user_id: str, summary: dict) -> None`
Merges new session summary into existing profile, appending to lists and updating `safety_flags` as a union.

`compose_memory_context(profile: dict, current_safety_recheck: bool) -> str | None`
Builds the cross-session context block. Returns `None` if:
- Profile is empty
- `safety_flags` is non-empty and `current_safety_recheck` is `False`

When returning content, **every reference is prefixed**: `"In an earlier conversation, you mentioned..."`. This attribution rule is non-negotiable — it is the primary differentiator from Abby's confabulation-risk pattern confirmed in benchmark tests G1, E1, and E4.

**The SI safety gate**: Abby's most critical clinical failure (benchmark E4 Tier 1) was surfacing passive SI content from a prior session in a non-crisis informational context without re-triggering any safety protocol. The `compose_memory_context` suppression logic prevents this: if `user_profile.get("safety_flags")` is non-empty, the function returns `None` unless explicitly called with `current_safety_recheck=True` after `safety_check` clears the current turn.

**Changes to `state.py`**

Add two fields:
```python
user_id: Optional[str]          # set by CLI/API caller
user_profile: dict              # loaded profile, injected at graph entry
```

**Changes to `freeflow_respond.py`**

In `compose_prompt`, after the conversation history block:
```python
memory_ctx = compose_memory_context(
    profile=state.get("user_profile", {}),
    current_safety_recheck=state.get("is_safe", True)
)
if memory_ctx:
    user_parts.append(f"PRIOR CONTEXT (always attribute with 'In an earlier conversation...'):\n{memory_ctx}")
```

**Session summary trigger in `output_gate.py`**

After computing the final response, if `user_id` is set and `turn_count >= 4`, call `summarise_session` and `save_profile` in a background thread (do not block response delivery on summarisation).

#### A2 — Three-Path Output Gate

**What to build**: Three distinct response paths for boundary violations. The crisis path already exists in `_crisis_response_node`. The output gate change adds differentiated handling for scope refusals and jailbreak attempts.

**New `gate_path` field in `state.py`**
```python
gate_path: Optional[Literal["standard", "scope_refusal", "jailbreak"]]
```

**Changes to `intent_route.py`**

Add `"scope_refusal"` and `"jailbreak"` to valid `primary_intent` values:
- `scope_refusal` = user asks for diagnosis, medication advice, or specific clinical recommendations beyond the companion's scope
- `jailbreak` = user attempts to override instructions, assign a false identity, or elicit prohibited outputs

**Changes to `graph.py`**

Update `_route_after_intent` to route both new intents directly to `output_gate`, bypassing `skill_select` and `freeflow_respond`, with the appropriate `gate_path` value.

**Changes to `output_gate.py`**

```python
gate_path = state.get("gate_path")

if gate_path == "scope_refusal":
    response_en = (
        "That's a question that's better answered by a medical professional or licensed therapist — "
        "I want to make sure you get accurate information. What I can do is help you think through "
        "how you're feeling about it, or find some general information. Would either of those help?"
    )

elif gate_path == "jailbreak":
    response_en = (
        "I'm Sage — a wellness companion built to offer emotional support and evidence-based coping "
        "techniques. That's my role, and it's what I'm here for. What's been on your mind today?"
    )
```

**Critical**: Neither scope_refusal nor jailbreak paths render crisis resources. Only the crisis_response_node does. This is the three-path differentiation that Abby's single catch-all fails to provide.

**Extended crisis resources for proactive queries (E5 benchmark finding)**

Add `CRISIS_RESPONSE_EXTENDED` for the case where `intent_route` classifies a message as `info_request` with crisis-resource content (user asking about resources, not in acute crisis):

```python
CRISIS_RESPONSE_EXTENDED = """Here are crisis resources for the UAE:
- CDA Mental Health Support: 800-4888
- National Lifeline (Estijaba): 800-HOPE (800-4673)
- Emergency Services: 999
- Al Amal Psychiatric Hospital: for in-person psychiatric support
- Lighthouse Arabia, Camali Clinic, American Center for Psychiatry and Neurology: therapy in Dubai

If you're in immediate danger, please call 999 or go to your nearest emergency room."""
```

Render in Arabic when `detected_language == "ar"`. Route to this extended response when `primary_intent == "info_request"` and crisis-resource keywords are present, without firing the full crisis protocol.

#### A3 — Secondary Intent Activation in `freeflow_respond.py`

The `secondary_intent` field is classified by `intent_route_node` but the response layer ignores it. Add a secondary intent instruction block in `compose_prompt` after the intent line:

```python
if state.get("secondary_intent"):
    si = state["secondary_intent"]
    if si == "info_request":
        user_parts.append(
            "SECONDARY INTENT: The user also has a factual question. Address both their emotional "
            "state AND their question. Answer the factual question naturally — do not make them ask again."
        )
    elif primary == "info_request" and si == "new_skill":
        user_parts.append(
            "SECONDARY INTENT: After answering their question, gently offer whether they'd like to "
            "try a short coping exercise."
        )
    else:
        user_parts.append(
            "SECONDARY INTENT: The user has expressed two distinct concerns. Acknowledge both. "
            "Do not collapse to only the primary. Use DBT dialectical framing — two things can be "
            "true at once."
        )
```

This directly addresses the benchmark F1 finding where Abby collapsed anger + guilt to anger only.

---

### Sprint B — Skills Library Expansion

Sprint B expands from one CBT skill to a library of six, adds semantic skill matching, and implements the digression bridge pattern.

#### B1 — Five New Skill JSON Files

Each follows the existing `skills/schema.py` exactly.

**`dbt_distress_tolerance.json`**
- Evidence base: Linehan (1993), DBT Skills Training Manual
- `target_presentations`: `["can't calm down", "about to explode", "overwhelmed right now", "intense emotion", "tipp", "calm me down"]`
- 3 steps: `assess_intensity` → `deliver_tipp_component` (default: Paced Breathing for acute distress) → `consolidate`
- **The consolidate step names the technique**: *"That was Paced Breathing, part of a DBT skill called TIPP — Temperature, Intense exercise, Paced breathing, Paired muscle relaxation."* This is the clinical differentiation from Abby's unnamed grounding approach confirmed in benchmark D3.
- Step policy: `emotional_intensity > 8` on any step triggers Paced Breathing immediately, skipping assessment

**`box_breathing.json`**
- Evidence base: US Navy SEAL protocol, replicated in acute anxiety RCTs
- `target_presentations`: `["anxious", "panic", "breathing", "box breathing", "can't breathe"]`
- 2 steps: `establish_readiness` → `guide_four_cycles` (four complete 4-4-4-4 cycles, each phase named)
- Step policy: `engagement < 3` returns a check-in before advancing cycles

**`grounding_5431.json`**
- Evidence base: trauma-informed grounding, EMDR literature
- `target_presentations`: `["grounding", "dissociated", "not here", "flashback", "disconnected", "5 things"]`
- 5 steps — one per sensory modality: `five_sight` → `four_touch` → `three_sound` → `two_smell` → `one_taste`
- **Stepped delivery is the differentiator**: Abby delivers 5-4-3-2-1 in one collapsed block (benchmark D3, turn 2). Sage guides one modality at a time, waiting for the user before advancing.
- Step policy: `emotional_intensity > 7` on any step repeats the current modality with additional anchoring before advancing
- Consolidate step names the skill: *"That was 5-4-3-2-1 grounding — it works by using your senses to bring you into the present moment."*

**`behavioural_activation.json`**
- Evidence base: Jacobson et al. (1996), NICE CG90
- `target_presentations`: `["no motivation", "can't get out of bed", "nothing feels good", "anhedonia", "feel nothing", "stopped doing things I liked"]`
- 3 steps: `activity_mapping` → `barrier_identification` → `smallest_possible_step`
- Step policy: `engagement < 4` at `activity_mapping` offers a prebuilt activity list rather than open exploration

**`psychoeducation_anxiety.json`**
- Evidence base: Barlow & Craske (2007)
- `target_presentations`: `["what is anxiety", "explain anxiety", "why do I feel this way", "fight or flight", "why is my body reacting"]`
- 2 steps: `explain_mechanism` (fight-or-flight → cortisol/adrenaline → somatic symptoms, clinically accurate) → `personalise` (ask which physical symptoms the user experiences, then reflect their specific pattern back)
- Informed by benchmark E1: Abby's psychoeducation was accurate but not personalised to the user's body

**Update `skill_select.py`:**
```python
SKILL_REGISTRY = [
    "cbt_thought_record",
    "dbt_distress_tolerance",
    "box_breathing",
    "grounding_5431",
    "behavioural_activation",
    "psychoeducation_anxiety",
]
```

#### B2 — Semantic Skill Matching

**Current state**: `skill_select_node` uses substring matching against `target_presentations`. This misses paraphrase and becomes brittle at scale.

**Replacement**: LLM-based semantic matching via `get_classifier()` (Haiku). Construct a prompt presenting the user's message and a JSON array of skill names with their target presentation lists. The classifier returns the `skill_id` of the best match or `null` if relevance is below 0.7.

- Function signature of `skill_select_node` unchanged
- Add `llm=None` parameter for testability
- Fallback to existing substring match on LLM error
- Update `tests/test_nodes.py` with mocked LLM tests for the semantic path

#### B3 — Digression Bridge Pattern

**Benchmark finding**: Abby abandons a skill entirely when a mid-skill digression occurs (test G1). Sage's graph architecture allows handling this within `skill_executor`.

**New `digression_handling` field in `state.py`**:
```python
digression_handling: Optional[dict]  # {"active": bool, "digression_turn": int, "bridge_offered": bool}
```

**Changes to `skill_executor.py`**:

Before evaluating the escalation matrix, detect if the current message is a topical digression: `primary_intent` classified as `general_chat` or `info_request` while an active skill is in progress.

When digression detected:
1. Set `digression_handling = {"active": True, "digression_turn": state["turn_count"], "bridge_offered": False}`
2. Set `step_instruction` to: `"[DIGRESSION] Address the user's question/comment fully and warmly. Then at the end of your response, offer a bridge: 'Whenever you're ready, we can return to [skill_name].' Do NOT continue the skill steps this turn."`
3. Do NOT advance `active_step_id`
4. Do NOT trigger escalation

On the next turn, if `digression_handling["active"] is True` and intent is `skill_continuation`, clear `digression_handling` and resume from the held step.

---

### Sprint C — Knowledge Base + Cultural Intelligence + UX Patterns

#### C1 — ChromaDB Vector-Indexed Knowledge Base

**What to build**: Replace the 10-entry `knowledge.py` with a ChromaDB-backed RAG. Use `voyage-3` embeddings (Voyage AI API) or `text-embedding-3-small` as fallback.

**Target corpus**: 100–200 clinically validated entries across categories:
- Anxiety mechanisms and coping (15 entries)
- Depression, anhedonia, burnout (15 entries)
- CBT concepts — named distortions, thought records, behavioural experiments (20 entries)
- DBT skills — TIPP, ACCEPTS, STOP, GIVE — named and explained (20 entries). **This is the Ask module foundation**: a user should be able to ask "what is TIPP?" and get a clinically accurate explanation.
- UAE mental health resources — clinics, hotlines, UAE legal context for self-harm (10 entries)
- Islamic psychology and spiritual wellbeing — sabr, tawakkul, ibtila, Quranic framing of trials (10 entries)
- Grief and loss (10 entries)
- Collectivist family dynamics — Gulf and Arab culture context (10 entries)
- Sleep, somatic symptoms, physical manifestations of psychological distress (10 entries)
- Parenting, child development, school stress (10 entries)

**New directory**: `sage-poc/src/sage_poc/kb/`
- `store.py` — ChromaDB client, `upsert_entry()`, `query_kb(query: str, n_results: int = 3) -> list[str]`
- `entries/` — YAML files per category, each entry: `{id, title, body, tags, language}`
- `seed.py` — CLI script to upsert from YAML files into ChromaDB

**Changes to `knowledge.py`**: Preserve `lookup_knowledge(query: str) -> str | None` signature. Implementation changes to call `query_kb(query, n_results=2)` and join results. Keep existing dict as offline/test fallback when `CHROMA_PERSIST_DIR` is not set.

**No changes to `freeflow_respond.py`** — the existing `lookup_knowledge` call benefits automatically.

**New dependencies in `pyproject.toml`**: `chromadb>=0.5.0`, `voyageai>=0.2.0`, `pyyaml>=6.0`

#### C2 — Arabic/Islamic/Collectivist System Prompt Enhancement

**What to build**: A new function `_compose_cultural_adaptation(state: SageState) -> str | None` in `freeflow_respond.py`, returning an additional system prompt block injected between `PERSONA` and `CLINICAL ADAPTATIONS`.

**Islamic framing detection** — when user message contains faith-related terms (`{"faith", "god", "allah", "prayer", "sin", "punishment", "haram", "halal", "qadar", "test", "trial", "dua", "salah"}`) inject:

```
ISLAMIC CULTURAL CONTEXT: The user is framing their distress through an Islamic lens.
Use appropriate vocabulary where natural: sabr (صبر — patience/endurance),
tawakkul (توكّل — trust in God), ibtila (ابتلاء — trial/test from God).
Frame hardship as ibtila rather than punishment — trials in Islam are described in
the Quran as tests (2:155–157), not evidence of wrongdoing. If the user uses "Allah",
mirror that usage. Do not use Christian-framed language.
```

**Collectivist family dynamics detection** — when message contains family terms alongside obligation or conflict terms, inject:

```
COLLECTIVIST CULTURAL CONTEXT: In this user's cultural context, family cohesion and
collective wellbeing are values, not constraints. Do not frame family expectations as
something the user must overcome. Hold space for both the user's individual experience
AND the legitimacy of their family's role. Avoid: "your own needs", "setting yourself
free", "what YOU want". Use: "finding a path that honours both you and your family",
"what feels right for you and those you care about".
```

**Code-switching detection** — when `detected_language == "ar"` but message contains Latin characters, inject:

```
CODE-SWITCHING: This user is writing in both Arabic and English. Mirror this bilingual
register — respond in a natural mix matching their input pattern.
```

This directly addresses benchmark findings I4 (Christian-biased religious framing), I5 (collectivist pathologisation), and I3 (code-switching response quality).

#### C3 — UX Patterns from Benchmark

**Conversation frame shortcuts in `run.py`**

At session start, display four intent-frame options before first input:
```
[1] Something's been weighing on me
[2] I want to work through a difficult thought
[3] I want to try a coping technique
[4] Just checking in
```
If user inputs `1`–`4`, prepend the corresponding phrase to their first message before graph invocation. Any other input proceeds normally. The message still goes through `intent_route` — this reduces cold-start friction without replacing NLU routing.

**Session naming after first turn**

After `output_gate_node` completes turn 1 (`turn_count == 1`), call `get_classifier()` with:
```
In 2–5 words, give this conversation a therapeutic, non-stigmatising title based on the
user's first message. Return only the title, no quotes.
```
Print as `\n[Session: {title}]\n`. Store in new `session_name: Optional[str]` field in `SageState` for audit logging. This mirrors Abby's sidebar naming behaviour (benchmark observation A).

---

## 5. Architecture Evolution Path

The 8-node LangGraph graph is the permanent backbone. Every node is a control decision; every model is factory-injected through `llm.py`. This separation is what enables the POC-to-production evolution without architectural rewrites.

**POC → Gitex Pilot** (this roadmap):
- OpenRouter removed; Anthropic API direct (Haiku for speed, Sonnet for quality)
- Session memory added
- Output gate differentiated (3 paths)
- Skills library expanded (6 skills)
- ChromaDB KB added
- Cultural intelligence enhanced

**Gitex Pilot → Full Build** (post-pilot, node-by-node model swap):
- `safety_check_node`: MARBERT-FT Arabic crisis classification added as parallel signal. Node computes union of keyword lexicon + MARBERT output. Graph topology unchanged.
- `freeflow_respond_node`: `get_responder()` factory switches from `claude-sonnet-4-6` to Falcon-34B+LoRA when UAE-sovereign hosting is active. No change to the node itself.
- `skill_select_node`: LLM semantic matcher (Sprint B) switches from Haiku to BGE-M3 embeddings in production for lower latency at scale.
- `knowledge_retrieve_node`: The deferred node 6 (currently skipped in POC) activates as the Ask module's graph entry point. Connects to the ChromaDB KB, which grows to a BGE-M3-indexed full clinical corpus curated by Sage Clinics.
- Memory: `save_profile` / `load_profile` swap file storage for MongoDB Atlas (UAE-hosted). Interface unchanged.
- Vocal biomarker: A `biomarker_check` node at graph entry (pre-`safety_check`) processes the 90-second daily audio recording. Output: `biomarker_state: dict` with `fatigue_level`, `speech_rate_deviation`, `valence`. Used by `freeflow_respond` to adjust opening tone and by `skill_select` to prefer lower-intensity skills when fatigue is high. No other nodes change.
- Admin Dashboard: Reads from `output_gate_node` audit logs (already structured JSON). No graph changes required.

**The graph node count may increase** (biomarker_check, profile_load, knowledge_retrieve) but the routing logic follows the same conditional edge pattern established in `graph.py`. The graph is a composition of independent, testable, model-agnostic nodes — the correct architecture for regulated, clinically validated, UAE-sovereign deployment.

---

## 6. Competitive Positioning Summary

| Dimension | Abby | Sage POC (current) | Sage Post-Roadmap |
|---|---|---|---|
| **Safety — passive SI detection** | Not detected | Keyword lexicon + crisis node | + LLM re-check; MARBERT-FT in full build |
| **Output gate paths** | 1 (single catch-all) | 1 (crisis separate; scope/jailbreak undifferentiated) | 3 (crisis / scope refusal / jailbreak) |
| **UAE crisis resources** | US-only by default; UAE only when location stated | 800-HOPE, 999 hardcoded | CDA 800-4888, Estijaba, extended proactive path |
| **Cross-session memory** | Active; attribution-free; SI content surfaces without re-check | None | Post-session summarisation; attribution required; SI safety gate |
| **Skill architecture** | Conversational only; digression causes abandonment | Step-policy CBT (1 skill); no digression bridge | 6 skills; digression bridge; semantic matching |
| **DBT technique naming** | TIPP delivered but never named | No DBT skill | `dbt_distress_tolerance.json` names TIPP explicitly in consolidate step |
| **Secondary intent** | Collapses to primary emotion | Classified but unused in response | DBT dialectical framing when dual emotions present |
| **Arabic classification** | English-only (sidebar labels confirm) | Arabic via Unicode detection; Arabic crisis keywords | + code-switching cultural adaptation |
| **Islamic / collectivist framing** | Christian-biased; collectivist values pathologised | Not addressed | Islamic vocabulary injection; collectivist framing guard |
| **Knowledge base** | Live web search + UTM tracking | 10 hardcoded entries, substring match | ChromaDB RAG; 100–200 validated entries; semantic query |
| **Vocal biomarker** | Web Speech API only (no server audio) | Planned; not in POC | Not in roadmap scope; full build feature |
| **Deployment model** | $19.99/month B2C; ~10 free messages | CDA B2G partnership | Same; regulatory compliance is structural differentiator |

---

## Appendix — Benchmark Source

Full competitive benchmark report: `/Users/knowledgebase/Documents/Sage/docs/abby-analysis/results/BENCHMARK_REPORT.md`

Test plan: `/Users/knowledgebase/Documents/Sage/docs/abby-analysis/TEST_PLAN.md`

Screenshots: `/Users/knowledgebase/Documents/Sage/docs/abby-analysis/results/screenshots/`

Tests run: Phase 1 (free tier, A2/B1-B5/C1-C4/D1-D2/E3), Phase 2 (Pro, I1-I5/F1/F4-F5/G1/G4-G5/J1/J3), Tier 1 (Voice/E1/E4/E5/D3/Bookmarks), Tier 2 (T1-T5 architecture probes). Abby confirmed as OpenAI GPT-4o with custom clinical system prompts, server-side MongoDB user profile memory, and live web search (UTM-tracked) for Discover tools.

---

*Document maintained by: Sage Architecture Team. Next review: after Sprint A completion.*
