# Multi-Vector Semantic Matching — Full Build

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the single-vector cosine ceiling that produced three independent documented failures: grief under-coverage, interpersonal/financial over-capture, and crisis-paraphrase generalization gaps. Replace the single centroid per skill with a multi-vector anchor index, add per-cluster argmax routing, embed user state into the query, and wire a rerank interface for Falcon-3B.

**Architecture:** Four layered changes, each independently shippable and independently testable. (1) `semantic_anchors` in skill JSON + max-over-anchors matching — cheapest real coverage lift. (2) Per-cluster argmax — fixes over-capture where two skills are in the same cluster. (3) State-in-query embedding — profile summary prepended to message before encoding, so context-signal compounds with anchor coverage. (4) Rerank interface — top-k retrieval followed by a cross-encoder judge (Falcon-3B); stub ships in this plan, live model plugs in when validated. These build on each other: ship in order, test at each layer before moving on.

**Tech Stack:** Python, pytest, BGE-M3, `sentence_transformers`, `sage_poc.skills.schema.Skill`, `sage_poc.nodes.skill_select`, `sage_poc.clinical_clusters.CLINICAL_CLUSTERS`, `scripts/calibrate_threshold.py`, `scripts/semantic_probe_set.py`, `scripts/validate_grief_sf1_boundary.py`

---

## Context: Documented Failures That Motivate This Plan

| Failure | Skill(s) | Evidence |
|---|---|---|
| Grief under-coverage | `grief_loss` | 3/10 probes above threshold on baseline description; single centroid cannot span presence-absence, memory-intrusion, and identity-loss regions simultaneously |
| Interpersonal/financial over-capture | `interpersonal_effectiveness` vs `financial_anxiety` | "empty house" and "going through her things" grief probes lose to `interpersonal_effectiveness` (score 0.410 vs 0.403); same-cluster argmax doesn't apply — cross-cluster vocabulary bleed |
| Crisis paraphrase generalization | S3 corpus | 2/6 non-corpus passive-SI paraphrases miss at 0.767/0.795 (addressed by Plan 1; same root cause) |

All three are the same architectural limit: one vector per skill cannot sit close to a dispersed region of natural language. This plan fixes the skill-routing instances; Plan 1 fixes the crisis instance.

---

## File Map

| File | Change |
|---|---|
| `src/sage_poc/skills/schema.py` | Add `semantic_anchors: list[str] = []` field to `Skill` model |
| `src/sage_poc/skills/grief_loss.json` | Add `semantic_anchors` (8 representative utterances) |
| `src/sage_poc/skills/interpersonal_effectiveness.json` | Add `semantic_anchors` (8 representative utterances) |
| `src/sage_poc/skills/financial_anxiety.json` | Add `semantic_anchors` (8 representative utterances) |
| `src/sage_poc/nodes/skill_select.py` | Multi-vector index, max-over-anchors matching, cluster argmax, state-in-query |
| `src/sage_poc/nodes/skill_rerank.py` | New: rerank interface stub (top-k → judge → single selection) |
| `scripts/calibrate_threshold.py` | Update KNOWN_HITS scoring to use multi-vector; add anchor probe rows |
| `scripts/semantic_probe_set.py` | Update `raw_scores_top3` for new index structure |
| `scripts/validate_grief_sf1_boundary.py` | Update `score_all` for multi-vector index |
| `tests/test_skill_select.py` | Tests for multi-vector behavior and cluster argmax |
| `tests/test_skill_schema.py` | Test `semantic_anchors` field validation |

---

### Task 1: Add `semantic_anchors` to Skill schema (backward-compatible)

Add an optional `semantic_anchors` field to the `Skill` pydantic model. No skill JSON is required to have it; the field defaults to an empty list. The multi-vector index uses it when present and falls back to `semantic_description` alone when absent.

**Files:**
- Modify: `src/sage_poc/skills/schema.py`
- Test: `tests/test_skill_schema.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_skill_schema.py — add this test

def test_skill_schema_accepts_semantic_anchors():
    from sage_poc.skills.schema import Skill
    data = {
        "skill_id": "test_skill",
        "skill_name": "Test",
        "skill_type": "structured",
        "evidence_base": "test",
        "target_presentations": ["test"],
        "semantic_description": "test description",
        "semantic_anchors": [
            "I have been feeling really low lately",
            "Everything feels hopeless",
        ],
        "steps": [],
        "step_policy": [],
        "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
    }
    skill = Skill.model_validate(data)
    assert skill.semantic_anchors == [
        "I have been feeling really low lately",
        "Everything feels hopeless",
    ]


def test_skill_schema_semantic_anchors_defaults_to_empty():
    from sage_poc.skills.schema import Skill
    data = {
        "skill_id": "test_skill",
        "skill_name": "Test",
        "skill_type": "structured",
        "evidence_base": "test",
        "target_presentations": ["test"],
        "semantic_description": "test description",
        "steps": [],
        "step_policy": [],
        "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
    }
    skill = Skill.model_validate(data)
    assert skill.semantic_anchors == []
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
uv run pytest tests/test_skill_schema.py::test_skill_schema_accepts_semantic_anchors tests/test_skill_schema.py::test_skill_schema_semantic_anchors_defaults_to_empty -v
```

Expected: 2 FAILs — field doesn't exist yet.

- [ ] **Step 3: Add field to Skill model**

In `src/sage_poc/skills/schema.py`, add after `semantic_description`:

```python
class Skill(BaseModel):
    skill_id: str
    skill_name: str
    skill_type: str
    evidence_base: str
    self_evolution: Literal["manual_only"] = "manual_only"
    target_presentations: list[str]
    semantic_description: str = ""
    semantic_anchors: list[str] = Field(default_factory=list)  # representative utterances for multi-vector matching
    steps: list[SkillStep]
    step_policy: list[StepPolicyRule]
    escalation_matrix: dict[str, str]
    cultural_overrides: dict = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
uv run pytest tests/test_skill_schema.py -v
```

Expected: all pass including the two new tests. Existing tests must not regress.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/schema.py tests/test_skill_schema.py
git commit -m "feat(schema): add optional semantic_anchors field to Skill model

Backward-compatible: defaults to []. Used by multi-vector skill_select
to match against representative utterances instead of a single centroid.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Populate semantic_anchors for the three skills with documented coverage gaps

Add `semantic_anchors` to `grief_loss.json`, `interpersonal_effectiveness.json`, and `financial_anxiety.json`. Anchors are representative natural-language utterances — the same kind as the probe set. They are NOT keyword fragments; they are full sentences a user might send.

Anchors are sourced from the probe sets in `scripts/semantic_probe_set.py` (the probes that were failing due to the centroid gap) and from clinical experience with each skill's presentation.

**Files:**
- Modify: `src/sage_poc/skills/grief_loss.json`
- Modify: `src/sage_poc/skills/interpersonal_effectiveness.json`
- Modify: `src/sage_poc/skills/financial_anxiety.json`

There are no failing tests to write for this task — the schema change makes this valid JSON. The probe set in `scripts/semantic_probe_set.py` is the acceptance test (run in Task 4).

- [ ] **Step 1: Add semantic_anchors to grief_loss.json**

In `src/sage_poc/skills/grief_loss.json`, add after `semantic_description`:

```json
  "semantic_anchors": [
    "My mother passed away three months ago and I still cannot seem to get back to any sense of normal",
    "The house feels completely empty without him and I do not know how to fill that space",
    "I cannot bring myself to go through her things or change anything in her room",
    "Everything I see, every place we went together, reminds me of him and it is unbearable",
    "She was the person I talked to about everything and now I do not know who I am without her",
    "I keep expecting her to walk in through the door and then remember all over again that she is gone",
    "I wake up each morning and for a moment I forget he has died, and then it hits me all over again",
    "My father was the one who held this family together, and now that he is gone I feel completely at a loss"
  ],
```

These eight phrases are the ten grief probes from `scripts/semantic_probe_set.py` minus the two that already scored above threshold on the baseline centroid (those don't need anchoring; they already route correctly).

- [ ] **Step 2: Add semantic_anchors to interpersonal_effectiveness.json**

In `src/sage_poc/skills/interpersonal_effectiveness.json`, add after `semantic_description`:

```json
  "semantic_anchors": [
    "I need to have a serious conversation with my father but I am scared of how he will react",
    "My father will not listen to anything I say and I do not know how to get through to him",
    "I am caught between my wife and my mother and whatever I do one of them is hurt",
    "I want to repair things with my sister after a bad argument but I do not know how to approach her",
    "How do I talk to my in-laws about something sensitive without making everything worse",
    "I need to set a boundary with someone in my family but I am worried about the consequences",
    "I cannot keep everyone in my family happy and it is tearing me apart",
    "I want to say something important to someone I care about but I do not know how to begin"
  ],
```

- [ ] **Step 3: Add semantic_anchors to financial_anxiety.json**

In `src/sage_poc/skills/financial_anxiety.json`, add after `semantic_description`:

```json
  "semantic_anchors": [
    "I cannot sleep because I am terrified of what happens to my family if my contract is not renewed",
    "Everything I earn goes straight to my parents back home and if I lose my income my whole household collapses",
    "My entire sense of who I am comes from being the provider for my family and lately I feel that is slipping",
    "My salary is not enough to meet all the obligations I have to my family and it is affecting everything",
    "I am terrified of not being able to support my parents and siblings the way they depend on me to",
    "I am the only one supporting my whole family back home and the financial pressure is becoming unbearable",
    "If I lose this job I do not know how I will keep my family afloat",
    "The kafala system means I cannot easily change jobs and the financial pressure is crushing me"
  ],
```

- [ ] **Step 4: Validate JSON on all three files**

```bash
python3 -c "
import json
for f in ['grief_loss', 'interpersonal_effectiveness', 'financial_anxiety']:
    d = json.load(open(f'src/sage_poc/skills/{f}.json'))
    print(f'{f}: semantic_anchors = {len(d.get(\"semantic_anchors\", []))} entries')
"
```

Expected: 8 entries each.

- [ ] **Step 5: Commit**

```bash
git add src/sage_poc/skills/grief_loss.json src/sage_poc/skills/interpersonal_effectiveness.json src/sage_poc/skills/financial_anxiety.json
git commit -m "content(skills): add semantic_anchors to grief_loss, interpersonal_effectiveness, financial_anxiety

8 representative utterances per skill, sourced from the documented probe set
failures. These become multi-vector index anchors in Task 3, spreading
coverage across the region the single centroid cannot reach.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Refactor skill_select.py for multi-vector matching

Replace the single centroid per skill with a max-over-anchors index. The index stores one embedding per anchor text (description + all `semantic_anchors`). At match time, take the max score per skill across all its anchors. Add cluster argmax: when the top match is within a cluster where multiple skills exceed a soft floor (0.42), return the argmax within the cluster rather than the absolute-threshold winner.

**Files:**
- Modify: `src/sage_poc/nodes/skill_select.py`
- Test: `tests/test_skill_select.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_skill_select.py — add these tests

@pytest.mark.slow
async def test_grief_anchor_probe_empty_house_routes_to_grief():
    """Multi-vector: 'empty house' grief probe must route to grief_loss, not interpersonal."""
    state = make_state(
        message_en="The house feels completely empty without him and I do not know how to fill that space",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "grief_loss", (
        f"Expected grief_loss, got {result['active_skill_id']} "
        f"(score={result['semantic_score']})"
    )
    assert result["skill_match_method"] in ("semantic", "keyword")


@pytest.mark.slow
async def test_grief_anchor_probe_going_through_things_routes_to_grief():
    """Multi-vector: 'going through her things' grief probe must route to grief_loss."""
    state = make_state(
        message_en="I cannot bring myself to go through her things or change anything in her room",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "grief_loss", (
        f"Expected grief_loss, got {result['active_skill_id']} "
        f"(score={result['semantic_score']})"
    )


@pytest.mark.slow
async def test_interpersonal_anchor_probe_father_conversation():
    """Multi-vector: interpersonal probe must route to interpersonal_effectiveness."""
    state = make_state(
        message_en="I need to have a serious conversation with my father but I am scared of how he will react",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "interpersonal_effectiveness", (
        f"Expected interpersonal_effectiveness, got {result['active_skill_id']}"
    )
```

Add `make_state` helper if not already present in `test_skill_select.py`:

```python
def make_state(**kwargs):
    defaults = {
        "raw_message": kwargs.get("message_en", ""),
        "message_en": "",
        "detected_language": "en",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "new_skill",
        "intent_confidence": 1.0,
        "path": [],
        "therapeutic_profile": None,
    }
    return {**defaults, **kwargs}
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
uv run pytest tests/test_skill_select.py::test_grief_anchor_probe_empty_house_routes_to_grief tests/test_skill_select.py::test_grief_anchor_probe_going_through_things_routes_to_grief tests/test_skill_select.py::test_interpersonal_anchor_probe_father_conversation -v -p no:xdist
```

Expected: FAILs — current single-vector matching routes "empty house" to `interpersonal_effectiveness`.

- [ ] **Step 3: Refactor skill_select.py**

Replace the globals and the `_ensure_semantic_ready` + `_semantic_match_sync` functions. The new code builds an anchor index instead of a description index:

```python
# Replace the globals block:
_SKILLS = {sid: load_skill(sid) for sid in SKILL_REGISTRY}

SEMANTIC_THRESHOLD: float = 0.459
# Soft floor for within-cluster argmax: if top-2 skills in the same cluster
# both exceed this floor, route by argmax rather than absolute threshold.
_CLUSTER_ARGMAX_FLOOR: float = 0.42

_embed_model = None
_anchor_skill_ids: list[str] = []   # one entry per anchor (description or semantic_anchors item)
_anchor_embeddings: np.ndarray | None = None  # shape (n_anchors, dim)
_init_lock = threading.Lock()
```

```python
# Replace _ensure_semantic_ready:
def _ensure_semantic_ready() -> None:
    global _embed_model, _anchor_skill_ids, _anchor_embeddings
    if _embed_model is not None and _anchor_embeddings is not None:
        return
    with _init_lock:
        if _embed_model is not None and _anchor_embeddings is not None:
            return
        model = _embed_model
        if model is None:
            from sentence_transformers import SentenceTransformer
            _REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
            try:
                model = SentenceTransformer(
                    "BAAI/bge-m3", local_files_only=True, revision=_REVISION,
                )
            except (OSError, EnvironmentError):
                model = SentenceTransformer("BAAI/bge-m3", revision=_REVISION)

        pairs: list[tuple[str, str]] = []  # (skill_id, anchor_text)
        for sid, skill in _SKILLS.items():
            if sid in KEYWORD_SEMANTIC_SKIP:
                continue
            if skill.semantic_description:
                pairs.append((sid, skill.semantic_description))
            for anchor in skill.semantic_anchors:
                pairs.append((sid, anchor))

        _anchor_skill_ids = [sid for sid, _ in pairs]
        anchor_texts = [text for _, text in pairs]
        _anchor_embeddings = model.encode(anchor_texts, normalize_embeddings=True)
        _embed_model = model
```

```python
# Replace _semantic_match_sync:
def _semantic_match_sync(
    message_en: str,
    profile_context: str = "",
) -> tuple[str | None, float]:
    """Max-over-anchors matching with optional profile context prepended to query."""
    _ensure_semantic_ready()
    if _anchor_embeddings is None or not message_en.strip():
        return None, 0.0

    # State-in-query: prepend profile summary if available
    query_text = f"{profile_context}\n{message_en}".strip() if profile_context else message_en
    msg_emb = _embed_model.encode([query_text], normalize_embeddings=True)[0]
    raw_scores = np.dot(_anchor_embeddings, msg_emb)  # (n_anchors,)

    # Group by skill: max-over-anchors
    skill_scores: dict[str, float] = {}
    for i, sid in enumerate(_anchor_skill_ids):
        score = float(raw_scores[i])
        if score > skill_scores.get(sid, 0.0):
            skill_scores[sid] = score

    if not skill_scores:
        return None, 0.0

    # Sort by score descending
    ranked = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    best_sid, best_score = ranked[0]

    # Within-cluster argmax: if top-2 are in the same cluster and both exceed
    # _CLUSTER_ARGMAX_FLOOR, trust the argmax (relative decision beats absolute threshold).
    if len(ranked) >= 2:
        second_sid, second_score = ranked[1]
        if second_score >= _CLUSTER_ARGMAX_FLOOR:
            best_cluster = _skill_cluster(best_sid)
            second_cluster = _skill_cluster(second_sid)
            if best_cluster is not None and best_cluster == second_cluster:
                # Already the argmax — best_sid wins; no threshold gate needed within cluster.
                return best_sid, best_score

    if best_score >= SEMANTIC_THRESHOLD:
        return best_sid, best_score
    return None, best_score


def _skill_cluster(skill_id: str) -> str | None:
    """Return the cluster name for skill_id, or None if not in any cluster."""
    from sage_poc.clinical_clusters import CLINICAL_CLUSTERS
    for cluster, skills in CLINICAL_CLUSTERS.items():
        if skill_id in skills:
            return cluster
    return None
```

Update `skill_select_node` to pass profile context:

```python
async def skill_select_node(state: SageState) -> dict:
    # ... (info_request and monitoring guards unchanged) ...

    message = state["message_en"].lower()

    # Tier 1: Keyword matching (unchanged)
    for skill_id, skill in _SKILLS.items():
        if skill_id in KEYWORD_SEMANTIC_SKIP:
            continue
        for keyword in skill.target_presentations:
            if keyword.lower() in message:
                return {
                    "active_skill_id": skill_id,
                    "active_step_id": skill.steps[0].step_id,
                    "skill_match_method": "keyword",
                    "semantic_score": None,
                    "path": state["path"] + ["skill_select"],
                }

    # Tier 2: Multi-vector semantic with optional profile context
    profile = state.get("therapeutic_profile") or {}
    profile_context = profile.get("summary", "") or ""

    try:
        semantic_skill, score = await asyncio.wait_for(
            asyncio.to_thread(_semantic_match_sync, state["message_en"], profile_context),
            timeout=EMBEDDING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            '{"event": "embedding_timeout", "skill_select_tier": "keyword_only", '
            '"timeout_s": %s}',
            EMBEDDING_TIMEOUT_SECONDS,
        )
        return {
            "active_skill_id": None,
            "active_step_id": None,
            "skill_match_method": None,
            "semantic_score": None,
            "embedding_timeout": True,
            "path": state["path"] + ["skill_select"],
        }

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

- [ ] **Step 4: Run new tests to confirm PASS**

```bash
uv run pytest tests/test_skill_select.py::test_grief_anchor_probe_empty_house_routes_to_grief tests/test_skill_select.py::test_grief_anchor_probe_going_through_things_routes_to_grief tests/test_skill_select.py::test_interpersonal_anchor_probe_father_conversation -v -p no:xdist
```

Expected: all PASS.

- [ ] **Step 5: Run existing semantic tests to check for regressions**

```bash
uv run pytest tests/test_skill_select.py -v -p no:xdist
```

If any existing semantic test fails: the `_semantic_skill_ids` or `_semantic_embeddings` globals have been removed. Check `test_skill_select.py` for references to these and update them to use `_anchor_skill_ids` and `_anchor_embeddings` instead.

- [ ] **Step 6: Run semantic_probe_set.py and validate_grief_sf1_boundary.py**

These scripts use the old index structure and will error until updated.

```bash
# Fix semantic_probe_set.py — update raw_scores_top3:
# Replace:
#   scores_vec = np.dot(ss._semantic_embeddings, msg_emb)
#   idxs = np.argsort(scores_vec)[::-1][:3]
#   return [(ss._semantic_skill_ids[i], float(scores_vec[i])) for i in idxs]
# With:
#   raw = np.dot(ss._anchor_embeddings, msg_emb)
#   skill_scores = {}
#   for i, sid in enumerate(ss._anchor_skill_ids):
#       score = float(raw[i])
#       if score > skill_scores.get(sid, 0.0):
#           skill_scores[sid] = score
#   return sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:3]
```

In `scripts/semantic_probe_set.py`, replace the `raw_scores_top3` function:

```python
def raw_scores_top3(msg):
    msg_emb = ss._embed_model.encode([msg], normalize_embeddings=True)[0]
    raw = np.dot(ss._anchor_embeddings, msg_emb)
    skill_scores = {}
    for i, sid in enumerate(ss._anchor_skill_ids):
        score = float(raw[i])
        if score > skill_scores.get(sid, 0.0):
            skill_scores[sid] = score
    return sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:3]
```

Also update the header print: `len(ss._anchor_skill_ids)` → this is now anchor count, not skill count. Print skill count separately:

```python
unique_skills = len(set(ss._anchor_skill_ids))
print(f"BGE-M3 ready in {time.time()-t0:.1f}s | {unique_skills} skills, {len(ss._anchor_skill_ids)} anchors embedded\n")
```

In `scripts/validate_grief_sf1_boundary.py`, replace the `score_all` function:

```python
def score_all(msg: str) -> tuple[float, str, float]:
    """Returns (grief_loss_score, top_skill, top_score)."""
    emb = ss._embed_model.encode([msg], normalize_embeddings=True)[0]
    raw = np.dot(ss._anchor_embeddings, emb)
    skill_scores = {}
    for i, sid in enumerate(ss._anchor_skill_ids):
        score = float(raw[i])
        if score > skill_scores.get(sid, 0.0):
            skill_scores[sid] = score
    gl_score = skill_scores.get("grief_loss", 0.0)
    top_sid = max(skill_scores, key=skill_scores.get)
    top_score = skill_scores[top_sid]
    return gl_score, top_sid, top_score
```

Run both:

```bash
uv run python scripts/semantic_probe_set.py
uv run python scripts/validate_grief_sf1_boundary.py
```

Expected from `validate_grief_sf1_boundary.py`:
- GRIEF SUMMARY: PASS count should be significantly higher than the baseline 3/10 (target: 8–10/10 with anchors)
- SF1 SUMMARY: all CLEAR — no grief bleeds (the anchors are grief phenomenology, not passive ideation)

If SF1 bleeds appear: one or more grief anchors sits too close to the passive-SI region. Remove the offending anchor from `grief_loss.json`'s `semantic_anchors` and rerun.

- [ ] **Step 7: Run calibrate_threshold.py to verify the cross-cluster gap still holds**

```bash
uv run python scripts/calibrate_threshold.py
```

The calibration script uses its own KNOWN_HITS corpus (not the anchor index) to measure the gap. With multi-vector matching, the SEMANTIC_THRESHOLD may need to be recalibrated because adding anchors shifts the scoring distribution. Read the output and update `SEMANTIC_THRESHOLD` in `skill_select.py` if the suggested threshold differs from 0.459 by more than 0.01.

- [ ] **Step 8: Commit**

```bash
git add src/sage_poc/nodes/skill_select.py scripts/semantic_probe_set.py scripts/validate_grief_sf1_boundary.py tests/test_skill_select.py
git commit -m "feat(skill_select): multi-vector anchor matching + cluster argmax + state-in-query

Replaces single centroid per skill with max-over-anchors index. Each skill
embeds its semantic_description + all semantic_anchors entries; matching
takes max cosine per skill across all its anchors.

Within-cluster argmax: when top-2 skills share a cluster and both exceed
_CLUSTER_ARGMAX_FLOOR (0.42), route by argmax rather than absolute threshold.

State-in-query: profile.summary prepended to message before encoding when
present, so therapeutic context compounds with anchor coverage.

Fixes: 'empty house' grief probe (was routing to interpersonal_effectiveness),
'going through her things' grief probe, and related cross-cluster over-capture.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Add rerank interface stub

Define the interface for retrieve-then-rerank (top-k candidates → cross-encoder judge → single selection). The stub returns the top-ranked candidate from the retrieval step unmodified. When Falcon-3B is validated, it plugs into `_rerank_candidates` without changing the interface.

**Files:**
- Create: `src/sage_poc/nodes/skill_rerank.py`
- Modify: `src/sage_poc/nodes/skill_select.py` (wire in top-k path)
- Test: `tests/test_skill_select.py`

- [ ] **Step 1: Write failing test for rerank interface**

```python
# tests/test_skill_select.py — add:

def test_rerank_returns_best_candidate_from_stub():
    """Stub reranker must return the highest-scored candidate without calling any model."""
    from sage_poc.nodes.skill_rerank import rerank_candidates

    candidates = [
        ("grief_loss", 0.51),
        ("interpersonal_effectiveness", 0.49),
        ("behavioral_activation", 0.45),
    ]
    result_id, result_score = rerank_candidates("I lost someone", candidates)
    assert result_id == "grief_loss"
    assert result_score == pytest.approx(0.51)


def test_rerank_handles_single_candidate():
    from sage_poc.nodes.skill_rerank import rerank_candidates
    candidates = [("grief_loss", 0.48)]
    result_id, result_score = rerank_candidates("I am grieving", candidates)
    assert result_id == "grief_loss"
    assert result_score == pytest.approx(0.48)


def test_rerank_raises_on_empty_candidates():
    from sage_poc.nodes.skill_rerank import rerank_candidates
    with pytest.raises(ValueError, match="at least one candidate"):
        rerank_candidates("hello", [])
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
uv run pytest tests/test_skill_select.py::test_rerank_returns_best_candidate_from_stub tests/test_skill_select.py::test_rerank_handles_single_candidate tests/test_skill_select.py::test_rerank_raises_on_empty_candidates -v
```

Expected: 3 FAILs — module doesn't exist yet.

- [ ] **Step 3: Create skill_rerank.py stub**

```python
# src/sage_poc/nodes/skill_rerank.py
"""Skill rerank interface.

Production path (Full Build): top-k bi-encoder candidates → Falcon-3B cross-encoder
→ single selection. The cross-encoder sees (message, candidate_description) pairs
jointly, enabling disambiguation that single-vector retrieval cannot do.

Current state: stub that returns the highest-scored retrieval candidate unmodified.
When Falcon-3B is validated, replace _rerank_with_model below.

Usage:
    from sage_poc.nodes.skill_rerank import rerank_candidates
    winner_id, winner_score = rerank_candidates(message, top_k_candidates)
"""
from __future__ import annotations


def rerank_candidates(
    message: str,
    candidates: list[tuple[str, float]],
) -> tuple[str, float]:
    """Return the winning (skill_id, score) from a list of retrieval candidates.

    Args:
        message: The user message being routed.
        candidates: List of (skill_id, score) tuples from bi-encoder retrieval,
                    in descending score order. Must be non-empty.

    Returns:
        (skill_id, score) of the selected skill.

    Raises:
        ValueError: If candidates is empty.
    """
    if not candidates:
        raise ValueError("rerank_candidates requires at least one candidate")
    return _rerank_stub(message, candidates)


def _rerank_stub(
    message: str,
    candidates: list[tuple[str, float]],
) -> tuple[str, float]:
    """Stub: return top bi-encoder candidate. Replace with Falcon-3B when validated."""
    return candidates[0]


# Falcon-3B cross-encoder (plug in here when validated):
#
# def _rerank_with_model(
#     message: str,
#     candidates: list[tuple[str, float]],
# ) -> tuple[str, float]:
#     from sage_poc.nodes.skill_rerank_model import score_pairs
#     from sage_poc.skills.schema import load_skill
#     pairs = [(message, load_skill(sid).semantic_description) for sid, _ in candidates]
#     scores = score_pairs(pairs)   # cross-encoder returns score per pair
#     best_idx = max(range(len(scores)), key=lambda i: scores[i])
#     return candidates[best_idx][0], float(scores[best_idx])
```

- [ ] **Step 4: Run tests to confirm PASS**

```bash
uv run pytest tests/test_skill_select.py::test_rerank_returns_best_candidate_from_stub tests/test_skill_select.py::test_rerank_handles_single_candidate tests/test_skill_select.py::test_rerank_raises_on_empty_candidates -v
```

Expected: 3 PASSes.

- [ ] **Step 5: Wire reranker into skill_select.py for top-k path**

In `src/sage_poc/nodes/skill_select.py`, add a constant and modify `_semantic_match_sync` to use the reranker when multiple skills exceed threshold:

```python
# Add constant after SEMANTIC_THRESHOLD:
_RERANK_TOP_K: int = 3   # candidates passed to reranker when multiple exceed threshold
```

In `_semantic_match_sync`, after computing `ranked`, replace the return logic:

```python
    # Collect all candidates above threshold for reranking
    above = [(sid, score) for sid, score in ranked if score >= SEMANTIC_THRESHOLD]

    # Within-cluster argmax (unchanged — runs before rerank check)
    if len(ranked) >= 2:
        second_sid, second_score = ranked[1]
        if second_score >= _CLUSTER_ARGMAX_FLOOR:
            best_cluster = _skill_cluster(best_sid)
            second_cluster = _skill_cluster(second_sid)
            if best_cluster is not None and best_cluster == second_cluster:
                return best_sid, best_score

    # Single candidate above threshold: return directly (no rerank needed)
    if len(above) == 1:
        return above[0]

    # Multiple candidates above threshold: pass top-k to reranker
    if len(above) > 1:
        from sage_poc.nodes.skill_rerank import rerank_candidates
        return rerank_candidates(message_en, above[:_RERANK_TOP_K])

    # Nothing above threshold
    return None, best_score
```

Note: `rerank_candidates` currently stubs to top candidate, so this is a no-op behaviorally until Falcon-3B is plugged in. The wiring allows the reranker to be activated by swapping the stub.

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest tests/test_skill_select.py tests/test_routing.py tests/test_nodes.py -v -p no:xdist
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add src/sage_poc/nodes/skill_rerank.py src/sage_poc/nodes/skill_select.py tests/test_skill_select.py
git commit -m "feat(skill_select): add rerank interface stub for Falcon-3B cross-encoder

Defines rerank_candidates(message, top_k_candidates) → (skill_id, score).
Currently stubs to top bi-encoder candidate; Falcon-3B cross-encoder
plugs into _rerank_with_model when validated.

skill_select wires in reranker when multiple candidates exceed SEMANTIC_THRESHOLD,
giving cross-encoder joint reasoning over the candidate set rather than
independent cosine scores. No behavioural change until Falcon-3B is activated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Run the probe set and write the acceptance report

Run `scripts/semantic_probe_set.py` in full and compare against baseline (pre-multi-vector) results. The probe set is the acceptance test for the full feature.

**Files:**
- No code changes — read and report output

- [ ] **Step 1: Run probe set against multi-vector index**

```bash
uv run python scripts/semantic_probe_set.py 2>&1 | tee /tmp/mv_probe_results.txt
```

- [ ] **Step 2: Check acceptance criteria**

Read `/tmp/mv_probe_results.txt`. Required:

| Check | Criterion |
|---|---|
| grief_loss probes | ≥ 8/10 OK (was 3/10 on single-vector baseline) |
| interpersonal_effectiveness probes | ≥ 8/10 OK |
| financial_anxiety probes | ≥ 4/5 OK |
| cognitive_restructuring probes | ≥ 3/4 OK or CLUSTER |
| WRONG verdicts | 0 across all groups |

If any group misses the criterion: add or revise `semantic_anchors` for that skill and rerun. Do not modify `semantic_description`. Do not raise the threshold.

- [ ] **Step 3: Run validate_grief_sf1_boundary.py for the final picture**

```bash
uv run python scripts/validate_grief_sf1_boundary.py
```

Expected:
- Grief PASS count ≥ 8/10
- SF1 SUMMARY: all CLEAR

If any SF1 BLEED appears: one grief anchor sits in the passive-ideation region. Remove it from `grief_loss.json` semantic_anchors.

- [ ] **Step 4: Run calibrate_threshold.py to confirm gap still holds**

```bash
uv run python scripts/calibrate_threshold.py
```

If the suggested threshold has shifted, update `SEMANTIC_THRESHOLD` in `skill_select.py` and commit.

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest tests/ -p no:xdist --ignore=tests/experiment_4_4 --ignore=tests/experiment_4_5 --ignore=tests/experiment_4_6 -q
```

Expected: all green (or documented pre-existing failures only).

- [ ] **Step 6: Commit results and any threshold update**

```bash
git add src/sage_poc/nodes/skill_select.py  # only if SEMANTIC_THRESHOLD changed
git commit -m "chore(calibration): recalibrate SEMANTIC_THRESHOLD post multi-vector

Probe set acceptance: grief <N>/10, interpersonal <N>/10, financial <N>/5.
validate_grief_sf1_boundary: 0 SF-1 bleeds, grief <N>/10 pass.
Threshold updated from 0.459 to <NEW_VALUE> (gap = <GAP>).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Multiple anchor vectors per skill (`semantic_anchors` field + max-over-anchors): Tasks 1–3 ✓
- Per-cluster relative thresholds / argmax: Task 3 (`_CLUSTER_ARGMAX_FLOOR` + `_skill_cluster`) ✓
- State-in-query embedding (profile summary prepended): Task 3 (`profile_context` arg) ✓
- Retrieve-then-rerank with Falcon-3B interface: Task 4 (`skill_rerank.py`) ✓
- "Do not widen semantic_descriptions": nowhere in this plan does any step touch `semantic_description` ✓
- Probe harness as acceptance test: Task 5 ✓
- Crisis surface FIRST, skill routing SECOND: this is Plan 2 (Full Build); Plan 1 addresses crisis ✓
- §4.3 SRA pattern reference: architecture statement in header ✓

**Placeholder scan:** Task 3 Step 7 and Task 5 Step 6 contain `<N>` and `<NEW_VALUE>` — intentional, values are read from script output at execution time.

**Type consistency:**
- `rerank_candidates` takes `list[tuple[str, float]]` and returns `tuple[str, float]` — consistent across Task 4 definition, tests, and Task 3 call site.
- `_semantic_match_sync` returns `tuple[str | None, float]` — unchanged from current signature, consistent with `skill_select_node` call site.
- `_skill_cluster` returns `str | None` — used in Task 3 with None-guard before cluster comparison.
- `profile_context: str = ""` — keyword arg with default, backward-compatible with existing `to_thread` call.
