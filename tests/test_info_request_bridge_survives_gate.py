"""Guarded contract: the info_request continuation bridge (a STATEMENT) survives the
directive-posture question strip, AND the strip's scope stays question-only.

Reconciles D4 (info_request -> strip trailing QUESTION, answer-first; commit abf1f8a,
governed carve-out ticket #22 LOCK-QDISC-22) with the engagement goal (keep the
conversation going, "question or not"). The reworded v2.1.0 bridge is a STATEMENT, so
it passes through `_strip_trailing_question` untouched.

Condition 2 (guarded contract, not coincidence): the survival rests on an
implementation detail — `_strip_trailing_question` matches only question-terminated
trailing sentences (`_TRAILING_QUESTION_RE`). If that scope is ever broadened to strip
statements, Invariant 2 reds the build BEFORE prod amputates the bridge again.
Arabic (؟) is included because prod is Khaleeji-first and ?/؟ is a per-language seam
(the strip was made ؟-aware in the D4 R1 work for native-Arabic generation).
"""
from sage_poc.nodes.output_gate import _strip_trailing_question, _limit_to_one_question

_EN_ANSWER = (
    "Anxiety is the body's response to perceived threat or uncertainty. "
    "It becomes a concern when it is persistent, intense, and interferes with daily life."
)
# v2.1.0 shape: a warm continuation STATEMENT, no '?'
_EN_STATEMENT_BRIDGE = _EN_ANSWER + " If any of this connects to something you're going through, I'm here to talk it through."
# v2.0.0 shape that FAILED in prod: an invitation rendered as a QUESTION
_EN_QUESTION_BRIDGE = _EN_ANSWER + " Is there something specific you'd like to know more about?"

_AR_ANSWER = "القلق هو استجابة الجسم لتهديد محتمل. يصبح مصدر قلق عندما يستمر ويؤثر على الحياة اليومية."
_AR_STATEMENT_BRIDGE = _AR_ANSWER + " إن كان هذا يمس شيئًا تمر به، أنا هنا إن أردت أن نتحدث فيه."
_AR_QUESTION_BRIDGE = _AR_ANSWER + " هل هناك شيء محدد تودّ معرفته؟"


# ---- Invariant 1: the STATEMENT bridge survives the strip (EN + AR) ----
def test_en_statement_bridge_survives_strip():
    assert _strip_trailing_question(_EN_STATEMENT_BRIDGE) == _EN_STATEMENT_BRIDGE
    assert _limit_to_one_question(_EN_STATEMENT_BRIDGE) == _EN_STATEMENT_BRIDGE


def test_ar_statement_bridge_survives_strip():
    assert _strip_trailing_question(_AR_STATEMENT_BRIDGE) == _AR_STATEMENT_BRIDGE
    assert _limit_to_one_question(_AR_STATEMENT_BRIDGE) == _AR_STATEMENT_BRIDGE


# ---- Contrast: this is WHY v2.0.0 failed — a QUESTION bridge is amputated (EN + AR) ----
def test_en_question_bridge_is_stripped():
    out = _strip_trailing_question(_EN_QUESTION_BRIDGE)
    assert out == _EN_ANSWER and "?" not in out


def test_ar_question_bridge_is_stripped():
    out = _strip_trailing_question(_AR_QUESTION_BRIDGE)
    assert "؟" not in out and out.startswith(_AR_ANSWER)


# ---- Invariant 2: strip scope is QUESTION-ONLY and TRAILING-ONLY — pin it (EN + AR) ----
# These contain a '?'/'؟' (so the fast-path guard does NOT short-circuit), yet end on a
# statement. The strip must remove nothing. If the regex is broadened to strip trailing
# sentences regardless of terminator, or to strip non-trailing questions, these RED.
def test_strip_is_trailing_question_only_en():
    t = _EN_ANSWER + " Does that make sense so far? I'm here if you want to go further."
    assert _strip_trailing_question(t) == t


def test_strip_is_trailing_question_only_ar():
    t = _AR_ANSWER + " هل هذا واضح حتى الآن؟ أنا هنا إن أردت أن نتعمق أكثر."
    assert _strip_trailing_question(t) == t
