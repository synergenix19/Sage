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
from unittest.mock import patch
from tests.fixtures.cradle_bench.loader import load_cradle_split, CradleCase
from tests.fixtures.cradle_bench.label_map import LABEL_MAP, CrisisTier, ClinicalTier
from sage_poc.nodes.safety_check import safety_check_node

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
    crisis_labels = {c.label for c in cases if LABEL_MAP.get(c.label, {}).get("tier") == "crisis"}
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


# ── Sentinel: explicit named skip when eval data absent ───────────────────

def test_cradle_data_available():
    """Skip with a clear message when eval.jsonl has not been downloaded.

    Without this sentinel, the four parametrized node-level tests generate
    zero test instances (empty argvalues list) and disappear silently from
    the run. This test always shows up as a named skip so the operator knows
    the harness needs data before it can validate the KPI.
    """
    if _DATA_MISSING:
        pytest.skip(
            "CRADLE Bench eval.jsonl not present. "
            "Run scripts/fetch_cradle_bench.py after confirming the DUA. "
            "Until then, the S1/S3 recall KPI is unvalidated by external data."
        )


# ── State factory ─────────────────────────────────────────────────────────

def _make_state(text: str, language: str = "en") -> dict:
    return {
        "raw_message": text,
        "detected_language": language,
        "message_en": text if language == "en" else "",
        "path": [],
        "crisis_state": "none",
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "clinical_flags": [],
        "turn_number": 0,
        "therapeutic_profile": None,
        "s7_result": None,
    }


# ── Load cases once at module level ───────────────────────────────────────

_ALL_CASES: list[CradleCase] = [] if _DATA_MISSING else load_cradle_split(_EVAL_PATH)

_CRISIS_CASES = [c for c in _ALL_CASES if LABEL_MAP.get(c.label, {}).get("tier") == "crisis"]
_SAFE_CASES   = [c for c in _ALL_CASES if c.label == "safe"]
_CLINICAL_CASES = [c for c in _ALL_CASES if LABEL_MAP.get(c.label, {}).get("tier") == "clinical"]


# ── S1-tier crisis recall ──────────────────────────────────────────────────

@pytest.mark.parametrize("case", _CRISIS_CASES, ids=[c.id for c in _CRISIS_CASES] or ["none"])
async def test_s1_crisis_recall(case: CradleCase, record_cradle_result: list) -> None:
    """S1 (rules engine) must flag each CRADLE crisis example as unsafe.

    S3 is patched to 0.0 so only the lexicon fires.
    Failures indicate phrases the rules engine does not cover.
    Review passive_si_patterns.json and crisis_keywords.json for gaps.

    PARTIAL PIPELINE: MARBERT (S2) is not integrated. This measures S1 only.
    """
    state = _make_state(case.text)

    with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.0):
        result = await safety_check_node(state)

    detected = result.get("is_safe") is False
    record_cradle_result.append({
        "tier": "crisis",
        "id": case.id,
        "label": case.label,
        "detected": detected,
        "s3_only": False,
        "crisis_flags": result.get("crisis_flags", []),
    })
    assert detected, (
        f"[S1 MISS] {case.id} label={case.label!r}\n"
        f"  text: {case.text!r}\n"
        f"  crisis_flags: {result.get('crisis_flags')}\n"
        f"  is_safe: {result.get('is_safe')}"
    )


# ── S1-tier precision (safe examples → no false positives) ────────────────

@pytest.mark.parametrize("case", _SAFE_CASES, ids=[c.id for c in _SAFE_CASES] or ["none"])
async def test_s1_precision_safe(case: CradleCase, record_cradle_result: list) -> None:
    """CRADLE safe examples must not trigger crisis flags.

    Failures indicate false positive rules — phrases that look like crisis
    language but are not. Review false_positive_exclusions.json for fixes.

    PARTIAL PIPELINE: MARBERT (S2) is not integrated. This measures S1+S3 stub only.
    """
    state = _make_state(case.text)

    with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.0):
        result = await safety_check_node(state)

    triggered = result.get("is_safe") is False
    record_cradle_result.append({
        "tier": "safe",
        "id": case.id,
        "label": "safe",
        "detected": triggered,
        "s3_only": False,
        "crisis_flags": result.get("crisis_flags", []),
    })
    assert not triggered, (
        f"[S1 FALSE POSITIVE] {case.id}\n"
        f"  text: {case.text!r}\n"
        f"  crisis_flags: {result.get('crisis_flags')}"
    )


# ── Clinical coverage analysis (categories 4-7, analytics only) ───────────
# These tests do NOT assert — they accumulate coverage data only.
# A "miss" here means our rules do not flag rape/DV/SH/CAE, which may be
# correct (these are often disclosed in past tense, not immediate crisis).
# Results are shown in the CRADLE Bench Results summary.

@pytest.mark.parametrize("case", _CLINICAL_CASES, ids=[c.id for c in _CLINICAL_CASES] or ["none"])
async def test_s1_clinical_coverage(case: CradleCase, record_cradle_result: list) -> None:
    """Accumulate clinical flag coverage on CRADLE categories 4-7.

    No assertion. Failures here are analytics, not regressions.
    """
    expected_flags = LABEL_MAP.get(case.label, {}).get("sage_flags", [])
    state = _make_state(case.text)

    with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.0):
        result = await safety_check_node(state)

    all_flags = list(dict.fromkeys(
        result.get("crisis_flags", []) + result.get("clinical_flags", [])
    ))
    hit = bool(set(all_flags) & set(expected_flags))
    record_cradle_result.append({
        "tier": "clinical",
        "id": case.id,
        "label": case.label,
        "detected": hit,
        "s3_only": False,
        "crisis_flags": all_flags,
    })
    # No assertion — see terminal summary for coverage %


# ── S3-tier slow tests (S1+S3 combined = current POC production config) ───
# Run with: pytest tests/test_cradle_bench.py -m "cradle and slow" -p no:xdist
# Requires BGE-M3 pre-warmed. Takes ~60-90s for the passive SI subset.
# Close Docker and Chrome before running (BGE-M3 ANE compilation uses all RAM).

_PASSIVE_SI_CASES = [c for c in _ALL_CASES if c.label == "passive_suicide_ideation"]


@pytest.mark.slow
@pytest.mark.parametrize(
    "case", _PASSIVE_SI_CASES,
    ids=[c.id for c in _PASSIVE_SI_CASES] or ["none"],
)
async def test_s3_passive_si_recall(
    case: CradleCase,
    s3_warmed,
    record_cradle_result: list,
) -> None:
    """S1+S3 combined must catch CRADLE passive SI examples.

    Passive SI is the hardest category: phrases like "I feel empty inside"
    have no S1 keyword match and rely on BGE-M3 semantic similarity
    (S3_THRESHOLD=0.8059). This is the SF-1 priority from the internal evaluation.

    PARTIAL PIPELINE NOTE: S2 (MARBERT) not yet integrated. This measures
    the current POC production configuration (S1+S3). S3 misses should be
    logged as MARBERT motivation for Exp 4.2, NOT used to justify lowering
    S3_THRESHOLD — threshold reduction buys recall at the cost of precision.

    s3_warmed is a session fixture in conftest.py that pre-builds the S3 phrase
    index via asyncio.to_thread before this test runs.
    """
    state = _make_state(case.text)
    # No check_s3 patch — let S3 run with real BGE-M3
    result = await safety_check_node(state)

    detected = result.get("is_safe") is False
    s3_fired = "s3_semantic" in result.get("crisis_flags", [])
    record_cradle_result.append({
        "tier": "crisis",
        "id": case.id,
        "label": case.label,
        "detected": detected,
        "s3_only": s3_fired and "si_passive" not in result.get("crisis_flags", []),
        "crisis_flags": result.get("crisis_flags", []),
    })
    assert detected, (
        f"[S3 MISS] {case.id} label=passive_suicide_ideation\n"
        f"  text: {case.text!r}\n"
        f"  crisis_flags: {result.get('crisis_flags')}\n"
        f"  is_safe: {result.get('is_safe')}\n"
        "  -> Log as MARBERT motivation for Exp 4.2. "
        "Do NOT lower S3_THRESHOLD: threshold reduction buys recall at cost of precision. "
        "To add coverage: add phrase to crisis_phrases.json + recalibrate, "
        "then verify test_s1_precision_safe still passes."
    )
