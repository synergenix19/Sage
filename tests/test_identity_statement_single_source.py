"""Single-source guard for Sage's identity statement (#6 drift fix).

Sage's identity line is defined canonically once in the ratified L0 persona (L0_persona.json v2.5.0,
clinical-lead signed 2026-06-25, live in prod): "a warm Khaleeji wellness companion ... You offer
emotional support and evidence-based coping tools." Two downstream surfaces restate it: the jailbreak
persona-reassertion (JAILBREAK_RESPONSE) and the CUO-ID-001 identity substitution. They had DRIFTED
("coping techniques" vs "coping tools"). These tests pin all three to one canonical wording so they
can never silently diverge again — the same defense pattern as the crisis byte-identical/parity guards.
"""
import json
from pathlib import Path

from sage_poc.nodes.output_gate import SAGE_IDENTITY_STATEMENT, JAILBREAK_RESPONSE

_SRC = Path(__file__).resolve().parents[1] / "src" / "sage_poc"


def test_jailbreak_response_is_the_canonical_identity_statement():
    # The jailbreak persona-reassertion IS the canonical identity statement, verbatim.
    assert JAILBREAK_RESPONSE == SAGE_IDENTITY_STATEMENT


def test_cuo_id_substitute_matches_canonical_identity_statement():
    # The CUO-ID-001 substitution must be byte-identical to the same canonical statement.
    w = json.loads((_SRC / "rules/data/cultural_output/wellness_identity.json").read_text(encoding="utf-8"))
    substitute = w["rules"][0]["action"]["substitute_with"]
    assert substitute == SAGE_IDENTITY_STATEMENT


def test_canonical_identity_conforms_to_signed_l0_persona():
    # Grounding: the canonical wording is anchored to the ratified L0 persona, not chosen ad hoc.
    persona = json.loads((_SRC / "prompts/templates/L0_persona.json").read_text(encoding="utf-8"))["content"]
    assert "wellness companion" in persona
    assert "evidence-based coping tools" in persona
    # and the canonical statement carries that exact persona phrasing
    assert "wellness companion" in SAGE_IDENTITY_STATEMENT
    assert "evidence-based coping tools" in SAGE_IDENTITY_STATEMENT
