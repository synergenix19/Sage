"""AR layer-1 corpus (batch-1 draft) integrity — keeps the draft-guard armable and mapping-faithful.

The AR corpus is engineering-drafted, awaiting Vee mapping sign-off + native dialect review (A0 split-role,
2026-07-23). These tests ensure it stays (a) marked draft on EVERY row so the runner's draft-guard fires and
no number is published pre-ratification, and (b) disposition-faithful to the EN corpus it mirrors (a mapping,
not a free translation — the disposition must not drift).
"""
import json, os

_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "tests/fixtures/bot_behaviour_audit")
_AR = os.path.join(_DIR, "layer1_trigger_corpus_ar_DRAFT.jsonl")
_EN = os.path.join(_DIR, "layer1_trigger_corpus.jsonl")


def _rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def test_every_ar_row_is_marked_draft_so_the_guard_fires():
    rows = _rows(_AR)
    assert rows, "AR corpus empty"
    assert all(r.get("draft") is True for r in rows), \
        "an AR row is not draft:true — the runner's draft-guard would not fire and a number could be published"


def test_ar_dispositions_match_the_en_source_row_mapping_not_drift():
    en = {(r["spec_id"], r["utterance"]): r for r in _rows(_EN)}
    for r in _rows(_AR):
        src = en.get((r["spec_id"], r["en_source"]))
        assert src, f"AR row {r['spec_id']} cites an en_source not in the EN corpus"
        assert src["prescribed_disposition"] == r["prescribed_disposition"], \
            f"disposition drift on {r['spec_id']} '{r['en_source']}' (mirror must preserve disposition)"


def test_ar_utterances_are_nonempty_arabic():
    for r in _rows(_AR):
        assert r["utterance"].strip(), f"empty AR utterance for {r['spec_id']}"
        assert any("؀" <= c <= "ۿ" for c in r["utterance"]), \
            f"AR utterance for {r['spec_id']} has no Arabic script"


def test_safety_critical_rows_are_flagged_to_aim_the_reviewer():
    # C (crisis) and HR (psychosis/dissociation) are the whole point of the AR detection axis; every one
    # must be flagged so the scarce native dialect pass lands on them.
    for r in _rows(_AR):
        if r["spec_id"] in ("C", "HR"):
            assert r.get("idiom_flag") == "lexicon-critical", \
                f"{r['spec_id']} row not flagged lexicon-critical: '{r['en_source']}'"
