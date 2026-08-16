"""The info_request consult set is a DISPOSITION set, pinned to the doc-derived corpus.

Guards against (a) drift from the corpus's per-category prescriptions, and (b) anyone
re-fusing the disposition/delivery axes by pulling a delivery-format value in here.
"""
import json
import pathlib

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.info_request_consult_set import INFO_REQUEST_SKILL_CONSULT_SET

_CORPUS = pathlib.Path("tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus.jsonl")
# The four in-scope categories: Mechanism-A + would-match. §4a (Mechanism B) and §7c
# (matching gap -> clinician packet) are deliberately excluded.
_IN_SCOPE = {"§1f", "§6d", "§3c", "S2c"}


def _corpus_families_for(categories: set[str]) -> frozenset[str]:
    fams: set[str] = set()
    for line in _CORPUS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("spec_id") in categories:
            fam = row.get("expected_skill_family")
            fams.update(fam if isinstance(fam, list) else [fam])
    return frozenset(f for f in fams if f)


def test_consult_set_equals_corpus_prescriptions_for_in_scope_categories():
    # The set IS the union of what the doc (via the corpus oracle) prescribes for the
    # in-scope categories. If the corpus prescriptions change, this fails -> re-derive.
    assert INFO_REQUEST_SKILL_CONSULT_SET == _corpus_families_for(_IN_SCOPE)


def test_every_consult_skill_exists_in_registry():
    for skill_id in INFO_REQUEST_SKILL_CONSULT_SET:
        assert skill_id in SKILL_REGISTRY, f"{skill_id} not in SKILL_REGISTRY"


def test_out_of_scope_categories_are_not_silently_included():
    # §4a's mood_check_in (Mechanism B) must not be in the consult set -- it is a routing
    # problem at a different site, not an info_request consult candidate.
    assert "mood_check_in" not in INFO_REQUEST_SKILL_CONSULT_SET
