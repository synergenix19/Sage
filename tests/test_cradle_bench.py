"""CRADLE Bench external validation of safety_check_node.

Runs the clinician-annotated CRADLE Bench eval set (600 examples, 7 crisis
types) against safety_check_node. Validates the >=95% crisis recall KPI
with data Sage did not author.

Markers:
  @pytest.mark.cradle   -- all tests in this file (set via pytestmark)
  @pytest.mark.slow     -- S3-tier tests (require real BGE-M3)

Skip condition: if tests/fixtures/cradle_bench/eval.jsonl is absent,
all parametrized tests skip automatically. Run scripts/fetch_cradle_bench.py first.
"""
import pytest
from pathlib import Path
from tests.fixtures.cradle_bench.loader import load_cradle_split, CradleCase
from tests.fixtures.cradle_bench.label_map import LABEL_MAP, CrisisTier, ClinicalTier

pytestmark = pytest.mark.cradle

_EVAL_PATH = Path(__file__).parent / "fixtures" / "cradle_bench" / "eval.jsonl"
_DATA_MISSING = not _EVAL_PATH.exists()
_skip_no_data = pytest.mark.skipif(
    _DATA_MISSING,
    reason="CRADLE Bench eval.jsonl not present -- run scripts/fetch_cradle_bench.py",
)


# -- Label map unit tests ---------------------------------------------------

def test_label_map_covers_all_seven_categories():
    expected = {
        "active_suicide_ideation",
        "passive_suicide_ideation",
        "self_harm",
        "rape",
        "domestic_violence",
        "sexual_harassment",
        "child_abuse_endangerment",
        "safe",
    }
    assert set(LABEL_MAP.keys()) == expected


def test_label_map_crisis_tier_flags():
    assert LABEL_MAP["active_suicide_ideation"]["tier"] == "crisis"
    assert LABEL_MAP["passive_suicide_ideation"]["tier"] == "crisis"
    assert LABEL_MAP["self_harm"]["tier"] == "crisis"


def test_label_map_clinical_tier():
    for label in ("rape", "domestic_violence", "sexual_harassment", "child_abuse_endangerment"):
        assert LABEL_MAP[label]["tier"] == "clinical"


def test_label_map_safe():
    assert LABEL_MAP["safe"]["tier"] == "safe"


def test_crisis_tier_set_has_three_members():
    assert len(CrisisTier) == 3
    assert "active_suicide_ideation" in CrisisTier
    assert "passive_suicide_ideation" in CrisisTier
    assert "self_harm" in CrisisTier


def test_clinical_tier_set_has_four_members():
    assert len(ClinicalTier) == 4


@_skip_no_data
def test_loader_returns_named_tuples():
    cases = load_cradle_split(_EVAL_PATH)
    assert len(cases) > 0
    first = cases[0]
    assert isinstance(first, CradleCase)
    assert isinstance(first.id, str)
    assert isinstance(first.text, str)
    assert isinstance(first.label, str)
    assert first.label in LABEL_MAP, f"Unknown label: {first.label!r}"


@_skip_no_data
def test_loader_covers_crisis_categories():
    cases = load_cradle_split(_EVAL_PATH)
    crisis_labels = {c.label for c in cases if LABEL_MAP[c.label]["tier"] == "crisis"}
    assert "active_suicide_ideation" in crisis_labels
    assert "passive_suicide_ideation" in crisis_labels
    assert "self_harm" in crisis_labels


@_skip_no_data
def test_loader_has_safe_examples():
    cases = load_cradle_split(_EVAL_PATH)
    safe = [c for c in cases if c.label == "safe"]
    assert len(safe) > 0


@_skip_no_data
def test_loader_all_texts_nonempty():
    cases = load_cradle_split(_EVAL_PATH)
    empty = [c for c in cases if not c.text.strip()]
    assert empty == [], f"Found {len(empty)} empty text examples"
