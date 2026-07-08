import importlib

def test_flag_defaults_off(monkeypatch):
    monkeypatch.delenv("SAGE_NATIVE_ARABIC_SHADOW", raising=False)
    import sage_poc.config as cfg; importlib.reload(cfg)
    assert cfg.NATIVE_ARABIC_SHADOW_ENABLED is False

def test_flag_on_when_true(monkeypatch):
    monkeypatch.setenv("SAGE_NATIVE_ARABIC_SHADOW", "true")
    import sage_poc.config as cfg; importlib.reload(cfg)
    assert cfg.NATIVE_ARABIC_SHADOW_ENABLED is True
