"""Tests for the EMR Phase-0 baseline runner (scripts/instrument/run_emr_baseline.py).

The runner drives the emr_request_family fixtures at N per fixture THROUGH the
parity helper and writes the baseline artifact with the template header block +
per-fixture outcome DISTRIBUTIONS. These tests cover the aggregation math and the
artifact shape with synthetic records — no network, no prod, no LLM.
"""
import importlib.util
import json
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rb = _load("scripts/instrument/run_emr_baseline.py", "run_emr_baseline")
ge = _load("scripts/instrument/graph_evidence.py", "graph_evidence_for_baseline_tests")


# ---------------------------------------------------------------------------
# Synthetic per-sample records (shape produced by graph_evidence.run_fixture)
# ---------------------------------------------------------------------------

def _rec(turn, intent, conf, path, offered=None, active=None, method=None):
    return {"turn": turn, "user_message": f"m{turn}", "primary_intent": intent,
            "secondary_intent": None, "confidence": conf, "path": path,
            "offered_skill_ids": offered, "active_skill_id": active,
            "completed_skill_id": None, "skill_match_method": method,
            "classifier_system_fingerprint": "fp_t",
            "degraded": intent == "general_chat" and conf == 0.5}


_PATH_OFFER = ["safety_check", "intent_route", "skill_select", "skill_respond"]
_PATH_FREEFLOW = ["safety_check", "intent_route", "freeflow_respond"]


def _sample(idx, final):
    first = _rec(1, "general_chat", 0.9, _PATH_FREEFLOW)
    return {"sample": idx, "thread_id": f"t{idx}", "records": [first, final]}


def _fixture_result():
    """4 samples: 3 land the offer mechanism, 1 flips to info_request freeflow."""
    offer_final = _rec(2, "new_skill", 0.9, _PATH_OFFER,
                       offered=["box_breathing"], method="keyword")
    flip_final = _rec(2, "info_request", 0.9, _PATH_FREEFLOW)
    return {"n": 4, "turns": 2,
            "samples": [_sample(0, offer_final), _sample(1, offer_final),
                        _sample(2, offer_final), _sample(3, flip_final)],
            "degraded_turn_count": 0}


# ---------------------------------------------------------------------------
# Aggregation math
# ---------------------------------------------------------------------------

def test_offer_rate_counts_final_turn_offers():
    agg = rb.aggregate_case(_fixture_result())
    assert agg["n"] == 4
    assert agg["offer_rate"] == pytest.approx(0.75)


def test_mechanism_counts_keyed_on_intent_plus_path_signature():
    agg = rb.aggregate_case(_fixture_result())
    key_offer = "new_skill|" + ">".join(_PATH_OFFER)
    key_flip = "info_request|" + ">".join(_PATH_FREEFLOW)
    assert agg["mechanism_counts"][key_offer] == 3
    assert agg["mechanism_counts"][key_flip] == 1


def test_flip_rate_is_fraction_off_the_modal_outcome():
    agg = rb.aggregate_case(_fixture_result())
    assert agg["mechanism_flip_rate"] == pytest.approx(0.25)
    assert agg["trajectory_flip_rate"] == pytest.approx(0.25)


def test_trajectory_frequencies_cover_all_samples():
    agg = rb.aggregate_case(_fixture_result())
    assert sum(agg["trajectory_freqs"].values()) == 4
    assert len(agg["trajectory_freqs"]) == 2  # modal trajectory + the flip


_PATH_ABSORB = ["safety_check", "intent_route", "skill_executor", "freeflow_respond"]
_PATH_PROMOTED = ["safety_check", "intent_route", "skill_select", "offer_promoted",
                  "skill_respond"]


def _three_mechanism_result():
    """Coordinator-specified fabricated set: absorption / first-line offer / KB abstain."""
    absorption = _rec(2, "skill_continuation", 0.9, _PATH_ABSORB,
                      active="psychoed_anxiety", method="info_request_skill_consult")
    first_line = _rec(2, "new_skill", 0.9, _PATH_OFFER,
                      offered=["box_breathing"], method="keyword")
    kb_abstain = _rec(2, "info_request", 0.8,
                      ["safety_check", "intent_route", "offer_ignored", "skill_select",
                       "knowledge_retrieve", "freeflow_respond"])
    return {"n": 3, "turns": 2,
            "samples": [_sample(0, absorption), _sample(1, first_line),
                        _sample(2, kb_abstain)],
            "degraded_turn_count": 0}


def test_first_line_column_vs_offer_rate_on_the_three_mechanisms():
    """absorption -> offer=1/conformant=0; first-line offer -> 1/1; KB abstain -> 0/0.
    The offer-rate/first-line DELTA is the DF-1 ordering evidence."""
    agg = rb.aggregate_case(_three_mechanism_result())
    assert agg["offer_rate"] == pytest.approx(2 / 3)          # absorption + offer count
    assert agg["first_line_offer_rate"] == pytest.approx(1 / 3)  # ONLY the §1a pair offer


def test_first_line_counts_pair_activation_only_via_offer_promoted_path():
    pair_promoted = _rec(2, "new_skill", 0.9, _PATH_PROMOTED,
                         active="box_breathing", method="offer_accept")
    pair_absorbed = _rec(2, "skill_continuation", 0.9, _PATH_ABSORB,
                         active="box_breathing", method="info_request_skill_consult")
    other_promoted = _rec(2, "new_skill", 0.9, _PATH_PROMOTED,
                          active="worry_time", method="offer_accept")
    res = {"n": 3, "turns": 2, "degraded_turn_count": 0,
           "samples": [_sample(0, pair_promoted), _sample(1, pair_absorbed),
                       _sample(2, other_promoted)]}
    agg = rb.aggregate_case(res)
    # ONLY the offer_promoted activation of a pair skill is spec-conformant:
    # a pair skill reached WITHOUT the offer path is not, another skill promoted is not
    assert agg["offer_rate"] == pytest.approx(1.0)
    assert agg["first_line_offer_rate"] == pytest.approx(1 / 3)


def test_first_line_pair_is_the_spec_tier1_pair():
    assert rb.FIRST_LINE_PAIR == {"box_breathing", "grounding_5_4_3_2_1"}


def test_semantic_offer_of_other_skills_counts_zero_in_first_line_column():
    other_offer = _rec(2, "new_skill", 0.9, _PATH_OFFER,
                       offered=["psychoed_anxiety", "worry_time"], method="semantic_offer")
    res = {"n": 1, "turns": 2, "degraded_turn_count": 0,
           "samples": [_sample(0, other_offer)]}
    agg = rb.aggregate_case(res)
    assert agg["offer_rate"] == 1.0
    assert agg["first_line_offer_rate"] == 0.0


def test_stable_fixture_has_zero_flip_rate():
    res = _fixture_result()
    stable_final = _rec(2, "new_skill", 0.9, _PATH_OFFER,
                        offered=["box_breathing"], method="keyword")
    res["samples"] = [_sample(i, stable_final) for i in range(4)]
    agg = rb.aggregate_case(res)
    assert agg["mechanism_flip_rate"] == 0.0
    assert agg["offer_rate"] == 1.0


# ---------------------------------------------------------------------------
# Provenance gate (Phase-0 register ruling: unrecorded-provenance baseline
# fails the signed instrument-parity rule)
# ---------------------------------------------------------------------------

def test_provenance_gate_refuses_when_flag_off():
    # rb loads its own graph_evidence instance — the refusal class must be ITS class
    with pytest.raises(rb.ge.ParityRefusal):
        rb.enforce_recorded_provenance({"SAGE_AUDIT_CLASSIFIER_PROVENANCE": "false"},
                                       allow_unrecorded=False)


def test_provenance_gate_passes_when_on_and_override_is_loud():
    rb.enforce_recorded_provenance({"SAGE_AUDIT_CLASSIFIER_PROVENANCE": "true"},
                                   allow_unrecorded=False)
    note = rb.enforce_recorded_provenance({"SAGE_AUDIT_CLASSIFIER_PROVENANCE": "false"},
                                          allow_unrecorded=True)
    assert note and "UNRECORDED" in note.upper()


# ---------------------------------------------------------------------------
# Artifact shape
# ---------------------------------------------------------------------------

def _fabricated_header():
    mapping = {"SAGE_HIGH_RISK_DETECTION": "false",
               "SAGE_AUDIT_CLASSIFIER_PROVENANCE": "false",
               "SAGE_CLASSIFIER_MODEL": "openai/gpt-4o-mini"}
    readback = {"build_sha": "feedfacebeef", "build_sha_source": "SAGE_BUILD_SHA",
                "high_risk_detection_raw_env": "true",
                "audit_classifier_provenance_raw_env": "true",
                "classifier_model_raw_env": None}
    derived = ge.derive_flag_set(
        readback,
        desired={"SAGE_HIGH_RISK_DETECTION": "true",
                 "SAGE_AUDIT_CLASSIFIER_PROVENANCE": "true"},
        mapping=mapping)
    return ge.header_block(derived, readback, n_per_fixture=4,
                           degraded_turn_count=0, fingerprints=["fp_t"])


def test_baseline_md_carries_header_then_distributions(tmp_path):
    per_case = {
        "EMR-S1-000": {"surface": "s1_active_skill_absorption",
                       "spec_expectation": {"expected": "offer box_breathing"},
                       **rb.aggregate_case(_fixture_result())},
    }
    out = tmp_path / "baseline.md"
    rb.write_baseline(str(out), _fabricated_header(), per_case)
    text = out.read_text()
    assert text.index("feedfacebeef") < text.index("EMR-S1-000"), "header must precede results"
    assert "offer-rate" in text.lower()
    assert "first-line" in text.lower()      # spec-conformance column present
    assert "box_breathing" in text           # the §1a pair is named in the metric key
    assert "0.75" in text
    assert "flip-rate" in text.lower()
    assert "new_skill|" in text          # mechanism keyed on intent+path signature
    assert "Trajectory frequencies" in text


def test_runner_default_n_is_ten():
    assert rb.DEFAULT_N == 10


def test_runner_writes_governance_artifact_path_by_default():
    assert rb.DEFAULT_OUT.endswith(
        "docs/superpowers/governance/2026-07-29-emr-phase0-baseline.md")


# ---------------------------------------------------------------------------
# Quiescence attestation (baseline pre-authorization, BINDING)
# ---------------------------------------------------------------------------

def _check(ts, clean=True, dep_id=None, dep_created=None,
           flags=("SAGE_INFO_REQUEST_CONSULT",)):
    return {"ts": ts, "clean": clean, "deployment_id": dep_id,
            "deployment_created_at": dep_created, "flags_checked": list(flags)}


def test_quiescence_satisfied_by_deployment_id_change():
    state = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa"),
        _check("2026-07-29T12:00:00+00:00", dep_id="dep-bbb"),
    ], "refusals": []}
    res = rb.evaluate_quiescence(state, "item1-condition-a")
    assert res["ok"] is True
    assert "deployment id changed" in res["detail"]


def test_quiescence_satisfied_by_bracketed_deployment_timestamp():
    state = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa"),
        _check("2026-07-29T12:00:00+00:00", dep_id=None,
               dep_created="2026-07-29T10:30:00+00:00"),
    ], "refusals": []}
    res = rb.evaluate_quiescence(state, "item1-condition-b")
    assert res["ok"] is True
    assert "bracket" in res["detail"]


def test_quiescence_clock_only_refuses_explicitly():
    """Two clean checks, hours apart, SAME deployment, nothing bracketed — the
    clock alone NEVER satisfies quiescence."""
    state = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa",
               dep_created="2026-07-29T01:00:00+00:00"),
        _check("2026-07-29T20:00:00+00:00", dep_id="dep-aaa",
               dep_created="2026-07-29T01:00:00+00:00"),
    ], "refusals": []}
    res = rb.evaluate_quiescence(state, "item1-condition-a")
    assert res["ok"] is False
    assert res["condition_failed"] == "no-deploy-cycle-spanned"
    assert "clock alone" in res["detail"]


def test_quiescence_unsatisfied_on_insufficient_clean_checks():
    one = {"checks": [_check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa")],
           "refusals": []}
    res = rb.evaluate_quiescence(one, "item1-condition-a")
    assert res["ok"] is False and res["condition_failed"] == "insufficient-clean-checks"

    dirty = {"checks": [
        _check("2026-07-29T08:00:00+00:00", clean=False, dep_id="dep-aaa"),
        _check("2026-07-29T12:00:00+00:00", dep_id="dep-bbb"),
    ], "refusals": []}
    res = rb.evaluate_quiescence(dirty, "item1-condition-a")
    assert res["ok"] is False and res["condition_failed"] == "insufficient-clean-checks"


def test_quiescence_check_must_cover_the_signed_flag():
    state = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa", flags=("SAGE_D1_SCREEN",)),
        _check("2026-07-29T12:00:00+00:00", dep_id="dep-bbb"),
    ], "refusals": []}
    res = rb.evaluate_quiescence(state, "item1-condition-a")
    assert res["ok"] is False and res["condition_failed"] == "insufficient-clean-checks"


def test_quiescence_missing_or_invalid_cause_refuses():
    good = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa"),
        _check("2026-07-29T12:00:00+00:00", dep_id="dep-bbb"),
    ], "refusals": []}
    for cause in (None, "", "it-felt-quiet", "condition-a"):
        res = rb.evaluate_quiescence(good, cause)
        assert res["ok"] is False, f"cause {cause!r} must not satisfy"
        assert res["condition_failed"] == "missing-or-invalid-cause"
        for allowed in rb.QUIESCENCE_CAUSES:
            assert allowed in res["detail"]  # explicit message lists the enum


def test_quiescence_causes_are_the_binding_enum():
    assert rb.QUIESCENCE_CAUSES == {"item1-condition-a", "item1-condition-b",
                                    "supersession-ratified"}


def test_refusals_are_recorded_and_persist(tmp_path):
    path = str(tmp_path / "quiescence.json")
    state = rb.load_quiescence_state(path)
    res = rb.evaluate_quiescence(state, "item1-condition-a")
    assert res["ok"] is False
    rb.record_refusal(state, res)
    rb.save_quiescence_state(path, state)
    reloaded = rb.load_quiescence_state(path)
    assert len(reloaded["refusals"]) == 1
    entry = reloaded["refusals"][0]
    assert entry["condition_failed"] == "insufficient-clean-checks"
    assert entry["ts"]  # timestamped


def test_attestation_and_refusal_log_land_in_the_header():
    header = {"parity_notes": []}
    state = {"checks": [
        _check("2026-07-29T08:00:00+00:00", dep_id="dep-aaa"),
        _check("2026-07-29T12:00:00+00:00", dep_id="dep-bbb"),
    ], "refusals": [{"ts": "2026-07-29T09:00:00+00:00",
                     "condition_failed": "insufficient-clean-checks",
                     "detail": "1 clean check(s)"}]}
    res = rb.evaluate_quiescence(state, "item1-condition-b")
    rb.attach_quiescence_to_header(header, "item1-condition-b", res, state)
    q = header["quiescence_attestation"]
    assert q["cause"] == "item1-condition-b"
    assert q["refusal_log"] == state["refusals"]
    joined = " ".join(header["parity_notes"])
    assert "item1-condition-b" in joined
    assert "refusal log" in joined.lower()
    assert "insufficient-clean-checks" in joined
