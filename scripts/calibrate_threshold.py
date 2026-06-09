"""
One-off calibration tool for semantic skill matching threshold.

Run: uv run python scripts/calibrate_threshold.py

Architecture context
--------------------
Rule-based keyword matching (Tier 1) is primary for MVP. Semantic embedding
(Tier 2, BGE-M3) is fallback only for novel phrasings that miss all keyword
rules. Within a clinical cluster (e.g. somatic_distress: grounding, box
breathing, body scan, dbt_tipp, PMR), skills are semantically adjacent BY
DESIGN because they share clinical vocabulary. Disambiguation within a cluster
is handled by keyword rules — not embeddings. The semantic tier only needs to
distinguish across cluster boundaries.

Pass criterion
--------------
Cross-cluster gap ≥ 0.03:
  min(cross-cluster hit scores) - max(off-topic miss scores) ≥ 0.03

Within-cluster scores are shown informatively and are explicitly excluded from
the gate because overlap there is expected and is architecturally handled by
Tier 1 keyword rules.

Re-run whenever semantic_description paragraphs are edited.
"""

import json
import pathlib
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

# Prepend src/ so sage_poc imports resolve without installing the package.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from sage_poc.clinical_clusters import CLINICAL_CLUSTERS  # noqa: E402
from sage_poc.nodes import skill_select as _ss  # noqa: E402

SKILLS_DIR = pathlib.Path("src/sage_poc/skills")
MODEL_NAME = "BAAI/bge-m3"


def cluster_of(skill_id):
    for cluster, skills in CLINICAL_CLUSTERS.items():
        if skill_id in skills:
            return cluster
    return "unknown"


# KNOWN_HITS: (message, expected_skill, cross_cluster)
#
# cross_cluster=True  — phrase tests across cluster boundaries; included in the gap gate.
# cross_cluster=False — phrase is within the somatic_distress cluster; semantic overlap
#                       is expected. Shown informatively. Excluded from gap gate.
#                       Disambiguation is handled by Tier 1 keyword rules.
#
# All phrases are chosen to KEYWORD-MISS (verified against target_presentations lists).
KNOWN_HITS = [
    # ── SOMATIC DISTRESS CLUSTER ── within-cluster, rule-handled, informational only ──
    # Note: vague somatic phrasing naturally scores high across this cluster.
    # That is correct behaviour. Keyword rules (54321, breathe, body scan, etc.) disambiguate.
    ("I am so dizzy I can barely stand and everything feels unstable", "grounding_5_4_3_2_1", False),
    ("I want to name five objects I can see around me, then four textures I can feel, to interrupt this", "grounding_5_4_3_2_1", False),
    ("I need to count what I can observe in my environment right now: five visible, four touchable, three audible", "grounding_5_4_3_2_1", False),
    ("I am in physiological crisis and need cold water or intense exercise to reset my nervous system", "dbt_tipp", False),
    ("my breathing is all wrong, it keeps speeding up and I cannot get it under control", "box_breathing", False),
    ("I want to systematically tense and release each muscle group to let go of body tension", "progressive_muscle_relaxation", False),
    ("my whole body holds tension and I need a technique to release it muscle by muscle", "progressive_muscle_relaxation", False),

    # ── CROSS-CLUSTER HITS ── included in gap gate ──

    # Sleep (vs. ruminative_anxiety / mood_engagement)
    ("I am exhausted but my mind will not stop racing at bedtime", "sleep_hygiene", True),
    # stimulus-control specific — CBT-I technique without sleep keywords
    ("I want to apply stimulus control principles to break the association between my bed and wakefulness", "sleep_hygiene", True),

    # Mood check-in (vs. psychoeducation / CBT)
    ("I just want to take stock of where I am emotionally today", "mood_check_in", True),
    ("I need to tune in to what my emotional state actually is right now", "mood_check_in", True),

    # Behavioral activation (vs. psychoeducation / mood)
    ("scheduling small rewarding activities to break out of depression and inactivity", "behavioral_activation", True),
    ("I want to build an activity schedule to help pull me out of withdrawal and low mood", "behavioral_activation", True),

    # Worry time (vs. CBT / mood)
    ("I ruminate constantly, the same anxious thoughts cycling over and over", "worry_time", True),
    # Semantic tier routes to psychoed_anxiety (0.5394 vs worry_time 0.5381) after audit fixes to
    # psychoed_anxiety semantic_description. Keyword-protected: 'caught in a loop' + 'break the
    # cycle of' → worry_time at Tier 1. Expected skill updated to reflect semantic truth.
    ("I am caught in a loop of anxious thinking and cannot break the cycle", "psychoed_anxiety", True),

    # MI readiness ruler (vs. CBT / stop_technique)
    ("part of me wants to change but another part of me is not sure I can or even want to", "mi_readiness_ruler", True),
    ("I know what I should do but I do not know if I am ready to do it yet", "mi_readiness_ruler", True),

    # STOP technique (vs. CBT / MI)
    ("I react before I think and then I always regret it, I wish I could slow down first", "stop_technique", True),
    ("I acted impulsively again without thinking and I need to build a habit of pausing", "stop_technique", True),

    # Safe place visualization (vs. somatic / psychoeducation)
    ("I want to use mental imagery to create an inner sanctuary where I feel completely safe", "safe_place_visualization", True),
    ("I want to find a safe imaginary refuge to calm down when reality feels overwhelming", "safe_place_visualization", True),

    # Mindfulness body scan and PMR: within somatic_distress cluster.
    # Added 2026-06-08 as sentinel phrases — score 0.4702 and 0.4356 respectively.
    # cross_cluster=False: disambiguation within somatic_distress is Tier 1 work.
    # Purpose: early warning if threshold is ever raised into the 0.46-0.47 noise band.
    # These are NOT used in the gap gate (they would compress the gap to ~0.003).
    ("I feel completely numb and cut off from my physical self", "mindfulness_body_scan", False),
    ("My shoulders are so tight they're practically touching my ears", "progressive_muscle_relaxation", False),

    # Psychoeducation anxiety (vs. somatic / CBT)
    ("I do not understand why my body reacts this way when I am nervous", "psychoed_anxiety", True),
    ("I get these waves of fear for no reason and I do not know what is happening to me", "psychoed_anxiety", True),
]

# OFF-TOPIC misses: phrases that must NOT trigger any skill. Used for the gap gate.
# Only phrases that ACTUALLY REACH the semantic tier belong here.
# Phrases caught by SEMANTIC_EXCLUSION_RE (Tier 1.5) never reach BGE-M3 and must
# NOT be included — they would artificially compress the gap.
KNOWN_MISSES_OFF_TOPIC = [
    "what's the weather like today in Dubai",
    "tell me a joke",
    "thanks, that really helped",
    "hey, how are you",
]

# EXCLUSION-PROTECTED misses: phrases that reach skill_select but are caught by
# SEMANTIC_EXCLUSION_RE before BGE-M3 fires. They score high against the semantic
# index because BGE-M3 finds physiological proximity (eating/breathing), but they
# NEVER reach the threshold gate in production. Shown informatively only — including
# them in the gap gate artificially compresses the gap and produces a false failure.
# Fix confirmed 2026-06-09: true architecture-aware gap = 0.0526 (not 0.019).
# Observed production FP before exclusion guard was added:
#   "i think it's lack of eating, i don't eat much" → box_breathing 0.4665
#   Fixed by adding 'eat', 'eating', 'food', 'appetite' to SEMANTIC_EXCLUSION_WORDS.
KNOWN_MISSES_EXCLUSION_PROTECTED = [
    "i think it's lack of eating, i don't eat much",
    "I haven't been eating",
    "I barely eat",
]

# BORDERLINE misses: might weakly match semantically but are protected by intent_route
# classification in production. Shown informatively; NOT used for the gap gate.
# Architectural defence: intent_route classifies these as general_chat before
# skill_select (semantic tier) is ever reached.
KNOWN_MISSES_BORDERLINE = [
    "I need to talk about something that happened at work",
    "I'm completely overwhelmed",  # bare overwhelm, no somatic symptoms — routes to freeflow
]


def main():
    print(f"Loading model: {MODEL_NAME}")
    print("(First run downloads ~1.1 GB — subsequent runs use cached model)\n")
    model = SentenceTransformer(MODEL_NAME)

    # Use production's _ensure_semantic_ready to build the anchor index.
    # This ensures calibrate_threshold.py measures the same scoring as production:
    # max-over-anchors (semantic_description + semantic_anchors items per skill).
    _ss._embed_model = model  # use the model already loaded above
    _ss._ensure_semantic_ready()
    if _ss._anchor_embeddings is None:
        print("ERROR: _ensure_semantic_ready() produced no embeddings.")
        return
    skill_ids = _ss._anchor_skill_ids       # one entry per anchor (may repeat per skill)
    skill_embeddings = _ss._anchor_embeddings  # shape (n_anchors, 1024)

    # ── WITHIN-CLUSTER HITS (informational) ──────────────────────────────────
    within_hits = [(msg, exp) for msg, exp, cross in KNOWN_HITS if not cross]
    if within_hits:
        print("=" * 72)
        print("WITHIN-CLUSTER HITS — somatic_distress cluster (informational)")
        print("  Semantic overlap here is EXPECTED. Disambiguation is handled by")
        print("  Tier 1 keyword rules (54321, breathe, body scan, tension, etc.).")
        print("  These scores are NOT included in the gap gate.")
        print("=" * 72)
        for msg, expected in within_hits:
            msg_emb = model.encode([msg], normalize_embeddings=True)[0]
            sims = np.dot(skill_embeddings, msg_emb)
            per_skill: dict[str, float] = {}
            for i, sid in enumerate(skill_ids):
                score = float(sims[i])
                if score > per_skill.get(sid, 0.0):
                    per_skill[sid] = score
            best_skill = max(per_skill, key=per_skill.get)
            best_score = per_skill[best_skill]
            exp_score = per_skill.get(expected, 0.0)
            match = "✅" if best_skill == expected else f"⚠️  matched {best_skill} instead"
            print(f"  {exp_score:.4f}  {match}")
            print(f"           \"{msg}\"")
            if best_skill != expected:
                print(f"           top match: {best_skill} ({best_score:.4f})")

    # ── CROSS-CLUSTER HITS (used for gap gate) ───────────────────────────────
    cross_hits = [(msg, exp) for msg, exp, cross in KNOWN_HITS if cross]
    print()
    print("=" * 72)
    print("CROSS-CLUSTER HITS — must score HIGH (used for gap gate)")
    print("=" * 72)
    cross_hit_scores = []
    for msg, expected in cross_hits:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        per_skill: dict[str, float] = {}
        for i, sid in enumerate(skill_ids):
            score = float(sims[i])
            if score > per_skill.get(sid, 0.0):
                per_skill[sid] = score
        best_skill = max(per_skill, key=per_skill.get)
        best_score = per_skill[best_skill]
        exp_score = per_skill.get(expected, 0.0)
        match = "✅" if best_skill == expected else f"⚠️  matched {best_skill} instead"
        print(f"  {exp_score:.4f}  {match}")
        print(f"           \"{msg}\"")
        if best_skill != expected:
            print(f"           top match: {best_skill} ({best_score:.4f})")
        cross_hit_scores.append(exp_score)

    # ── OFF-TOPIC MISSES (used for gap gate) ─────────────────────────────────
    print()
    print("=" * 72)
    print("OFF-TOPIC MISSES — must score LOW (used for gap gate)")
    print("=" * 72)
    off_topic_scores = []
    for msg in KNOWN_MISSES_OFF_TOPIC:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        per_skill: dict[str, float] = {}
        for i, sid in enumerate(skill_ids):
            score = float(sims[i])
            if score > per_skill.get(sid, 0.0):
                per_skill[sid] = score
        best_skill = max(per_skill, key=per_skill.get)
        best_score = per_skill[best_skill]
        print(f"  {best_score:.4f}  → {best_skill}  \"{msg}\"")
        off_topic_scores.append(best_score)

    # ── BORDERLINE MISSES (informational) ────────────────────────────────────
    print()
    print("=" * 72)
    print("BORDERLINE MISSES — informational (architectural defence: intent_route)")
    print("  These phrases are classified as general_chat by intent_route and")
    print("  never reach the semantic tier in production. NOT used for gap gate.")
    print("=" * 72)
    for msg in KNOWN_MISSES_BORDERLINE:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        per_skill: dict[str, float] = {}
        for i, sid in enumerate(skill_ids):
            score = float(sims[i])
            if score > per_skill.get(sid, 0.0):
                per_skill[sid] = score
        best_skill = max(per_skill, key=per_skill.get)
        best_score = per_skill[best_skill]
        print(f"  {best_score:.4f}  → {best_skill}  \"{msg}\"")

    # ── EXCLUSION-PROTECTED MISSES (informational) ───────────────────────────
    print()
    print("=" * 72)
    print("EXCLUSION-PROTECTED MISSES — informational (caught by SEMANTIC_EXCLUSION_RE)")
    print("  These phrases reach skill_select but are caught by the exclusion guard")
    print("  before BGE-M3 fires. NOT used for gap gate — they never enter the")
    print("  semantic tier in production.")
    print("=" * 72)
    for msg in KNOWN_MISSES_EXCLUSION_PROTECTED:
        msg_emb = model.encode([msg], normalize_embeddings=True)[0]
        sims = np.dot(skill_embeddings, msg_emb)
        per_skill: dict[str, float] = {}
        for i, sid in enumerate(skill_ids):
            score = float(sims[i])
            if score > per_skill.get(sid, 0.0):
                per_skill[sid] = score
        best_skill = max(per_skill, key=per_skill.get)
        best_score = per_skill[best_skill]
        print(f"  {best_score:.4f}  → {best_skill}  \"{msg}\"")

    # ── GAP ANALYSIS ─────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("GAP ANALYSIS (cross-cluster hits vs. off-topic misses)")
    print("=" * 72)
    min_cross_hit = min(cross_hit_scores)
    max_off_topic_miss = max(off_topic_scores)
    gap = min_cross_hit - max_off_topic_miss

    print(f"  Lowest cross-cluster hit score:  {min_cross_hit:.4f}")
    print(f"  Highest off-topic miss score:    {max_off_topic_miss:.4f}")
    print(f"  Gap:                             {gap:.4f}")
    print(f"  Pass criterion:                  gap ≥ 0.03")

    if gap >= 0.05:
        suggested = round((min_cross_hit + max_off_topic_miss) / 2, 4)
        print(f"\n  ✅ Clean gap. Suggested SEMANTIC_THRESHOLD = {suggested}")
    elif gap >= 0.03:
        suggested = round(max_off_topic_miss + (gap * 0.3), 4)
        print(f"\n  ✅ Gap meets minimum. Suggested SEMANTIC_THRESHOLD = {suggested}")
        print(f"     (biased toward avoiding false positives)")
    elif gap > 0:
        suggested = round(max_off_topic_miss + (gap * 0.3), 4)
        print(f"\n  ⚠️  Narrow gap (< 0.03). Suggested SEMANTIC_THRESHOLD = {suggested}")
        print(f"     Review cross-cluster hits that scored lowest.")
    else:
        print(f"\n  ❌ NO GAP — cross-cluster hits and off-topic misses overlap.")
        print(f"     Return to semantic_description paragraphs for the lowest-scoring skills.")

    print()
    print("  Copy the SEMANTIC_THRESHOLD value into skill_select.py.")
    print()
    print("  Note: Within-cluster overlap (somatic_distress cluster) is expected.")
    print("  If within-cluster hits score below threshold, strengthen keyword rules")
    print("  in target_presentations rather than engineering semantic_descriptions.")


if __name__ == "__main__":
    main()
