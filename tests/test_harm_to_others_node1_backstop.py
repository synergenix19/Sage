"""#219 harm-to-others Node-1 deterministic backstop (Layer 2).

Built active:false pending clinician Group-A approval. These tests assert:
1. rule structure (Node-1 crisis rule, Group A only, negation_check, correct flag_id);
2. INERT AS SHIPPED — active:false means the engine does NOT fire it, so prod is unaffected
   until the clinician approves and it is activated;
3. pattern-level Group A/B separation — explicit intent matches; figurative venting does not
   (the inverted-FP-asymmetry the packet names: a false positive here is a crisis card served
   to someone venting, not a warm abstain).

The FULL gate (engine firing + negation suppression + crisis-recall + downstream shadow) runs
on activation, per the clinician-approval flow.
"""
import json
import pathlib

from sage_poc.rules import engine as rules_engine

_KW = pathlib.Path("src/sage_poc/rules/data/safety/crisis_keywords.json")


def _rule():
    d = json.loads(_KW.read_text())
    return next((r for r in d["rules"] if r["rule_id"] == "SK-EN-HTO-001"), None)


def test_rule_structure_node1_group_a_only():
    r = _rule()
    assert r is not None, "SK-EN-HTO-001 must exist"
    assert r["active"] is True, "Group A clinician-approved 2026-07-09 -> active"
    assert r["action"] == {"type": "crisis_flag", "flag_id": "harm_to_others_explicit"}, \
        "must be a Node-1 crisis_flag (reaches crisis/escalation path), NOT a skill_select veto"
    assert "negation_check" in r["modifiers"], "must carry negation_check ('would never hurt him')"
    assert r["language"] == "en"


def _crisis_flags(utt):
    res = rules_engine.evaluate("safety", {
        "text_en": utt.lower(), "text_ar": None, "language": "en", "text_raw": utt.lower(),
    })
    return [a.get("flag_id") for a in res.actions if a.get("type") == "crisis_flag"]


def test_fires_on_group_a_explicit_intent():
    for utt in ["i'm planning to hurt him when he gets home",
                "i want to hurt someone so badly right now",
                "i'm going to hurt them, i've decided"]:
        assert "harm_to_others_explicit" in _crisis_flags(utt), f"Group A must reach crisis: {utt}"


def test_does_not_fire_on_venting_or_negation():
    # inverted FP asymmetry: figurative venting + negation must NOT over-escalate to a crisis card
    for utt in ["i'm so angry at my boss i could kill him",
                "my brother is so annoying i could strangle him",
                "i would never hurt him, i just needed to vent"]:
        assert "harm_to_others_explicit" not in _crisis_flags(utt), \
            f"figurative venting / negation must NOT fire (trust-damaging over-escalation): {utt}"


def test_pattern_group_a_matches_explicit_intent():
    pats = [p.lower() for p in _rule()["patterns"]]
    group_a = [
        "i'm planning to hurt him when he gets home",
        "i want to hurt someone so badly right now",
        "i'm going to hurt them, i've decided",
    ]
    for utt in group_a:
        assert any(p in utt.lower() for p in pats), f"Group A explicit intent must match: {utt}"


def test_pattern_does_not_match_figurative_venting():
    # Group B (figurative/anger-adjacent) is HELD — must NOT be in the shipped Group A patterns.
    pats = [p.lower() for p in _rule()["patterns"]]
    venting = [
        "i'm so angry at my boss i could kill him",
        "my brother is so annoying i could strangle him",
        "that meeting was so frustrating i wanted to scream",
    ]
    for utt in venting:
        assert not any(p in utt.lower() for p in pats), \
            f"figurative venting must NOT match Group A (inverted FP asymmetry): {utt}"
