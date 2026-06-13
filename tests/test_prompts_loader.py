import pytest
from sage_poc.prompts.loader import get_template, get_intent_template, reload_all
from sage_poc.prompts.schemas import PromptTemplate


@pytest.fixture(autouse=True)
def reset_cache():
    reload_all()
    yield
    reload_all()


def test_loader_raises_key_error_for_unknown_template():
    with pytest.raises(KeyError):
        get_template("nonexistent_id")


def test_get_intent_template_returns_none_for_unknown_intent():
    assert get_intent_template("completely_unknown_intent") is None


def test_prompt_template_pydantic_validates():
    data = {
        "template_id": "test_tmpl",
        "version": "1.0.0",
        "effective_date": "2026-05-22",
        "layer": "L0",
        "role": "system",
        "always_include": True,
        "word_budget": 100,
        "content": "Hello world",
    }
    tmpl = PromptTemplate.model_validate(data)
    assert tmpl.template_id == "test_tmpl"
    assert tmpl.variables == []
    assert tmpl.intent is None


def test_load_l3_skill_wrapper():
    tmpl = get_template("L3_skill_wrapper")
    assert tmpl.layer == "L3"
    assert tmpl.role == "user"
    assert tmpl.always_include is False
    assert "{skill_name}" in tmpl.content
    assert "{few_shot_block}" in tmpl.content
    assert "Do NOT announce the technique name" in tmpl.content


def test_l3_skill_wrapper_tone_appears_before_skill_name():
    """Tone instruction must be the first variable in L3 so it primes the LLM before technique detail."""
    tmpl = get_template("L3_skill_wrapper")
    assert tmpl.content.index("{tone_instruction}") < tmpl.content.index("{skill_name}")


def test_get_template_loads_from_disk(tmp_path, monkeypatch):
    """Verify the loader actually reads JSON files from disk and parses them."""
    import sage_poc.prompts.loader as loader_module

    tmpl_json = {
        "template_id": "fixture_tmpl",
        "version": "1.0.0",
        "effective_date": "2026-05-22",
        "layer": "L0",
        "role": "system",
        "always_include": True,
        "word_budget": 50,
        "content": "Hello from fixture",
    }
    (tmp_path / "fixture_tmpl.json").write_text(
        __import__("json").dumps(tmpl_json), encoding="utf-8"
    )

    monkeypatch.setattr(loader_module, "_DATA_DIR", tmp_path)
    reload_all()

    tmpl = get_template("fixture_tmpl")
    assert tmpl.template_id == "fixture_tmpl"
    assert tmpl.content == "Hello from fixture"
    assert tmpl.layer == "L0"


def test_load_l0_persona():
    tmpl = get_template("L0_persona")
    assert tmpl.layer == "L0"
    assert tmpl.role == "system"
    assert tmpl.always_include is True
    # L0 v2.0.0 (2026-06-14): budget raised 150->550 to match the prompt's actual scope
    # (format + relational + safety + limits); content now starts with the FORMAT block.
    assert tmpl.word_budget == 550
    assert tmpl.content.startswith("FORMAT")


def test_l0_persona_has_no_em_dashes():
    tmpl = get_template("L0_persona")
    assert "—" not in tmpl.content


def test_l0_persona_contains_scope_constraint():
    tmpl = get_template("L0_persona")
    assert "diagnos" in tmpl.content.lower()


def test_l0_persona_contains_skill_instructions_clause():
    tmpl = get_template("L0_persona")
    assert "skill instructions" in tmpl.content


def test_load_l1_history():
    tmpl = get_template("L1_history")
    assert tmpl.layer == "L1"
    assert tmpl.role == "user"
    assert tmpl.window_size == 8
    assert "{history_lines}" in tmpl.content


import pytest as _pytest


@_pytest.mark.parametrize("intent", [
    "general_chat", "new_skill", "skill_continuation", "info_request",
    "exit_skill", "scope_refusal", "jailbreak", "crisis", "low_confidence",
])
def test_all_intents_have_l2_template(intent):
    tmpl = get_intent_template(intent)
    assert tmpl is not None, f"No L2 template for intent: {intent}"
    assert tmpl.layer == "L2"
    assert tmpl.intent == intent


def test_load_l4_knowledge():
    tmpl = get_template("L4_knowledge")
    assert tmpl.layer == "L4"
    assert tmpl.max_passages == 3
    assert "{passages}" in tmpl.content
    assert "not certain" in tmpl.content


def test_load_l5_user_context():
    tmpl = get_template("L5_user_context")
    assert tmpl.layer == "L5"
    assert "{flags_summary}" in tmpl.content
    assert "{distress_note}" in tmpl.content


def test_l0_persona_no_explicit_therapy_technique_names():
    """L0_persona must not name specific clinical techniques (CBT, DBT, MI).
    These map to 'mental health coach' in LLM training data.
    """
    tmpl = get_template("L0_persona")
    content_lower = tmpl.content.lower()
    assert "cbt" not in content_lower, "L0_persona must not reference CBT by name"
    assert "dbt" not in content_lower, "L0_persona must not reference DBT by name"
    assert "motivational interviewing" not in content_lower, (
        "L0_persona must not reference MI by name"
    )


def test_l0_persona_has_negative_identity_constraint():
    """L0_persona must explicitly prohibit coach/therapist/counsellor self-labelling."""
    tmpl = get_template("L0_persona")
    content_lower = tmpl.content.lower()
    assert "not a therapist" in content_lower or "not a coach" in content_lower, (
        "L0_persona must contain an explicit negative identity constraint"
    )


def test_l0_persona_has_prescribed_self_description():
    """L0_persona must tell the LLM what to say when asked what it is."""
    tmpl = get_template("L0_persona")
    content_lower = tmpl.content.lower()
    assert "wellness companion" in content_lower, (
        "L0_persona must contain 'wellness companion' as the prescribed self-description"
    )


def test_l0_persona_no_sycophantic_openers():
    """Anti-sycophancy guarantee. As of L0 v2.0.0 (2026-06-14) the persona uses POSITIVE framing
    (prompt-engineering best practice: positive directives beat long 'don't' lists, which can prime
    the banned phrases). The explicit banned-opener LIST was moved OUT of the prompt; the hard
    guarantee now lives in output_gate's banned-opener enforcement. This test verifies BOTH halves
    so the guarantee cannot silently disappear:
      1) L0 carries the positive opener directive, and
      2) output_gate still HARD-blocks the sycophantic praise openers (which were previously
         prompt-only and NOT gate-enforced — see output_gate._BANNED_OPENER_PATTERNS).
    """
    tmpl = get_template("L0_persona")
    content = tmpl.content
    assert "OPENERS" in content, "L0 persona must contain an OPENERS constraint block"
    assert "stock pleasantries" in content or "Warmth comes from substance" in content, (
        "L0 persona must carry the positive opener directive (warmth from substance, not stock phrases)"
    )
    # The hard guarantee now lives at the gate, independent of the prompt.
    from sage_poc.nodes.output_gate import _BANNED_OPENER_RE
    for opener in ("That's great to hear", "That's really good to hear", "I'm glad to hear that"):
        assert _BANNED_OPENER_RE.match(opener), (
            f"output_gate must hard-block the sycophantic opener {opener!r} now that the L0 prompt "
            f"no longer lists it"
        )


def test_l3_skill_wrapper_no_therapeutic_framing():
    """L3_skill_wrapper must not use 'therapeutic' in its header.
    Cumulative clinical framing contributes to identity drift toward 'mental health coach'.
    """
    tmpl = get_template("L3_skill_wrapper")
    assert "THERAPEUTIC APPROACH" not in tmpl.content, (
        "L3_skill_wrapper header must not use 'THERAPEUTIC APPROACH' — use 'SUPPORT APPROACH'"
    )
    assert "SUPPORT APPROACH" in tmpl.content, (
        "L3_skill_wrapper header must use 'SUPPORT APPROACH FOR THIS TURN'"
    )
