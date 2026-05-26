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
    ("I just have this constant voice telling me I'm terrible", "cbt_thought_record"),  # replaced "I hate myself so much" — moved to keyword tier (Task C)
    ("I feel like such a disappointment to everyone", "cbt_thought_record"),
    ("why can't I just be normal", "cbt_thought_record"),
    # Grounding — none of these contain a grounding keyword
    ("I am so dizzy I can barely stand and everything feels unstable", "grounding_5_4_3_2_1"),  # replaced "my heart is pounding so hard and I feel faint" — 'heart is pounding' moved to keyword tier (Task C)
    ("my body is shaking and I can not catch my breath", "grounding_5_4_3_2_1"),  # replaced "I feel like I'm dissociating" — moved to keyword tier (Task C); self-referential dissociation phrases cross-matched CBT (scored 0.5209–0.5463)
    ("my hands are trembling and I cannot catch my breath properly", "grounding_5_4_3_2_1"),  # replaced "I feel completely overwhelmed, my head is spinning" — 'spinning' keyword present since skill creation (pre-Task C contamination)
    # Sleep — none of these contain a sleep keyword
    ("I am exhausted but my mind will not stop racing at bedtime", "sleep_hygiene"),
    ("my brain just won't let me rest when it's dark", "sleep_hygiene"),  # replaced "I am tired all day but wide awake at night" — moved to keyword tier (Task C)

    # DBT TIPP — physiological/somatic regulation without TIPP keywords
    # Note: vague emotional-control phrases route to CBT; TIPP wins on somatic+physical language
    ("I am in physiological crisis and need cold water or intense exercise to reset my nervous system", "dbt_tipp"),

    # Box breathing — paced-breathing structure without 'breathing'/'breathe' keywords
    ("my breathing is all wrong, it keeps speeding up and I cannot get it under control", "box_breathing"),

    # Mood check-in — introspective self-monitoring without keyword phrases
    ("I just want to take stock of where I am emotionally today", "mood_check_in"),
    ("I need to tune in to what my emotional state actually is right now", "mood_check_in"),

    # Behavioral activation — activity-re-engagement framing without skill keywords
    # Note: withdrawal-without-activity-language routes to CBT; BA wins on activity scheduling language
    ("scheduling small rewarding activities to break out of depression and inactivity", "behavioral_activation"),
    ("I want to build an activity schedule to help pull me out of withdrawal and low mood", "behavioral_activation"),

    # Worry time — rumination without 'worry' or 'overthinking'
    ("I ruminate constantly, the same anxious thoughts cycling over and over", "worry_time"),
    ("I am caught in a loop of anxious thinking and cannot break the cycle", "worry_time"),

    # MI readiness ruler — ambivalence language
    ("part of me wants to change but another part of me is not sure I can or even want to", "mi_readiness_ruler"),
    ("I know what I should do but I do not know if I am ready to do it yet", "mi_readiness_ruler"),

    # STOP technique — impulsivity and reactivity language without 'need to pause'
    ("I react before I think and then I always regret it, I wish I could slow down first", "stop_technique"),
    ("I acted impulsively again without thinking and I need to build a habit of pausing", "stop_technique"),

    # Progressive muscle relaxation — body tension without the skill name
    ("I want to systematically tense and release each muscle group to let go of body tension", "progressive_muscle_relaxation"),
    ("my whole body holds tension and I need a technique to release it muscle by muscle", "progressive_muscle_relaxation"),

    # Safe place visualization — mental imagery/refuge language without the skill's own keywords
    # Note: 'guided imagery', 'visualization', 'calm place' are in keyword tier for this skill
    ("I want to use mental imagery to create an inner sanctuary where I feel completely safe", "safe_place_visualization"),
    ("I want to find a safe imaginary refuge to calm down when reality feels overwhelming", "safe_place_visualization"),

    # Psychoeducation — anxiety (no 'anxiety' keyword, no technique name)
    ("I do not understand why my body reacts this way when I am nervous", "psychoed_anxiety"),
    ("I get these waves of fear for no reason and I do not know what is happening to me", "psychoed_anxiety"),

    # Psychoeducation — depression (no 'depression' keyword, no technique name)
    ("I have been feeling grey and flat for weeks and I cannot explain why", "psychoed_depression"),
    ("everything feels heavy and I have lost interest in things I used to enjoy", "psychoed_depression"),

    # Psychoeducation — stress (no 'stress' keyword, no technique name)
    ("I feel like I am constantly running on empty and my body is always on edge", "psychoed_stress"),
    ("I cannot switch off, I am always braced for the next thing to go wrong", "psychoed_stress"),
]

# Messages that should NOT match any skill
KNOWN_MISSES = [
    "what's the weather like today in Dubai",
    "can you diagnose me with depression",
    "tell me a joke",
    "thanks, that really helped",
    "hey, how are you",
    "I need to talk about something that happened at work",  # edge case — may weakly match
    "I've been feeling stressed lately",  # vague stress must not match any skill
    "Hi, I've been feeling stressed",  # exact RT-4 regression phrase — must not match any skill
    "I'm overwhelmed and anxious",  # actual FP pre-fix — must not match any skill
    "I'm completely overwhelmed",  # bare overwhelm (no somatic symptoms) — must route to freeflow
    # NOTE: "I just feel off today" removed from this corpus (2026-05-21 RT-4c).
    # It scores 0.5566 for CBT at the semantic tier — a known single-vector embedding
    # limitation: BGE-M3 cannot cleanly separate first-person cognitive-distortion
    # statements from vague negative affect in the same embedding space.
    # Architectural defence: intent_route (Node 2) classifies vague openings as
    # general_chat before they reach skill_select (Node 4). Confirmed in R-3 audit.
    # The calibration corpus should only contain phrases that actually reach the
    # semantic tier in production (i.e., passed intent_route as new_skill).
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
        suggested = round(max_miss + (gap * 0.3), 4)
        print(f"\n  ⚠️  Narrow gap. Suggested SEMANTIC_THRESHOLD = {suggested}")
        print(f"     (biased toward avoiding false positives)")
    else:
        print(f"\n  ❌ NO GAP — hits and misses overlap.")
        print(f"     Return to Task 2 and enrich the semantic_description paragraphs.")

    print()
    print("  Copy the SEMANTIC_THRESHOLD value into Task 4 Step 3.")


if __name__ == "__main__":
    main()
