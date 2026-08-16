"""#218 — vetoed-OCD abstain carries the spec §1d ERP professional-referral signpost.

Pinned VERBATIM at Node 8 (output_gate), mirroring the mood-anchor pin: un-paraphrasable +
audit-visible. Fires ONLY on the ocd_erp directive in English; byte-identical everywhere else.
"""
from sage_poc.nodes.output_gate import _pin_ocd_referral, _OCD_ERP_REFERRAL_EN, _OCD_ERP_REFERRAL_AR

_REPLY = "Those thoughts sound really distressing. Have you been able to talk to anyone about them?"


def test_appends_on_ocd_veto_english():
    out = _pin_ocd_referral(_REPLY, "ocd_erp", "en")
    assert out.endswith(_OCD_ERP_REFERRAL_EN), "must append the pinned ERP referral verbatim"
    assert "exposure and response prevention" in out, "ERP named (evidence-based modality, per #218)"
    assert _REPLY in out, "must preserve the composed empathic reply, then append"


def test_byte_identical_without_directive():
    # non-OCD abstains and all other turns must be untouched (byte-identical guard)
    assert _pin_ocd_referral(_REPLY, None, "en") == _REPLY
    assert _pin_ocd_referral(_REPLY, "something_else", "en") == _REPLY


def test_appends_on_ocd_veto_arabic():
    # #4-AR: Arabic vetoed-OCD abstain must ALSO get the ERP referral, natively authored (not
    # translate-out), appended verbatim — mirroring the EN pin. Arabic users are not left without
    # the §1d signpost.
    ar_reply = "هذي الأفكار تبدو مزعجة فعلاً. تقدر تحكي لي أكثر عنها؟"
    out = _pin_ocd_referral(ar_reply, "ocd_erp", "ar")
    assert out.endswith(_OCD_ERP_REFERRAL_AR), "must append the pinned AR ERP referral verbatim"
    assert ar_reply in out, "must preserve the composed Arabic reply, then append"
    assert out != ar_reply, "AR must no longer be a no-op (the #4-AR gap is closed)"


def test_idempotent_when_already_present_en():
    once = _pin_ocd_referral(_REPLY, "ocd_erp", "en")
    twice = _pin_ocd_referral(once, "ocd_erp", "en")
    assert once == twice, "must not double-append if the EN referral is already present"


def test_idempotent_when_already_present_ar():
    ar_reply = "هذي الأفكار تبدو مزعجة فعلاً."
    once = _pin_ocd_referral(ar_reply, "ocd_erp", "ar")
    twice = _pin_ocd_referral(once, "ocd_erp", "ar")
    assert once == twice, "must not double-append the AR referral"


def test_verbatim_wording_names_erp():
    # the clinician-approved wording ships exactly — guard the ERP-class enrichment
    assert "ERP (exposure and response prevention) for OCD" in _OCD_ERP_REFERRAL_EN
