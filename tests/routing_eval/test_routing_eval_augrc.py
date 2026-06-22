"""§1.3 multi-threshold AUGRC sweep — per-stratum, no pooled path.

AUGRC here = the area under the generalized risk-coverage step curve, computed as the
mean selective risk over coverage levels k=1..N (records ordered by descending router
confidence = top-candidate score). Lower is better. Conceptual source: Traub et al.,
NeurIPS 2024 (multi-threshold area, not a single fixed-threshold point). Hand-computable
on tiny inputs so the definition is pinned.
"""
import sage_poc.routing_eval.augrc as augrc_mod
from sage_poc.routing_eval.augrc import LossWeights, augrc, per_cell_augrc
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord

LOSS = LossWeights(misroute=1.0, override_misroute=4.0)


def _rec(lang, stratum, expected, top_skill, top_score, override=False, second=("x", 0.0), flag=False):
    return EvalRecord(
        utterance=f"{lang}-{stratum}-{top_skill}-{top_score}",
        lang=lang, stratum=stratum, expected_route=expected,
        scored_candidates=((top_skill, top_score), second),
        override_fired=override, flag_bearing=flag,
    )


def test_augrc_zero_when_all_covered_rows_route_correctly():
    cell = [
        _rec("en", "in_scope", "cbt_thought_record", "cbt_thought_record", 0.70),
        _rec("en", "in_scope", "box_breathing", "box_breathing", 0.60),
    ]
    assert augrc(cell, LOSS) == 0.0


def test_augrc_equals_misroute_weight_when_all_covered_rows_misroute():
    # expected ABSTAIN, but each has a routed top candidate -> covering them is a misroute.
    cell = [
        _rec("en", "id_oos", ABSTAIN, "worry_time", 0.70),
        _rec("en", "id_oos", ABSTAIN, "sleep_hygiene", 0.60),
    ]
    # selective_risk(1)=1.0, selective_risk(2)=1.0 -> mean 1.0
    assert augrc(cell, LOSS) == 1.0


def test_override_misroute_is_weighted_heavier():
    cell = [
        _rec("en", "id_oos", ABSTAIN, "dbt_tipp", 0.70, override=True),   # loss 4.0, most confident
        _rec("en", "id_oos", ABSTAIN, "sleep_hygiene", 0.60),            # loss 1.0
    ]
    # sr(1)=4.0, sr(2)=(4.0+1.0)/2=2.5 -> mean 3.25
    assert augrc(cell, LOSS) == 3.25


def test_flag_bearing_rows_are_excluded_from_the_curve():
    cell = [
        _rec("en", "id_oos", ABSTAIN, "worry_time", 0.70, flag=True),   # excluded
        _rec("en", "id_oos", ABSTAIN, "sleep_hygiene", 0.60),
    ]
    assert augrc(cell, LOSS) == 1.0  # only the one non-flag row, a misroute


def test_per_cell_keys_each_lang_stratum_separately_and_ignores_na():
    recs = [
        _rec("en", "in_scope", "box_breathing", "box_breathing", 0.7),
        _rec("ar", "id_oos", ABSTAIN, "worry_time", 0.7),
        EvalRecord("crisis", "ar", "n/a", ABSTAIN, case_kind="crisis_invariance"),  # ignored
    ]
    out = per_cell_augrc(recs, LOSS)
    assert set(out.keys()) == {("en", "in_scope"), ("ar", "id_oos")}
    assert out[("en", "in_scope")].augrc == 0.0
    assert out[("ar", "id_oos")].augrc == 1.0
    assert out[("ar", "id_oos")].n == 1


def test_there_is_no_pooled_augrc_path():
    # BC3 structural: the worst-cell inflation makes pooled AR-vs-EN parity invalid (F8),
    # so the module must not expose any pooled aggregate.
    assert not hasattr(augrc_mod, "pooled_augrc")
    assert not hasattr(augrc_mod, "augrc_pooled")
