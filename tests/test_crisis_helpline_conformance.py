"""Crisis helpline — config.CRISIS_CONFIG is the single CANONICAL number; every crisis-copy site
must use it and none may re-embed a divergent number. Until backend crisis prose is templated,
this conformance test is the enforcement: a diverging literal fails CI (can't merge).

Deliberately NOT runtime-templating the number into live crisis prose — a placeholder that fails
to resolve IN a crisis message is worse than a test-enforced literal. This guards instead.
"""
from pathlib import Path
from sage_poc.config import CRISIS_CONFIG

_NUM = CRISIS_CONFIG["number"]
_ROOT = Path(__file__).resolve().parents[1] / "src" / "sage_poc"

# Full inventory of backend crisis-copy sites that embed the helpline number (verified 2026-07-08).
_CRISIS_COPY_FILES = [
    "rules/data/crisis_content/en_uae.json",
    "rules/data/crisis_content/ar_uae.json",
    "rules/data/prompt_injection/clinical_flag_adaptations.json",
    "rules/data/prompt_injection/third_party_guidance.json",
    "prompts/templates/L0_persona.json",
    "skills/psychotic_referral.json",
    "skills/psychoed_depression.json",
    "skills/post_crisis_check_in.json",
]


def test_config_pins_the_po_approved_number():
    assert _NUM == "800 46342"          # PO-approved 2026-07-08 (G8 transcription theory overruled)
    assert CRISIS_CONFIG["hours"] == "24/7"
    assert CRISIS_CONFIG["emergency"] == "999"


def test_every_crisis_copy_site_uses_the_canonical_number():
    for rel in _CRISIS_COPY_FILES:
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert _NUM in text, f"{rel} does not contain the canonical crisis number {_NUM!r}"


def test_no_site_re_embeds_the_wrong_g8_variant():
    # The 800 4673 / 800-HOPE transcription variant must never appear in crisis copy.
    for rel in _CRISIS_COPY_FILES:
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert "800 4673" not in text and "8004673" not in text, f"{rel} re-embeds the wrong number 800 4673"
