"""Cheap-gains K1-K5 (Vee-approved 2026-07-28) — keyword coverage for uncovered affect phrasings.

K1 §3a low-mood, K2 §3b worthlessness, K3 §6b boundary, K4 §7b reconnection -> add a phrasing to the
matching skill; K5 S2a fresh grief -> remove the over-broad bare death-announcement that over-offered
grief_loss where presence was prescribed. Per-category: new phrasing present; neighbors unmoved; K2 stays
off the crisis surface; K5 keeps processing-grief coverage (S2b) while dropping the fresh-grief over-fire.
"""
import json, os

B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/sage_poc/skills")
def tp(skill): return json.load(open(os.path.join(B, skill + ".json")))["target_presentations"]


def test_k1_k4_new_phrasings_present():
    ba = tp("behavioral_activation")
    assert "mood has dropped" in ba and "pulled back" in ba          # K1
    assert "want to reconnect" in ba and "reconnect" in ba            # K4
    assert "no value as a person" in tp("cbt_thought_record")         # K2
    ie = tp("interpersonal_effectiveness")
    assert "crossing a line" in ie and "stop crossing a line" in ie   # K3


def test_k5_removed_the_fresh_grief_over_fire_but_kept_processing_grief():
    gl = tp("grief_loss")
    assert "someone died" not in gl                                   # K5 removed
    # S2b (processing grief -> skill IS prescribed) must stay covered — neighbor unmoved
    assert any(x in gl for x in ("coping with loss", "how to deal with grief", "can't stop grieving"))


def test_neighbors_unmoved_passing_variants_still_covered():
    ba = tp("behavioral_activation")
    assert "lost interest in everything" in ba and "keep cancelling" in ba
    assert "worthless" in tp("cbt_thought_record")


def test_k2_new_keyword_does_not_overlap_the_crisis_surface():
    new = ["no value as a person", "mood has dropped", "pulled back", "reconnect",
           "want to reconnect", "crossing a line", "stop crossing a line"]
    crisis = []
    for f in ("crisis_keywords.json", "passive_si_patterns.json"):
        d = json.load(open(os.path.join(os.path.dirname(B), "rules/data/safety", f)))
        for r in (d.get("rules", d) if isinstance(d, (list, dict)) else []):
            crisis += [p.lower() for p in (r.get("patterns") or [])]
    hits = [(n, c) for n in new for c in crisis if n in c or c in n]
    assert not hits, f"a cheap-gains keyword overlaps a crisis phrase: {hits}"
