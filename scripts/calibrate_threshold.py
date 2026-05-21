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
    ("my heart is pounding so hard and I feel faint", "grounding_5_4_3_2_1"),
    ("I feel like I'm dissociating", "grounding_5_4_3_2_1"),
    ("my heart is pounding so hard and I feel faint", "grounding_5_4_3_2_1"),
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
    "I've been feeling stressed lately",  # vague stress must not match any skill
    "Hi, I've been feeling stressed",  # exact RT-4 regression phrase — must not match any skill
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
