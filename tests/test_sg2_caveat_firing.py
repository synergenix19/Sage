"""SG-2 firing fix — the mandatory contraindication caveat is delivered DETERMINISTICALLY by the
gate, bypassing LLM discretion (Cardinal Rule: the LLM renders language, it does NOT decide whether
safety copy fires). Content-in-JSON is NECESSARY BUT NOT SUFFICIENT — the driven transcript
(2026-07-10, prod) showed the LLM dropping the caveat and suggesting cold water without the screen.
This fix + these tests guarantee firing, and the firing test asserts the caveat leads (before any
temperature/exercise content). Generalizes to any step carrying `mandatory_caveat` (the class fix).
"""
from sage_poc.nodes.output_gate import _pin_contraindication_caveat
from sage_poc.skills.schema import load_skill


def test_gate_prepends_caveat_ahead_of_technique_content():
    caveat = ("Please check before trying this: the temperature step can slow the heart rate; "
              "if you have a heart condition or you're pregnant, skip those two steps.")
    llm_reply = "Let's get cold water on your wrists for 30 seconds, tell me when you've done it."
    out = _pin_contraindication_caveat(llm_reply, caveat)
    assert out.startswith(caveat), "caveat must lead — ahead of any temperature/exercise instruction"
    assert "cold water" in out, "technique content preserved after the caveat"


def test_gate_noop_when_step_has_no_caveat():
    assert _pin_contraindication_caveat("hello", "") == "hello"
    assert _pin_contraindication_caveat("hello", None) == "hello"


def test_gate_idempotent_if_caveat_already_surfaced():
    caveat = "Please check before trying this: skip the temperature and exercise steps if pregnant."
    already = caveat + " Now, when you're ready, breathe slowly."
    assert _pin_contraindication_caveat(already, caveat) == already, "must not double the caveat"


def test_dbt_tipp_entry_screen_carries_mandatory_caveat():
    entry = next(s for s in load_skill("dbt_tipp").steps if s.step_id == "entry_screen")
    cav = entry.mandatory_caveat
    assert "heart condition" in cav and "pregnant" in cav and "skip those two steps" in cav, (
        "the TIPP entry screen must carry the verbatim cardiac/pregnancy caveat as mandatory copy"
    )


# ── box_breathing (NO-GATE acute skill) — clinician-approved caveat, packet 2026-07-14 #1 ──
# box_breathing has no entry_screen: the FIRST EXECUTED step is the first content step
# (skill.steps[0] == "inhale_hold", the step skill_select seeds active_step_id to). The SG-2
# mechanism keys on the executed step_id (skill_executor.py: step_mandatory_caveat = the caveat
# of the step whose step_id == active/executed step), so it fires on the no-gate first content
# step with no entry_screen-specific logic. These tests lock that: the caveat is present on the
# first executed step, it LEADS the first-step output ahead of any breathing/hold instruction,
# it is idempotent, and it does NOT fire on the second (uncaveated) step.

# The clinician-approved caveat, verbatim (packet 2026-07-14 item #1).
_BOX_CAVEAT = (
    "Before we start — if you have asthma, a breathing condition, or a heart condition, "
    "we'll keep this gentle and skip the breath-hold. Just let me know and we'll adjust."
)


def _executed_step_caveat(skill_id: str, step_id: str) -> str:
    """Mirror skill_executor.py's selection of step_mandatory_caveat for the executed step:
    step_mandatory_caveat = next((s.mandatory_caveat for s in skill.steps if s.step_id == step_id), "").
    This is the value the gate receives via state["step_mandatory_caveat"]."""
    skill = load_skill(skill_id)
    return next((s.mandatory_caveat for s in skill.steps if s.step_id == step_id), "")


def test_box_breathing_first_executed_step_is_first_content_step():
    # No-gate skill: the executor runs skill.steps[0] first (skill_select seeds active_step_id
    # to skill.steps[0].step_id). That step, not an entry_screen, must carry the caveat.
    steps = load_skill("box_breathing").steps
    assert steps[0].step_id == "inhale_hold", "first executed step must be the first content step"


def test_box_breathing_first_step_carries_verbatim_approved_caveat():
    cav = _executed_step_caveat("box_breathing", "inhale_hold")
    assert cav == _BOX_CAVEAT, "the first content step must carry the clinician-approved caveat verbatim"


def test_box_breathing_caveat_leads_before_breathing_instructions():
    # The value the gate receives for the executed first step, pinned onto a representative
    # first-step breathing instruction. Behavioral: the caveat LEADS, ahead of the hold cue.
    step_caveat = _executed_step_caveat("box_breathing", "inhale_hold")
    llm_reply = ("Let's start together. Breathe in slowly through your nose: 1... 2... 3... 4. "
                 "Now hold gently, no strain: 1... 2... 3... 4.")
    out = _pin_contraindication_caveat(llm_reply, step_caveat)
    assert out.startswith(step_caveat), "caveat must lead — ahead of any breathing/hold instruction"
    assert "Breathe in" in out, "breathing technique content preserved after the caveat"
    assert out.index(step_caveat) < out.index("hold"), "caveat must precede the breath-hold cue"


def test_box_breathing_caveat_idempotent_no_double_prepend():
    step_caveat = _executed_step_caveat("box_breathing", "inhale_hold")
    already = step_caveat + " Breathe in slowly through your nose: 1... 2... 3... 4."
    assert _pin_contraindication_caveat(already, step_caveat) == already, "must not double the caveat"


def test_box_breathing_second_step_has_no_caveat_and_gate_noops():
    # Only the first content step is signed; the exhale step carries no caveat, so the gate
    # must not inject one when the executor runs the second step.
    step_caveat = _executed_step_caveat("box_breathing", "exhale_hold")
    assert step_caveat == "", "second step must not carry a mandatory caveat (only inhale_hold is signed)"
    reply = "Now breathe out slowly through your mouth: 1... 2... 3... 4."
    assert _pin_contraindication_caveat(reply, step_caveat) == reply, "no caveat step -> gate no-op"


# ── delivery-path observability: sg2_caveat_delivery structured log (day-one on box_breathing) ──
# The gate records WHICH path delivered the caveat: gate_injected (gate prepended, LLM omitted it)
# vs llm_complied (LLM already surfaced it, gate no-op). Prod-queryable gate-inject rate: nonzero =>
# composer instruction not landing (tuning signal); zero on a firing skill => backstop untested live.

def test_sg2_delivery_path_logged_gate_injected(caplog):
    import logging
    step_caveat = _executed_step_caveat("box_breathing", "inhale_hold")
    with caplog.at_level(logging.INFO, logger="sage_poc.nodes.output_gate"):
        out = _pin_contraindication_caveat(
            "Breathe in slowly through your nose: 1... 2... 3... 4.",
            step_caveat, skill_id="box_breathing", step_id="inhale_hold",
        )
    assert out.startswith(step_caveat), "gate must have injected the caveat"
    assert "sg2_caveat_delivery" in caplog.text and "path=gate_injected" in caplog.text
    assert "skill=box_breathing" in caplog.text and "step=inhale_hold" in caplog.text


def test_sg2_delivery_path_logged_llm_complied(caplog):
    import logging
    step_caveat = _executed_step_caveat("box_breathing", "inhale_hold")
    already = step_caveat + " Breathe in slowly through your nose: 1... 2... 3... 4."
    with caplog.at_level(logging.INFO, logger="sage_poc.nodes.output_gate"):
        out = _pin_contraindication_caveat(
            already, step_caveat, skill_id="box_breathing", step_id="inhale_hold",
        )
    assert out == already, "LLM already surfaced it -> gate no-op"
    assert "sg2_caveat_delivery" in caplog.text and "path=llm_complied" in caplog.text
