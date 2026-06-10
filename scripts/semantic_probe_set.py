"""Fixed semantic routing probe set for grief_loss and interpersonal_effectiveness.

Committed before any description edits — this is the gate, not the calibration gap.
Run: uv run python scripts/semantic_probe_set.py

Each probe is (skill_id, message). Messages deliberately avoid exact target_presentations
phrases (those are keyword-tier). All probes test the semantic tier only.

Includes financial_anxiety bleed probes to detect interpersonal/financial over-capture.
"""
from __future__ import annotations

PROBES: list[tuple[str, str]] = [
    # ── grief_loss (10 probes) ──────────────────────────────────────────────
    # Presence-absence patterns
    ("grief_loss", "My mother passed away three months ago and I still cannot seem to get back to any sense of normal"),
    ("grief_loss", "The house feels completely empty without him and I do not know how to fill that space"),
    ("grief_loss", "I keep expecting her to walk in through the door and then remember all over again that she is gone"),
    ("grief_loss", "I wake up each morning and for a moment I forget he has died, and then it hits me all over again"),
    # Memory intrusion and grief anchoring
    ("grief_loss", "I cannot bring myself to go through her things or change anything in her room"),
    ("grief_loss", "Everything I see, every place we went together, reminds me of him and it is unbearable"),
    # Grief without outlet
    ("grief_loss", "People keep telling me I need to move on but I do not know what moving on is supposed to look like"),
    ("grief_loss", "I have not been able to cry properly and I do not know if something is wrong with me"),
    # Loss of identity/world
    ("grief_loss", "She was the person I talked to about everything and now I do not know who I am without her"),
    ("grief_loss", "My father was the one who held this family together, and now that he is gone I feel completely at a loss"),

    # ── interpersonal_effectiveness (10 probes) ────────────────────────────
    # Family hierarchy navigation
    ("interpersonal_effectiveness", "I need to have a serious conversation with my father but I am scared of how he will react"),
    ("interpersonal_effectiveness", "My father will not listen to anything I say and I do not know how to get through to him"),
    ("interpersonal_effectiveness", "I am caught between my wife and my mother and whatever I do one of them is hurt"),
    ("interpersonal_effectiveness", "I want to repair things with my sister after a bad argument but I do not know how to approach her"),
    ("interpersonal_effectiveness", "How do I talk to my in-laws about something sensitive without making everything worse"),
    # Competing loyalties
    ("interpersonal_effectiveness", "My parents are putting enormous pressure on me about something and I do not know how to handle it without damaging our relationship"),
    ("interpersonal_effectiveness", "I need to set a boundary with someone in my family but I am worried about the consequences"),
    ("interpersonal_effectiveness", "I cannot keep everyone in my family happy and it is tearing me apart"),
    # Conflict and repair
    ("interpersonal_effectiveness", "There is a lot of tension between my wife and her family and I am stuck in the middle"),
    ("interpersonal_effectiveness", "I want to say something important to someone I care about but I do not know how to begin"),

    # ── financial_anxiety (5 probes — bleed test) ──────────────────────────
    # Core financial (should route correctly to financial_anxiety)
    ("financial_anxiety", "I cannot sleep because I am terrified of what happens to my family if my contract is not renewed"),
    ("financial_anxiety", "Everything I earn goes straight to my parents back home and if I lose my income my whole household collapses"),
    ("financial_anxiety", "My entire sense of who I am comes from being the provider for my family and lately I feel that is slipping"),
    # Overlap cases (family + financial combined — interpersonal should NOT win)
    ("financial_anxiety", "My salary is not enough to meet all the obligations I have to my family and it is affecting everything"),
    ("financial_anxiety", "I am terrified of not being able to support my parents and siblings the way they depend on me to"),

    # ── cognitive_restructuring (4 probes — regression guard) ──────────────
    # These should route to cognitive_restructuring or cbt_thought_record (cluster)
    ("cognitive_restructuring", "Every time something uncertain comes up my mind immediately assumes the worst possible outcome"),
    ("cognitive_restructuring", "My thoughts spiral into catastrophe before I have any evidence that something is actually wrong"),
    ("cognitive_restructuring", "I know my thinking is distorted but I cannot seem to stop the negative patterns"),
    # Within-cluster (cbt_thought_record) — expected, note it
    ("cognitive_restructuring", "I assume people dislike me almost constantly even when there is no evidence for it"),
]

THRESHOLD = 0.459  # current SEMANTIC_THRESHOLD

if __name__ == "__main__":
    import sys, time
    sys.path.insert(0, "src")

    from sage_poc.nodes import skill_select as ss
    from sage_poc.skill_ids import SKILL_REGISTRY
    from sage_poc.skills.schema import load_skill
    import numpy as np

    t0 = time.time()
    ss._ensure_semantic_ready()
    unique_skills = len(set(ss._anchor_skill_ids))
    print(f"BGE-M3 ready in {time.time()-t0:.1f}s | {unique_skills} skills, {len(ss._anchor_skill_ids)} anchors embedded\n")

    def no_keyword_match(msg):
        msg_l = msg.lower()
        for sid in SKILL_REGISTRY:
            s = load_skill(sid)
            for kw in s.target_presentations:
                if kw.lower() in msg_l:
                    return False, sid, kw
        return True, None, None

    def raw_scores_top3(msg):
        msg_emb = ss._embed_model.encode([msg], normalize_embeddings=True)[0]
        raw = np.dot(ss._anchor_embeddings, msg_emb)
        skill_scores = {}
        for i, sid in enumerate(ss._anchor_skill_ids):
            score = float(raw[i])
            if score > skill_scores.get(sid, 0.0):
                skill_scores[sid] = score
        return sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)[:3]

    skills_seen = set()
    current_group = None
    results = []

    for expected_skill, msg in PROBES:
        if expected_skill != current_group:
            current_group = expected_skill
            print(f"── {expected_skill} ──")

        clean, blocker_sid, blocker_kw = no_keyword_match(msg)
        if not clean:
            print(f"  KEYWORD_BLOCK: '{blocker_kw}' ({blocker_sid}) in {repr(msg[:50])}")
            results.append({"expected": expected_skill, "msg": msg, "blocked": True})
            continue

        top3 = raw_scores_top3(msg)
        top_skill, top_score = top3[0]
        above = top_score >= THRESHOLD
        correct = top_skill == expected_skill
        cluster_hit = top_skill in ("cbt_thought_record",) and expected_skill == "cognitive_restructuring"

        status = "OK" if (correct and above) else ("CLUSTER" if cluster_hit else ("MISS_LOW" if not above else "WRONG"))
        gap_to_threshold = top_score - THRESHOLD

        print(f"  [{status:9}] score={top_score:.3f} ({gap_to_threshold:+.3f}) top={top_skill}")
        if not correct:
            print(f"             2nd={top3[1][0]}:{top3[1][1]:.3f}  3rd={top3[2][0]}:{top3[2][1]:.3f}")
        print(f"             msg: {repr(msg[:65])}")

        results.append({
            "expected": expected_skill,
            "msg": msg,
            "top_skill": top_skill,
            "top_score": top_score,
            "status": status,
            "above": above,
            "correct": correct,
        })

    ok = sum(1 for r in results if not r.get("blocked") and r["status"] == "OK")
    cluster = sum(1 for r in results if not r.get("blocked") and r.get("status") == "CLUSTER")
    miss_low = sum(1 for r in results if not r.get("blocked") and r.get("status") == "MISS_LOW")
    wrong = sum(1 for r in results if not r.get("blocked") and r.get("status") == "WRONG")
    total = sum(1 for r in results if not r.get("blocked"))

    print(f"\n{'─'*60}")
    print(f"OK={ok}  CLUSTER={cluster}  MISS_LOW={miss_low}  WRONG={wrong}  total={total}")
    print(f"(CLUSTER = within ruminative_anxiety cluster, expected behaviour)")
