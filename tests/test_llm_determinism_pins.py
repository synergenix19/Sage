"""Determinism pins for the classifier family — Node-2 bistability finding (2026-07-28).

Reference: docs/superpowers/governance/2026-07-28-node2-intent-bistability-finding.md
(branch 1a-gap-phase0). Established causes of Node-2 non-reproducibility: no seed, no
OpenRouter provider pin, and the classifier prompt embedding temp-0.7 responder history.
These tests pin the first two.

Scope contract:
- Classifier FAMILY only: classifier, fallback_classifier, translator (all temp-0).
- The responder family (responder, fallback_responder) runs temp 0.7 DELIBERATELY
  (therapeutic copy variation) and must NEVER receive a seed or provider pin — a
  both-direction assertion below, not a comment.
- Dark by default: SAGE_CLASSIFIER_SEED unset -> no seed sent at all (not seed=0,
  not seed=None-in-payload — the key is absent from the request params, byte-identical
  to today). Same discipline for SAGE_OPENROUTER_PROVIDER_PIN.
"""
import importlib

import pytest

import sage_poc.config as cfg
from sage_poc import llm as llm_mod


@pytest.fixture(autouse=True)
def _fresh_llm_cache():
    """_make_llm is lru_cached; clear around every test so a pinned instance from one
    test can never satisfy another test's constructor call (mock-leak convention)."""
    llm_mod.reset_singletons()
    yield
    llm_mod.reset_singletons()


def _reload_config_with(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    importlib.reload(cfg)


@pytest.fixture
def _restore_config(monkeypatch):
    """Undo env mutations FIRST, then reload config so module-level values match the
    real environment again (reload-based tests otherwise leak into later tests)."""
    yield
    monkeypatch.undo()
    importlib.reload(cfg)


# ---------------------------------------------------------------------------
# SAGE_CLASSIFIER_SEED — env parsing (config.py)
# ---------------------------------------------------------------------------

def test_classifier_seed_defaults_to_none_when_unset(monkeypatch, _restore_config):
    _reload_config_with(monkeypatch, SAGE_CLASSIFIER_SEED=None)
    assert cfg.CLASSIFIER_SEED is None


def test_classifier_seed_parses_int_when_set(monkeypatch, _restore_config):
    _reload_config_with(monkeypatch, SAGE_CLASSIFIER_SEED="1234")
    assert cfg.CLASSIFIER_SEED == 1234


def test_classifier_seed_garbage_falls_back_to_none(monkeypatch, _restore_config):
    """Safe-default convention (same as the strict flag parses): a non-int value must
    not crash import and must not half-enable — unparseable -> None (no seed sent)."""
    _reload_config_with(monkeypatch, SAGE_CLASSIFIER_SEED="not-an-int")
    assert cfg.CLASSIFIER_SEED is None


def test_classifier_seed_empty_string_is_none(monkeypatch, _restore_config):
    """Railway empty-string env-injection shape: '' must behave exactly like unset."""
    _reload_config_with(monkeypatch, SAGE_CLASSIFIER_SEED="")
    assert cfg.CLASSIFIER_SEED is None


# ---------------------------------------------------------------------------
# Seed pass-through — constructors (llm.py)
# ---------------------------------------------------------------------------

def test_classifier_family_receives_seed_when_configured(monkeypatch):
    monkeypatch.setattr(cfg, "CLASSIFIER_SEED", 4242)
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_classifier, llm_mod.get_fallback_classifier,
                   llm_mod.get_translator):
        llm = getter()
        assert llm.seed == 4242, f"{getter.__name__} did not receive the seed"
        assert llm._default_params.get("seed") == 4242, (
            f"{getter.__name__}: seed set on the instance but absent from request params"
        )


def test_seed_omitted_entirely_when_unset(monkeypatch):
    monkeypatch.setattr(cfg, "CLASSIFIER_SEED", None)
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_classifier, llm_mod.get_fallback_classifier,
                   llm_mod.get_translator):
        llm = getter()
        assert llm.seed is None
        assert "seed" not in llm._default_params, (
            f"{getter.__name__}: unset seed must not appear in request params at all "
            "(dark default = byte-identical request payload)"
        )


def test_responder_family_never_receives_seed(monkeypatch):
    """Responder temp-0.7 stochasticity is deliberate (therapeutic copy). Even with the
    classifier seed configured, the responder family must stay unseeded."""
    monkeypatch.setattr(cfg, "CLASSIFIER_SEED", 4242)
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_responder, llm_mod.get_fallback_responder):
        llm = getter()
        assert llm.seed is None, f"{getter.__name__} must never be seeded"
        assert "seed" not in llm._default_params


# ---------------------------------------------------------------------------
# SAGE_OPENROUTER_PROVIDER_PIN — env parsing (config.py)
# ---------------------------------------------------------------------------

def test_provider_pin_defaults_to_none_when_unset(monkeypatch, _restore_config):
    _reload_config_with(monkeypatch, SAGE_OPENROUTER_PROVIDER_PIN=None)
    assert cfg.OPENROUTER_PROVIDER_PIN is None


def test_provider_pin_parses_string_when_set(monkeypatch, _restore_config):
    _reload_config_with(monkeypatch, SAGE_OPENROUTER_PROVIDER_PIN="openai")
    assert cfg.OPENROUTER_PROVIDER_PIN == "openai"


def test_provider_pin_empty_string_is_none(monkeypatch, _restore_config):
    """Railway empty-string env-injection shape: '' must behave exactly like unset."""
    _reload_config_with(monkeypatch, SAGE_OPENROUTER_PROVIDER_PIN="  ")
    assert cfg.OPENROUTER_PROVIDER_PIN is None


# ---------------------------------------------------------------------------
# Provider-pin pass-through — constructors (llm.py)
# ---------------------------------------------------------------------------

_EXPECTED_PROVIDER_BLOCK = {"provider": {"order": ["openai"], "allow_fallbacks": False}}


def test_classifier_family_receives_provider_pin_when_configured(monkeypatch):
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", "openai")
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_classifier, llm_mod.get_fallback_classifier,
                   llm_mod.get_translator):
        llm = getter()
        assert llm.extra_body == _EXPECTED_PROVIDER_BLOCK, (
            f"{getter.__name__} did not receive the OpenRouter provider routing block"
        )
        assert llm._default_params.get("extra_body") == _EXPECTED_PROVIDER_BLOCK


def test_provider_block_omitted_entirely_when_unset(monkeypatch):
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", None)
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_classifier, llm_mod.get_fallback_classifier,
                   llm_mod.get_translator):
        llm = getter()
        assert llm.extra_body is None
        assert "extra_body" not in llm._default_params, (
            f"{getter.__name__}: unset pin must not appear in request params at all "
            "(dark default = byte-identical request payload)"
        )


def test_responder_family_never_receives_provider_pin(monkeypatch):
    monkeypatch.setattr(cfg, "OPENROUTER_PROVIDER_PIN", "openai")
    llm_mod.reset_singletons()
    for getter in (llm_mod.get_responder, llm_mod.get_fallback_responder):
        llm = getter()
        assert llm.extra_body is None, f"{getter.__name__} must never be provider-pinned"
        assert "extra_body" not in llm._default_params
