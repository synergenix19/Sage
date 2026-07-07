from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars


def test_loader_returns_version_and_block():
    version, block = load_khaleeji_shadow_exemplars()
    assert isinstance(version, str) and version
    assert "KHALEEJI EXEMPLARS" in block
    assert "one breath at a time" in block
