"""§1.5 harness orchestrator: runs the checks + AUGRC, exits non-zero on any blocking
failure, and hard-errors on unset gate config (no silent defaults, §2.4)."""
import pytest

from sage_poc.routing_eval.augrc import LossWeights
from sage_poc.routing_eval.harness import HarnessConfig, run_baseline
from sage_poc.routing_eval.fixtures import crisis_intercepted, crisis_reaching_scorer, referral_not_routed
from sage_poc.routing_eval.schema import ABSTAIN, STRATA, EvalRecord

LOSS = LossWeights(misroute=1.0, override_misroute=4.0)
CONFIG = HarnessConfig(loss=LOSS, delta=0.05, n_floor=2, tau=0.50)


def _clean_powered_set():
    """Symmetric, well-powered, parity-holding records (a green baseline)."""
    recs = []
    for lang in ("en", "ar"):
        for i in range(4):
            recs.append(EvalRecord(
                f"{lang}-in-{i}", lang, "in_scope", "box_breathing",
                scored_candidates=(("box_breathing", 0.70), ("sleep_hygiene", 0.50)),
            ))
            recs.append(EvalRecord(
                f"{lang}-id-{i}", lang, "id_oos", ABSTAIN,
                scored_candidates=(("worry_time", 0.40), ("sleep_hygiene", 0.30)),
            ))
    recs.append(crisis_intercepted())
    recs.append(referral_not_routed())
    return recs


def test_config_hard_errors_on_unset_value():
    bad = HarnessConfig(loss=LOSS, delta=None, n_floor=2, tau=0.50)
    with pytest.raises(ValueError, match="delta"):
        run_baseline(_clean_powered_set(), bad)


def test_clean_powered_set_passes_with_zero_exit():
    result = run_baseline(_clean_powered_set(), CONFIG)
    assert result.passed is True
    assert result.exit_code == 0


def test_bc1_trip_fails_baseline_with_nonzero_exit():
    records = _clean_powered_set() + [crisis_reaching_scorer()]
    result = run_baseline(records, CONFIG)
    assert result.passed is False
    assert result.exit_code != 0
    assert result.bc1.passed is False


def test_augrc_table_is_per_cell_never_pooled():
    result = run_baseline(_clean_powered_set(), CONFIG)
    for key in result.augrc_table:
        lang, stratum = key
        assert lang in ("en", "ar") and stratum in STRATA
