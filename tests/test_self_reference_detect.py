import pytest
from sage_poc.nodes.self_reference_detect import detect_self_reference


@pytest.mark.parametrize("msg,raw,lang,expected", [
    ("what did I just tell you about my husband?", "", "en", True),
    ("didn't I say I drink to cope?", "", "en", True),
    ("you said breathing would help", "", "en", True),
    ("do you remember what I told you", "", "en", True),
    ("ماذا قلت لك عن زوجي؟", "ماذا قلت لك عن زوجي؟", "ar", True),
    ("ألم أخبرك من قبل؟", "ألم أخبرك من قبل؟", "ar", True),
    ("what is generalized anxiety disorder?", "", "en", False),
    ("can you teach me a breathing exercise?", "", "en", False),
])
def test_detect_self_reference(msg, raw, lang, expected):
    state = {"message_en": msg, "raw_message": raw or msg, "detected_language": lang}
    assert detect_self_reference(state) is expected


def test_empty_text_is_false():
    assert detect_self_reference({"message_en": "", "raw_message": "", "detected_language": "en"}) is False
