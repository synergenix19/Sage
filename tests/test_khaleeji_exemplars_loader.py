import json
from pathlib import Path

from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars

_EXEMPLARS_PATH = Path(__file__).parent.parent / "src" / "sage_poc" / "prompts" / "khaleeji_shadow_exemplars.json"


def test_loader_returns_version_and_block():
    version, block = load_khaleeji_shadow_exemplars()
    assert version == "1.0.0"
    assert "KHALEEJI EXEMPLARS" in block
    assert "one breath at a time" in block


def test_version_is_off_draft():
    data = json.loads(_EXEMPLARS_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"
    assert "-draft" not in data["version"]


def test_schema_has_three_renderings_per_exemplar():
    data = json.loads(_EXEMPLARS_PATH.read_text(encoding="utf-8"))
    assert len(data["exemplars"]) == 2
    for ex in data["exemplars"]:
        for key in ("en", "ar_m", "ar_f", "ar_neutral"):
            assert ex.get(key), f"missing/empty {key!r} in exemplar {ex!r}"


def test_default_rendering_is_neutral():
    _, block = load_khaleeji_shadow_exemplars()
    assert "هالشي ثقيل فعلاً" in block  # ar_neutral of exemplar 1
    assert "واضح إن اللي عليك ثقيل" not in block  # ar_m must not leak into neutral default
    assert "واضح إن اللي عليج ثقيل" not in block  # ar_f must not leak into neutral default


def test_masculine_rendering_selected_on_m():
    _, block = load_khaleeji_shadow_exemplars("m")
    assert "واضح إن اللي عليك ثقيل" in block
    assert "أنا وياك" in block


def test_feminine_rendering_selected_on_f():
    _, block = load_khaleeji_shadow_exemplars("f")
    assert "واضح إن اللي عليج ثقيل" in block
    assert "أنا وياج" in block


def test_feminine_rendering_preserves_kaf_to_jeem_shift():
    # Emirati feminine ك→ج (عليج/وياج) is intentional — do not normalize to ك.
    _, block = load_khaleeji_shadow_exemplars("f")
    assert "عليج" in block
    assert "وياج" in block


def test_unknown_gender_falls_back_to_neutral():
    _, block = load_khaleeji_shadow_exemplars("none")
    assert "هالشي ثقيل فعلاً" in block
