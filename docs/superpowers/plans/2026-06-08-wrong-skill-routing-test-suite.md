# Wrong-Skill Routing Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 125-case colloquial-phrase test suite that enforces correct skill routing for each of the 25 keyword/semantic-matchable skills, plus a coverage matrix script that reveals per-skill Tier 1 vs Tier 2 gaps.

**Architecture:** Three files — a fixture data module (`cases.py`), a pytest parametrized test (`test_wrong_skill_routing.py`), and a standalone diagnostic script (`scripts/coverage_matrix.py`). The pytest suite asserts correctness and fails when routing is wrong. The matrix script runs the same cases through the full pipeline and outputs a per-skill breakdown of keyword hits, semantic hits, misfires, and no-matches. Both consume the same fixture.

**Tech Stack:** pytest-asyncio, `sage_poc.nodes.skill_select.skill_select_node`, `sage_poc.nodes.skill_select._SKILLS`, `sage_poc.corpus_constants.KEYWORD_SEMANTIC_SKIP`, `sage_poc.skill_ids.SKILL_REGISTRY`

---

## Background

`skill_select_node` uses a two-tier matching system:
- **Tier 1 (keyword)**: Iterates `SKILL_REGISTRY` order, checks each skill's `target_presentations` as substring matches against `message_en` (and `raw_message` for Arabic). First match wins.
- **Tier 2 (semantic)**: BGE-M3 cosine similarity against `semantic_description` embeddings. Threshold `SEMANTIC_THRESHOLD = 0.4593`.

`post_crisis_check_in` and `psychotic_referral` are in `KEYWORD_SEMANTIC_SKIP` — they are auto-selected via special paths (monitoring state, clinical flag) and are excluded from both tiers. This leaves **25 matchable skills** to test.

The Alec session failure (root cause of this plan) was caused by a missing Tier 1 keyword for a workplace conflict phrase that instead hit the `self_compassion_break` semantic description. The test suite systematically covers all 25 skills so this class of regression is caught early.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `tests/fixtures/wrong_skill/__init__.py` | Create | Package marker |
| `tests/fixtures/wrong_skill/cases.py` | Create | 125 `(skill_id, phrase)` tuples — one source of truth for both test and matrix |
| `tests/test_wrong_skill_routing.py` | Create | Fast Tier 1 collision check (sync) + full correctness assertions (async, `@pytest.mark.slow`) |
| `scripts/coverage_matrix.py` | Create | Standalone diagnostic: runs all 125 through `skill_select_node`, prints per-skill table |

---

## Task 1: Create fixture data

**Files:**
- Create: `tests/fixtures/wrong_skill/__init__.py`
- Create: `tests/fixtures/wrong_skill/cases.py`

- [ ] **Step 1: Write the `__init__.py` package marker**

```python
# tests/fixtures/wrong_skill/__init__.py
```
(Empty file — just needed for Python to treat the directory as a package.)

- [ ] **Step 2: Write `cases.py` with all 125 test cases**

```python
# tests/fixtures/wrong_skill/cases.py
"""125 colloquial routing test cases — 5 phrases per matchable skill.

Each phrase is a realistic user message using emotional/colloquial language rather
than clinical keywords. The goal is to exercise Tier 2 (semantic) coverage and
detect cases where colloquial framing causes misrouting.

Format: list of (skill_id, phrase) tuples.

Known semantic-bleed risks documented inline:
- cognitive_restructuring vs worry_time: "I overthink everything" is a
  cognitive_restructuring keyword — worry_time phrases avoid this word.
- interpersonal_effectiveness vs assertive_communication: close semantic
  overlap; phrases specify relationship vs workplace context.
- psychoed_* three-way: all psychoeducation skills are semantically similar;
  phrases specify the target domain (anxiety/depression/stress).
"""
from __future__ import annotations

WRONG_SKILL_CASES: list[tuple[str, str]] = [

    # ── act_psychological_flexibility ────────────────────────────────────────
    # Keywords include: "I've been dealing with so many things", "everything at once",
    # "anxiety and depression". Semantic: ACT acceptance/defusion/values model.
    ("act_psychological_flexibility", "I've been struggling with so many things at once and I don't know where to start"),
    ("act_psychological_flexibility", "I keep fighting against my own thoughts and it's exhausting me"),
    ("act_psychological_flexibility", "I know what I want to do but anxiety keeps getting in the way"),
    ("act_psychological_flexibility", "I want to stop letting fear make all my decisions for me"),
    ("act_psychological_flexibility", "I keep avoiding things I care about and my world is slowly shrinking"),

    # ── assertive_communication ──────────────────────────────────────────────
    # Keywords include: "can't say no", "saying no", "assertiveness", "express myself",
    # "throwing me under the bus" (added in Alec sprint).
    ("assertive_communication", "I said yes to something I didn't want to do again and now I'm resentful"),
    ("assertive_communication", "Someone threw me under the bus in front of everyone in a meeting today"),
    ("assertive_communication", "I need to confront my manager about something but I freeze every time I try"),
    ("assertive_communication", "I always back down during disagreements even when I know I'm right"),
    ("assertive_communication", "I let people take advantage of me at work and I need to change that"),

    # ── behavioral_activation ────────────────────────────────────────────────
    # Keywords include: "no motivation", "lost motivation", "can't get out of bed",
    # "doing nothing", "lost interest".
    ("behavioral_activation", "I've stopped doing all the things I used to enjoy"),
    ("behavioral_activation", "I haven't left the house in days and I know it's making things worse"),
    ("behavioral_activation", "I lie in bed most of the day because nothing feels worth doing"),
    ("behavioral_activation", "I keep cancelling on everyone because going out feels impossible"),
    ("behavioral_activation", "I've given up on hobbies and socialising and I know it's a cycle"),

    # ── box_breathing ────────────────────────────────────────────────────────
    # Keywords include: "breathing exercise", "breathing technique", "box breathing",
    # "help me breathe", "breathe with me". Phrases below use colloquial framing.
    ("box_breathing", "I need you to walk me through a breathing technique right now"),
    ("box_breathing", "Can you pace me through counting inhales and exhales to calm down?"),
    ("box_breathing", "I need something structured with counts to regulate my breathing"),
    ("box_breathing", "I want to practice a four-count in-and-out pattern to settle myself"),
    ("box_breathing", "I need a timed rhythm to breathe along with right now"),

    # ── cbt_thought_record ───────────────────────────────────────────────────
    # Keywords include: "negative thoughts", "self-blame", "cognitive distortions",
    # "catastrophizing", "failure", "automatic thoughts".
    ("cbt_thought_record", "I'm catastrophizing again but I can't stop myself"),
    ("cbt_thought_record", "I had one mistake and now I've decided I'm terrible at everything"),
    ("cbt_thought_record", "My brain keeps jumping to the worst conclusion with no evidence"),
    ("cbt_thought_record", "I keep assuming people are judging me when I have no actual proof"),
    ("cbt_thought_record", "I told myself I'd fail before I started and now I'm convinced it's true"),

    # ── cognitive_restructuring ──────────────────────────────────────────────
    # Keywords include: "thinking patterns are unhelpful", "mind keeps going to dark places".
    # NOTE: "I overthink everything" is ALSO in cognitive_restructuring keywords —
    # worry_time phrases deliberately avoid this string.
    ("cognitive_restructuring", "My thinking patterns are really unhelpful and I want to change them"),
    ("cognitive_restructuring", "I have a deep-rooted belief that I'm not good enough and I need to challenge it"),
    ("cognitive_restructuring", "I want to examine and rewrite the way I think about myself"),
    ("cognitive_restructuring", "I always assume the worst outcome, I need to understand why and change it"),
    ("cognitive_restructuring", "There's a story I've been telling myself for years that I know isn't true"),

    # ── dbt_tipp ─────────────────────────────────────────────────────────────
    # Keywords include: "overwhelmed", "can't calm down", "flooded",
    # "unbearable feelings", "I can't handle this", "I'm losing it".
    ("dbt_tipp", "I'm completely overwhelmed and nothing is calming me down"),
    ("dbt_tipp", "My emotions are at a ten and normal things aren't working at all"),
    ("dbt_tipp", "I need something physical and intense to bring my body down right now"),
    ("dbt_tipp", "I'm completely flooded and I need an emergency reset"),
    ("dbt_tipp", "Breathing and talking aren't working, I need something much stronger"),

    # ── financial_anxiety ────────────────────────────────────────────────────
    # Keywords include: "kafala visa", "visa depends on my job", "can't send money home",
    # "remittance pressure", "debt". Gulf/MENA context is primary.
    ("financial_anxiety", "My visa is tied to my employment and now I might lose my job"),
    ("financial_anxiety", "I'm drowning in debt and too ashamed to talk about it with anyone"),
    ("financial_anxiety", "I lie awake running numbers wondering if I can make it through the month"),
    ("financial_anxiety", "Money stress is consuming my whole life and I can't concentrate"),
    ("financial_anxiety", "I'm terrified to open any financial statements or look at my bank account"),

    # ── grief_loss ───────────────────────────────────────────────────────────
    # Keywords include: "grief", "bereavement", "lost someone", "someone died",
    # "my father died", specific family member phrases.
    ("grief_loss", "My father passed away a few months ago and I still can't process it"),
    ("grief_loss", "I lost the person I was closest to and I feel completely hollowed out"),
    ("grief_loss", "I keep expecting them to call and then I remember they're not there"),
    ("grief_loss", "I've been numb since the funeral and I don't know if I'm grieving right"),
    ("grief_loss", "There's so much I never got to say to them and it's eating me up"),

    # ── grounding_5_4_3_2_1 ─────────────────────────────────────────────────
    # Keywords include: "panic attack", "panic", "dissociated", "feel disconnected",
    # "heart racing", "nothing feels real", "I feel frozen".
    ("grounding_5_4_3_2_1", "I'm having a full panic attack right now and I can't bring myself back"),
    ("grounding_5_4_3_2_1", "Everything around me feels completely unreal and I'm scared"),
    ("grounding_5_4_3_2_1", "I feel like I'm watching myself from a distance and I can't reconnect"),
    ("grounding_5_4_3_2_1", "I feel completely frozen and disconnected from everything around me"),
    ("grounding_5_4_3_2_1", "I need to anchor myself to something real right now, everything is spinning"),

    # ── interpersonal_effectiveness ──────────────────────────────────────────
    # Keywords include: "navigating relationships", "relationship problems",
    # "relationship conflict". Phrases specify close/personal relationships to
    # distinguish from assertive_communication (which is workplace/general).
    ("interpersonal_effectiveness", "I'm having real problems in my closest relationship and I don't know how to fix it"),
    ("interpersonal_effectiveness", "I need to ask my partner for something important but I don't know how"),
    ("interpersonal_effectiveness", "I always give everything in relationships and I never get what I need back"),
    ("interpersonal_effectiveness", "I want to communicate what I need to my partner without it turning into a fight"),
    ("interpersonal_effectiveness", "I'm losing close relationships because I can't express what I need from people"),

    # ── mi_readiness_ruler ───────────────────────────────────────────────────
    # Keywords include: "want to change", "trying to change", "know I should change",
    # "should stop drinking/smoking".
    ("mi_readiness_ruler", "I know I should change this but I don't know if I actually want to"),
    ("mi_readiness_ruler", "Part of me wants to get better and part of me doesn't see the point"),
    ("mi_readiness_ruler", "I'm not sure how motivated I really am to do what I know I need to do"),
    ("mi_readiness_ruler", "I keep going back and forth about whether I'm actually ready for this"),
    ("mi_readiness_ruler", "I have really mixed feelings about getting help, I don't know where I stand"),

    # ── mindfulness_body_scan ────────────────────────────────────────────────
    # Keywords include: "body scan", "mindfulness body scan", "feel my body",
    # "feel grounded", "body awareness".
    ("mindfulness_body_scan", "I want to do a body scan to reconnect with what I'm feeling"),
    ("mindfulness_body_scan", "I feel completely numb and cut off from my physical self"),
    ("mindfulness_body_scan", "I want something slow and gentle that helps me notice my body"),
    ("mindfulness_body_scan", "I need to get out of my head and feel where I'm holding tension"),
    ("mindfulness_body_scan", "I want to do something present-focused that connects me to my body"),

    # ── mood_check_in ────────────────────────────────────────────────────────
    # Keywords include: "check in", "mood check", "how am I doing", "track my mood".
    ("mood_check_in", "I want to check in on how I'm actually feeling today"),
    ("mood_check_in", "I'm not sure what I'm feeling right now, can you help me figure it out?"),
    ("mood_check_in", "I need to get clear on my emotional state before we do anything else"),
    ("mood_check_in", "I feel like something is off but I can't identify what it is"),
    ("mood_check_in", "I want to take stock of where I am emotionally right now"),

    # ── problem_solving_therapy ──────────────────────────────────────────────
    # Keywords include: "help me solve this", "problem solving", "structured approach",
    # "help me figure out what to do", "don't know what to do".
    ("problem_solving_therapy", "I have a real practical problem and I don't know what to do about it"),
    ("problem_solving_therapy", "I keep going in circles about this situation and can't find a way forward"),
    ("problem_solving_therapy", "I need to break this problem down step by step"),
    ("problem_solving_therapy", "I want to think through all my options in a structured way"),
    ("problem_solving_therapy", "I've been stuck on this issue for weeks and need a clear process"),

    # ── progressive_muscle_relaxation ───────────────────────────────────────
    # Keywords include: "muscle tension", "tense muscles", "tight shoulders",
    # "tension headache", "body is tense", "so tense".
    ("progressive_muscle_relaxation", "My shoulders are so tight they're practically touching my ears"),
    ("progressive_muscle_relaxation", "My whole body feels like it's tied in knots from stress"),
    ("progressive_muscle_relaxation", "I carry all my stress in my muscles and I need to physically release it"),
    ("progressive_muscle_relaxation", "Every muscle in my body feels clenched and I can't let go"),
    ("progressive_muscle_relaxation", "I'm so physically tense from stress I can barely sit still"),

    # ── psychoed_anxiety ─────────────────────────────────────────────────────
    # Keywords include: "what is anxiety", "anxiety explained", "understand anxiety",
    # "why do I panic". Phrases seek education about anxiety mechanisms.
    ("psychoed_anxiety", "I want to understand what anxiety actually is and why my body reacts this way"),
    ("psychoed_anxiety", "Can you explain why I get physical symptoms when I'm not in any real danger?"),
    ("psychoed_anxiety", "Why does my heart race even when nothing is actually wrong?"),
    ("psychoed_anxiety", "I want to learn the science behind anxiety so I can make sense of what I feel"),
    ("psychoed_anxiety", "Nobody ever explained to me why anxiety happens, I want to understand it properly"),

    # ── psychoed_depression ──────────────────────────────────────────────────
    # Keywords include: "what is depression", "depression explained", "am I depressed",
    # "sadness vs depression". Phrases seek education about depression.
    ("psychoed_depression", "I want to understand the difference between regular sadness and depression"),
    ("psychoed_depression", "Can you explain what depression actually does to the brain and body?"),
    ("psychoed_depression", "Why does low mood make even tiny tasks feel completely impossible?"),
    ("psychoed_depression", "I want to learn about depression so I can understand what's happening to me"),
    ("psychoed_depression", "Nobody has ever properly explained to me what depression is and why it works the way it does"),

    # ── psychoed_stress ──────────────────────────────────────────────────────
    # Keywords include: "what is stress", "stress explained", "what does stress do",
    # "acute vs chronic stress". Phrases seek education about stress mechanisms.
    ("psychoed_stress", "I want to understand what chronic stress actually does to the body"),
    ("psychoed_stress", "Can you explain the physical effects of being under constant pressure?"),
    ("psychoed_stress", "I want to learn why stress affects everything from sleep to memory"),
    ("psychoed_stress", "Why does sustained stress make me feel physically ill? I want to understand it"),
    ("psychoed_stress", "I want to understand the connection between the pressure I'm under and how I feel physically"),

    # ── safe_place_visualization ─────────────────────────────────────────────
    # Keywords include: "need to feel safe", "don't feel safe", "want to feel safe",
    # "need a safe space", "safe place".
    ("safe_place_visualization", "I need to imagine a safe place right now to get through this"),
    ("safe_place_visualization", "I want to go somewhere in my mind where I feel completely calm and protected"),
    ("safe_place_visualization", "I need a mental escape right now, somewhere only I can go"),
    ("safe_place_visualization", "I want you to help me visualize somewhere peaceful where nothing can reach me"),
    ("safe_place_visualization", "I need to picture a calm place in my head to get through the next few minutes"),

    # ── self_compassion_break ────────────────────────────────────────────────
    # Keywords include: "self-compassion", "being kind to myself", "too hard on myself",
    # "inner critic", "self-criticism".
    ("self_compassion_break", "I keep beating myself up over this and I can't stop"),
    ("self_compassion_break", "I'm so hard on myself, I'd never speak to anyone else the way I speak to myself"),
    ("self_compassion_break", "I need to find some kindness for myself right now but I don't know how"),
    ("self_compassion_break", "I failed at something and now I'm tearing myself apart over it"),
    ("self_compassion_break", "My inner voice is just non-stop criticism and I'm exhausted by it"),

    # ── sleep_hygiene ────────────────────────────────────────────────────────
    # Keywords include: "can't sleep", "cant sleep", "insomnia", "sleep problems",
    # "sleeping badly", "wake up in the night".
    ("sleep_hygiene", "I haven't slept properly in weeks"),
    ("sleep_hygiene", "I lie awake for hours staring at the ceiling no matter how tired I am"),
    ("sleep_hygiene", "I wake up at 3am every night and I can't get back to sleep"),
    ("sleep_hygiene", "I'm exhausted during the day but then I can't fall asleep when I try"),
    ("sleep_hygiene", "My sleep is completely broken and it's affecting everything else in my life"),

    # ── stop_technique ───────────────────────────────────────────────────────
    # Keywords include: "spiraling", "spiralling", "about to lose it",
    # "cant think straight", "about to react badly".
    ("stop_technique", "I'm spiralling right now and I need something to interrupt it immediately"),
    ("stop_technique", "I'm about to say something I'll really regret, I need to pause right now"),
    ("stop_technique", "My mind is going a hundred miles an hour and I need to slam the brakes"),
    ("stop_technique", "I can feel myself escalating and I need something immediate to break the cycle"),
    ("stop_technique", "I'm in a loop in my head and I need to interrupt it right now before I act on it"),

    # ── values_clarification ─────────────────────────────────────────────────
    # Keywords include: "what do I value", "values clarification", "what matters to me",
    # "living by my values", "I feel lost in life".
    ("values_clarification", "I feel completely lost in life and I don't know what direction to go"),
    ("values_clarification", "I've been doing what other people expect of me and I've completely lost myself"),
    ("values_clarification", "I don't know what I actually care about anymore, everything feels equally empty"),
    ("values_clarification", "I need to figure out what actually matters to me before I can make any decision"),
    ("values_clarification", "I feel like I've been drifting without purpose and I need to find my own direction"),

    # ── worry_time ───────────────────────────────────────────────────────────
    # Keywords include: "can't stop worrying", "cant stop worrying", "worrying all the time",
    # "I keep worrying about everything", "constantly worrying".
    # NOTE: Do NOT use "I overthink everything" — that is a cognitive_restructuring keyword
    # and would route to the wrong skill, giving a misleading failure.
    ("worry_time", "I can't stop worrying, it just runs all day no matter what I do"),
    ("worry_time", "My brain keeps cycling through worst-case scenarios about things I can't control"),
    ("worry_time", "I spend hours every day on worries that probably won't ever happen"),
    ("worry_time", "The anxious thoughts never stop, from the moment I wake up to when I go to sleep"),
    ("worry_time", "I need a way to contain my worrying to a specific time instead of having it run all day"),
]

assert len(WRONG_SKILL_CASES) == 125, f"Expected 125 cases, got {len(WRONG_SKILL_CASES)}"
```

- [ ] **Step 3: Verify the file parses correctly**

```bash
cd /path/to/sage-poc
python -c "from tests.fixtures.wrong_skill.cases import WRONG_SKILL_CASES; print(f'{len(WRONG_SKILL_CASES)} cases loaded')"
```

Expected: `125 cases loaded`

- [ ] **Step 4: Commit the fixture**

```bash
git add tests/fixtures/wrong_skill/__init__.py tests/fixtures/wrong_skill/cases.py
git commit -m "test: add wrong-skill routing fixture (125 colloquial phrases)"
```

---

## Task 2: Write the pytest test file

**Files:**
- Create: `tests/test_wrong_skill_routing.py`

Two test classes:
1. **Fast Tier 1 snapshot** — sync, no BGE-M3, mirrors the production keyword scan. Reveals phrases with no keyword coverage and identifies Tier 1 collisions (phrase routes to wrong skill via keyword).
2. **Full pipeline correctness** — async, `@pytest.mark.slow`, runs `skill_select_node`. Asserts `active_skill_id == expected_skill_id`. Failures = routing gaps to fix.

- [ ] **Step 1: Write the test file**

```python
# tests/test_wrong_skill_routing.py
"""Wrong-skill routing test suite.

125 colloquial phrases — 5 per matchable skill — that should route to a specific skill
but use emotional/everyday language rather than clinical keywords.

Two test layers:
  test_tier1_snapshot        Fast sync check: detects Tier 1 keyword collisions and
                             phrases with zero keyword coverage. No BGE-M3 needed.
  test_full_routing          Slow async check: runs full skill_select_node pipeline,
                             asserts active_skill_id == expected_skill_id.
                             Failures = semantic routing gaps or keyword collisions to fix.

See tests/fixtures/wrong_skill/cases.py for the full phrase list and known-collision notes.
"""
from __future__ import annotations

import pytest

from sage_poc.nodes.skill_select import skill_select_node
from sage_poc.nodes.skill_select import _SKILLS
from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

from tests.fixtures.wrong_skill.cases import WRONG_SKILL_CASES


# ── helpers ──────────────────────────────────────────────────────────────────

def _ss_state(**overrides) -> dict:
    """Minimal state dict for skill_select_node. Mirrors the helper in test_skill_select.py."""
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def _tier1_match(phrase: str) -> str | None:
    """Mirror production Tier 1 scan without async overhead.

    Iterates SKILL_REGISTRY order, skips KEYWORD_SEMANTIC_SKIP, returns the first
    skill whose keyword is a substring of phrase (case-insensitive). Identical logic
    to test_skill_routing_ba_pd._tier1_match — kept local to avoid cross-test coupling.
    """
    phrase_lower = phrase.lower()
    for sid in SKILL_REGISTRY:
        if sid not in _SKILLS or sid in KEYWORD_SEMANTIC_SKIP:
            continue
        for kw in _SKILLS[sid].target_presentations:
            if kw.lower() in phrase_lower:
                return sid
    return None


# ── Tier 1 snapshot (fast, synchronous) ──────────────────────────────────────

@pytest.mark.parametrize("expected_skill,phrase", WRONG_SKILL_CASES)
def test_tier1_snapshot(expected_skill: str, phrase: str) -> None:
    """Tier 1 collision gate: if a phrase matches ANY keyword, it must route to the
    correct skill — not a different one.

    This test does NOT fail on phrases with no keyword match (that is expected for
    semantic-only phrases). It only fails when a phrase hits a keyword in the WRONG
    skill, which is always a bug.

    Use the coverage_matrix.py script to see which phrases have no keyword coverage.
    """
    actual_tier1 = _tier1_match(phrase)
    if actual_tier1 is None:
        # No keyword match at all — will rely on Tier 2. Fine, not a failure here.
        return
    assert actual_tier1 == expected_skill, (
        f"Tier 1 COLLISION: '{phrase}'\n"
        f"  Expected skill : {expected_skill}\n"
        f"  Tier 1 matched : {actual_tier1}\n"
        f"  This phrase hit a keyword belonging to a different skill. "
        f"Fix by removing the colliding keyword or adjusting SKILL_REGISTRY order."
    )


# ── Full pipeline correctness (slow, async) ───────────────────────────────────

@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize("expected_skill,phrase", WRONG_SKILL_CASES)
async def test_full_routing(expected_skill: str, phrase: str) -> None:
    """Full routing assertion: phrase must reach the correct skill via either tier.

    Marked slow because Tier 2 requires BGE-M3 embedding inference. Run with:
        pytest tests/test_wrong_skill_routing.py -m slow -v

    A failure means the phrase routed to the wrong skill or to None. Each failure is
    a documented gap — either Tier 1 keyword coverage is missing, or Tier 2 semantic
    match is too weak / is dominated by a different skill's embedding.

    The coverage_matrix.py script provides per-skill aggregate data to prioritise fixes.
    """
    state = _ss_state(
        message_en=phrase,
        raw_message=phrase,
        detected_language="en",
        primary_intent="new_skill",
    )
    result = await skill_select_node(state)
    actual_skill = result.get("active_skill_id")
    method = result.get("skill_match_method")
    score = result.get("semantic_score")

    assert actual_skill == expected_skill, (
        f"ROUTING MISS: '{phrase}'\n"
        f"  Expected : {expected_skill}\n"
        f"  Got      : {actual_skill!r}  (method={method!r}, score={score})\n"
        f"  Fix options:\n"
        f"    Tier 1: Add colloquial phrase to {expected_skill} target_presentations\n"
        f"    Tier 2: Verify semantic_description is technique-identity only (no symptom language)\n"
        f"    See docs/SKILL_AUTHORING_CONVENTIONS.md for authoring standards."
    )
```

- [ ] **Step 2: Run the fast Tier 1 test to verify no immediate errors**

```bash
cd /path/to/sage-poc
python -m pytest tests/test_wrong_skill_routing.py -k "test_tier1_snapshot" -v --tb=short 2>&1 | tail -30
```

Expected: All 125 tests pass or some fail with `COLLISION:` in the error. Any `COLLISION` failure is a real bug; investigate and fix before committing.

- [ ] **Step 3: Commit the test file**

```bash
git add tests/test_wrong_skill_routing.py
git commit -m "test: add wrong-skill routing correctness suite (125 phrases)"
```

---

## Task 3: Write the coverage matrix script

**Files:**
- Create: `scripts/coverage_matrix.py`

This script runs all 125 phrases through `skill_select_node` (full pipeline including BGE-M3), collects results, and prints a per-skill table showing Tier 1 hits, Tier 2 correct hits, Tier 2 wrong hits, and no-matches.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
# scripts/coverage_matrix.py
"""Wrong-skill routing coverage matrix.

Runs all 125 colloquial phrases from tests/fixtures/wrong_skill/cases.py through
the production skill_select_node and prints a per-skill coverage table.

Usage:
    cd sage-poc
    python scripts/coverage_matrix.py

Output columns:
  T1     — Tier 1 (keyword) match, correct skill
  T2-OK  — Tier 2 (semantic) match, correct skill
  T2-ERR — Tier 2 match, WRONG skill (semantic bleed)
  MISS   — No match at all (active_skill_id is None)
  TOTAL  — always 5 per skill

High T1 with 0 T2-OK means the skill has zero semantic coverage — risky if new colloquial
phrases don't happen to use known keywords.
High T2-ERR or high MISS = priority targets for Tier 1 keyword expansion.
"""
from __future__ import annotations

import asyncio
import sys
import os

# Ensure sage_poc is importable when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from sage_poc.nodes.skill_select import skill_select_node
from tests.fixtures.wrong_skill.cases import WRONG_SKILL_CASES


def _make_state(phrase: str) -> dict:
    return {
        "raw_message": phrase,
        "detected_language": "en",
        "message_en": phrase,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": "new_skill",
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }


async def run_all() -> list[dict]:
    results = []
    total = len(WRONG_SKILL_CASES)
    for i, (expected_skill, phrase) in enumerate(WRONG_SKILL_CASES, 1):
        print(f"\r  Running {i}/{total}...", end="", flush=True)
        state = _make_state(phrase)
        result = await skill_select_node(state)
        actual = result.get("active_skill_id")
        method = result.get("skill_match_method")
        score = result.get("semantic_score")

        if actual == expected_skill and method == "keyword":
            category = "T1"
        elif actual == expected_skill and method == "semantic":
            category = "T2-OK"
        elif actual != expected_skill and actual is not None:
            category = "T2-ERR"
        else:
            category = "MISS"

        results.append({
            "expected": expected_skill,
            "actual": actual,
            "method": method,
            "score": score,
            "phrase": phrase,
            "category": category,
        })
    print()  # newline after progress
    return results


def print_matrix(results: list[dict]) -> None:
    # Aggregate by expected skill
    from collections import defaultdict
    by_skill: dict[str, dict[str, int]] = defaultdict(lambda: {"T1": 0, "T2-OK": 0, "T2-ERR": 0, "MISS": 0})
    for r in results:
        by_skill[r["expected"]][r["category"]] += 1

    col_w = 38
    print()
    print(f"{'Skill':<{col_w}} {'T1':>5} {'T2-OK':>6} {'T2-ERR':>7} {'MISS':>6} {'TOTAL':>6}")
    print("-" * (col_w + 35))

    t1_total = t2ok_total = t2err_total = miss_total = 0
    for skill in sorted(by_skill):
        counts = by_skill[skill]
        t1 = counts["T1"]
        t2ok = counts["T2-OK"]
        t2err = counts["T2-ERR"]
        miss = counts["MISS"]
        total_row = t1 + t2ok + t2err + miss
        flag = " ⚠" if (t2err > 0 or miss > 0) else ""
        print(f"{skill:<{col_w}} {t1:>5} {t2ok:>6} {t2err:>7} {miss:>6} {total_row:>6}{flag}")
        t1_total += t1
        t2ok_total += t2ok
        t2err_total += t2err
        miss_total += miss

    print("-" * (col_w + 35))
    grand_total = t1_total + t2ok_total + t2err_total + miss_total
    print(f"{'TOTAL':<{col_w}} {t1_total:>5} {t2ok_total:>6} {t2err_total:>7} {miss_total:>6} {grand_total:>6}")
    print()
    print("T1=keyword, T2-OK=semantic correct, T2-ERR=semantic wrong skill, MISS=no match")
    print(f"⚠  = needs attention ({t2err_total} T2-ERR + {miss_total} MISS = {t2err_total+miss_total} gaps)")


def print_failures(results: list[dict]) -> None:
    failures = [r for r in results if r["category"] in ("T2-ERR", "MISS")]
    if not failures:
        print("\nNo routing failures — all 125 phrases routed correctly.")
        return

    print(f"\n{'─'*70}")
    print(f"ROUTING FAILURES ({len(failures)} phrases):")
    print(f"{'─'*70}")
    for r in sorted(failures, key=lambda x: (x["expected"], x["category"])):
        print(f"\n  [{r['category']}] Expected: {r['expected']}")
        print(f"          Actual:   {r['actual']!r} (score={r['score']})")
        print(f"          Phrase:   {r['phrase']!r}")


if __name__ == "__main__":
    print("Loading BGE-M3 and running 125 phrases through skill_select_node...")
    print("(First run takes ~30s for model warmup; subsequent runs are faster)")
    results = asyncio.run(run_all())
    print_matrix(results)
    print_failures(results)
```

- [ ] **Step 2: Verify the script is importable**

```bash
cd /path/to/sage-poc
python -c "import ast; ast.parse(open('scripts/coverage_matrix.py').read()); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit the script**

```bash
git add scripts/coverage_matrix.py
git commit -m "script: add wrong-skill routing coverage matrix"
```

---

## Task 4: Run the fast tests and interpret results

- [ ] **Step 1: Run the Tier 1 snapshot test**

```bash
cd /path/to/sage-poc
python -m pytest tests/test_wrong_skill_routing.py -k "test_tier1_snapshot" -v --tb=short 2>&1 | tee /tmp/tier1_results.txt
grep -E "PASSED|FAILED|ERROR" /tmp/tier1_results.txt | tail -30
```

Expected: All 125 pass. If any fail with `COLLISION`, a phrase is being stolen by a different skill's keyword. That is a bug — fix before proceeding to slow tests.

- [ ] **Step 2: Interpret any Tier 1 collision failures**

If `test_tier1_snapshot[assertive_communication-I said yes...]` fails with route = `interpersonal_effectiveness`, then `interpersonal_effectiveness` has a shorter keyword that is a substring of the phrase. Check `test_skill_routing_ba_pd._KNOWN_SUBSTRING_SHADOWS` — if it is a known pre-existing collision it is already documented. If new, it needs a fix.

Fix procedure: look at the colliding keyword in the wrong skill and either (a) remove it if it is too broad, or (b) rewrite the test phrase to avoid the collision.

- [ ] **Step 3: Run the coverage matrix script**

```bash
cd /path/to/sage-poc
python scripts/coverage_matrix.py 2>&1 | tee /tmp/coverage_matrix_baseline.txt
cat /tmp/coverage_matrix_baseline.txt
```

Expected output format (exact values will vary):
```
Loading BGE-M3 and running 125 phrases through skill_select_node...
(First run takes ~30s for model warmup; subsequent runs are faster)
  Running 125/125...

Skill                                  T1    T2-OK  T2-ERR    MISS   TOTAL
-----------------------------------------------------------------------
act_psychological_flexibility           2      2      1       0       5 ⚠
assertive_communication                 2      2      0       1       5 ⚠
...
```

- [ ] **Step 4: Read the failure list and copy the gap count to a comment**

Open `/tmp/coverage_matrix_baseline.txt` and note the total gap count (T2-ERR + MISS). Add a comment to `cases.py` with the baseline:

```python
# Baseline run 2026-06-08: X T2-ERR + Y MISS = Z total gaps across 25 skills.
# Re-run scripts/coverage_matrix.py after any target_presentations edit to track progress.
```

Edit `tests/fixtures/wrong_skill/cases.py` to add this comment at the top, then:

```bash
git add tests/fixtures/wrong_skill/cases.py
git commit -m "test: record baseline coverage matrix result in cases.py"
```

---

## Task 5: Run the slow full-pipeline test suite and document failures

This task verifies that the slow test suite correctly identifies existing gaps and that all infrastructure is working.

- [ ] **Step 1: Run a single slow test to verify the async infrastructure works**

```bash
cd /path/to/sage-poc
python -m pytest "tests/test_wrong_skill_routing.py::test_full_routing[worry_time-I can't stop worrying, it just runs all day no matter what I do]" -m slow -v --tb=short
```

Expected: PASSED (this phrase contains the `can't stop worrying` keyword, so it will route correctly via Tier 1).

- [ ] **Step 2: Run the full slow suite and capture results**

```bash
cd /path/to/sage-poc
python -m pytest tests/test_wrong_skill_routing.py -m slow -v --tb=line 2>&1 | tee /tmp/slow_suite_results.txt
grep -c "PASSED" /tmp/slow_suite_results.txt
grep -c "FAILED" /tmp/slow_suite_results.txt
```

Expected: Some failures. Each `FAILED` test is a routing gap. The failure messages include the exact skill, actual result, method, and score to guide the fix.

- [ ] **Step 3: Commit final state and record gap count**

```bash
git add -p  # stage any local edits from steps above
git commit -m "test: wrong-skill routing suite — baseline established, gaps documented"
```

---

## Self-Review

### Spec coverage

| Requirement | Covered by |
|------------|-----------|
| 5 phrases per skill | `cases.py` (verified by `assert len == 125`) |
| Colloquial/emotional language | All phrases are lay-language descriptions |
| Records Tier 1 / Tier 2 / wrong / no-match | `test_tier1_snapshot` + `test_full_routing` + `coverage_matrix.py` |
| Coverage matrix output | `scripts/coverage_matrix.py` T1/T2-OK/T2-ERR/MISS columns |
| CI enforcement | `test_full_routing` fails on wrong routing |
| Addresses RT-4 regression class | Tests directly exercise the Alec session failure pattern |

### Known gaps intentionally out of scope

- **Arabic phrases**: 25 Arabic equivalents (5 per skill) are a separate task — they require native-speaker review (see `project_arabic_rule_id_status.md`).
- **Passive SI / SF-1**: Safety-path tests belong in `test_safety_node_integration.py`, not skill routing.
- **psychoed_* three-way semantic bleed**: Known close-cluster issue; `calibrate_threshold.py` handles the within-cluster decision. If T2-ERR shows psychoed_anxiety routing to psychoed_depression, that is expected within-cluster ambiguity, not a test failure to fix.

### Placeholder scan

No placeholders — all code is complete. Baseline numbers in Task 4 Step 4 are filled in after the first run, which is the correct sequence.

### Type consistency

- `_make_state()` in `coverage_matrix.py` matches `_ss_state()` field names in `test_wrong_skill_routing.py`
- Both import from `tests.fixtures.wrong_skill.cases` — single source of truth
- `skill_select_node` return keys (`active_skill_id`, `skill_match_method`, `semantic_score`) verified against `skill_select.py:176-184`
