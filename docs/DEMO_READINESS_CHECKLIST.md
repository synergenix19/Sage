# Gitex Demo Readiness Checklist — Sage v7

**Last updated:** 2026-05-27  
**System gate:** C1/C2/C3 functional tests all PASS (see `docs/superpowers/audits/2026-05-27-v7-gitex-content-sprint-results.md`)

---

## Technical gates (DONE)

- [x] C1 safety paths — crisis detection, S3 semantic, third-party
- [x] C2 knowledge retrieval — CBT, anxiety, depression, Arabic
- [x] C3 Arabic full pipeline — distress, crisis, info, code-switching
- [x] 982 non-slow tests passing, 0 failures
- [x] Calibration gate: SEMANTIC_THRESHOLD=0.4972, gap=0.0422
- [x] Guard query verification: bare emotional words confirmed → general_chat via intent_route
- [x] intent_route SPOF documented with warning comment + slow regression test
- [x] Demo narrative: 6-turn script verified PASS (`scripts/demo_script_gitex.py`)

---

## Pre-demo: 3 actions required before going on stage

### 1. Clinical review of crisis knowledge articles (budget: 1 day)

**Owner:** Gulf-native clinical advisor  
**Blocking:** Any demo scenario that surfaces content from the knowledge base crisis articles  
**Articles requiring review:**

| Article ID | File | Flag |
|------------|------|------|
| `crisis-001` | `data/knowledge_corpus/crisis/crisis-001-en.json` | Review recommended |
| `crisis-002` | `data/knowledge_corpus/crisis/crisis-002-en.json` | Review recommended |
| `crisis-003` | `data/knowledge_corpus/crisis/crisis-003-en.json` | Review recommended |
| `crisis-004` | `data/knowledge_corpus/crisis/crisis-004-en.json` | `requires_clinical_review: true` — **hard gate** |

**Note:** This is a clinical and regulatory gate, not a technical one. Sage's crisis response (C1a–C1c in functional tests) uses hardcoded rule-based responses (not knowledge base content), so crisis_response routing does not expose these articles. However, if any demo flow queries for crisis-related knowledge via the knowledge_retrieve path (e.g., "what should I do if a friend is suicidal?"), crisis-004 content could surface. Confirm the demo script does not include such queries before skipping this review.

### 2. Presenter rehearsal — all 6 demo turns (budget: 2 hours)

**Owner:** Presenter  
**Script:** `scripts/demo_script_gitex.py`  
**Run the script:** `uv run python scripts/demo_script_gitex.py`

What automated tests cannot verify:
- Are responses therapeutically appropriate (not just correctly routed)?
- Are responses culturally resonant for a Gulf audience?
- Does Turn 2's grounding response feel warm and natural, or clinical and robotic?
- Does Turn 4's "Let's keep going" feel right when the user just said they feel calmer?
- Does Turn 5's CBT explanation feel like knowledge from a trusted source?
- Does Turn 6's third-party response feel supportive without being alarmist?

**Weak spots to watch:**
- Turn 4: The system continues the grounding exercise even after "I feel much calmer" — therapeutically correct, but can feel like the system ignored the user's statement. Presenter should be ready to call this out as intentional ("it completes the exercise").
- Turn 6: "no point anymore" (third-party) → safety_check passes as `none` (not monitoring). The response suggests professional help but doesn't escalate. This is the right behavior. Be prepared to explain the graduated response.

**Arabic pass:** Run the Arabic demo scenarios (C3a–C3d from `scripts/functional_test_c1_c2_c3.py`) with an Arabic-speaking colleague and verify the register/dialect feels appropriate for the Gulf.

### 3. Guard test before any intent_route prompt change

If anyone edits `INTENT_SYSTEM` in `src/sage_poc/nodes/intent_route.py` before the demo:

```bash
uv run pytest tests/test_nodes.py -k "bare_emotional_words" -m "slow" -v
```

All 4 guard phrases must return `general_chat`. Failure means psychoeducation skills would misfire on bare emotional affect words — a visible regression at the demo.

---

## Strategic: demo narrative

The 6-turn script (`scripts/demo_script_gitex.py`) demonstrates all three pillars in one continuous conversation:

| Turn | Pillar | What it shows |
|------|--------|---------------|
| 1 | Chat | System listens first — no premature skill activation |
| 2 | Chat | Panic symptoms → evidence-based grounding skill (5-4-3-2-1) |
| 3 | Chat | Interactive skill continuation — stepped, co-present |
| 4 | Chat | Warm transition — system completes the exercise |
| 5 | Ask | Seamless Chat→Ask handoff → RAG returns CBT corpus article |
| 6 | Safety | Third-party concern handled with care, not over-escalation |

**Presentation framing (suggested):**
- Turn 1: "The system doesn't rush to a technique — it explores first"
- Turn 2: "Specific panic symptoms trigger a clinically validated grounding protocol"
- Turn 3: "Interactive, stepped — co-present with the user in the exercise"
- Turn 5: "One question shifts the system from therapeutic skill to evidence-based knowledge — seamlessly, in the same session"
- Turn 6: "Safety awareness that's graduated — supportive without being alarmist"

**What this sells:** Chat (20 skills), Ask (30 articles, hybrid RAG), and Safety (S1+S3 OR-fusion) working as a unified architecture, not three separate demos stitched together.
