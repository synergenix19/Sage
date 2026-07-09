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


_MIRROR_DIRECTIVE = (
    "Address the user in the gender they grammatically self-mark; if unmarked, use "
    "gender-neutral constructions. Never infer gender from topic or name."
)


def test_shadow_mode_includes_mirror_when_marked_directive():
    sys_shadow, _, _ = compose_prompt(_ar_state(), shadow_arabic=True)
    assert _MIRROR_DIRECTIVE in sys_shadow


def test_shadow_mode_unmarked_input_uses_neutral_exemplars():
    # "تعبت من كل شي" ("I got tired of everything") is a verb, not the marked
    # predicate-adjective form -> detect_gender_marking resolves it to "none".
    sys_shadow, _, _ = compose_prompt(_ar_state(), shadow_arabic=True)
    assert "هالشي ثقيل فعلاً" in sys_shadow  # ar_neutral of exemplar 1
    assert "واضح إن اللي عليك ثقيل" not in sys_shadow  # ar_m must not leak in
    assert "واضح إن اللي عليج ثقيل" not in sys_shadow  # ar_f must not leak in


def test_shadow_mode_feminine_marked_input_uses_feminine_exemplars():
    state = {
        "detected_language": "ar",
        "raw_message": "أنا تعبانة اليوم",
        "message_en": "I'm tired today",
    }
    sys_shadow, _, _ = compose_prompt(state, shadow_arabic=True)
    assert "واضح إن اللي عليج ثقيل" in sys_shadow  # ar_f of exemplar 1
    assert "أنا وياج" in sys_shadow  # ar_f of exemplar 2
    assert "واضح إن اللي عليك ثقيل" not in sys_shadow  # ar_m must not leak in
    assert _MIRROR_DIRECTIVE in sys_shadow


def test_shadow_mode_masculine_marked_input_uses_masculine_exemplars():
    state = {
        "detected_language": "ar",
        "raw_message": "أنا تعبان اليوم",
        "message_en": "I'm tired today",
    }
    sys_shadow, _, _ = compose_prompt(state, shadow_arabic=True)
    assert "واضح إن اللي عليك ثقيل" in sys_shadow  # ar_m of exemplar 1
    assert "أنا وياك" in sys_shadow  # ar_m of exemplar 2
    assert "واضح إن اللي عليج ثقيل" not in sys_shadow  # ar_f must not leak in


def test_default_arabic_register_mode_has_no_mirror_directive():
    # The translate-out path (shadow_arabic=False) is unrelated to native gendered
    # generation; the directive is scoped to the shadow path only.
    sys_default, _, _ = compose_prompt(_ar_state())
    assert _MIRROR_DIRECTIVE not in sys_default
