def test_psychotic_referral_skill_loads():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("psychotic_referral")
    assert skill.skill_id == "psychotic_referral"
    assert skill.target_presentations == []
    assert skill.semantic_description == ""
    assert len(skill.steps) == 1
    step = skill.steps[0]
    combined = (step.technique_description or "") + (step.goal or "") + " ".join(step.examples or [])
    # H4 adopted (all gates cleared 2026-07-10): National line 800-4673 (supersedes MoHAP 800 46342).
    # Copy remediated (H4 false-24/7 ripple fix): "MoHAP Counselling Line" -> {{crisis_label}}, and the
    # false "available 24 hours a day" / AR "متاح كل وقت" claims replaced with the true {{crisis_hours}}
    # (8am-8pm daily), urgency pointed to 999. Availability truthfulness is now guarded by
    # test_crisis_availability_consistency.py. Copy PENDING clinician review. See PR #288 body.
    assert "800-4673" in combined, "Helpline number 800-4673 must appear verbatim"
    en_examples = [e for e in (step.examples or []) if not any('؀' <= c <= 'ۿ' for c in e)]
    ar_examples = [e for e in (step.examples or []) if any('؀' <= c <= 'ۿ' for c in e)]
    assert len(en_examples) >= 3, f"Need ≥3 EN examples, got {len(en_examples)}"
    assert len(ar_examples) >= 3, f"Need ≥3 AR examples, got {len(ar_examples)}"

def test_psychotic_referral_in_registry():
    from sage_poc.skill_ids import SKILL_REGISTRY
    assert "psychotic_referral" in SKILL_REGISTRY

def test_psychotic_referral_in_keyword_semantic_skip():
    from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
    assert "psychotic_referral" in KEYWORD_SEMANTIC_SKIP
