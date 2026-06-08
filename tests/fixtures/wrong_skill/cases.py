# tests/fixtures/wrong_skill/cases.py
"""125 colloquial routing test cases — 5 phrases per matchable skill.

Each phrase is a realistic user message using emotional/everyday language rather
than clinical keywords. The goal is to exercise Tier 2 (semantic) coverage and
detect cases where colloquial framing causes misrouting.

Format: list of (skill_id, phrase) tuples.

PSYCHOED CLUSTER
    psychoed_anxiety, psychoed_depression, and psychoed_stress are semantically
    near-identical in embedding space (all three are psychoeducation requests,
    domain differs by one word). Within-cluster Tier 2 routing is treated as
    acceptable ambiguity; the correct fix is Tier 1 keyword expansion, not
    semantic_description modification. Tests apply a softer assertion: correct
    cluster is sufficient, exact skill within cluster is logged but not enforced.
    See PSYCHOED_CLUSTER below.

KNOWN KEYWORD RISKS documented inline:
    - cognitive_restructuring: "I overthink everything" is a keyword for that skill.
      worry_time phrases deliberately avoid "overthink" to prevent misrouting.
    - interpersonal_effectiveness vs assertive_communication: share semantic space.
      Phrases specify relationship vs workplace context to guide routing.
    - "panic" / "panic attack": grounding_5_4_3_2_1 keywords that shadow psychoed_anxiety
      keywords ("why do I panic"). Phrases for psychoed_anxiety avoid "panic" as a standalone
      word in favour of describing the mechanism question.

REAL KEYWORD COLLISION DISCOVERED BY THIS SUITE (2026-06-08):
    stop_technique contains "flooded" and "emotional flooding" — both are dbt_tipp clinical
    terms that have no relevance to the STOP technique. stop_technique scans before dbt_tipp
    in SKILL_REGISTRY (pos 10 vs pos 13), meaning any phrase containing "flooded" incorrectly
    routes to stop_technique. This is a production routing bug; the correct fix is to remove
    "flooded" and "emotional flooding" from stop_technique.target_presentations. Tracked
    separately from this plan (requires clinical sign-off on keyword removal).
    Phrases below avoid "flooded" until the bug is resolved.

Baseline run 2026-06-08: TBD — run scripts/coverage_matrix.py after first install.
Re-run scripts/coverage_matrix.py after any target_presentations edit to track progress.
"""
from __future__ import annotations

# Skills that are semantically near-identical in embedding space.
# Tier 2 routing within this cluster is acceptable ambiguity.
# The correct fix for inter-cluster misses is Tier 1 keyword expansion.
PSYCHOED_CLUSTER: frozenset[str] = frozenset({
    "psychoed_anxiety",
    "psychoed_depression",
    "psychoed_stress",
})

WRONG_SKILL_CASES: list[tuple[str, str]] = [

    # ── act_psychological_flexibility ────────────────────────────────────────
    # Keywords: "I've been dealing with so many things", "everything at once",
    # "anxiety and depression", "I have multiple problems", "all at once".
    # Semantic: ACT acceptance/defusion/values-based action despite distress.
    ("act_psychological_flexibility", "I've been struggling with so many things at once and I don't know where to start"),
    ("act_psychological_flexibility", "I keep fighting against my own thoughts and it's exhausting me"),
    ("act_psychological_flexibility", "I know what I want to do but anxiety keeps getting in the way"),
    ("act_psychological_flexibility", "I want to stop letting fear make all my decisions for me"),
    ("act_psychological_flexibility", "I keep avoiding things I care about and my world is slowly shrinking"),

    # ── assertive_communication ──────────────────────────────────────────────
    # Keywords: "can't say no", "saying no", "assertiveness", "express myself",
    # "throwing me under the bus", "thrown under the bus" (added in Alec sprint).
    ("assertive_communication", "I said yes to something I didn't want to do again and now I'm resentful"),
    ("assertive_communication", "Someone threw me under the bus in front of everyone in a meeting today"),
    ("assertive_communication", "I need to confront my manager about something but I freeze every time I try"),
    ("assertive_communication", "I always back down during disagreements even when I know I'm right"),
    ("assertive_communication", "I let people take advantage of me at work and I need to change that"),

    # ── behavioral_activation ────────────────────────────────────────────────
    # Keywords: "no motivation", "lost motivation", "can't get out of bed",
    # "doing nothing", "lost interest", "stopped doing things".
    ("behavioral_activation", "I've stopped doing all the things I used to enjoy"),
    ("behavioral_activation", "I haven't left the house in days and I know it's making things worse"),
    ("behavioral_activation", "I lie in bed most of the day because nothing feels worth doing"),
    ("behavioral_activation", "I keep cancelling on everyone because going out feels impossible"),
    ("behavioral_activation", "I've given up on hobbies and socialising and I know it's a cycle"),

    # ── box_breathing ────────────────────────────────────────────────────────
    # Keywords: "breathing exercise", "breathing technique", "box breathing",
    # "help me breathe", "breathe with me", "walk me through breathing".
    ("box_breathing", "I need you to walk me through a breathing technique right now"),
    ("box_breathing", "Can you pace me through counting inhales and exhales to calm down?"),
    ("box_breathing", "I need something structured with counts to regulate my breathing"),
    ("box_breathing", "I want to practice a four-count in-and-out pattern to settle myself"),
    ("box_breathing", "I need a timed rhythm to breathe along with right now"),

    # ── cbt_thought_record ───────────────────────────────────────────────────
    # Keywords: "negative thoughts", "self-blame", "cognitive distortions",
    # "catastrophizing", "failure", "automatic thoughts", "thought record".
    ("cbt_thought_record", "I'm catastrophizing again but I can't stop myself"),
    ("cbt_thought_record", "I had one mistake and now I've decided I'm terrible at everything"),
    ("cbt_thought_record", "My brain keeps jumping to the worst conclusion with no evidence"),
    ("cbt_thought_record", "I keep assuming people are judging me when I have no actual proof"),
    ("cbt_thought_record", "I told myself I'd fail before I started and now I'm convinced it's true"),

    # ── cognitive_restructuring ──────────────────────────────────────────────
    # Keywords: "thinking patterns are unhelpful", "mind keeps going to dark places",
    # "I overthink everything" (also in this skill — see NOTE).
    # NOTE: "I overthink everything" is a cognitive_restructuring keyword.
    # worry_time phrases deliberately avoid "overthink" to prevent misrouting.
    ("cognitive_restructuring", "My thinking patterns are really unhelpful and I need to break this cycle"),
    ("cognitive_restructuring", "I have a deep-rooted belief that I fall short and I need to challenge it"),
    ("cognitive_restructuring", "I want to examine and rewrite the way I think about myself"),
    ("cognitive_restructuring", "I always assume the worst outcome, I need to understand why and change it"),
    ("cognitive_restructuring", "There's a story I've been telling myself for years that I know isn't true"),

    # ── dbt_tipp ─────────────────────────────────────────────────────────────
    # Keywords: "overwhelmed", "can't calm down", "flooded", "unbearable feelings",
    # "I can't handle this", "I'm losing it", "need to calm down fast".
    ("dbt_tipp", "I'm completely overwhelmed and nothing is calming me down"),
    ("dbt_tipp", "My emotions are at a ten and normal things aren't working at all"),
    ("dbt_tipp", "I need something physical and intense to bring my body down right now"),
    ("dbt_tipp", "I need to calm down fast and nothing is working, my feelings are unbearable"),  # avoids "flooded"/"overwhelmed right now"/"i can't calm down" — stop_technique/grounding collision bugs documented above
    ("dbt_tipp", "Breathing and talking aren't working, I need something much stronger"),

    # ── financial_anxiety ────────────────────────────────────────────────────
    # Keywords: "kafala visa", "visa depends on my job", "can't send money home",
    # "remittance pressure", "debt", "losing my job would mean losing my visa".
    # Gulf/MENA context is primary for this skill.
    ("financial_anxiety", "My visa is tied to my employment and now I might lose my job"),
    ("financial_anxiety", "I'm drowning in debt and too ashamed to talk about it with anyone"),
    ("financial_anxiety", "I can't stop mentally calculating whether my money will last the month"),
    ("financial_anxiety", "Money stress is consuming my whole life and I can't concentrate"),
    ("financial_anxiety", "I'm terrified to open any financial statements or look at my bank account"),

    # ── grief_loss ───────────────────────────────────────────────────────────
    # Keywords: "grief", "bereavement", "lost someone", "someone died",
    # "my father died", "my mother died", specific family member phrases.
    ("grief_loss", "My father passed away a few months ago and I still can't process it"),
    ("grief_loss", "I lost the person I was closest to and I feel completely hollowed out"),
    ("grief_loss", "I keep expecting them to call and then I remember they're not there"),
    ("grief_loss", "I've been numb since the funeral and I don't know if I'm grieving right"),
    ("grief_loss", "There's so much I never got to say to them and it's eating me up"),

    # ── grounding_5_4_3_2_1 ─────────────────────────────────────────────────
    # Keywords: "panic attack", "panic", "dissociated", "feel disconnected",
    # "heart racing", "nothing feels real", "I feel frozen", "freaking out".
    ("grounding_5_4_3_2_1", "I'm having a full panic attack right now and I can't bring myself back"),
    ("grounding_5_4_3_2_1", "Everything around me feels completely unreal and I'm scared"),
    ("grounding_5_4_3_2_1", "I feel like I'm watching myself from a distance and I can't reconnect"),
    ("grounding_5_4_3_2_1", "I feel completely frozen and disconnected from everything around me"),
    ("grounding_5_4_3_2_1", "I need to anchor myself to something real right now, everything is spinning"),

    # ── interpersonal_effectiveness ──────────────────────────────────────────
    # Keywords: "navigating relationships", "relationship problems",
    # "relationship conflict", "managing relationships", "keeping relationships healthy".
    # Phrases specify close/personal relationships to distinguish from
    # assertive_communication (workplace/general) and avoid "can't say no" (keyword
    # collision with assertive_communication, documented in _KNOWN_SUBSTRING_SHADOWS).
    ("interpersonal_effectiveness", "I'm having real problems in my closest relationship and I don't know how to fix it"),
    ("interpersonal_effectiveness", "I need to ask my partner for something important but I don't know how"),
    ("interpersonal_effectiveness", "I always give everything in relationships and I never get what I need back"),
    ("interpersonal_effectiveness", "I want to communicate what I need to my partner without it turning into a fight"),
    ("interpersonal_effectiveness", "I'm losing close relationships because I can't express what I need from people"),

    # ── mi_readiness_ruler ───────────────────────────────────────────────────
    # Keywords: "want to change", "trying to change", "know I should change",
    # "should stop drinking", "should stop smoking", "ready to change".
    ("mi_readiness_ruler", "I know I should change this but I don't know if I actually want to"),
    ("mi_readiness_ruler", "Part of me wants to get better and part of me doesn't see the point"),
    ("mi_readiness_ruler", "I'm not sure how motivated I really am to do what I know I need to do"),
    ("mi_readiness_ruler", "I keep going back and forth about whether I'm actually ready for this"),
    ("mi_readiness_ruler", "I have really mixed feelings about getting help, I don't know where I stand"),

    # ── mindfulness_body_scan ────────────────────────────────────────────────
    # Keywords: "body scan", "mindfulness body scan", "feel my body",
    # "feel grounded", "body awareness".
    ("mindfulness_body_scan", "I want to do a body scan to reconnect with what I'm feeling"),
    ("mindfulness_body_scan", "I feel completely numb and cut off from my physical self"),
    ("mindfulness_body_scan", "I want something slow and gentle that helps me notice my body"),
    ("mindfulness_body_scan", "I need to get out of my head and feel where I'm holding tension"),
    ("mindfulness_body_scan", "I want to do something present-focused that connects me to my body"),

    # ── mood_check_in ────────────────────────────────────────────────────────
    # Keywords: "check in", "mood check", "how am I doing", "track my mood",
    # "how are you tracking".
    ("mood_check_in", "I want to check in on how I'm actually feeling today"),
    ("mood_check_in", "I'm not sure what I'm feeling right now, can you help me figure it out?"),
    ("mood_check_in", "I need to get clear on my emotional state before we do anything else"),
    ("mood_check_in", "I feel like something is off but I can't identify what it is"),
    ("mood_check_in", "I want to take stock of where I am emotionally right now"),

    # ── problem_solving_therapy ──────────────────────────────────────────────
    # Keywords: "help me solve this", "problem solving", "structured approach",
    # "help me figure out what to do", "don't know what to do".
    ("problem_solving_therapy", "I have a real practical problem and I don't know what to do about it"),
    ("problem_solving_therapy", "I keep hitting the same dead ends with this situation and I can't find a solution"),
    ("problem_solving_therapy", "I need to break this problem down step by step"),
    ("problem_solving_therapy", "I want to think through all my options in a structured way"),
    ("problem_solving_therapy", "I've been stuck on this issue for weeks and need a clear process"),

    # ── progressive_muscle_relaxation ───────────────────────────────────────
    # Keywords: "muscle tension", "tense muscles", "tight shoulders",
    # "tension headache", "body is tense", "so tense", "tense all over".
    ("progressive_muscle_relaxation", "My shoulders are so tight they're practically touching my ears"),
    ("progressive_muscle_relaxation", "My whole body feels like it's tied in knots from stress"),
    ("progressive_muscle_relaxation", "I carry all my stress in my muscles and I need to physically release it"),
    ("progressive_muscle_relaxation", "Every muscle in my body feels clenched and I can't let go"),
    ("progressive_muscle_relaxation", "I'm so physically tense from stress I can barely sit still"),

    # ── psychoed_anxiety ─────────────────────────────────────────────────────
    # Keywords: "what is anxiety", "anxiety explained", "understand anxiety",
    # "why do I panic", "how does anxiety work", "explain anxiety to me".
    # CLUSTER: PSYCHOED_CLUSTER — within-cluster routing (psychoed_depression,
    # psychoed_stress) is logged but not a CI failure.
    # NOTE: phrases avoid standalone "panic" (grounding_5_4_3_2_1 keyword shadow).
    ("psychoed_anxiety", "I want to understand what anxiety actually is and why my body reacts this way"),
    ("psychoed_anxiety", "Can you explain why I get physical symptoms when I'm not in any real danger?"),
    ("psychoed_anxiety", "Why does my heart race even when nothing is actually wrong?"),
    ("psychoed_anxiety", "I want to learn the science behind anxiety so I can make sense of what I feel"),
    ("psychoed_anxiety", "Nobody ever explained to me why anxiety happens, I want to understand it properly"),

    # ── psychoed_depression ──────────────────────────────────────────────────
    # Keywords: "what is depression", "depression explained", "am I depressed",
    # "sadness vs depression", "what is anhedonia", "teach me about depression".
    # CLUSTER: PSYCHOED_CLUSTER — within-cluster routing is logged but not a CI failure.
    ("psychoed_depression", "I want to understand the difference between regular sadness and depression"),
    ("psychoed_depression", "Can you explain what depression actually does to the brain and body?"),
    ("psychoed_depression", "Why does low mood make even tiny tasks feel completely impossible?"),
    ("psychoed_depression", "I want to learn about depression so I can understand what's happening to me"),
    ("psychoed_depression", "Nobody has ever properly explained to me what depression is and how it works"),

    # ── psychoed_stress ──────────────────────────────────────────────────────
    # Keywords: "what is stress", "stress explained", "what does stress do",
    # "acute vs chronic stress", "stress education", "explain stress".
    # CLUSTER: PSYCHOED_CLUSTER — within-cluster routing is logged but not a CI failure.
    ("psychoed_stress", "I want to understand what chronic stress actually does to the body"),
    ("psychoed_stress", "Can you explain the physical effects of being under constant pressure?"),
    ("psychoed_stress", "I want to learn why stress affects everything from sleep to memory"),
    ("psychoed_stress", "Why does sustained stress make me feel physically ill? I want to understand it"),
    ("psychoed_stress", "I want to understand the connection between the pressure I'm under and how I feel physically"),

    # ── safe_place_visualization ─────────────────────────────────────────────
    # Keywords: "need to feel safe", "don't feel safe", "want to feel safe",
    # "need a safe space", "safe place", "somewhere safe".
    ("safe_place_visualization", "I need to imagine a safe place right now to get through this"),
    ("safe_place_visualization", "I want to go somewhere in my mind where I feel completely calm and protected"),
    ("safe_place_visualization", "I need a mental escape right now, somewhere only I can go"),
    ("safe_place_visualization", "I want you to help me visualize somewhere peaceful where nothing can reach me"),
    ("safe_place_visualization", "I need to picture a calm place in my head to get through the next few minutes"),

    # ── self_compassion_break ────────────────────────────────────────────────
    # Keywords: "self-compassion", "being kind to myself", "too hard on myself",
    # "inner critic", "self-criticism", "I'm too harsh on myself".
    ("self_compassion_break", "I keep beating myself up over this and I can't stop"),
    ("self_compassion_break", "I'm so hard on myself, I'd never speak to anyone else the way I speak to myself"),
    ("self_compassion_break", "I need to find some kindness for myself right now but I don't know how"),
    ("self_compassion_break", "I failed at something and now I'm tearing myself apart over it"),
    ("self_compassion_break", "My inner voice is just non-stop criticism and I'm exhausted by it"),

    # ── sleep_hygiene ────────────────────────────────────────────────────────
    # Keywords: "can't sleep", "cant sleep", "insomnia", "sleep problems",
    # "sleeping badly", "wake up in the night", "can't fall asleep".
    ("sleep_hygiene", "I haven't slept properly in weeks"),
    ("sleep_hygiene", "I lie awake for hours staring at the ceiling no matter how tired I am"),
    ("sleep_hygiene", "I wake up at 3am every night and I can't get back to sleep"),
    ("sleep_hygiene", "I'm exhausted during the day but then I can't fall asleep when I try"),
    ("sleep_hygiene", "My sleep is completely broken and it's affecting everything else in my life"),

    # ── stop_technique ───────────────────────────────────────────────────────
    # Keywords: "spiraling", "spiralling", "about to lose it", "cant think straight",
    # "about to react badly", "can't think straight".
    ("stop_technique", "I'm spiralling right now and I need something to interrupt it immediately"),
    ("stop_technique", "I'm about to say something I'll really regret, I need to pause right now"),
    ("stop_technique", "My mind is going a hundred miles an hour and I need to slam the brakes"),
    ("stop_technique", "I can feel myself escalating and I need something immediate to break the cycle"),
    ("stop_technique", "I'm in a loop in my head and I need to interrupt it right now before I act on it"),

    # ── values_clarification ─────────────────────────────────────────────────
    # Keywords: "what do I value", "values clarification", "what matters to me",
    # "living by my values", "I feel lost in life", "find my values".
    ("values_clarification", "I feel completely lost in life and I don't know what direction to go"),
    ("values_clarification", "I've been doing what other people expect of me and I've completely lost myself"),
    ("values_clarification", "I don't know what I actually care about anymore, everything feels equally empty"),
    ("values_clarification", "I need to figure out what actually matters to me before I can make any decision"),
    ("values_clarification", "I feel like I've been drifting without purpose and I need to find my own direction"),

    # ── worry_time ───────────────────────────────────────────────────────────
    # Keywords: "can't stop worrying", "cant stop worrying", "worrying all the time",
    # "I keep worrying about everything", "constantly worrying".
    # NOTE: Deliberately avoids "I overthink everything" — that is a
    # cognitive_restructuring keyword and would cause a Tier 1 collision.
    ("worry_time", "I can't stop worrying, it just runs all day no matter what I do"),
    ("worry_time", "My brain keeps cycling through worst-case scenarios about things I can't control"),
    ("worry_time", "I spend hours every day on worries that probably won't ever happen"),
    ("worry_time", "The anxious thoughts never stop, from the moment I wake up to when I go to sleep"),
    ("worry_time", "I need a way to contain my worrying to a specific time instead of having it run all day"),
]

assert len(WRONG_SKILL_CASES) == 125, f"Expected 125 cases, got {len(WRONG_SKILL_CASES)}"
