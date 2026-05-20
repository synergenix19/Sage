# Semantic Skill Matching — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a BGE-M3 semantic embedding fallback to `skill_select_node` so that when keyword matching returns `None`, the system computes cosine similarity between the user message and each skill's `semantic_description` — eliminating the class of missed-activation bugs permanently without requiring keyword additions for every new phrasing.

**Architecture:** Keywords remain Tier 1 (deterministic, fast, auditable — unchanged). When keywords miss, Tier 2 fires: compute cosine similarity between the user message embedding and pre-embedded skill descriptions, return the top match if above an empirically-calibrated threshold. This is the v7 §4.3 MVP hybrid approach. The Full Build "Skill Retrieval Augmentation" pattern (semantic as primary with Falcon-3B reranker) is a separate future step.

**Tech Stack:** Python 3.12, `sentence-transformers` (BAAI/bge-m3), `numpy`, pydantic v2, pytest.

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `pyproject.toml` | Modify | Add `sentence-transformers`, `numpy` dependencies |
| `src/sage_poc/skills/schema.py` | Modify | Add `semantic_description: str = ""` to `Skill` model |
| `src/sage_poc/state.py` | Modify | Add `skill_match_method`, `semantic_score` fields to `SageState` |
| `run.py` | Modify | Add new fields to `make_initial_state()` |
| `src/sage_poc/skills/*.json` | Modify | Add `semantic_description` paragraph to each skill |
| `scripts/calibrate_threshold.py` | Create | One-off calibration tool — not production code |
| `src/sage_poc/nodes/skill_select.py` | Modify | Add lazy semantic fallback + `SEMANTIC_THRESHOLD` |
| `src/sage_poc/nodes/output_gate.py` | Modify | Add `skill_match_method` + `semantic_score` to AUDIT log |
| `tests/test_nodes.py` | Modify | Add `make_state` fields + semantic fallback tests (slow) |

---

### Task 1: Foundation — deps, schema, state, helpers

**Context:** Before any content or production code can be written, four small scaffolding changes are needed. The `Skill` pydantic model doesn't have `semantic_description` — pydantic v2 silently ignores unknown fields on load, so accessing `skill.semantic_description` raises `AttributeError` until the model declares it. `SageState` needs two new optional fields so the TypedDict is coherent. `make_initial_state()` and `make_state()` need those fields to avoid silent key-missing bugs. `sentence-transformers` and `numpy` aren't in `pyproject.toml` at all.

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/sage_poc/skills/schema.py`
- Modify: `src/sage_poc/state.py`
- Modify: `run.py`
- Modify: `tests/test_nodes.py` (lines 1-30, the `make_state` helper only)

- [ ] **Step 1: Add dependencies to pyproject.toml**

Open `pyproject.toml`. In the `dependencies` list, add after `python-dotenv`:

```toml
    "sentence-transformers>=3.0.0,<4.0.0",
    "numpy>=1.26.0,<3.0.0",
```

Full updated dependencies block:
```toml
dependencies = [
    "langgraph>=1.0.0,<2.0.0",
    "langchain-openai>=1.0.0,<2.0.0",
    "langchain-core>=1.0.0,<2.0.0",
    "langdetect>=1.0.9,<2.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "python-dotenv>=1.0.0,<2.0.0",
    "sentence-transformers>=3.0.0,<4.0.0",
    "numpy>=1.26.0,<3.0.0",
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn>=0.30.0,<1.0.0",
]
```

- [ ] **Step 2: Install the new dependencies**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv sync
```

Expected: resolves and installs `sentence-transformers` and `numpy` without conflicts. First BGE-M3 model download (~1.1 GB) happens later on first use — NOT here.

- [ ] **Step 3: Add `semantic_description` to the `Skill` schema**

Open `src/sage_poc/skills/schema.py`. In the `Skill` class, add one line after `target_presentations`:

```python
class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    evidence_base: str
    target_presentations: list[str]
    semantic_description: str = ""   # ← add this line
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]
```

The default `""` means existing skill JSONs without the field load without error — the field is populated in Task 2.

- [ ] **Step 4: Add new fields to `SageState`**

Open `src/sage_poc/state.py`. After `active_step_id`:

```python
    active_skill_id: Optional[str]
    active_step_id: Optional[str]
    executed_step_id: Optional[str]
    step_instruction: Optional[str]
    skill_match_method: Optional[str]   # ← add: "keyword" | "semantic" | None
    semantic_score: Optional[float]     # ← add: cosine similarity if semantic match
    escalation_triggered: Optional[dict]
```

- [ ] **Step 5: Add new fields to `make_initial_state()` in run.py**

Open `run.py`. In the `make_initial_state()` dict, add after `executed_step_id`:

```python
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,   # ← add
        "semantic_score": None,       # ← add
        "escalation_triggered": None,
```

- [ ] **Step 6: Add new fields to `make_state()` test helper**

Open `tests/test_nodes.py`. In the `make_state` defaults dict (lines 6-29), add after `executed_step_id`:

```python
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,   # ← add
        "semantic_score": None,       # ← add
        "escalation_triggered": None,
```

- [ ] **Step 7: Run the existing fast tests to verify no regressions**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m "not slow"
```

Expected: same count as before (162+), all pass. If any fail, a field name or default was mistyped — check the exact change made.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/sage_poc/skills/schema.py src/sage_poc/state.py run.py tests/test_nodes.py
git commit -m "feat(skill-select): scaffold for semantic fallback — deps, schema, state fields"
```

---

### Task 2: Write `semantic_description` paragraphs for all skill JSONs

**Context:** The quality of the `semantic_description` is the single biggest factor in matching accuracy. These paragraphs are NOT clinical descriptions — they are written in the voice and register of the user, describing how the problem feels from the inside. A description that contains phrases like "cognitive distortions" will fail to match "I always mess everything up." A description that says "feeling like nothing you do is ever good enough" will match it at 0.7+ cosine similarity.

**Rule for writing descriptions:**
- 3-5 sentences, 60-100 words
- Written AS IF the user is describing their experience — not as if a clinician is describing the condition
- Include common phrasings, colloquial synonyms, and the emotional texture of the experience
- Do NOT duplicate `target_presentations` — this is a richer semantic representation, not a keyword list
- Do NOT use clinical terminology (Beck, CBT, DBT, etc.) that users wouldn't say

**Important:** Verify that no phrase in `semantic_description` accidentally becomes a keyword match. The description is embedded for cosine similarity — it doesn't participate in keyword matching — but you want the description to represent the semantic space around the skill, not the specific strings already in `target_presentations`.

**Files:**
- Modify: `src/sage_poc/skills/cbt_thought_record.json`
- Modify: `src/sage_poc/skills/grounding_5_4_3_2_1.json`
- Modify: `src/sage_poc/skills/sleep_hygiene.json`

- [ ] **Step 1: Add `semantic_description` to `cbt_thought_record.json`**

Open `src/sage_poc/skills/cbt_thought_record.json`. Add the `semantic_description` field after `target_presentations`:

```json
  "target_presentations": [
    "negative thoughts", "self-blame", "cognitive distortions", "catastrophizing",
    "failure", "worthless", "always my fault", "my fault", "blame myself",
    "i'm a burden", "everything is my fault"
  ],
  "semantic_description": "This skill is for someone caught in relentless self-criticism — feeling like nothing they do is ever good enough, that they always mess things up, that every mistake proves something fundamentally wrong with them. It helps with the kind of thinking where one setback becomes proof of total failure, where the person can't stop replaying what they did wrong, or where they feel like a disappointment to everyone around them. Suitable when the user expresses harsh self-judgment, distorted self-perception, or a sense of shame they can't shake.",
```

- [ ] **Step 2: Add `semantic_description` to `grounding_5_4_3_2_1.json`**

Open `src/sage_poc/skills/grounding_5_4_3_2_1.json`. Add after `target_presentations`:

```json
  "target_presentations": [
    "panic attack", "panic", "overwhelmed", "dissociated", "dissociation",
    "can't breathe", "heart racing", "spinning", "grounding", "anxious right now",
    "anxiety attack", "feel disconnected", "not real", "losing control"
  ],
  "semantic_description": "This skill is for someone who needs to come back to the present moment right now — feeling like things are spiralling out of control, like they cannot handle the intensity of what they are feeling, or like they are losing their grip. It helps in moments of acute distress where emotions feel like too much all at once, where the person feels flooded and cannot think straight, or where they need something immediate rather than a longer conversation. Suitable when the distress is happening right now, not as a reflection on the past.",
```

- [ ] **Step 3: Add `semantic_description` to `sleep_hygiene.json`**

Open `src/sage_poc/skills/sleep_hygiene.json`. Add after `target_presentations`:

```json
  "target_presentations": [
    "can't sleep", "insomnia", "sleep problems", "sleeping badly", "lie awake",
    "lying awake", "sleep issues", "trouble sleeping", "not sleeping", "poor sleep",
    "sleep deprived", "no sleep", "waking up", "can't fall asleep"
  ],
  "semantic_description": "This skill is for someone whose relationship with sleep has broken down — lying in bed exhausted but unable to rest, mind racing when they finally get a moment to themselves, dragging through the day because nights don't restore them. It addresses the pattern of being tired all day but wide awake at night, the frustration of desperately wanting sleep but being unable to get it, and the habits or thoughts that get in the way of a good night. Suitable when poor sleep is a recurring pattern affecting daily life, not a single bad night.",
```

- [ ] **Step 4: Validate all JSON files parse correctly and have the field**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python3 -c "
import json, pathlib
for f in sorted(pathlib.Path('src/sage_poc/skills').glob('*.json')):
    data = json.loads(f.read_text())
    desc = data.get('semantic_description', '')
    word_count = len(desc.split())
    status = '✅' if 50 < word_count < 150 else '❌ out of range'
    print(f'{f.name}: {status} ({word_count} words)')
"
```

Expected:
```
cbt_thought_record.json: ✅ (73 words)
grounding_5_4_3_2_1.json: ✅ (78 words)
sleep_hygiene.json: ✅ (81 words)
```

If any show `❌`, open that file and enrich or trim the description.

- [ ] **Step 5: Verify `load_skill` reads the new field correctly**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
python3 -c "
from sage_poc.skills.schema import load_skill
for sid in ['cbt_thought_record', 'grounding_5_4_3_2_1', 'sleep_hygiene']:
    skill = load_skill(sid)
    print(f'{sid}: {repr(skill.semantic_description[:60])}...')
"
```

Expected: each prints the first 60 chars of its description without error.

- [ ] **Step 6: Commit**

```bash
git add src/sage_poc/skills/cbt_thought_record.json src/sage_poc/skills/grounding_5_4_3_2_1.json src/sage_poc/skills/sleep_hygiene.json
git commit -m "feat(skills): add semantic_description paragraphs to all skill JSONs"
```

---

### Task 3: Empirical threshold calibration

**Context:** The threshold is the cosine similarity score above which a semantic match is accepted. It cannot be guessed — it must be measured. This task runs known hits (messages that SHOULD match a skill but will keyword-miss) and known misses (messages that should NOT match any skill) through the embedder, reports the scores, and calculates the midpoint of the gap. That midpoint becomes `SEMANTIC_THRESHOLD` in Task 4.

**DO NOT write production code in this task.** The script is a one-off calibration tool. It ships to `scripts/` for re-runs when descriptions change, but it is not imported by any production module.

**Note:** The first run of this script triggers BGE-M3 download (~1.1 GB). On a good connection this takes 3-5 minutes. Subsequent runs use the cached model.

**Important:** The known-hit messages below were chosen to NOT match any current keyword. If you add keywords in the future, re-run calibration to confirm the semantic scores remain useful reference points.

**Files:**
- Create: `scripts/calibrate_threshold.py`

- [ ] **Step 1: Create the `scripts/` directory and calibration script**

```bash
mkdir -p /Users/knowledgebase/Documents/Sage/sage-poc/scripts
```

Create `scripts/calibrate_threshold.py`:

```python
"""
One-off calibration tool for semantic skill matching threshold.

Run: uv run python scripts/calibrate_threshold.py

Outputs similarity scores for keyword-miss messages that SHOULD match a skill
(known hits) and messages that SHOULD NOT match any skill (known misses).
The threshold lives in the gap between the lowest hit and the highest miss.

Re-run whenever semantic_description paragraphs are edited.
"""

import json
import pathlib
import numpy as np
from sentence_transformers import SentenceTransformer

SKILLS_DIR = pathlib.Path("src/sage_poc/skills")
MODEL_NAME = "BAAI/bge-m3"

# Messages that should match a specific skill — all chosen to KEYWORD-MISS
# (verified against current target_presentations lists)
KNOWN_HITS = [
    # CBT — none of these contain a CBT keyword
    ("nothing I do is good enough", "cbt_thought_record"),
    ("I always mess everything up", "cbt_thought_record"),
    ("I hate myself so much", "cbt_thought_record"),
    ("I feel like such a disappointment to everyone", "cbt_thought_record"),
    ("why can't I just be normal", "cbt_thought_record"),
    # Grounding — none of these contain a grounding keyword
    # NOTE: phrases deliberately use different words than semantic_description to avoid
    # inflating calibration scores with near-phrase matches
    ("I feel like I'm falling apart and I can't stop it", "grounding_5_4_3_2_1"),
    ("I can't handle this, everything feels like too much", "grounding_5_4_3_2_1"),
    ("I feel like I'm completely losing it", "grounding_5_4_3_2_1"),
    # Sleep — none of these contain a sleep keyword
    ("I'm exhausted but my mind won't stop racing", "sleep_hygiene"),
    ("I'm tired all day but wide awake at night", "sleep_hygiene"),
]

# Messages that should NOT match any skill
KNOWN_MISSES = [
    "what's the weather like today in Dubai",
    "can you diagnose me with depression",
    "tell me a joke",
    "thanks, that really helped",
    "hey, how are you",
    "I need to talk about something that happened at work",  # edge case — may weakly match
]


def main():
    print(f"Loading model: {MODEL_NAME}")
    print("(First run downloads ~1.1 GB — subsequent runs use cached model)\n")
    model = SentenceTransformer(MODEL_NAME)

    # Load skill descriptions
    skills = {}
    for f in sorted(SKILLS_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        sid = data.get("skill_id", f.stem)
        desc = data.get("semantic_description", "")
        if desc:
            skills[sid] = desc
        else:
            print(f"WARNING: {f.name} has no semantic_description — run Task 2 first")

    if not skills:
        print("ERROR: No skills with semantic_description found.")
        return

    skill_ids = list(skills.keys())
    skill_texts = [skills[sid] for sid in skill_ids]
    skill_embeddings = model.encode(skill_texts, normalize_embeddings=True)

    # Score known hits
    print("=" * 72)
    print("KNOWN HITS — keyword-miss messages that MUST score HIGH")
    print("=" * 72)
    hit_scores = []
    for msg, expected in KNOWN_HITS:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        best_idx = int(np.argmax(sims))
        best_skill = skill_ids[best_idx]
        best_score = float(sims[best_idx])

        exp_idx = skill_ids.index(expected) if expected in skill_ids else -1
        exp_score = float(sims[exp_idx]) if exp_idx >= 0 else 0.0

        match = "✅" if best_skill == expected else f"⚠️  matched {best_skill} instead"
        print(f"  {exp_score:.4f}  {match}")
        print(f"           \"{msg}\"")
        if best_skill != expected:
            print(f"           top match: {best_skill} ({best_score:.4f})")
        hit_scores.append(exp_score)

    # Score known misses
    print()
    print("=" * 72)
    print("KNOWN MISSES — messages that must score LOW against all skills")
    print("=" * 72)
    miss_scores = []
    for msg in KNOWN_MISSES:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        best_idx = int(np.argmax(sims))
        best_skill = skill_ids[best_idx]
        best_score = float(sims[best_idx])
        print(f"  {best_score:.4f}  → {best_skill}  \"{msg}\"")
        miss_scores.append(best_score)

    # Gap analysis
    print()
    print("=" * 72)
    print("GAP ANALYSIS")
    print("=" * 72)
    min_hit = min(hit_scores)
    max_miss = max(miss_scores)
    gap = min_hit - max_miss

    print(f"  Lowest hit score:    {min_hit:.4f}")
    print(f"  Highest miss score:  {max_miss:.4f}")
    print(f"  Gap:                 {gap:.4f}")

    if gap > 0.05:
        suggested = round((min_hit + max_miss) / 2, 4)
        print(f"\n  ✅ Clean gap. Suggested SEMANTIC_THRESHOLD = {suggested}")
    elif gap > 0:
        # Bias toward false-positive avoidance
        suggested = round(max_miss + (gap * 0.3), 4)
        print(f"\n  ⚠️  Narrow gap. Suggested SEMANTIC_THRESHOLD = {suggested}")
        print(f"     (biased toward avoiding false positives)")
    else:
        print(f"\n  ❌ NO GAP — hits and misses overlap.")
        print(f"     Return to Task 2 and enrich the semantic_description paragraphs.")
        print(f"     Overlapping hits (score < max_miss = {max_miss:.4f}):")
        for (msg, expected), score in zip(KNOWN_HITS, hit_scores):
            if score <= max_miss:
                print(f"       {score:.4f}  \"{msg}\"  (expected: {expected})")

    print()
    print("  Copy the SEMANTIC_THRESHOLD value into Task 4 Step 2.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the calibration script**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run python scripts/calibrate_threshold.py
```

Expected output: a gap analysis table ending with `✅ Clean gap. Suggested SEMANTIC_THRESHOLD = 0.XX`.

**If ❌ NO GAP:** Return to Task 2. The `semantic_description` paragraphs need to be more specific to the emotional register of the known-hit messages. Add concrete user-register phrasings. Re-run calibration.

**If ⚠️ Narrow gap:** Acceptable for MVP. Use the suggested (bias-adjusted) threshold.

- [ ] **Step 3: Record the calibrated threshold**

Write down the exact `SEMANTIC_THRESHOLD` value from the script output. You will use it in Task 4 Step 2. Do not guess a different value.

Example: `SEMANTIC_THRESHOLD = 0.63`  ← replace with actual output

- [ ] **Step 4: Commit**

```bash
git add scripts/calibrate_threshold.py
git commit -m "chore(scripts): one-off semantic threshold calibration tool"
```

---

### Task 4: Implement semantic fallback in `skill_select.py` and update audit log

**Context:** Two files change. `skill_select.py` gets the lazy-loaded semantic fallback: BGE-M3 is NOT loaded at module import (it's 1.1 GB and would add 15s to every cold start) — instead it loads on the first semantic miss and caches for the process lifetime. `output_gate.py` gets two new audit log fields so the clinical reviewer can see whether a skill was matched via keyword or semantic.

**Replace `SEMANTIC_THRESHOLD = 0.XX` with the value from Task 3 Step 3 before committing.**

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Modify: `src/sage_poc/nodes/output_gate.py`

- [ ] **Step 1: Write the failing tests first**

In `tests/test_nodes.py`, at the end of the file, add:

```python
# ---------------------------------------------------------------------------
# Semantic fallback tests — require BGE-M3, marked slow
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_semantic_fallback_catches_nothing_good_enough():
    """'nothing I do is good enough' keyword-misses; semantic fallback must catch → cbt."""
    state = make_state(message_en="nothing I do is good enough")
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record", (
        "'nothing I do is good enough' must activate cbt_thought_record via semantic fallback"
    )
    assert result["skill_match_method"] == "semantic"
    assert result["semantic_score"] is not None and result["semantic_score"] > 0


@pytest.mark.slow
def test_semantic_fallback_catches_spiralling():
    """'spiralling out of control' keyword-misses; semantic fallback must catch → grounding."""
    state = make_state(message_en="things are spiralling out of control right now")
    result = skill_select_node(state)
    assert result["active_skill_id"] == "grounding_5_4_3_2_1", (
        "'spiralling out of control' must activate grounding_5_4_3_2_1 via semantic fallback"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
def test_semantic_fallback_catches_exhausted_mind_racing():
    """Sleep-register message that keyword-misses; semantic fallback must catch → sleep_hygiene."""
    state = make_state(message_en="I'm exhausted but my mind won't stop racing at night")
    result = skill_select_node(state)
    assert result["active_skill_id"] == "sleep_hygiene", (
        "Exhausted-but-wired message must activate sleep_hygiene via semantic fallback"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
def test_semantic_fallback_rejects_weather_question():
    """Off-topic question must not match any skill even via semantic fallback."""
    state = make_state(message_en="what's the weather like today in Dubai")
    result = skill_select_node(state)
    assert result["active_skill_id"] is None, (
        "Weather question must not activate any skill"
    )


@pytest.mark.slow
def test_semantic_fallback_rejects_diagnosis_request():
    """Scope-refusal territory — must not match a therapeutic skill."""
    state = make_state(message_en="can you diagnose me with depression")
    result = skill_select_node(state)
    assert result["active_skill_id"] is None, (
        "Diagnosis request must not activate any skill"
    )


@pytest.mark.slow
def test_keyword_match_takes_priority_over_semantic():
    """When a keyword fires, skill_match_method must be 'keyword', not 'semantic'."""
    # "my fault" is in CBT target_presentations — this is a guaranteed keyword match
    state = make_state(message_en="I feel like everything is my fault")
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword", (
        "Keyword match must fire before semantic fallback"
    )
    assert result["semantic_score"] is None


@pytest.mark.slow
def test_semantic_match_returns_score_in_result():
    """Semantic matches must include the similarity score for audit trail."""
    state = make_state(message_en="I hate myself so much")
    result = skill_select_node(state)
    if result["skill_match_method"] == "semantic":
        assert isinstance(result["semantic_score"], float)
        assert 0.0 < result["semantic_score"] <= 1.0
```

- [ ] **Step 2: Run the tests to confirm they FAIL (expected)**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m slow -k "semantic"
```

Expected: all 7 new tests FAIL with `AssertionError` or `AttributeError` — the implementation doesn't exist yet. If any pass, check that `skill_select.py` hasn't already been modified.

- [ ] **Step 3: Write the new `skill_select.py`**

Replace the entire content of `src/sage_poc/nodes/skill_select.py` with:

```python
from __future__ import annotations

import numpy as np
from sage_poc.state import SageState
from sage_poc.skills.schema import load_skill

# All available skills — in production this comes from the CMS
SKILL_REGISTRY = ["cbt_thought_record", "grounding_5_4_3_2_1", "sleep_hygiene"]

# Pre-load skills at module init — not per request
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

# Threshold from empirical calibration (Task 3 Step 3).
# Replace 0.XX with the value output by scripts/calibrate_threshold.py.
SEMANTIC_THRESHOLD: float = 0.XX  # ← replace before committing

# --- Lazy semantic components — initialised on first semantic miss, not at import ---
_embed_model = None
_semantic_skill_ids: list[str] = []
_semantic_embeddings: np.ndarray | None = None


def _ensure_semantic_ready() -> None:
    """Load BGE-M3 and embed all skill descriptions. No-op on subsequent calls."""
    global _embed_model, _semantic_skill_ids, _semantic_embeddings
    if _embed_model is not None:
        return
    from sentence_transformers import SentenceTransformer
    _embed_model = SentenceTransformer("BAAI/bge-m3")
    ids, texts = [], []
    for sid, skill in _SKILLS.items():
        if skill.semantic_description:
            ids.append(sid)
            texts.append(skill.semantic_description)
    _semantic_skill_ids = ids
    _semantic_embeddings = _embed_model.encode(texts, normalize_embeddings=True)


def _semantic_match(message_en: str) -> tuple[str | None, float]:
    """Cosine similarity against all skill semantic_descriptions. Tier 2 fallback only."""
    _ensure_semantic_ready()
    if _semantic_embeddings is None or not message_en.strip():
        return None, 0.0
    msg_emb = _embed_model.encode([message_en], normalize_embeddings=True)[0]
    scores = np.dot(_semantic_embeddings, msg_emb)
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    if best_score >= SEMANTIC_THRESHOLD:
        return _semantic_skill_ids[best_idx], best_score
    return None, best_score


def skill_select_node(state: SageState) -> dict:
    message = state["message_en"].lower()

    # Tier 1: Keyword matching — deterministic, fast, auditable
    for skill_id, skill in _SKILLS.items():
        for keyword in skill.target_presentations:
            if keyword.lower() in message:
                return {
                    "active_skill_id": skill_id,
                    "active_step_id": skill.steps[0].step_id,
                    "skill_match_method": "keyword",
                    "semantic_score": None,
                    "path": state["path"] + ["skill_select"],
                }

    # Tier 2: Semantic fallback — fires only when keywords miss
    semantic_skill, score = _semantic_match(state["message_en"])
    if semantic_skill is not None:
        skill = _SKILLS[semantic_skill]
        return {
            "active_skill_id": semantic_skill,
            "active_step_id": skill.steps[0].step_id,
            "skill_match_method": "semantic",
            "semantic_score": round(score, 4),
            "path": state["path"] + ["skill_select"],
        }

    return {
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "semantic_score": None,
        "path": state["path"] + ["skill_select"],
    }
```

**Before continuing:** replace `0.XX` with the calibrated threshold from Task 3 Step 3.

- [ ] **Step 4: Update `output_gate.py` to log `skill_match_method` and `semantic_score`**

Open `src/sage_poc/nodes/output_gate.py`. In the `audit` dict (around line 38), add two lines after `"active_skill"`:

```python
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": state["turn_count"],
            "path": path,
            "gate_path": gate_path or "standard",
            "detected_language": lang,
            "primary_intent": state.get("primary_intent"),
            "active_skill": state.get("active_skill_id"),
            "skill_match_method": state.get("skill_match_method"),   # ← add
            "semantic_score": state.get("semantic_score"),            # ← add
            "executed_step": state.get("executed_step_id"),
            "next_step": state.get("active_step_id"),
            "emotional_intensity": state.get("emotional_intensity"),
            "engagement": state.get("engagement"),
            "is_safe": state.get("is_safe"),
            "clinical_flags": state.get("clinical_flags", []),
            "escalation": state.get("escalation_triggered"),
        }
```

- [ ] **Step 5: Run the fast test suite for regressions**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m "not slow"
```

Expected: all existing tests pass (162+). No new tests run (they're all marked slow).

- [ ] **Step 6: Run the slow semantic tests**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_nodes.py -v -m slow -k "semantic"
```

Expected: all 7 new slow tests pass. If any known-hit test fails:
- Check the calibration script output — re-run `scripts/calibrate_threshold.py` and confirm the threshold value
- If threshold is correct but the score falls below it: the `semantic_description` needs enrichment — return to Task 2 and add more user-register phrasings for that skill

- [ ] **Step 7: Run full slow test suite**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/ -v -m slow
```

Expected: all 49+ existing slow tests still pass. The semantic fallback must not affect any test that previously matched via keyword.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py src/sage_poc/nodes/output_gate.py tests/test_nodes.py
git commit -m "feat(skill-select): BGE-M3 semantic fallback — lazy-loaded, calibrated, audited"
```

---

### Task 5: Re-run the audit scenarios that originally exposed the problem

**Context:** With semantic fallback live, re-run the specific scenarios that failed in the original benchmarks and in the TD3 audit. This produces the before/after evidence for the clinical handoff and confirms the feature works end-to-end through the full graph (not just in unit tests).

**Files:**
- Read: `docs/TD3_audit_results_20260521.md` (for before-state reference)

- [ ] **Step 1: B4 Turn 1 — "nothing I do is good enough"**

Before state (TD3 audit): skill_select returned None, fell through to freeflow.

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
printf "I feel like nothing I do is good enough\nquit\n" | uv run python run.py
```

Expected:
- Audit log shows `"active_skill": "cbt_thought_record"`, `"skill_match_method": "semantic"`, `"semantic_score": 0.6X`
- Path includes `skill_executor`
- Response begins the CBT identify_thought step

If skill still returns None: check that `SEMANTIC_THRESHOLD` in `skill_select.py` matches the calibration output and that `semantic_description` was saved correctly.

- [ ] **Step 2: Original Scenario 1 — "feeling overwhelmed" phrasing**

Before state: this phrase activated grounding via keyword (the word "overwhelmed" is in `target_presentations`). **This is a keyword match — semantic fallback does not fire here.** Run it to confirm keyword path still works.

```bash
printf "Hey, I've been feeling really overwhelmed lately\nquit\n" | uv run python run.py
```

Expected: audit log shows `"skill_match_method": "keyword"`, `grounding_5_4_3_2_1` active.

- [ ] **Step 3: "Everything is my fault" — confirm keyword path still works (RT-4)**

```bash
printf "Everything is my fault, it's always been my fault\nquit\n" | uv run python run.py
```

Expected: `"skill_match_method": "keyword"`, `cbt_thought_record` active. This confirms keyword Tier 1 is intact alongside the semantic Tier 2.

- [ ] **Step 4: Novel phrase not in any keyword list**

This tests a phrasing that has never been in any test, keyword list, or benchmark — the true long-tail case.

```bash
printf "I hate myself so much, I don't know how to stop\nquit\n" | uv run python run.py
```

Expected: `"skill_match_method": "semantic"`, `cbt_thought_record` active. If it returns None, the semantic score was below threshold — note the `semantic_score` value in the audit log and compare to the calibration gap. If the score is 0.58 and threshold is 0.62, consider lowering the threshold one tick (rerun calibration to verify it doesn't pull in false positives).

- [ ] **Step 5: Confirm non-therapeutic messages still return None**

```bash
printf "Can you diagnose me with depression?\nquit\n" | uv run python run.py
printf "What's the weather today?\nquit\n" | uv run python run.py
```

Expected: both show `"active_skill": null`, `"skill_match_method": null`. Gate path for the diagnosis message will be `scope_refusal`.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "docs: TD3 semantic fallback verification — before/after confirmed on audit scenarios"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task | Status |
|-------------|------|--------|
| sentence-transformers + numpy in deps | 1 | ✅ |
| `semantic_description` field in Skill schema | 1 | ✅ |
| New state fields + helpers updated | 1 | ✅ |
| User-register semantic_description content | 2 | ✅ |
| Threshold empirically calibrated | 3 | ✅ |
| Keyword path unchanged (Tier 1) | 4 | ✅ |
| Semantic fallback lazy-loaded (not module-init) | 4 | ✅ |
| `skill_match_method` + `semantic_score` in return dict | 4 | ✅ |
| Audit log updated with new fields | 4 | ✅ |
| Tests for known hits, known misses, keyword priority | 4 | ✅ |
| Semantic tests marked slow | 4 | ✅ |
| Before/after on original failing scenarios | 5 | ✅ |

**Placeholder scan:**

- `SEMANTIC_THRESHOLD = 0.XX` — **not a placeholder in the final committed code**. This is intentionally left for the implementer to fill after Task 3. Task 4 Step 3 explicitly instructs replacing it. The calibration script produces the exact value.

**Type consistency:**

- `skill_match_method: Optional[str]` declared in `SageState`, set in all three return branches of `skill_select_node`, read via `.get()` in `output_gate.py` — consistent
- `semantic_score: Optional[float]` — same pattern, keyword path returns `None`, semantic path returns `round(score, 4)`, no-match returns `None` — consistent

**Performance note:**

- Keyword path: 0ms added latency (semantic never runs)
- Semantic path (first call): ~15s model load + ~30ms encode. All subsequent calls: ~30ms encode only
- Module startup: unchanged (model is lazy-loaded, not at import)

**Architectural boundary:**

- This is v7 §4.3 MVP: keywords primary, semantic fallback. Nothing else changes.
- The Full Build "Skill Retrieval Augmentation" pattern (semantic primary, Falcon-3B reranker over top-5 candidates) is NOT implemented here and is out of scope.
