import importlib


def _reload_config(monkeypatch, **env):
    for k in ("SAGE_PSYCHOED_PATHWAYS", "SAGE_PSYCHOED_CATEGORIES"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from sage_poc import config
    return importlib.reload(config)


def test_flag_default_off(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is False
    assert cfg.PSYCHOED_CATEGORIES == frozenset()
    assert cfg.psychoed_enabled_for("1f") is False


def test_flag_on_with_categories(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,3c")
    assert cfg.PSYCHOED_PATHWAYS_ENABLED is True
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f", "3c"})
    assert cfg.psychoed_enabled_for("1f") and not cfg.psychoed_enabled_for("s2c")


def test_invalid_category_rejected(monkeypatch):
    cfg = _reload_config(monkeypatch, SAGE_PSYCHOED_PATHWAYS="true",
                         SAGE_PSYCHOED_CATEGORIES="1f,bogus")
    assert cfg.PSYCHOED_CATEGORIES == frozenset({"1f"})  # bogus dropped with a warning, never served


def test_psychoed_channels_declared():
    from sage_poc.state import SageState
    keys = SageState.__annotations__
    for k in ("psychoed_serve", "psychoed_active_category", "psychoed_delivery_shape",
              "psychoed_blocks_served", "psychoed_menu_offered", "psychoed_weave_fired",
              "psychoed_weave_pending", "psychoed_matched_row_id", "psychoed_collision_path",
              "psychoed_framing", "psychoed_family_exposures"):
        assert k in keys, f"undeclared channel: {k}"
