"""SG-2 — DBT TIPP cardiac/pregnancy safety caveat (BOT BEHAVIOUR.docx L188).

Safety-content contract: the most-used acute skill MUST carry the signed cardiac/
pregnancy contraindication caveat at its entry screen, and MUST hold on a pregnancy
disclosure. Guards against silent removal/regression of signed safety copy.

Verbatim source (BOT BEHAVIOUR.docx, Category 3 High Anxiety > 3. Psychoeducation, L188):
  "Please check before trying this: the temperature step (cold water or ice on the
   face) can slow the heart rate suddenly, and the exercise step raises it quickly.
   If you have a heart condition, an irregular heartbeat, or you're pregnant, please
   skip those two steps or check with a doctor first."
"""
from sage_poc.skills.schema import load_skill


def _entry_screen():
    skill = load_skill("dbt_tipp")
    return next(s for s in skill.steps if s.step_id == "entry_screen")


def test_entry_screen_holds_on_pregnancy():
    """Pregnancy must be an explicit hold condition (was entirely absent pre-SG-2)."""
    entry = _entry_screen()
    combined = " ".join(
        [entry.contraindications or "", entry.completion_criteria or "", entry.technique_description or ""]
    ).lower()
    assert "pregnan" in combined, (
        "TIPP entry screen must hold on a pregnancy disclosure (BOT BEHAVIOUR L188)"
    )


def test_entry_screen_surfaces_cardiac_pregnancy_caveat_verbatim():
    """The verbatim L188 caveat must be present as user-facing entry copy (examples)."""
    entry = _entry_screen()
    haystack = " ".join(entry.examples or []).lower()
    assert "heart condition" in haystack, "caveat must warn on heart condition"
    assert "irregular heartbeat" in haystack, "caveat must warn on irregular heartbeat"
    assert "pregnant" in haystack, "caveat must warn on pregnancy"
    assert ("skip those two steps" in haystack) or ("check with a doctor" in haystack), (
        "caveat must instruct skipping the temperature/exercise steps or checking with a doctor"
    )
