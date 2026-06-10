"""
Per-skill routing analysis against the production SageAI API.

Tests each skill with 5 phrase varieties to reveal exactly where activation gaps are:
  DIRECT   — explicit technique request ("I want to try X") — must always work
  KEYWORD  — phrase containing a Tier-1 keyword — should work when routed to skill_select
  SYMPTOM  — natural symptom description — many legitimately go to freeflow first
  SYMPTOM2 — second symptom variant
  OBLIQUE  — indirect/culturally specific presentation — diagnostic only

Routing outcomes:
  ✓  SKILL   — correct skill selected
  ~  FREEFLOW — no skill selected (empathic response; may be appropriate for symptom phrases)
  ~  KNOWLEDGE — info_request routed to knowledge_retrieve (expected for psychoed)
  ✗  WRONG   — a different skill was selected

Usage:
    python scripts/per_skill_routing_test.py               # all skills
    python scripts/per_skill_routing_test.py sleep_hygiene  # one skill
    python scripts/per_skill_routing_test.py --local        # run against localhost:8765

Requires: pip install httpx
"""

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

try:
    import httpx
except ImportError:
    print("Missing httpx — run: pip install httpx")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROD_URL   = "https://sage-api-production-3328.up.railway.app"
LOCAL_URL  = "http://localhost:8765"
SAGE_API_KEY = os.environ.get(
    "SAGE_API_KEY",
    "8384792dfb576c5d7b975f40c4f21a8eb82fb024eb243570dc1cc9f7a871b328",
)
TIMEOUT    = 90.0
CONCURRENCY = 4  # conservative — production is shared infra
_RUN_ID    = str(int(time.time()))[-6:]

# Psychoed cluster — any member is correct
PSYCHOED_CLUSTER = {"psychoed_anxiety", "psychoed_depression", "psychoed_stress"}


# ---------------------------------------------------------------------------
# Per-skill phrase sets
# phrase type order: DIRECT | KEYWORD | SYMPTOM | SYMPTOM2 | OBLIQUE
# ---------------------------------------------------------------------------

# Format: (phrase_type, phrase_text)
SKILL_PHRASES: dict[str, list[tuple[str, str]]] = {

    "behavioral_activation": [
        ("DIRECT",   "I need help getting active again — can you walk me through a structured plan to start doing things?"),
        ("KEYWORD",  "I've given up on hobbies and socialising and I know it's a cycle I need to break"),
        ("KEYWORD",  "I've stopped doing all the things I used to love and I need to get back to them"),
        ("SYMPTOM",  "I've stopped doing all the things I used to enjoy"),
        ("SYMPTOM2", "I lie in bed most of the day because nothing feels worth doing"),
    ],

    "box_breathing": [
        ("DIRECT",   "Can you pace me through a four-count breathing exercise right now?"),
        ("KEYWORD",  "I need a timed rhythm to breathe along with right now"),
        ("KEYWORD",  "I need you to walk me through a breathing technique right now"),
        ("SYMPTOM",  "My heart is racing and I can't calm down — I need to breathe"),
        ("SYMPTOM2", "I'm really anxious right now and I need something to do with my breath"),
    ],

    "cbt_thought_record": [
        ("DIRECT",   "Can you help me do a thought record for this situation?"),
        ("KEYWORD",  "I'm catastrophizing and I need help examining my thinking"),
        ("KEYWORD",  "My brain keeps jumping to the worst conclusion with no evidence"),
        ("SYMPTOM",  "I had one mistake and now I've decided I'm terrible at everything"),
        ("SYMPTOM2", "I keep assuming people are judging me when I have no actual proof"),
    ],

    "cognitive_restructuring": [
        ("DIRECT",   "I want to work on restructuring my thought patterns — can you help?"),
        ("KEYWORD",  "I want to examine and rewrite the way I think about myself"),
        ("KEYWORD",  "There's a deep-rooted belief that I fall short and I need to challenge it"),
        ("SYMPTOM",  "I have a story I've been telling myself for years that I know isn't true"),
        ("SYMPTOM2", "I always assume the worst outcome and I need to understand why"),
    ],

    "grounding_5_4_3_2_1": [
        ("DIRECT",   "Can you walk me through the 5-4-3-2-1 grounding exercise?"),
        ("KEYWORD",  "I'm having a full panic attack and I need something to anchor myself right now"),
        ("KEYWORD",  "Everything around me feels completely unreal and I'm scared — I need to ground myself"),
        ("SYMPTOM",  "I feel completely disconnected from everything around me right now"),
        ("OBLIQUE",  "I feel like I'm watching myself from a distance and I can't reconnect"),
    ],

    "dbt_tipp": [
        ("DIRECT",   "I need the DBT TIPP skill — my emotions are at a 10 and nothing is helping"),
        ("KEYWORD",  "I'm completely flooded and I need an emergency reset"),
        ("KEYWORD",  "Breathing isn't working, I need something physical and intense right now"),
        ("SYMPTOM",  "I'm completely overwhelmed and nothing is calming me down"),
        ("SYMPTOM2", "My emotions are so high I can't think straight"),
    ],

    "safe_place_visualization": [
        ("DIRECT",   "Can you guide me through a safe place visualization?"),
        ("KEYWORD",  "I need to imagine a safe place right now to get through this"),
        ("KEYWORD",  "I want you to help me visualize somewhere peaceful where nothing can reach me"),
        ("SYMPTOM",  "I need a mental escape right now, somewhere calm I can go in my head"),
        ("OBLIQUE",  "I just want to go somewhere in my mind where I feel completely safe"),
    ],

    "progressive_muscle_relaxation": [
        ("DIRECT",   "Can you guide me through progressive muscle relaxation?"),
        ("KEYWORD",  "My whole body is tense all over and I need to release it"),
        ("KEYWORD",  "My whole body feels like it's tied in knots from stress and I can't release it"),
        ("SYMPTOM",  "My shoulders are so tight they're practically touching my ears"),
        ("SYMPTOM2", "I carry all my stress in my muscles and I need to physically release it"),
    ],

    "stop_technique": [
        ("DIRECT",   "I need the STOP technique right now — I'm about to react badly"),
        ("KEYWORD",  "I'm spiralling and I need something to interrupt it immediately"),
        ("KEYWORD",  "I can feel myself escalating and I need something immediate to break the cycle"),
        ("SYMPTOM",  "I'm about to say something I'll really regret and I need to pause"),
        ("SYMPTOM2", "My mind is racing and I can't slow it down before I do something"),
    ],

    "worry_time": [
        ("DIRECT",   "Can you help me set up a structured worry time?"),
        ("KEYWORD",  "I need a way to contain my worrying to a specific time instead of all day"),
        ("KEYWORD",  "The anxious thoughts never stop, from the moment I wake up"),
        ("SYMPTOM",  "I can't stop worrying, it just runs all day no matter what I do"),
        ("SYMPTOM2", "My brain keeps cycling through worst-case scenarios I can't control"),
    ],

    "mindfulness_body_scan": [
        ("DIRECT",   "Can you guide me through a body scan meditation?"),
        ("KEYWORD",  "I want to do a body scan to reconnect with what I'm feeling"),
        ("KEYWORD",  "I need to get out of my head and feel where I'm holding tension"),
        ("SYMPTOM",  "I feel completely numb and cut off from my physical self"),
        ("SYMPTOM2", "I want something slow and gentle that helps me notice my body"),
    ],

    "self_compassion_break": [
        ("DIRECT",   "Can you walk me through a self-compassion break?"),
        ("KEYWORD",  "I keep beating myself up over this and I can't stop"),
        ("KEYWORD",  "I need to find some kindness for myself but I don't know how"),
        ("SYMPTOM",  "I'd never speak to anyone else the way I speak to myself"),
        ("SYMPTOM2", "I failed at something and now I'm tearing myself apart over it"),
    ],

    "sleep_hygiene": [
        ("DIRECT",   "Can you help me build better sleep habits?"),
        ("KEYWORD",  "I can't sleep and I lie awake for hours every night"),
        ("KEYWORD",  "I wake up at 3am and can't get back to sleep"),
        ("SYMPTOM",  "I haven't slept properly in weeks"),
        ("SYMPTOM2", "I'm exhausted during the day but I can't fall asleep at night"),
    ],

    "mood_check_in": [
        ("DIRECT",   "Can we do a quick mood check-in?"),
        ("KEYWORD",  "I want to check in on how I'm feeling today"),
        ("KEYWORD",  "I'm not sure what I'm feeling right now, can you help me figure it out?"),
        ("SYMPTOM",  "I feel like something is off but I can't identify what it is"),
        ("SYMPTOM2", "I want to take stock of where I am emotionally right now"),
    ],

    "mi_readiness_ruler": [
        ("DIRECT",   "I want to rate my readiness for change — can you help me with a readiness ruler?"),
        ("KEYWORD",  "I know I should change this but I don't know if I actually want to"),
        ("KEYWORD",  "I keep going back and forth about whether I'm actually ready for this"),
        ("SYMPTOM",  "Part of me wants to get better and part of me doesn't see the point"),
        ("SYMPTOM2", "I have really mixed feelings about getting help, I don't know where I stand"),
    ],

    "values_clarification": [
        ("DIRECT",   "I need help figuring out what I actually value — can we do a values exercise?"),
        ("KEYWORD",  "I feel completely lost in life and I don't know what direction to go"),
        ("KEYWORD",  "I've been doing what other people expect of me and I've lost myself"),
        ("SYMPTOM",  "I don't know what I actually care about anymore, everything feels empty"),
        ("SYMPTOM2", "I feel like I've been drifting without purpose and I need to find my direction"),
    ],

    "problem_solving_therapy": [
        ("DIRECT",   "I need a structured problem-solving approach — can you walk me through it?"),
        ("KEYWORD",  "I need to break this problem down step by step"),
        ("KEYWORD",  "I have a real practical problem and I don't know what to do about it"),
        ("SYMPTOM",  "I've been stuck on the same issue for weeks and I can't find a solution"),
        ("SYMPTOM2", "I want to think through all my options in a structured way"),
    ],

    "assertive_communication": [
        ("DIRECT",   "Can you help me practice assertive communication?"),
        ("KEYWORD",  "I need to confront my manager but I freeze every time I try"),
        ("KEYWORD",  "I always back down during disagreements even when I know I'm right"),
        ("SYMPTOM",  "I said yes to something I didn't want to do again and now I'm resentful"),
        ("SYMPTOM2", "I let people take advantage of me and I need to stop that"),
    ],

    "interpersonal_effectiveness": [
        ("DIRECT",   "Can you help me with interpersonal effectiveness skills for this relationship?"),
        ("KEYWORD",  "I need to ask my partner for something important but I don't know how"),
        ("KEYWORD",  "I need help setting limits in this relationship without damaging it"),
        ("SYMPTOM",  "I want to communicate what I need without it turning into a fight"),
        ("OBLIQUE",  "I always give everything in relationships and I never get what I need back"),
    ],

    "grief_loss": [
        ("DIRECT",   "I need help processing grief — can you guide me?"),
        ("KEYWORD",  "My father passed away and I still can't process it"),
        ("KEYWORD",  "I lost the person I was closest to and I feel completely hollowed out"),
        ("SYMPTOM",  "I keep expecting them to call and then I remember they're not there"),
        ("SYMPTOM2", "I've been numb since the funeral and I don't know if I'm grieving right"),
    ],

    "financial_anxiety": [
        ("DIRECT",   "I need help managing financial anxiety — can you walk me through it?"),
        ("KEYWORD",  "I have financial stress that's consuming my life and causing anxiety"),
        ("KEYWORD",  "I can't stop mentally calculating whether my money will last the month"),
        ("SYMPTOM",  "Money stress is consuming my whole life and I can't concentrate"),
        ("SYMPTOM2", "I'm terrified to even look at my bank account"),
    ],

    "act_psychological_flexibility": [
        ("DIRECT",   "I want to work on psychological flexibility with ACT — can you help?"),
        ("KEYWORD",  "I keep avoiding things I care about and my world is slowly shrinking"),
        ("KEYWORD",  "I want to stop letting fear make all my decisions for me"),
        ("SYMPTOM",  "I know what I want to do but anxiety keeps getting in the way"),
        ("SYMPTOM2", "I keep fighting against my own thoughts and it's exhausting"),
    ],

    "psychoed_anxiety": [
        ("DIRECT",   "Can you explain to me what anxiety actually is and why it happens?"),
        ("KEYWORD",  "I want to understand what anxiety actually is and why my body reacts this way"),
        ("KEYWORD",  "Can you explain why I get physical symptoms when I'm not in real danger?"),
        ("SYMPTOM",  "Why does my heart race even when nothing is actually wrong?"),
        ("SYMPTOM2", "I want to learn the science behind anxiety so I can make sense of what I feel"),
    ],

    "psychoed_depression": [
        ("DIRECT",   "Can you explain what depression actually is and how it affects the brain?"),
        ("KEYWORD",  "I want to understand the difference between sadness and clinical depression"),
        ("KEYWORD",  "Can you explain what depression does to the brain and body?"),
        ("SYMPTOM",  "I want to learn about depression so I can understand what's happening to me"),
        ("SYMPTOM2", "Nobody has ever explained to me what depression is and how it works"),
    ],

    "psychoed_stress": [
        ("DIRECT",   "Can you explain the effects of chronic stress on the body?"),
        ("KEYWORD",  "I want to understand what chronic stress actually does to the body"),
        ("KEYWORD",  "Can you explain the physical effects of being under constant pressure?"),
        ("SYMPTOM",  "I want to understand why stress makes me feel physically ill"),
        ("SYMPTOM2", "I've been under sustained pressure for months and I want to understand what it's doing to me"),
    ],
}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

@dataclass
class PhraseResult:
    skill_id_target: str
    phrase_type: str
    phrase: str
    routed_skill: str
    node_path: list
    intent: str
    mechanism: str  # keyword | semantic | info_request | freeflow | other
    elapsed_s: float
    response_preview: str  # first 120 chars of response

    @property
    def outcome(self) -> str:
        if not self.routed_skill:
            if "knowledge_retrieve" in self.node_path:
                return "KNOWLEDGE"
            return "FREEFLOW"
        if self.routed_skill == self.skill_id_target:
            return "CORRECT"
        if self.skill_id_target in PSYCHOED_CLUSTER and self.routed_skill in PSYCHOED_CLUSTER:
            return "CORRECT"
        return "WRONG"

    @property
    def outcome_sym(self) -> str:
        return {"CORRECT": "✓", "FREEFLOW": "~", "KNOWLEDGE": "≈", "WRONG": "✗"}.get(self.outcome, "?")


async def run_phrase(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    skill_id: str,
    phrase_type: str,
    phrase: str,
) -> PhraseResult:
    session_id = f"perskill-{_RUN_ID}-{uuid.uuid4().hex[:8]}"
    t0 = time.monotonic()
    try:
        async with sem:
            # Use stream() to consume the full body before reading headers.
            # StreamingResponse headers can be empty under concurrent load with post().
            async with client.stream(
                "POST",
                f"{_API_URL}/chat",
                headers=_HEADERS,
                json={"messages": [{"role": "user", "content": phrase}], "session_id": session_id},
                timeout=TIMEOUT,
            ) as resp:
                raw_body = await resp.aread()
    except Exception as exc:
        return PhraseResult(
            skill_id_target=skill_id, phrase_type=phrase_type, phrase=phrase,
            routed_skill="", node_path=[], intent="", mechanism="error",
            elapsed_s=time.monotonic() - t0, response_preview=f"ERROR: {exc}",
        )

    elapsed = time.monotonic() - t0
    routed = resp.headers.get("x-sage-skill-id", "")
    path = json.loads(resp.headers.get("x-sage-node-path", "[]"))
    intent = resp.headers.get("x-sage-intent", "")
    method = resp.headers.get("x-sage-gate-path", "") or (
        "keyword" if "keyword" in str(resp.headers.get("x-sage-semantic-score", "")) else ""
    )
    # Infer mechanism from path + headers
    skill_method = ""
    if routed:
        sem_score = resp.headers.get("x-sage-semantic-score", "")
        skill_method = f"semantic({sem_score})" if sem_score else "keyword"
    elif "knowledge_retrieve" in path:
        skill_method = "info_request→rag"
    elif "freeflow_respond" in path:
        skill_method = f"freeflow(intent={intent})"
    elif "crisis_response" in path:
        skill_method = "CRISIS"

    preview = raw_body.decode(errors="replace")[:120].replace("\n", " ").strip()

    return PhraseResult(
        skill_id_target=skill_id,
        phrase_type=phrase_type,
        phrase=phrase,
        routed_skill=routed,
        node_path=path,
        intent=intent,
        mechanism=skill_method,
        elapsed_s=elapsed,
        response_preview=preview,
    )


async def test_skill(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    skill_id: str,
) -> list[PhraseResult]:
    phrases = SKILL_PHRASES.get(skill_id)
    if not phrases:
        print(f"  No phrases defined for skill '{skill_id}'")
        return []
    tasks = [
        asyncio.create_task(run_phrase(client, sem, skill_id, ptype, phrase))
        for ptype, phrase in phrases
    ]
    return await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

OUTCOME_COLORS = {
    "CORRECT":   "\033[32m",  # green
    "FREEFLOW":  "\033[33m",  # yellow
    "KNOWLEDGE": "\033[36m",  # cyan
    "WRONG":     "\033[31m",  # red
}
RESET = "\033[0m"


def print_skill_results(skill_id: str, results: list[PhraseResult]) -> dict:
    correct = sum(1 for r in results if r.outcome == "CORRECT")
    freeflow = sum(1 for r in results if r.outcome == "FREEFLOW")
    knowledge = sum(1 for r in results if r.outcome == "KNOWLEDGE")
    wrong = sum(1 for r in results if r.outcome == "WRONG")
    total = len(results)

    header_color = "\033[32m" if correct == total else ("\033[31m" if wrong > 0 else "\033[33m")
    print(f"\n  {header_color}{'─'*60}{RESET}")
    print(f"  {header_color}{skill_id.upper()}{RESET}   "
          f"correct={correct}/{total}  freeflow={freeflow}  wrong={wrong}")
    print(f"  {'─'*60}")

    for r in sorted(results, key=lambda x: x.phrase_type):
        color = OUTCOME_COLORS.get(r.outcome, "")
        routed_label = r.routed_skill if r.routed_skill else f"[{r.outcome.lower()}]"
        print(f"  {color}{r.outcome_sym} {r.phrase_type:<9}{RESET}  {r.phrase[:65]:<65}  → {routed_label}")
        if r.outcome == "WRONG":
            print(f"    {'':9}  mechanism: {r.mechanism}")
        if r.outcome == "FREEFLOW" and r.phrase_type == "KEYWORD":
            print(f"    {'':9}  intent classified as: {r.intent} (never reached skill_select)")

    # Gap analysis
    freeflow_keywords = [r for r in results if r.outcome == "FREEFLOW" and r.phrase_type == "KEYWORD"]
    if freeflow_keywords:
        print(f"\n  ⚠ KEYWORD phrases routed to freeflow — intent router gap:")
        for r in freeflow_keywords:
            print(f"    '{r.phrase[:70]}'")
            print(f"    → intent={r.intent!r} — never reached skill_select")

    wrong_results = [r for r in results if r.outcome == "WRONG"]
    if wrong_results:
        print(f"\n  ✗ Wrong skill selected:")
        for r in wrong_results:
            print(f"    '{r.phrase[:70]}'")
            print(f"    → got '{r.routed_skill}' via {r.mechanism}")

    return {"skill_id": skill_id, "correct": correct, "freeflow": freeflow,
            "knowledge": knowledge, "wrong": wrong, "total": total}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_API_URL: str = PROD_URL
_HEADERS: dict = {}


async def main(target_skills: list[str], use_local: bool):
    global _API_URL, _HEADERS
    _API_URL = LOCAL_URL if use_local else PROD_URL
    _HEADERS = {"Content-Type": "application/json"}
    if not use_local:
        _HEADERS["X-Sage-Api-Key"] = SAGE_API_KEY

    skills_to_test = target_skills or list(SKILL_PHRASES.keys())

    print(f"\n{'='*70}")
    print(f"  Per-Skill Routing Analysis")
    print(f"  URL    : {_API_URL}")
    print(f"  Skills : {len(skills_to_test)}   Phrases/skill: 5")
    print(f"  Run ID : {_RUN_ID}")
    print(f"{'='*70}")

    # Health check
    try:
        async with httpx.AsyncClient(timeout=10) as probe:
            hr = await probe.get(f"{_API_URL}/health/ready")
            print(f"  /health/ready → {hr.status_code}  {hr.text[:50]}")
            if hr.status_code != 200:
                print("  Server not ready — aborting.")
                return
    except Exception as e:
        print(f"  Health check failed: {e}")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    summaries = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if len(skills_to_test) == 1:
            # Single skill: run all 5 phrases, print immediately
            results = await test_skill(client, sem, skills_to_test[0])
            summary = print_skill_results(skills_to_test[0], results)
            summaries.append(summary)
        else:
            # Multiple skills: run skill by skill for readable output
            for skill_id in skills_to_test:
                results = await test_skill(client, sem, skill_id)
                summary = print_skill_results(skill_id, results)
                summaries.append(summary)

    # Summary table
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY TABLE")
    print(f"  {'Skill':<35}  {'✓':>5}  {'~freeflow':>9}  {'≈rag':>4}  {'✗wrong':>6}")
    print(f"  {'─'*35}  {'─'*5}  {'─'*9}  {'─'*4}  {'─'*6}")
    for s in summaries:
        flag = "  ←" if s["wrong"] > 0 else ("  ↗" if s["freeflow"] >= 3 else "")
        print(f"  {s['skill_id']:<35}  {s['correct']:>5}  {s['freeflow']:>9}  "
              f"{s['knowledge']:>4}  {s['wrong']:>6}{flag}")
    print(f"{'='*70}")

    total_correct = sum(s["correct"] for s in summaries)
    total_phrases = sum(s["total"] for s in summaries)
    total_wrong   = sum(s["wrong"] for s in summaries)
    print(f"\n  Overall: {total_correct}/{total_phrases} correct  "
          f"{total_wrong} wrong-skill  "
          f"{sum(s['freeflow'] for s in summaries)} freeflow")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]
    use_local = "--local" in args
    if use_local:
        args.remove("--local")

    target_skills = []
    for arg in args:
        if arg in SKILL_PHRASES:
            target_skills.append(arg)
        else:
            print(f"Unknown skill '{arg}'. Available:")
            for s in sorted(SKILL_PHRASES.keys()):
                print(f"  {s}")
            sys.exit(1)

    asyncio.run(main(target_skills, use_local))
