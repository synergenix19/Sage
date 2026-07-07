import asyncio
from sage_poc.shadow_arabic import generate_shadow_arabic

class _FakeResp:
    def __init__(self, c): self.content = c
class _FakeLLM:
    def __init__(self, c="مرحبا", raises=False): self._c, self._r = c, raises
    async def ainvoke(self, m):
        if self._r: raise RuntimeError("boom")
        return _FakeResp(self._c)

def _ar(): return {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired"}

def test_none_for_english():
    assert asyncio.run(generate_shadow_arabic({"detected_language": "en"}, _FakeLLM())) is None

def test_payload_for_arabic():
    out = asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM("مرحبا")))
    assert out["text"] == "مرحبا" and out["generation_language"] == "ar_native"
    assert len(out["prompt_hash"]) == 16 and out["exemplar_version"]
    assert isinstance(out["gen_latency_ms"], int) and out["gen_latency_ms"] >= 0

def test_fail_open():
    assert asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM(raises=True))) is None

def test_empty_content_is_treated_as_failed_generation():
    # empty string content = failed generation → None (never a stored empty row / repr)
    out = asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM("")))
    assert out is None

def test_whitespace_only_content_is_failed_generation():
    assert asyncio.run(generate_shadow_arabic(_ar(), _FakeLLM("   \n "))) is None
