"""W7 (commit-1): the crisis helpline NUMBER is single-sourced from config.CRISIS_CONFIG.

SCOPE (deliberately narrow — see plan §K / G8):
  - This guards the CODE sites only (graph.py, output_gate.py): they must reference the
    number via the config constant, never re-embed the digits.
  - Skill JSONs and crisis_content rules carry the number as CLINICIAN CONTENT
    (Cardinal Rule 4). Those literals are pinned by test_corpus_integrity.py and are
    changed only under the G8 fast-track re-sign — NOT by this test, and NOT via
    placeholder templating (that would be schema scope creep beyond §K).

Commit-1 is behaviour-identical: values are unchanged (number "800 46342", hours "24/7",
label as-authored). The value/label/hours correction to "800 4673" / "Mental Support Line"
/ "8am-8pm daily" + the rules-JSON + L0 edits ship together in the gated commit-2.
"""
import pathlib
from sage_poc.config import CRISIS_CONFIG, CRISIS_LINE_UAE

_SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "sage_poc"


def _read(rel: str) -> str:
    return (_SRC / rel).read_text(encoding="utf-8")


def test_crisis_config_shape():
    assert set(CRISIS_CONFIG) >= {"number", "label", "hours", "emergency"}
    # back-compat alias so existing importers keep working during the migration
    assert CRISIS_LINE_UAE == CRISIS_CONFIG["number"]


def test_code_sites_do_not_hardcode_the_helpline_number():
    # graph.py / output_gate.py must reference the number through the config constant,
    # never the literal digits. (Clinician-authored JSONs are out of scope — see module docstring.)
    number = CRISIS_CONFIG["number"]
    for rel in ("graph.py", "nodes/output_gate.py"):
        assert number not in _read(rel), (
            f"{rel} hardcodes the crisis number {number!r}; reference CRISIS_CONFIG instead"
        )
