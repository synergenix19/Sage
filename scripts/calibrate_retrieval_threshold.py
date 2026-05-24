"""
Calibration tool for session summary retrieval threshold.

Run: uv run python scripts/calibrate_retrieval_threshold.py

Measures BGE-M3 cosine similarity between user queries and synthetic session
summaries for two corpora:

  KNOWN_RELEVANT   — (query, summary_id) pairs that SHOULD produce high similarity
                     (the summary is genuinely relevant to the query)
  KNOWN_IRRELEVANT — (query, summary_id) pairs that SHOULD produce low similarity
                     (cross-topic: different clinical domain; or non-clinical query)

_SIMILARITY_THRESHOLD in check_user_history.py sits in the gap between the lowest
KNOWN_RELEVANT score and the highest KNOWN_IRRELEVANT score.

Why synthetic summaries (not real ones): real session summaries live in the database
and vary by deployment. Synthetic summaries are written to be representative of what
the LLM-generated summarise_history() produces — clinical, multi-sentence, topic-dense.

Re-run whenever:
  - _SIMILARITY_THRESHOLD changes
  - The summarise_history() prompt template is edited (summary style changes)
  - BGE-M3 is replaced with a different embedding model
  - A systematic false-positive (irrelevant injection) or false-negative (missed
    relevant context) complaint arrives from a clinician or QA run

Gap analysis decision table (identical to calibrate_threshold.py):
  gap > 0.05:           Clean gap — use midpoint as threshold
  0.008 < gap <= 0.05:  Narrow gap — use max_irrelevant + gap * 0.3
  0 < gap <= 0.008:     Marginal — review corpus before updating threshold
  gap <= 0:             NO GAP — summaries or queries need revision

KNOWN_IRRELEVANT corpus design rationale:
  The most clinically dangerous false positive is cross-topic injection: a session
  about sleep getting injected into a CBT thought record, or a crisis-adjacent
  session being surfaced (crisis summaries are excluded separately via
  exclude_safety_levels=["crisis"]). The corpus therefore includes both:
  (a) cross-topic clinical pairs — same user, different clinical domain
  (b) non-clinical queries — general-purpose questions that should never match
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"

# ---------------------------------------------------------------------------
# Synthetic session summaries
# Representative of what summarise_history() produces for each clinical domain.
# Each summary is multi-sentence, topic-dense, and plausibly LLM-generated.
# ---------------------------------------------------------------------------

SYNTHETIC_SUMMARIES = {
    "S1_cbt_performance": (
        "User identified catastrophic thinking patterns around job performance. "
        "Practiced CBT thought challenging — replaced 'I will definitely fail the "
        "presentation' with 'I have prepared thoroughly, and even if it is imperfect, "
        "one presentation does not define my career.' Distress rated 7/10 before, "
        "4/10 after exercise. User acknowledged they had received positive feedback "
        "on their last three projects. Agreed to track automatic thoughts before the "
        "next presentation."
    ),
    "S2_sleep_insomnia": (
        "User reported persistent insomnia — averaging 2 to 3 hours of sleep per "
        "night for the past two weeks, linked to rumination about a family conflict. "
        "Explored sleep hygiene principles: consistent bedtime, avoiding screens one "
        "hour before bed, writing worries in a journal before lights-out. User "
        "committed to a 10pm bedtime and no phone after 9pm. Follow-up scheduled "
        "for one week to review sleep log."
    ),
    "S3_grounding_panic": (
        "User experienced a panic attack at work three days ago. Used the 5-4-3-2-1 "
        "grounding technique during session. Noted physical sensations — racing heart, "
        "tunnel vision — and anchored to senses: described two cold objects on desk, "
        "sound of air conditioning. Panic subsided within eight minutes. User reported "
        "this was the first time they had managed a panic attack without leaving the "
        "situation. Praised for staying present."
    ),
    "S4_social_isolation": (
        "User disclosed self-isolating since the breakup two months ago and has not "
        "replied to friends' messages. Identified avoidance as a coping pattern that "
        "is increasing loneliness. Discussed gradual behavioural activation: replied "
        "to one friend's message during the session itself. User expressed hope but "
        "also fear of being perceived as needy. Scheduled one low-stakes social "
        "interaction before next session."
    ),
    "S5_cultural_identity": (
        "Session focused on pressure from extended family around career choices and "
        "tension between cultural obligations and personal autonomy. User described "
        "feeling split between two worlds. Explored values clarification — identified "
        "autonomy and family connection as core values currently in tension. Agreed to "
        "bring a specific family scenario to the next session for role-play practice. "
        "User expressed relief at naming the tension rather than feeling guilty."
    ),
    "S6_cbt_self_worth": (
        "User presented with pervasive self-critical thinking about their worth as a "
        "parent. Automatic thought: 'I am failing my children by being depressed.' "
        "Examined evidence — user attends every school event, prepares meals daily, "
        "maintains bedtime routines. Balanced thought: 'I am struggling, and I am "
        "still showing up.' User rated conviction in original thought at 85 before, "
        "40 after. Identified distortion pattern: all-or-nothing thinking."
    ),
}

# ---------------------------------------------------------------------------
# KNOWN_RELEVANT: (query, summary_id) pairs where similarity MUST be high
# All queries chosen to avoid direct keyword overlap with the summary text —
# the similarity must come from semantic meaning, not shared surface terms.
# ---------------------------------------------------------------------------

KNOWN_RELEVANT = [
    # CBT / performance anxiety — S1
    ("I keep thinking I am going to mess up the big meeting tomorrow",           "S1_cbt_performance"),
    ("every time I try to reassure myself it works for a minute then the panic comes back", "S1_cbt_performance"),
    ("I told myself I was prepared but my brain keeps saying I will embarrass myself", "S1_cbt_performance"),

    # Sleep / insomnia — S2
    ("I cannot switch my brain off at night no matter what I try",               "S2_sleep_insomnia"),
    ("I have been lying awake for hours going over the same argument",            "S2_sleep_insomnia"),
    ("the moment I get into bed my thoughts start racing again",                 "S2_sleep_insomnia"),

    # Panic / grounding — S3
    ("I had another panic attack, my heart was going crazy and I froze",         "S3_grounding_panic"),
    ("I tried to breathe through it but I still feel shaky afterwards",          "S3_grounding_panic"),

    # Social isolation — S4
    ("my friends keep asking me to hang out but I just cannot make myself go",   "S4_social_isolation"),
    ("I have been ignoring everyone and I know it is making things worse",       "S4_social_isolation"),

    # Cultural identity / family pressure — S5
    ("my family has very different expectations for my career than I do",         "S5_cultural_identity"),
    ("I feel guilty every time I choose what I want over what my family expects","S5_cultural_identity"),

    # Self-worth CBT — S6
    ("I feel like such a bad mother, I cannot stop crying and my kids see it",   "S6_cbt_self_worth"),
    ("I know I am there for them but I still feel like I am not enough",         "S6_cbt_self_worth"),
]

# ---------------------------------------------------------------------------
# KNOWN_IRRELEVANT: (query, summary_id) pairs where similarity MUST be low
# Two categories:
#   (a) Cross-topic clinical: query from one domain vs summary from another
#   (b) Non-clinical: general-purpose questions vs any clinical summary
# The threshold must keep all of these BELOW the cutoff.
# ---------------------------------------------------------------------------

KNOWN_IRRELEVANT = [
    # Cross-topic: sleep query vs panic summary
    ("I cannot get to sleep, my mind just will not stop",                        "S3_grounding_panic"),
    # Cross-topic: panic query vs sleep summary
    ("I had a panic attack in the supermarket and could not breathe",            "S2_sleep_insomnia"),
    # Cross-topic: performance anxiety vs isolation summary
    ("I am terrified I will fail in front of my whole team",                     "S4_social_isolation"),
    # Cross-topic: isolation query vs cultural identity summary
    ("I have been avoiding everyone and spending all my time at home",           "S5_cultural_identity"),
    # Cross-topic: family pressure query vs sleep summary
    ("my family will not accept my career choice and it is causing conflict",    "S2_sleep_insomnia"),
    # Cross-topic: self-worth query vs grounding summary
    ("I feel like I am a terrible parent and my kids deserve better",            "S3_grounding_panic"),
    # Cross-topic: cultural identity vs performance CBT summary
    ("I feel torn between what my family wants and who I want to be",            "S1_cbt_performance"),
    # Non-clinical: purely off-topic
    # NOTE: "I have been feeling stressed out lately" was removed — a general distress
    # query legitimately matches any clinical summary and belongs in KNOWN_RELEVANT,
    # not here. KNOWN_IRRELEVANT must contain queries that should NOT match any summary.
    ("what time does the pharmacy close today",                                  "S1_cbt_performance"),
    ("can you help me write a cover letter for a job application",               "S2_sleep_insomnia"),
    ("I need advice on how to cook rice properly",                               "S4_social_isolation"),
]


def main():
    print(f"Loading model: {MODEL_NAME}")
    print("(First run downloads ~1.1 GB — subsequent runs use cached model)\n")
    model = SentenceTransformer(MODEL_NAME)

    # Embed all synthetic summaries once
    summary_ids = list(SYNTHETIC_SUMMARIES.keys())
    summary_texts = [SYNTHETIC_SUMMARIES[sid] for sid in summary_ids]
    summary_embeddings = model.encode(summary_texts, normalize_embeddings=True)
    summary_emb_map = dict(zip(summary_ids, summary_embeddings))

    # ------------------------------------------------------------------
    # KNOWN_RELEVANT
    # ------------------------------------------------------------------
    print("=" * 72)
    print("KNOWN_RELEVANT — queries that MUST score HIGH against their summary")
    print("=" * 72)
    relevant_scores = []
    for query, expected_sid in KNOWN_RELEVANT:
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        expected_score = float(np.dot(summary_emb_map[expected_sid], q_emb))

        # Also find the best-scoring summary (may differ from expected)
        all_scores = np.dot(summary_embeddings, q_emb)
        best_idx = int(np.argmax(all_scores))
        best_sid = summary_ids[best_idx]
        best_score = float(all_scores[best_idx])

        match_marker = "✅" if best_sid == expected_sid else f"⚠️  top={best_sid}({best_score:.4f})"
        print(f"  {expected_score:.4f}  {match_marker}")
        print(f"           \"{query[:80]}\"")
        relevant_scores.append(expected_score)

    # ------------------------------------------------------------------
    # KNOWN_IRRELEVANT
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("KNOWN_IRRELEVANT — (query, summary) pairs that MUST score LOW")
    print("=" * 72)
    irrelevant_scores = []
    for query, sid in KNOWN_IRRELEVANT:
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        score = float(np.dot(summary_emb_map[sid], q_emb))

        # Also show the best-scoring summary for context
        all_scores = np.dot(summary_embeddings, q_emb)
        best_idx = int(np.argmax(all_scores))
        best_sid = summary_ids[best_idx]
        best_score = float(all_scores[best_idx])

        danger = " ⚠️  HIGHEST MATCH" if best_sid == sid else f" (best={best_sid} {best_score:.4f})"
        print(f"  {score:.4f}  vs {sid}{danger}")
        print(f"           \"{query[:80]}\"")
        irrelevant_scores.append(score)

    # ------------------------------------------------------------------
    # Gap analysis
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    print("GAP ANALYSIS")
    print("=" * 72)
    min_relevant = min(relevant_scores)
    max_irrelevant = max(irrelevant_scores)
    gap = min_relevant - max_irrelevant

    print(f"  Lowest KNOWN_RELEVANT score:    {min_relevant:.4f}")
    print(f"  Highest KNOWN_IRRELEVANT score: {max_irrelevant:.4f}")
    print(f"  Gap:                            {gap:.4f}")

    if gap > 0.05:
        suggested = round((min_relevant + max_irrelevant) / 2, 4)
        label = "Clean gap"
        formula = "midpoint"
    elif gap > 0.008:
        suggested = round(max_irrelevant + gap * 0.3, 4)
        label = "Narrow gap"
        formula = "max_irrelevant + gap * 0.3"
    elif gap > 0:
        suggested = round(max_irrelevant + gap * 0.3, 4)
        label = "Marginal gap"
        formula = "max_irrelevant + gap * 0.3 (REVIEW CORPUS before applying)"
    else:
        suggested = None
        label = "NO GAP"
        formula = "N/A"

    print()
    if suggested is not None:
        print(f"  {label}. Formula: {formula}")
        print(f"  Suggested _SIMILARITY_THRESHOLD = {suggested}")
        print()
        print("  Update check_user_history.py:")
        print(f"    _SIMILARITY_THRESHOLD = {suggested}")
        print()
        print("  Update the calibration comment block in check_user_history.py")
        print("  with today's date, gap value, and threshold decision.")
    else:
        print("  ❌ NO GAP — KNOWN_RELEVANT and KNOWN_IRRELEVANT scores overlap.")
        print("  Revise corpus or synthetic summaries before setting threshold.")

    print()
    print("  Re-run this script after editing summarise_history() prompt template")
    print("  or switching embedding models.")


if __name__ == "__main__":
    main()
