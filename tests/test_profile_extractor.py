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
