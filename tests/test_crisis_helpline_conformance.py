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
from sage_poc.crisis_copy import resolve_crisis_placeholders

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
    # Consistency: whatever config holds, every site must carry it after resolution. The files now
    # carry {{crisis_*}} placeholders (raw text no longer holds the number), so this checks the
    # RESOLVED output — what actually reaches the LLM / user — carries config's number. Change
    # config -> resolved sites follow. Still asserts NOTHING about which number is correct.
    for rel in _CRISIS_COPY_FILES:
        resolved = resolve_crisis_placeholders((_ROOT / rel).read_text(encoding="utf-8"))
        assert _NUM in resolved, (
            f"{rel} resolved output diverges from config.CRISIS_CONFIG['number'] ({_NUM!r}). "
            "Every site renders config (the single source) via the {{crisis_number}} placeholder; "
            "update config if the number changed, or restore the placeholder if it was edited out."
        )


def test_python_fallbacks_do_not_hardcode_the_crisis_number():
    # The Python fail-safe crisis strings (graph.py hard-fallback, output_gate.py monitoring
    # fallback) source number/emergency/hours from CRISIS_CONFIG, not literals. The JSON boot
    # guard does NOT cover Python f-strings, so this guards them: the number must not reappear
    # inline (that would be a second, unguarded source that could silently diverge).
    for rel in ["graph.py", "nodes/output_gate.py"]:
        src = (_ROOT / rel).read_text(encoding="utf-8")
        assert _NUM not in src, f"{rel} hardcodes the crisis number {_NUM!r} inline; use CRISIS_CONFIG."
