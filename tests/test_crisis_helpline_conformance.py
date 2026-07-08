"""Crisis helpline — CONSISTENCY guard, not a correctness verdict.

config.CRISIS_CONFIG is the single SOURCE. Every crisis-copy site must render WHATEVER number
config holds — this enforces "change it in one place and all sites follow," nothing more.

IMPORTANT: this test asserts NOTHING about which number is correct. The G8 question — is the
currently-served "800 46342" a transcription error for "800 4673" (LifeLine Arabia / 800-HOPE),
which is what the authoritative directories list? — is a FACTUAL matter for a DIAL-TEST, not a
test literal. Whatever the dial-test confirms, set it in config.CRISIS_CONFIG and every site
follows; this test stays green because it only checks they all match config. It deliberately does
NOT forbid any candidate number (forbidding 800 4673 would red the build for inserting the
possibly-correct value).
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


def test_config_has_a_nonempty_number():
    # A value exists. NOT asserting WHICH — the dial-test owns correctness, not this literal.
    assert _NUM and _NUM.strip()


def test_every_crisis_copy_site_matches_config():
    # Consistency: whatever config holds, every site must carry it. Change config -> sites follow.
    for rel in _CRISIS_COPY_FILES:
        text = (_ROOT / rel).read_text(encoding="utf-8")
        assert _NUM in text, (
            f"{rel} diverges from config.CRISIS_CONFIG['number'] ({_NUM!r}). "
            "Update the site to match config (the single source), or update config if the number changed."
        )
