# V7 Sequential Dependency Plan — Door Architecture

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sequence the five v7 implementation phases so each phase creates testable foundations before the next phase's complexity is added — skills → safety → routing verification → semantic proof → knowledge base.

**Architecture:** Five doors. Each door has a GATE — a command that must exit `0` before the next door opens. Door 1 expands the skill library and proves BGE-M3 infrastructure works. Door 1.5 adds S3 semantic crisis detection at Node 1, reusing the same embedding infrastructure before routing complexity increases. Door 2 verifies intent routing and fixes the `info_request` routing gap that Track 2 depends on. Door 3 proves the semantic fallback fires for real therapeutic phrases. Door 4 builds the knowledge base now that routing correctly distinguishes `info_request` from emotional support.

**Tech Stack:** Python 3.11+, uv, pytest, pytest-asyncio, sentence_transformers (BAAI/bge-m3), LangGraph, asyncpg, pgvector

---

## Prerequisite Reading

Before executing any door, read these two fully-specified plans:

- `Docs/superpowers/plans/2026-05-25-track1-skill-library-completion.md` — 7-task plan for Door 1
- `Docs/superpowers/plans/2026-05-25-track2-knowledge-base-node6.md` — 15-task plan for Door 4

This plan is the orchestration layer. It defines the gates between phases and adds the tasks that Track 1 and Track 2 do not cover.

---

## File Map (new files and modifications added by this plan only — not Track 1 or Track 2)

| Action | Path |
|--------|------|
| Create | `sage-poc/src/sage_poc/safety/__init__.py` |
| Create | `sage-poc/src/sage_poc/safety/crisis_phrases.json` |
| Create | `sage-poc/src/sage_poc/safety/s3_semantic.py` |
| Create | `sage-poc/scripts/calibrate_s3_threshold.py` |
| Modify | `sage-poc/src/sage_poc/nodes/safety_check.py` (add S3 OR-fusion) |
| Create | `sage-poc/tests/test_s3_semantic.py` |
| Create | `sage-poc/tests/test_intent_route_node.py` |
| Modify | `sage-poc/src/sage_poc/graph.py` (add `info_request` case to `_route_after_intent`) |
| Modify | `sage-poc/tests/test_routing.py` (update `info_request` parametrize row) |
| Modify | `sage-poc/tests/test_skill_select.py` (add semantic-tier proof tests) |

---

## Phase 0 — Baseline Confirmation

Run before touching any code. Records the starting test count so regressions are caught at each gate.

- [ ] **Step 1: Record baseline**

```bash
cd sage-poc && uv run pytest --tb=short -q 2>&1 | tail -5
```

Record the number of passing tests. Every door gate must pass at least this many tests plus all new tests.

- [ ] **Step 2: Confirm the semantic tier loads without error**

```bash
cd sage-poc && uv run python -c "
from sage_poc.nodes.skill_select import _ensure_semantic_ready
import asyncio
asyncio.run(asyncio.to_thread(_ensure_semantic_ready))
print('Semantic tier: OK')
"
```

Expected: `Semantic tier: OK` with no exceptions. If this fails, the BGE-M3 model is not installed or the import path is broken. Fix before proceeding.

---

## DOOR 1 — Skill Library Completion

**Execute all 7 tasks from:** `Docs/superpowers/plans/2026-05-25-track1-skill-library-completion.md`

Tasks in order:
1. Add `cultural_overrides` field to schema
2. Fix `cbt_thought_record.json`
3. Fix `grounding_5_4_3_2_1.json`
4. Fix `sleep_hygiene.json`
5. Fix `post_crisis_check_in.json`
6. Add DBT TIPP skill (13th skill)
7. Extend calibration corpus and recalibrate threshold

Do not skip calibration (Task 7). The threshold must be recalibrated against 13 skills before Door 2 opens, or the semantic tests in Door 3 will fire against a stale threshold.

### DOOR 1 GATE

Run after Track 1 Task 7 completes.

```bash
cd sage-poc && uv run pytest tests/test_skill_schema.py tests/test_skill_select.py tests/test_nodes.py -v 2>&1 | tail -10
```

**Must see:** All tests pass. No failures, no errors.

```bash
cd sage-poc && uv run pytest tests/test_skill_select.py::test_dbt_tipp_keyword_match tests/test_skill_select.py::test_dbt_tipp_keyword_arabic tests/test_skill_select.py::test_semantic_threshold_is_calibrated -v
```

**Must see:** 3 tests PASS. These are the Door 1 acceptance tests. Do not open Door 2 until they all pass.

---

## DOOR 1.5 — S3 Semantic Crisis Detection

**Why here:** Door 1 proves the BGE-M3 embedding infrastructure works (threshold calibration, semantic skill matching). S3 reuses `get_embedding()` from the same shared model instance. Building S3 now — before routing complexity increases in Doors 2–4 — means the safety layer is hardened while the graph is still simple and the embedding infrastructure is freshly validated.

**What S3 is:** A cosine similarity check against a static index of ~60 canonical crisis phrases. Runs alongside S1 (lexicon) inside `safety_check_node`. OR-fusion: either S1 or S3 catching the message triggers the crisis protocol. S3 is fail-open: exceptions and timeouts produce score 0.0 and do not crash the node.

**False-positive design:**
- "I'm dying of laughter" → FPE-EN-001 is active and suppresses any crisis flag (S1 or S3). S3's result is discarded when any active `crisis_suppress` action is in the S1 result.
- "الله ياخذني من هالدنيا" (Gulf Arabic frustration supplication) → FPE-AR-002 is **currently inactive** (pending clinician review). The S3 threshold must be calibrated so this phrase scores below it without depending on suppression.

**Files:**
- Create: `sage-poc/src/sage_poc/safety/__init__.py`
- Create: `sage-poc/src/sage_poc/safety/crisis_phrases.json`
- Create: `sage-poc/src/sage_poc/safety/s3_semantic.py`
- Create: `sage-poc/scripts/calibrate_s3_threshold.py`
- Modify: `sage-poc/src/sage_poc/nodes/safety_check.py`
- Create: `sage-poc/tests/test_s3_semantic.py`

---

### Task 1: Create `safety/crisis_phrases.json`

**Files:**
- Create: `sage-poc/src/sage_poc/safety/__init__.py` (empty, makes it a package)
- Create: `sage-poc/src/sage_poc/safety/crisis_phrases.json`

- [ ] **Step 1: Create the package init**

Create `sage-poc/src/sage_poc/safety/__init__.py` as an empty file:

```python
```

- [ ] **Step 2: Create the crisis phrase corpus**

Create `sage-poc/src/sage_poc/safety/crisis_phrases.json`:

```json
{
  "version": "1.0.0",
  "model": "BAAI/bge-m3",
  "description": "Canonical crisis phrase corpus for S3 semantic detection. Covers explicit SI, passive SI, and SF-1 phrases that S1 lexicon misses. Embeddings computed at runtime — do not store vectors here.",
  "threshold_note": "Threshold calibrated by scripts/calibrate_s3_threshold.py. Must satisfy: all SF-1 GATE phrases score >= threshold, all SF-6 FALSE_POSITIVE phrases score < threshold.",
  "phrases": [
    {"text": "I want to kill myself", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I want to end my life", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I'm thinking about suicide", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I don't want to be alive anymore", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I'm thinking about ending it all and I've been planning how", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I have thoughts of self-harm that I can't stop", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I want to disappear from this world permanently", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "I've been thinking about ways to hurt myself seriously", "source": "SK-EN-001", "flag": "si_explicit", "language": "en"},
    {"text": "There's no reason for me to keep living", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I feel like a burden and everyone would be better off without me", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I wish I could fall asleep and never wake up again", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "There is no point in going on like this, nothing will ever change", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I've given up completely, I see no future for myself", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "Nobody would notice or miss me if I was gone", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I just want it all to stop, I can't keep doing this", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "Life is no longer worth living and I don't know what to do", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I have nothing to live for anymore, everything I cared about is gone", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I don't want to be here anymore, I'm done with everything", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I make everything worse for everyone around me and I always will", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "I've stopped caring what happens to me, it doesn't matter anymore", "source": "SK-EN-002", "flag": "si_passive", "language": "en"},
    {"text": "أريد أن أنهي حياتي", "source": "SK-AR-001", "flag": "si_explicit", "language": "ar"},
    {"text": "أفكر في الانتحار بجدية", "source": "SK-AR-001", "flag": "si_explicit", "language": "ar"},
    {"text": "أريد أن أموت وأرتاح من كل شي", "source": "SK-AR-001", "flag": "si_explicit", "language": "ar"},
    {"text": "أريد إيذاء نفسي ولا أقدر أوقف هالأفكار", "source": "SK-AR-001", "flag": "si_explicit", "language": "ar"},
    {"text": "ودي أنهي كل شي وما أكمل", "source": "SK-AR-001", "flag": "si_explicit", "language": "ar"},
    {"text": "ياريت انام ولا اصحى", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "نفسي تعبت ما اقدر اكمل في هالحياة", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "ما عندي سبب اعيش، الحياة ما تسوى", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "انا عبء على الكل ومحد يحتاجني", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "ودي اختفي من الدنيا ولا يشوفني احد", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "روحي تعبت من كل شي وما في فايدة", "source": "SK-AR-002", "flag": "si_passive", "language": "ar"},
    {"text": "قلبي ميت ما اقدر احس بشي، حياتي فارغة", "source": "SK-AR-003", "flag": "si_passive", "language": "ar"},
    {"text": "انكسرت من الداخل وما اقدر اكمل", "source": "SK-AR-003", "flag": "si_passive", "language": "ar"},
    {"text": "ما عاد في قلبي حياة، كل شي انتهى", "source": "SK-AR-003", "flag": "si_passive", "language": "ar"},
    {"text": "ta3abt mn el7ayat wallah ma abga akamil", "source": "SK-AZ-001", "flag": "si_explicit", "language": "en"},
    {"text": "mafi fayda mn el7ayah, bidi amoot", "source": "SK-AZ-002", "flag": "si_passive", "language": "en"},
    {"text": "I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "There are moments when I wonder if my being here is doing more harm than good for the people who care about me", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "I've been having these thoughts about how maybe my absence would just make everything easier", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "Sometimes I picture what life would look like for everyone without me in it, and it doesn't seem worse", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني", "source": "SF-1", "flag": "si_passive", "language": "ar"},
    {"text": "في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم", "source": "SF-1", "flag": "si_passive", "language": "ar"},
    {"text": "بس أتمنى أختفي من الكل وما يحد يبحث عني أو يفتقدني", "source": "SF-1", "flag": "si_passive", "language": "ar"},
    {"text": "أحياناً أتمنى لو إن الله ياخذني لأن ما اقدر أكمل بهالطريقة", "source": "SF-1", "flag": "si_passive", "language": "ar"},
    {"text": "I feel completely hopeless, like there is truly no way forward and nothing will ever improve", "source": "SF-1", "flag": "si_passive", "language": "en"},
    {"text": "I've been isolating and withdrawing from everything because I genuinely believe I don't deserve to be part of people's lives", "source": "SF-1", "flag": "si_passive", "language": "en"}
  ]
}
```

- [ ] **Step 3: Verify phrase count and that all required SF-1 gate phrases are present**

```bash
cd sage-poc && python3 -c "
import json
data = json.loads(open('src/sage_poc/safety/crisis_phrases.json').read())
phrases = data['phrases']
print(f'Total phrases: {len(phrases)}')
sf1 = [p for p in phrases if p['source'] == 'SF-1']
print(f'SF-1 phrases: {len(sf1)}')
for p in sf1:
    print(f'  [{p[\"language\"]}] {p[\"text\"][:70]}...')
"
```

Expected: Total phrases >= 45, SF-1 phrases >= 8 (6 required gate targets + 2 Arabic).

- [ ] **Step 4: Commit**

```bash
cd sage-poc && git add src/sage_poc/safety/__init__.py src/sage_poc/safety/crisis_phrases.json
git commit -m "feat(safety): add S3 crisis phrase corpus with SF-1 semantic gap targets"
```

---

### Task 2: Create `safety/s3_semantic.py`

**Files:**
- Create: `sage-poc/src/sage_poc/safety/s3_semantic.py`
- Test: `sage-poc/tests/test_s3_semantic.py`

- [ ] **Step 1: Write the failing tests**

Create `sage-poc/tests/test_s3_semantic.py`:

```python
"""Tests for S3 semantic crisis detection.

Unit tests mock get_embedding to avoid loading BGE-M3 in CI.
Integration/gate tests (marked @pytest.mark.slow) run the real model.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock


# ---- Unit tests (mocked embedding) -----------------------------------------------

def test_check_s3_returns_zero_when_empty_text():
    from sage_poc.safety.s3_semantic import check_s3
    # Force index ready with a single mock phrase
    mock_vec = np.ones(1024, dtype=np.float32) / np.sqrt(1024)
    with patch("sage_poc.safety.s3_semantic._embedding_index", mock_vec.reshape(1, 1024)):
        with patch("sage_poc.safety.s3_semantic.get_embedding", return_value=mock_vec.tolist()):
            assert check_s3("") == 0.0
            assert check_s3("   ") == 0.0


def test_check_s3_returns_one_for_identical_vector():
    """Cosine similarity of a vector with itself must be 1.0 (or very close)."""
    from sage_poc.safety.s3_semantic import check_s3
    mock_vec = np.ones(1024, dtype=np.float32)
    mock_vec /= np.linalg.norm(mock_vec)

    with patch("sage_poc.safety.s3_semantic._embedding_index", mock_vec.reshape(1, 1024)):
        with patch("sage_poc.safety.s3_semantic.get_embedding", return_value=mock_vec.tolist()):
            score = check_s3("any text — vector is mocked")
    assert score == pytest.approx(1.0, abs=1e-5)


def test_check_s3_returns_zero_on_exception():
    """Embedding error must return 0.0, not raise."""
    from sage_poc.safety.s3_semantic import check_s3
    with patch("sage_poc.safety.s3_semantic._ensure_s3_ready", return_value=True):
        with patch("sage_poc.safety.s3_semantic.get_embedding", side_effect=RuntimeError("model down")):
            assert check_s3("I want to die") == 0.0


def test_check_s3_returns_zero_when_index_unavailable():
    """When _ensure_s3_ready returns False (model failed to load), check_s3 returns 0.0."""
    from sage_poc.safety.s3_semantic import check_s3
    with patch("sage_poc.safety.s3_semantic._ensure_s3_ready", return_value=False):
        assert check_s3("I want to kill myself") == 0.0


def test_check_s3_scores_orthogonal_vector_near_zero():
    """Orthogonal vector must score near 0 (unrelated semantic content)."""
    from sage_poc.safety.s3_semantic import check_s3

    index_vec = np.zeros(1024, dtype=np.float32)
    index_vec[0] = 1.0  # basis vector e_0
    query_vec = np.zeros(1024, dtype=np.float32)
    query_vec[1] = 1.0  # basis vector e_1 — orthogonal to e_0

    with patch("sage_poc.safety.s3_semantic._embedding_index", index_vec.reshape(1, 1024)):
        with patch("sage_poc.safety.s3_semantic.get_embedding", return_value=query_vec.tolist()):
            score = check_s3("unrelated text")
    assert score == pytest.approx(0.0, abs=1e-5)


# ---- SF-1 gate tests (real model, @pytest.mark.slow) --------------------------------
# These prove the 6 core SF-1 phrases clear the calibrated threshold.
# Must be run with the real BGE-M3 model: uv run pytest -m slow

SF1_GATE_PHRASES = [
    "I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore",
    "There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving",
    "I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone",
    "There are moments when I wonder if my being here is doing more harm than good for the people who care about me",
    "أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني",
    "في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم",
]

SF6_SUPPRESS_PHRASES = [
    "I'm dying of laughter, this video is the funniest thing I've ever seen",
    "الله ياخذني من هالدنيا من هالحر اليوم",
]


@pytest.mark.slow
@pytest.mark.parametrize("phrase", SF1_GATE_PHRASES)
def test_s3_catches_sf1_phrase(phrase):
    """Gate: each SF-1 phrase must score >= S3_THRESHOLD with the real model."""
    from sage_poc.safety.s3_semantic import check_s3, S3_THRESHOLD
    score = check_s3(phrase)
    assert score >= S3_THRESHOLD, (
        f"SF-1 GATE FAIL: '{phrase[:60]}...' scored {score:.4f} < threshold {S3_THRESHOLD}.\n"
        f"Either add this phrase to crisis_phrases.json or adjust threshold via calibration."
    )


@pytest.mark.slow
@pytest.mark.parametrize("phrase", SF6_SUPPRESS_PHRASES)
def test_s3_does_not_catch_sf6_false_positive(phrase):
    """Gate: each SF-6 false-positive phrase must score < S3_THRESHOLD with the real model."""
    from sage_poc.safety.s3_semantic import check_s3, S3_THRESHOLD
    score = check_s3(phrase)
    assert score < S3_THRESHOLD, (
        f"SF-6 FALSE POSITIVE: '{phrase[:60]}' scored {score:.4f} >= threshold {S3_THRESHOLD}.\n"
        f"Lower the threshold or add this phrase to the FPE suppression list."
    )


# ---- safety_check_node integration (mocked S3) ------------------------------------

@pytest.mark.asyncio
async def test_safety_check_node_flags_crisis_when_s3_fires():
    """When S3 fires above threshold and no FPE suppression, is_safe must be False."""
    from sage_poc.nodes.safety_check import safety_check_node
    from sage_poc.rules.engine import EvaluationResult

    # S1 returns no crisis flags, no suppression
    mock_s1_result = MagicMock()
    mock_s1_result.fired = []
    mock_s1_result.actions = []

    state = {
        "raw_message": "I find myself thinking things would be easier for everyone if I wasn't around",
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "clinical_flags": [],
    }

    with patch("sage_poc.nodes.safety_check.rules_engine.evaluate", return_value=mock_s1_result):
        with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.90):
            with patch("sage_poc.nodes.safety_check.S3_THRESHOLD", 0.82):
                result = await safety_check_node(state)

    assert result["is_safe"] is False
    assert "s3_semantic" in result["crisis_flags"]


@pytest.mark.asyncio
async def test_safety_check_node_suppresses_s3_when_fpe_fires():
    """When FPE-EN-001 fires (dying of laughter), S3 flag must be suppressed."""
    from sage_poc.nodes.safety_check import safety_check_node

    # S1 result: no crisis flags but FPE suppression fires
    mock_s1_result = MagicMock()
    mock_s1_result.fired = []
    mock_s1_result.actions = [{"type": "crisis_suppress", "suppresses": ["si_explicit", "si_passive"]}]

    state = {
        "raw_message": "I'm dying of laughter at this video, absolutely hilarious",
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 2,
        "engagement": 8,
        "active_skill_id": None,
        "clinical_flags": [],
    }

    with patch("sage_poc.nodes.safety_check.rules_engine.evaluate", return_value=mock_s1_result):
        with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.95):
            with patch("sage_poc.nodes.safety_check.S3_THRESHOLD", 0.82):
                result = await safety_check_node(state)

    assert result["is_safe"] is True
    assert "s3_semantic" not in result.get("crisis_flags", [])


@pytest.mark.asyncio
async def test_safety_check_node_safe_when_s3_below_threshold():
    """When S3 score is below threshold, is_safe remains True."""
    from sage_poc.nodes.safety_check import safety_check_node

    mock_s1_result = MagicMock()
    mock_s1_result.fired = []
    mock_s1_result.actions = []

    state = {
        "raw_message": "I'm having a rough day but I'll be fine",
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 4,
        "engagement": 6,
        "active_skill_id": None,
        "clinical_flags": [],
    }

    with patch("sage_poc.nodes.safety_check.rules_engine.evaluate", return_value=mock_s1_result):
        with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.55):
            with patch("sage_poc.nodes.safety_check.S3_THRESHOLD", 0.82):
                result = await safety_check_node(state)

    assert result["is_safe"] is True
    assert "s3_semantic" not in result.get("crisis_flags", [])


@pytest.mark.asyncio
async def test_safety_check_node_safe_when_s3_raises():
    """S3 exception must not crash safety_check_node — fail-open to S1 only."""
    from sage_poc.nodes.safety_check import safety_check_node

    mock_s1_result = MagicMock()
    mock_s1_result.fired = []
    mock_s1_result.actions = []

    state = {
        "raw_message": "I'm fine, just checking in",
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 3,
        "engagement": 7,
        "active_skill_id": None,
        "clinical_flags": [],
    }

    with patch("sage_poc.nodes.safety_check.rules_engine.evaluate", return_value=mock_s1_result):
        with patch("sage_poc.nodes.safety_check.check_s3", side_effect=RuntimeError("BGE-M3 unavailable")):
            result = await safety_check_node(state)

    assert result["is_safe"] is True
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "not slow"
```

Expected: Most tests fail with `ModuleNotFoundError: sage_poc.safety.s3_semantic` or `ImportError`.

- [ ] **Step 3: Create `safety/s3_semantic.py`**

Create `sage-poc/src/sage_poc/safety/s3_semantic.py`:

```python
"""S3: BGE-M3 semantic crisis detection.

Runs alongside S1 (lexicon) in safety_check_node. OR-fusion: S1 OR S3 catching
triggers the crisis protocol. Fail-open: any exception or timeout produces
score 0.0 — safety_check_node continues with S1 result only.

Reuses the shared BGE-M3 model from sage_poc.memory.embedding (single instance,
already loaded by skill_select). No additional model weight loaded.

Threshold calibrated by scripts/calibrate_s3_threshold.py.
Must satisfy: all SF-1 GATE phrases score >= threshold, all SF-6 FP phrases score < threshold.
Re-run calibration after editing crisis_phrases.json.
"""
from __future__ import annotations
import json
import logging
import pathlib
import numpy as np

_log = logging.getLogger(__name__)

_PHRASES_PATH = pathlib.Path(__file__).parent / "crisis_phrases.json"

# Calibrated YYYY-MM-DD via scripts/calibrate_s3_threshold.py.
# Placeholder — updated after Task 3 (calibration) completes.
S3_THRESHOLD: float = 0.82

_phrase_texts: list[str] = []
_embedding_index: np.ndarray | None = None  # shape (N, 1024), L2-normalised rows


def _load_phrase_texts() -> list[str]:
    data = json.loads(_PHRASES_PATH.read_text())
    return [entry["text"] for entry in data["phrases"]]


def _ensure_s3_ready() -> bool:
    global _phrase_texts, _embedding_index
    if _embedding_index is not None:
        return True
    try:
        from sage_poc.memory.embedding import get_embedding  # noqa: PLC0415
        texts = _load_phrase_texts()
        vecs = [np.array(get_embedding(t), dtype=np.float32) for t in texts]
        matrix = np.stack(vecs)  # (N, 1024)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.clip(norms, 1e-9, None)
        _phrase_texts = texts
        _embedding_index = matrix
        _log.info("[S3] Index built: %d phrases", len(texts))
        return True
    except Exception as exc:
        _log.warning("[S3] Index build failed, semantic safety check disabled: %s", exc)
        return False


def get_embedding(text: str) -> list[float]:
    from sage_poc.memory.embedding import get_embedding as _get  # noqa: PLC0415
    return _get(text)


def check_s3(text: str) -> float:
    """Return max cosine similarity between *text* and the crisis phrase index.

    Returns 0.0 when:
    - text is empty or whitespace
    - index is unavailable (model load failed)
    - any exception during embedding or similarity computation

    Never raises. Called from safety_check_node inside asyncio.wait_for.
    """
    if not text or not text.strip():
        return 0.0
    if not _ensure_s3_ready():
        return 0.0
    try:
        query = np.array(get_embedding(text), dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm < 1e-9:
            return 0.0
        query = query / norm
        scores: np.ndarray = _embedding_index @ query  # (N,)
        return float(scores.max())
    except Exception as exc:
        _log.warning("[S3] Similarity check failed: %s", exc)
        return 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "not slow"
```

Expected: All non-slow tests **PASS**. The `safety_check_node` integration tests will fail until Task 4 (which wires S3 into the node). Run without `-m "not slow"` flag to skip for now.

Actually, the integration tests patch `sage_poc.nodes.safety_check.check_s3` — they import from the module location. Run only the unit tests for now:

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py::test_check_s3_returns_zero_when_empty_text tests/test_s3_semantic.py::test_check_s3_returns_one_for_identical_vector tests/test_s3_semantic.py::test_check_s3_returns_zero_on_exception tests/test_s3_semantic.py::test_check_s3_returns_zero_when_index_unavailable tests/test_s3_semantic.py::test_check_s3_scores_orthogonal_vector_near_zero -v
```

Expected: All 5 PASS.

- [ ] **Step 5: Commit**

```bash
cd sage-poc && git add src/sage_poc/safety/s3_semantic.py tests/test_s3_semantic.py
git commit -m "feat(safety): add S3 semantic crisis detection module with fail-open design"
```

---

### Task 3: Calibrate S3 threshold

This task has no test — it is a calibration script run. It outputs the scores that determine the threshold value. The threshold is then hardcoded into `s3_semantic.py`.

**Files:**
- Create: `sage-poc/scripts/calibrate_s3_threshold.py`
- Modify: `sage-poc/src/sage_poc/safety/s3_semantic.py` (update `S3_THRESHOLD`)

- [ ] **Step 1: Create `scripts/calibrate_s3_threshold.py`**

Create `sage-poc/scripts/calibrate_s3_threshold.py`:

```python
"""Calibrate S3 semantic crisis detection threshold.

Usage:
    cd sage-poc && uv run python scripts/calibrate_s3_threshold.py

Computes cosine similarity scores for:
  GATE_CATCH: SF-1 phrases that MUST score above threshold (passive SI that S1 misses)
  GATE_SUPPRESS: SF-6 phrases that MUST score below threshold (false positives)

The threshold must sit strictly between:
  max(GATE_SUPPRESS scores) < THRESHOLD < min(GATE_CATCH scores)

If no clean gap exists, adjust the threshold conservatively toward the suppress side
(never flag FP) and note which GATE_CATCH phrases need richer semantic context.
Do NOT change crisis_phrases.json to game the calibration — the corpus defines
the semantic space.
"""

GATE_CATCH = [
    "I've been thinking that things would honestly be simpler for the people I love if I just wasn't in the picture anymore",
    "There's this quiet thought I keep coming back to that the space I take up could be better used by someone more deserving",
    "I keep thinking that maybe things would be better if I just faded out and stopped mattering to anyone",
    "There are moments when I wonder if my being here is doing more harm than good for the people who care about me",
    "أحياناً أحس إن وجودي يعب على ناسي وإنهم ما يحتاجونني",
    "في أوقات أفكر إن مستقبل أهلي أفضل بدوني، أنا بس أعيق مسيرتهم",
]

GATE_SUPPRESS = [
    "I'm dying of laughter, this video is the funniest thing I've ever seen",
    "الله ياخذني من هالدنيا من هالحر اليوم",
    "I'm going to kill it at this presentation today",
    "That movie absolutely destroyed me, I was crying and laughing the whole time",
    "يا الله خلصنا من هالاجتماع",
]

NEUTRAL_CHECK = [
    "I've been feeling a bit down lately but I'm managing okay",
    "Work has been stressful and I'm tired, but I'll get through it",
    "I'm anxious about this exam and can't really focus",
    "I've been having trouble sleeping because of everything going on",
]


def main():
    from sage_poc.safety.s3_semantic import check_s3

    print("\n=== S3 CALIBRATION REPORT ===\n")

    print("GATE CATCH — these must exceed the threshold:")
    catch_scores = []
    for phrase in GATE_CATCH:
        score = check_s3(phrase)
        catch_scores.append(score)
        status = "✓" if score >= 0.82 else "✗"
        print(f"  {status} {score:.4f}  {phrase[:70]}")

    print("\nGATE SUPPRESS — these must be below the threshold:")
    suppress_scores = []
    for phrase in GATE_SUPPRESS:
        score = check_s3(phrase)
        suppress_scores.append(score)
        status = "✓" if score < 0.82 else "✗"
        print(f"  {status} {score:.4f}  {phrase[:70]}")

    print("\nNEUTRAL CHECK — should score well below threshold:")
    for phrase in NEUTRAL_CHECK:
        score = check_s3(phrase)
        print(f"        {score:.4f}  {phrase[:70]}")

    if catch_scores and suppress_scores:
        min_catch = min(catch_scores)
        max_suppress = max(suppress_scores)
        gap = min_catch - max_suppress
        print(f"\n=== THRESHOLD ANALYSIS ===")
        print(f"  min(CATCH)     = {min_catch:.4f}")
        print(f"  max(SUPPRESS)  = {max_suppress:.4f}")
        print(f"  gap            = {gap:.4f}")
        if gap > 0:
            suggested = max_suppress + gap * 0.4
            print(f"  suggested threshold (40% of gap from suppress side) = {suggested:.4f}")
            print(f"\n  ✅ Clean gap. Set S3_THRESHOLD = {suggested:.4f} in s3_semantic.py")
            print(f"     Update the calibration date comment too.")
        else:
            print(f"\n  ❌ NO GAP: threshold cannot separate catch from suppress.")
            print(f"     Options:")
            print(f"     1. Add more diverse phrases to crisis_phrases.json for the failing CATCH phrases")
            print(f"     2. Check whether any SUPPRESS phrase belongs in FPE (activate FPE-AR-002?)")
            print(f"     3. Accept conservative threshold at {max_suppress + 0.01:.4f} and mark failing")
            print(f"        CATCH phrases as requiring FPE suppression path instead of threshold fix")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run calibration (requires BGE-M3 model)**

```bash
cd sage-poc && uv run python scripts/calibrate_s3_threshold.py 2>&1 | tee /tmp/s3_calibration.txt
cat /tmp/s3_calibration.txt
```

Read the output carefully:
- If `✅ Clean gap`: use the suggested threshold.
- If `❌ NO GAP` and "الله ياخذني من هالدنيا" is the problem: the phrase is semantically close to genuine passive SI (religiously framed). Document this gap and set the threshold at `max(CATCH)` score for the 5 English SF-1 phrases only. The Arabic SF-1 gate test for that phrase may need to shift to requiring FPE-AR-002 activation (a separate clinical decision, not a code decision).
- If `❌ NO GAP` for an English phrase: revise the phrase in `crisis_phrases.json` to be more semantically concentrated.

**Do not proceed to Step 3 if there is no gap for any English CATCH phrase.** Fix the phrase corpus first.

- [ ] **Step 3: Update `S3_THRESHOLD` in `s3_semantic.py`**

Replace the threshold line and update the calibration comment in `sage-poc/src/sage_poc/safety/s3_semantic.py`:

```python
# Calibrated 2026-05-26 via scripts/calibrate_s3_threshold.py.
# Gap = <INSERT_GAP_FROM_OUTPUT>. Re-run after editing crisis_phrases.json.
# SF-6 "الله ياخذني من هالدنيا" scored <INSERT_SCORE> (must be < threshold).
S3_THRESHOLD: float = <INSERT_VALUE_FROM_OUTPUT>
```

- [ ] **Step 4: Re-run slow gate tests to verify threshold is correct**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "slow"
```

Expected:
- All 6 `test_s3_catches_sf1_phrase` tests PASS.
- Both `test_s3_does_not_catch_sf6_false_positive` tests PASS.

If any SF-1 phrase fails: that phrase scores below threshold. Either add more semantically similar phrases to `crisis_phrases.json` (re-run calibration) or adjust the threshold toward that phrase's score (if gap allows).

If "الله ياخذني من هالدنيا" fails (scores >= threshold): lower threshold until it passes, even if one Arabic SF-1 phrase then falls below. Document which Arabic SF-1 phrase lost coverage as a known gap requiring FPE-AR-002 clinical review.

- [ ] **Step 5: Commit**

```bash
cd sage-poc && git add src/sage_poc/safety/s3_semantic.py scripts/calibrate_s3_threshold.py
git commit -m "fix(safety): calibrate S3_THRESHOLD — gap=<VALUE>, SF-1 catch rate 6/6, SF-6 FP rate 0/2"
```

---

### Task 4: Wire S3 into `safety_check_node`

**Files:**
- Modify: `sage-poc/src/sage_poc/nodes/safety_check.py`
- Test: `sage-poc/tests/test_s3_semantic.py` (integration tests written in Task 2)

- [ ] **Step 1: Run the integration tests to verify they fail**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py::test_safety_check_node_flags_crisis_when_s3_fires tests/test_s3_semantic.py::test_safety_check_node_suppresses_s3_when_fpe_fires tests/test_s3_semantic.py::test_safety_check_node_safe_when_s3_below_threshold tests/test_s3_semantic.py::test_safety_check_node_safe_when_s3_raises -v
```

Expected: Tests either PASS (if patch targets resolve) or FAIL with import errors. They should not be PASS yet because `check_s3` is not imported in `safety_check.py`.

- [ ] **Step 2: Update `safety_check.py`**

In `sage-poc/src/sage_poc/nodes/safety_check.py`, add these imports after the existing imports:

```python
import asyncio
from sage_poc.safety.s3_semantic import check_s3, S3_THRESHOLD
```

In `safety_check_node`, after the `rules_engine.evaluate("safety", ...)` block and after `third_party_flags` extraction (before the trajectory update at line 108), add the S3 check:

```python
    # S3: semantic crisis detection — OR-fusion with S1
    # Fail-open: exceptions and timeouts → score 0.0, no crash, S1 result stands.
    try:
        s3_score = await asyncio.wait_for(
            asyncio.to_thread(check_s3, message_en),
            timeout=5.0,
        )
        if s3_score >= S3_THRESHOLD:
            s3_suppressed = any(
                a.get("type") == "crisis_suppress" for a in safety_result.actions
            )
            if not s3_suppressed and "s3_semantic" not in new_crisis_flags:
                new_crisis_flags.append("s3_semantic")
    except asyncio.TimeoutError:
        pass
    except Exception as _exc:
        pass
```

The full updated `safety_check_node` function signature and surrounding context (lines 76–147 of the original), with the S3 block inserted between lines 102 and 108:

```python
async def safety_check_node(state: SageState) -> dict:
    raw = state["raw_message"]
    code_switching = bool(_HAS_ARABIC_RE.search(raw) and _HAS_LATIN_RE.search(raw))
    lang = detect_language(raw)

    if lang == "ar":
        message_en = translate_to_english(raw)
        text_ar = raw
    else:
        message_en = raw
        text_ar = None

    safety_result = rules_engine.evaluate("safety", {
        "text_en": message_en,
        "text_ar": text_ar,
        "language": lang,
    })

    new_crisis_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "crisis_flag"
    ]
    new_clinical_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "clinical_flag"
    ]
    third_party_flags = [
        a["flag_id"] for a in safety_result.actions if a.get("type") == "third_party_crisis"
    ]

    # Third-party crisis overrides direct crisis — more specific pattern wins
    if third_party_flags:
        new_crisis_flags = []

    # S3: semantic crisis detection — OR-fusion with S1
    # Fail-open: exceptions and timeouts → score 0.0, no crash, S1 result stands.
    try:
        s3_score = await asyncio.wait_for(
            asyncio.to_thread(check_s3, message_en),
            timeout=5.0,
        )
        if s3_score >= S3_THRESHOLD:
            s3_suppressed = any(
                a.get("type") == "crisis_suppress" for a in safety_result.actions
            )
            if not s3_suppressed and "s3_semantic" not in new_crisis_flags:
                new_crisis_flags.append("s3_semantic")
    except asyncio.TimeoutError:
        pass
    except Exception:
        pass

    trajectory, escalating = _update_distress_trajectory(state)
    engagement_trajectory, engagement_declining = _update_engagement_trajectory(state)

    skill_active = bool(state.get("active_skill_id"))
    engagement_ok = state.get("engagement", 5) >= 5

    persisted = state.get("clinical_flags", [])
    distress_signal = escalating or engagement_declining
    extra = ["escalating_distress"] if distress_signal and not (skill_active and engagement_ok) else []
    all_clinical = list(set(new_clinical_flags + extra + persisted))

    crisis_state = state.get("crisis_state", "none")
    s7_result: str | None = None
    s7_method: str | None = None

    if crisis_state == "monitoring":
        s7_result, s7_method = await evaluate_s7(message_en)

    return {
        "detected_language": lang,
        "message_en": message_en,
        "is_safe": len(new_crisis_flags) == 0,
        "crisis_flags": new_crisis_flags,
        "third_party_crisis": bool(third_party_flags),
        "clinical_flags": all_clinical,
        "distress_trajectory": trajectory,
        "engagement_trajectory": engagement_trajectory,
        "code_switching": code_switching,
        "crisis_state": crisis_state,
        "s7_result": s7_result,
        "s7_method": s7_method,
        "path": state["path"] + ["safety_check"],
    }
```

- [ ] **Step 3: Run the integration tests**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "not slow"
```

Expected: All 9 non-slow tests PASS (5 unit tests + 4 integration tests).

- [ ] **Step 4: Run the full safety test suite — must not regress**

```bash
cd sage-poc && uv run pytest tests/test_safety_node_integration.py tests/test_rules_safety.py tests/test_rules_integration.py -v 2>&1 | tail -10
```

Expected: All PASS. The S3 block is fail-open and does not change S1 behavior.

- [ ] **Step 5: Commit**

```bash
cd sage-poc && git add src/sage_poc/nodes/safety_check.py
git commit -m "feat(safety): wire S3 semantic crisis detection into safety_check_node with OR-fusion"
```

---

### DOOR 1.5 GATE

Run all three gate commands in order. All must pass before opening Door 2.

**Gate 1: No regressions in existing safety tests**

```bash
cd sage-poc && uv run pytest tests/test_safety_node_integration.py tests/test_rules_safety.py tests/test_rules_integration.py tests/test_rules_engine.py -v 2>&1 | tail -5
```

Must see: all PASS.

**Gate 2: S3 unit + integration tests pass**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "not slow" 2>&1 | tail -5
```

Must see: all PASS.

**Gate 3: SF-1 and SF-6 slow gate tests pass (real model)**

```bash
cd sage-poc && uv run pytest tests/test_s3_semantic.py -v -m "slow" 2>&1 | tail -10
```

Must see: all 6 `test_s3_catches_sf1_phrase` tests PASS, both `test_s3_does_not_catch_sf6_false_positive` tests PASS.

If Gate 3 fails:
- Go back to Task 3 calibration output.
- If "الله ياخذني من هالدنيا" is the only failure: set threshold conservatively and document the gap as requiring FPE-AR-002 clinical activation. This is an acceptable deferred gap — the clinical decision is not a code decision.
- If an English SF-1 phrase fails: add more semantically aligned phrases to `crisis_phrases.json` for that phrase's content area. Re-run calibration. Re-run gate.

Do not open Door 2 until all three gate commands pass.

---

## DOOR 2 — Intent Routing Verification

Three tasks. Each is independent; they can be read before Door 1 completes but must not be committed until the Door 1 gate passes.

### Task 1: Write RT-2 blended intent parsing integration test

RT-2 is: the `intent_route_node` correctly parses and writes `secondary_intent` from the LLM JSON response. This has never been tested with a mocked LLM. The routing tests in `test_routing.py` verify the routing logic but use pre-set state values; they do not exercise the parsing in `intent_route.py:58–66`.

**Files:**
- Create: `sage-poc/tests/test_intent_route_node.py`

- [ ] **Step 1: Write the failing tests**

Create `sage-poc/tests/test_intent_route_node.py`:

```python
"""Integration tests for intent_route_node: LLM response parsing and state output.

These tests mock resilient_invoke to return controlled JSON strings.
They verify that intent_route_node correctly parses the LLM output and
writes all expected fields to state — including secondary_intent (RT-2).

test_routing.py covers the routing functions (_route_after_intent, etc.) with
pre-set state values. These tests are the complementary layer: they prove the
node itself produces the state values that the routing functions rely on.
"""
import pytest
from unittest.mock import AsyncMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "message_en": "I've been feeling down for weeks",
        "detected_language": "en",
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "therapeutic_profile": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "path": ["safety_check"],
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_rt2_secondary_intent_parsed_and_written():
    """RT-2: secondary_intent must be written to state when LLM returns a blended intent."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": "info_request", '
        '"intent_confidence": 0.87, "emotional_intensity": 6, "engagement": 7}'
    )
    state = _base_state(
        message_en="I've been blaming myself for everything — also, is CBT something that could help?",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "new_skill", (
        f"Expected primary_intent='new_skill', got '{result['primary_intent']}'"
    )
    assert result["secondary_intent"] == "info_request", (
        f"RT-2 FAIL: secondary_intent should be 'info_request', got '{result['secondary_intent']}'"
    )
    assert result["intent_confidence"] == pytest.approx(0.87)
    assert result["emotional_intensity"] == 6
    assert result["engagement"] == 7
    assert "intent_route" in result["path"]


@pytest.mark.asyncio
async def test_secondary_intent_is_none_when_llm_returns_null():
    """When LLM returns secondary_intent: null, state must have secondary_intent=None."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.91, "emotional_intensity": 3, "engagement": 8}'
    )
    state = _base_state(message_en="Hey, how's it going?")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_low_confidence_writes_correct_confidence():
    """When LLM returns low confidence, intent_confidence in state must be < 0.6.

    This is the prerequisite for RT-1: _route_after_intent reads intent_confidence
    from state. This test proves that state value is correctly written by the node.
    The routing logic itself is tested in test_routing.py.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.42, "emotional_intensity": 4, "engagement": 3}'
    )
    state = _base_state(message_en="I don't know... just stuff I guess")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["intent_confidence"] < 0.6, (
        f"Expected intent_confidence < 0.6 for ambiguous message, got {result['intent_confidence']}"
    )
    assert result["intent_confidence"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_intent_route_defaults_to_general_chat_on_malformed_json():
    """Malformed LLM response must not raise — defaults to general_chat with confidence 0.5."""
    from sage_poc.nodes.intent_route import intent_route_node

    state = _base_state(message_en="test message")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value="NOT JSON AT ALL")):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == pytest.approx(0.5)
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_path_appended():
    """intent_route node must append 'intent_route' to the path field."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 5, "engagement": 5}'
    )
    state = _base_state(path=["safety_check"])

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["path"] == ["safety_check", "intent_route"]
```

- [ ] **Step 2: Run to verify they fail (or confirm they pass from a cold start)**

```bash
cd sage-poc && uv run pytest tests/test_intent_route_node.py -v
```

If the file doesn't exist yet, expected: `ERROR collecting` — file not found.
After creating the file: expected all tests **PASS**. (The node implementation is correct; these tests confirm the existing behavior, not add new behavior.)

If any test fails, that indicates a regression in `intent_route.py` that must be fixed before continuing.

- [ ] **Step 3: Commit**

```bash
cd sage-poc && git add tests/test_intent_route_node.py
git commit -m "test(intent): add RT-2 blended intent and RT-1 confidence parsing integration tests"
```

---

### Task 2: Fix `_route_after_intent` for `info_request`

**Why this is in Door 2, not Door 4:** Track 2 (Door 4) adds `knowledge_retrieve` as the destination for `info_request` messages. Track 2 Task 9 updates `_route_after_skill_select` to branch `info_request → knowledge_retrieve`. But `_route_after_skill_select` is only reached when `_route_after_intent` first routes to `skill_select`. Today, `_route_after_intent` sends `info_request` to `"freeflow"` (graph.py:105 fallthrough), bypassing `skill_select` entirely. Track 2's Node 6 wiring is therefore unreachable. This fix must be applied before Door 4.

After this fix, the path for `info_request` is:
- (now, before Door 4): `intent_route → skill_select → freeflow_respond` (skill_select finds no skill match, falls to freeflow)
- (after Door 4): `intent_route → skill_select → knowledge_retrieve → freeflow_respond`

**Files:**
- Modify: `sage-poc/src/sage_poc/graph.py`
- Modify: `sage-poc/tests/test_routing.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_routing.py` in the `test_route_after_intent` parametrize list. The existing row:

```python
("info_request", 0.8, None, "freeflow"),
```

must become:

```python
("info_request", 0.8, None, "skill_select"),
```

Find that line in `test_routing.py` (line 53 of the original file) and change the expected route from `"freeflow"` to `"skill_select"`. This test will now **fail** until the graph change in Step 3.

- [ ] **Step 2: Run to verify it fails**

```bash
cd sage-poc && uv run pytest tests/test_routing.py::test_route_after_intent -v 2>&1 | grep -A3 "info_request"
```

Expected: FAIL — `info_request → expected 'skill_select'` but got `'freeflow'`.

- [ ] **Step 3: Update `_route_after_intent` in `graph.py`**

In `sage-poc/src/sage_poc/graph.py`, replace the `_route_after_intent` function (lines 81–105) with:

```python
def _route_after_intent(state: SageState) -> str:
    intent = state.get("primary_intent", "general_chat")
    confidence = state.get("intent_confidence", 1.0)

    if intent == "crisis":
        return "crisis"
    if intent == "scope_refusal":
        return "gate"
    if intent == "jailbreak":
        # NOTE: jailbreak in monitoring state: persona reassertion takes priority.
        # crisis_state remains 'monitoring' — S7 will re-evaluate on the next turn.
        return "gate"
    # Post-crisis monitoring takes priority over confidence gating — short or fragmented
    # messages are expected after a crisis; route to skill_select regardless of confidence.
    if state.get("crisis_state") == "monitoring":
        return "skill_select"
    if confidence < 0.6:
        return "low_confidence"
    if intent == "exit_skill":
        return "skill_executor" if state.get("active_skill_id") else "freeflow"
    if intent in ("new_skill", "info_request"):
        return "skill_select"
    if intent == "skill_continuation" and state.get("active_skill_id"):
        return "skill_executor"
    return "freeflow"
```

The only change from the original is line 101: `if intent == "new_skill"` becomes `if intent in ("new_skill", "info_request")`. This routes `info_request` through `skill_select`, enabling Track 2's `knowledge_retrieve` path.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sage-poc && uv run pytest tests/test_routing.py -v
```

Expected: All PASS including the updated `info_request` row.

- [ ] **Step 5: Confirm no regression in existing routing behavior**

```bash
cd sage-poc && uv run pytest tests/test_routing.py tests/test_graph.py -v
```

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
cd sage-poc && git add src/sage_poc/graph.py tests/test_routing.py
git commit -m "fix(graph): route info_request through skill_select, enabling Track 2 Node 6 path"
```

---

### DOOR 2 GATE

```bash
cd sage-poc && uv run pytest tests/test_routing.py tests/test_intent_route_node.py -v 2>&1 | tail -5
```

**Must see:** All tests pass. No failures. If any test fails, do not open Door 3.

---

## DOOR 3 — Semantic Fallback Proof

Proves that the BGE-M3 semantic tier fires for real therapeutic phrases that do not match any keyword in any skill's `target_presentations`. This is the architectural validation the spec calls out as unverified: the question is whether semantic matching actually routes cases that keyword matching misses.

Two tasks. Run them in order.

### Task 1: Write keyword-clean semantic routing tests

A phrase is "keyword-clean" for a skill if no string in that skill's `target_presentations` is a substring of the phrase. The test helper `_phrase_is_keyword_clean` enforces this so the assertion `skill_match_method == "semantic"` is meaningful.

**Files:**
- Modify: `sage-poc/tests/test_skill_select.py`

- [ ] **Step 1: Write the failing tests**

Add to `sage-poc/tests/test_skill_select.py`:

```python
# ---- Door 3: Semantic fallback proof ------------------------------------------------
# Each test uses a phrase that is keyword-clean for the target skill.
# _phrase_is_keyword_clean asserts this so the 'semantic' method assertion is meaningful.

from sage_poc.nodes.skill_select import _SKILLS as _ALL_SKILLS


def _phrase_is_keyword_clean(phrase: str, target_skill_id: str) -> bool:
    """Return True if no keyword in ANY skill is a substring of phrase.

    This is a stricter check than keyword-clean for the target skill only,
    because a phrase matching a DIFFERENT skill's keywords would route to that
    skill via keyword tier rather than the target skill via semantic tier.
    """
    phrase_lower = phrase.lower()
    for skill_id, skill in _ALL_SKILLS.items():
        for kw in skill.target_presentations:
            if kw.lower() in phrase_lower:
                return False
    return True


@pytest.mark.asyncio
async def test_semantic_cbt_inherently_broken_phrase():
    """CBT semantic match: phrase describes self-critical schema without keyword overlap."""
    phrase = "I feel like there is something inherently broken in the way I am built"
    assert _phrase_is_keyword_clean(phrase, "cbt_thought_record"), (
        "Phrase accidentally matches a keyword — choose a different phrase for this test."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record", (
        f"Expected cbt_thought_record, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.asyncio
async def test_semantic_behavioral_activation_stuck_cycle_phrase():
    """Behavioral activation semantic match: withdrawal cycle described without keywords."""
    phrase = "The less I do the worse I feel and the worse I feel the less I do, I am completely stuck"
    assert _phrase_is_keyword_clean(phrase, "behavioral_activation"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "behavioral_activation", (
        f"Expected behavioral_activation, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.asyncio
async def test_semantic_worry_time_brain_cycling_phrase():
    """Worry time semantic match: ruminative cycling described without worry/overthink keywords."""
    phrase = "My brain just refuses to stop, the same scenarios cycle through all night"
    assert _phrase_is_keyword_clean(phrase, "worry_time"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "worry_time", (
        f"Expected worry_time, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.asyncio
async def test_semantic_dbt_tipp_internal_volcano_phrase():
    """DBT TIPP semantic match: acute emotional flooding described without TIPP keywords."""
    phrase = "Something is boiling inside me and I have no idea how to make it stop before I do something I regret"
    assert _phrase_is_keyword_clean(phrase, "dbt_tipp"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.asyncio
async def test_semantic_mi_readiness_half_wanting_phrase():
    """MI readiness ruler semantic match: ambivalence described without readiness/change keywords."""
    phrase = "Half of me genuinely wants things to be different but the other half just does not believe it is possible"
    assert _phrase_is_keyword_clean(phrase, "mi_readiness_ruler"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "mi_readiness_ruler", (
        f"Expected mi_readiness_ruler, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"
```

- [ ] **Step 2: Run to verify they fail (cold)**

```bash
cd sage-poc && uv run pytest tests/test_skill_select.py::test_semantic_cbt_inherently_broken_phrase tests/test_skill_select.py::test_semantic_behavioral_activation_stuck_cycle_phrase tests/test_skill_select.py::test_semantic_worry_time_brain_cycling_phrase tests/test_skill_select.py::test_semantic_dbt_tipp_internal_volcano_phrase tests/test_skill_select.py::test_semantic_mi_readiness_half_wanting_phrase -v
```

**Expected on first run:** Some FAIL with wrong `active_skill_id` or wrong `skill_match_method`. This is the proof point — if they all pass immediately, the phrases accidentally contain keywords (check the `_phrase_is_keyword_clean` assertion).

**If `_phrase_is_keyword_clean` raises an AssertionError:** The phrase you chose contains a keyword. Choose a different phrase, re-run.

**If a test fails with wrong `active_skill_id`:** The semantic score for that phrase falls below the threshold or matches a different skill. Acceptable options:
1. Accept the failure and adjust the phrase to be more semantically aligned with the target skill.
2. Accept the test as a known semantic limitation and mark with `@pytest.mark.xfail(reason="semantic score borderline, phrase needs tuning")`.

The Door 3 gate requires **4 of the 5 tests pass**. One allowed failure.

- [ ] **Step 3: Iterate until 4/5 pass (adjust phrases, not thresholds)**

If fewer than 4 pass, adjust the failing phrases to more closely describe the target skill's clinical presentation. Do NOT adjust the semantic threshold — the threshold was calibrated in Door 1 Task 7 and must not be changed to make tests pass.

When adjusting phrases: they must remain keyword-clean (the `_phrase_is_keyword_clean` guard will catch you if they're not).

- [ ] **Step 4: Commit (4/5 passing minimum)**

```bash
cd sage-poc && git add tests/test_skill_select.py
git commit -m "test(skill_select): add Door 3 semantic fallback proof — 5 keyword-clean phrases"
```

---

### Task 2: Embedding timeout fallback confirmation test

Proves that when the BGE-M3 embedding times out, `skill_select` falls back to keyword-only matching rather than raising an exception.

**Files:**
- Modify: `sage-poc/tests/test_skill_select.py`

- [ ] **Step 1: Write the failing test**

Add to `sage-poc/tests/test_skill_select.py`:

```python
@pytest.mark.asyncio
async def test_semantic_timeout_falls_back_to_keyword_match():
    """When embedding times out, skill_select must return a keyword match if one exists.

    Timeout fallback must not raise — it must return the keyword match (or None
    if no keyword match), never an exception.
    """
    import asyncio
    from unittest.mock import patch

    async def slow_embedding(*args, **kwargs):
        await asyncio.sleep(100)  # Force timeout

    # "always my fault" matches cbt_thought_record via keyword
    state = _ss_state(message_en="always my fault")

    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    # Keyword match must still work even when semantic times out
    assert result["active_skill_id"] == "cbt_thought_record", (
        "Keyword fallback failed when semantic timed out"
    )
    assert result["skill_match_method"] == "keyword"
    assert result.get("semantic_score") is None


@pytest.mark.asyncio
async def test_semantic_timeout_returns_none_when_no_keyword_match():
    """When embedding times out and no keyword matches, active_skill_id must be None."""
    import asyncio
    from unittest.mock import patch

    # A factual question that matches no skill keyword
    state = _ss_state(message_en="what is the difference between anxiety and depression")

    with patch("sage_poc.nodes.skill_select.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await skill_select_node(state)

    assert result["active_skill_id"] is None
    assert result.get("semantic_score") is None
```

- [ ] **Step 2: Run to verify they pass**

```bash
cd sage-poc && uv run pytest tests/test_skill_select.py::test_semantic_timeout_falls_back_to_keyword_match tests/test_skill_select.py::test_semantic_timeout_returns_none_when_no_keyword_match -v
```

Expected: Both **PASS**. The timeout fallback is already implemented in `skill_select.py`. These tests confirm it works correctly.

If either FAILS: the timeout fallback in `skill_select.py` is broken. Investigate `asyncio.wait_for` usage in `skill_select.py` before continuing.

- [ ] **Step 3: Commit**

```bash
cd sage-poc && git add tests/test_skill_select.py
git commit -m "test(skill_select): add embedding timeout fallback proof tests"
```

---

### DOOR 3 GATE

```bash
cd sage-poc && uv run pytest tests/test_skill_select.py -v 2>&1 | tail -15
```

**Must see:** All timeout tests pass. At least 4 of the 5 semantic phrase tests pass. If fewer than 4 semantic phrase tests pass, adjust phrases (not threshold) until the gate clears.

Also confirm the full suite hasn't regressed:

```bash
cd sage-poc && uv run pytest --tb=short -q 2>&1 | tail -5
```

Do not open Door 4 until both commands exit cleanly.

---

## DOOR 4 — Knowledge Base

**Execute all 15 tasks from:** `Docs/superpowers/plans/2026-05-25-track2-knowledge-base-node6.md`

Tasks in order:
1. Add `knowledge_passages`, `knowledge_abstain`, `knowledge_source` to `SageState`
2. Create Supabase migration 007 (`knowledge_articles` table)
3. Create `knowledge/models.py`
4. Create `knowledge/repository.py` and `knowledge/rewriter.py`
5. Create `knowledge/postgres_repository.py`
6. Create `knowledge/ingestion.py`
7. Create `knowledge/__init__.py` and migrate `knowledge.py`
8. Create Node 6 (`knowledge_retrieve.py`)
9. Update graph routing for Node 6
10. Upgrade `knowledge_lookup` tool to use real retrieval
11. Update `composer.py` L4 block to use state passages
12. Update `freeflow_respond.py` to set `knowledge_source="tool_lookup"`
13. Update `output_gate.py` audit trail
14. Create `scripts/ingest_knowledge.py`
15. E2E audit trail test

**Critical note for Track 2 Task 9:** The Track 2 plan updates `_route_after_skill_select` to branch `info_request → knowledge_retrieve`. This is correct. However, Track 2's plan does NOT update `_route_after_intent` to route `info_request → skill_select` — that fix was already applied in Door 2 Task 2. Do not apply any `_route_after_intent` changes in Task 9; they are already committed. Only apply the `_route_after_skill_select` update and graph wiring.

**Also for Track 2 Task 9:** The existing parametrize row in `test_routing.py` for `info_request` was already updated in Door 2 Task 2 (changed from `"freeflow"` to `"skill_select"`). Track 2's `test_routing.py` changes in Task 9 add NEW test rows for `_route_after_skill_select`, not replacements of the existing intent routing rows. No conflict.

### DOOR 4 GATE

Run Track 2's final check from Task 15:

```bash
cd sage-poc && uv run pytest tests/test_e2e_knowledge_audit.py -v -m slow
```

Expected: PASS.

Then run the full suite without slow tests:

```bash
cd sage-poc && uv run pytest --tb=short -m "not slow" -q 2>&1 | tail -5
```

Expected: All tests pass, no regressions from the baseline recorded in Phase 0.

---

## Cross-Door Invariants

These conditions must hold at the gate of every door:

1. **No threshold changes without calibration.** The `SEMANTIC_THRESHOLD` in `skill_select.py` must only change when `scripts/calibrate_threshold.py` is run and the gap is positive. Never change it to make a test pass.

2. **No freeflow shortcuts.** `info_request` must route through `skill_select` after Door 2. Any test that expects `info_request → freeflow` (bypassing `skill_select`) represents a regression.

3. **Track 1 tests must pass at all doors.** The 13-skill schema tests in `test_skill_schema.py` must pass at Door 2, 3, and 4 gates. Adding Track 2 must not break any skill schema test.

4. **knowledge_source must always be set.** After Door 4, any state that touches the knowledge path must have `knowledge_source` set to `"node_6"`, `"tool_lookup"`, or `""`. Never `None`.

---

## Execution Handoff

This plan defines the orchestration. Two options for executing it:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task using `superpowers:subagent-driven-development`. Each task is isolated; review happens between tasks. Track 1 and Track 2 tasks are dispatched with their respective plan documents as context.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`. Suitable if you want continuous context across all four doors.

**Which approach?**
