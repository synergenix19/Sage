import pytest
from unittest.mock import AsyncMock, patch

SAMPLE_LLM_RESPONSE = """{
  "effective_techniques": ["box_breathing"],
  "ineffective_techniques": [],
  "distortion_patterns": ["catastrophising"],
  "disclosed_concerns": ["work_stress"],
  "communication_style": "reflective, responds well to Socratic questions",
  "cultural_preferences": {"religious_framing": false, "family_context": true},
  "mood_score": 4,
  "skills_completed": 1
}"""

SAMPLE_HISTORY = [
    {"role": "user", "content": "I've been really anxious"},
    {"role": "assistant", "content": "What does the anxiety feel like?"},
    {"role": "user", "content": "The box breathing helped a lot"},
    {"role": "assistant", "content": "Let's try it again."},
]

@pytest.mark.asyncio
async def test_extract_returns_dict():
    from sage_poc.memory.profile_extractor import extract_session_profile
    with patch("sage_poc.memory.profile_extractor.resilient_invoke", return_value=SAMPLE_LLM_RESPONSE):
        result = await extract_session_profile(SAMPLE_HISTORY, llm=AsyncMock())
    assert result["effective_techniques"] == ["box_breathing"]
    assert result["cultural_preferences"]["family_context"] is True

@pytest.mark.asyncio
async def test_extract_returns_none_on_bad_json():
    from sage_poc.memory.profile_extractor import extract_session_profile
    with patch("sage_poc.memory.profile_extractor.resilient_invoke", return_value="not json"):
        result = await extract_session_profile(SAMPLE_HISTORY, llm=AsyncMock())
    assert result is None


def test_extraction_system_does_not_say_mental_health():
    """_EXTRACTION_SYSTEM must not frame Sage as a 'mental health' tool.
    Internal framing consistency: matches the public 'wellbeing' identity.
    """
    from sage_poc.memory.profile_extractor import _EXTRACTION_SYSTEM
    assert "mental health" not in _EXTRACTION_SYSTEM.lower(), (
        "_EXTRACTION_SYSTEM must say 'wellbeing support conversation', not 'mental health support conversation'"
    )
    assert "wellbeing" in _EXTRACTION_SYSTEM.lower(), (
        "_EXTRACTION_SYSTEM should reference 'wellbeing support conversation'"
    )


def test_effective_techniques_cleared_for_psychotic_disclosure_clinical_flag():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["breathing exercise", "box breathing"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["stress"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    result = apply_contraindications(profile, clinical_flags=["psychotic_disclosure"])
    assert result["effective_techniques"] == []


def test_effective_techniques_cleared_for_psychotic_disclosure_in_concerns():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["breathing exercise"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["psychotic_disclosure"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    result = apply_contraindications(profile, clinical_flags=[])
    assert result["effective_techniques"] == []


def test_effective_techniques_preserved_without_contraindication():
    from sage_poc.memory.profile_extractor import apply_contraindications
    profile = {
        "effective_techniques": ["box breathing"],
        "ineffective_techniques": [],
        "disclosed_concerns": ["stress"],
        "distortion_patterns": [],
        "communication_style": None,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "observations": [],
    }
    assert apply_contraindications(profile, clinical_flags=[])["effective_techniques"] == ["box breathing"]
