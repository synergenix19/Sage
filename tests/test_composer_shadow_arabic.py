from sage_poc.prompts.composer import compose_prompt


def _ar_state():
    return {"detected_language": "ar", "raw_message": "تعبت من كل شي", "message_en": "I'm tired of everything"}


def test_default_is_english_first_unchanged():
    sys_default, _, layers = compose_prompt(_ar_state())
    assert "Generate in English" in sys_default and "Do not write in Arabic" in sys_default
    assert "arabic_register" in layers


def test_shadow_mode_swaps_to_khaleeji_direct():
    sys_shadow, _, layers = compose_prompt(_ar_state(), shadow_arabic=True)
    assert "Generate your reply directly in warm, informal Gulf Arabic" in sys_shadow
    assert "Do not write in Arabic" not in sys_shadow
    assert "KHALEEJI EXEMPLARS" in sys_shadow and "arabic_native_shadow" in layers


def test_shadow_mode_noop_for_english_session():
    sys_en, _, _ = compose_prompt({"detected_language": "en", "raw_message": "hi", "message_en": "hi"}, shadow_arabic=True)
    assert "KHALEEJI EXEMPLARS" not in sys_en
