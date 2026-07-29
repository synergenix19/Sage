import pytest
from sage_poc.psychoed import store

def test_all_40_blocks_load():
    assert len(store.block_ids()) == 40
    b = store.get_block("1f-b1")
    assert b["psychoed"]["category"] == "1f" and b["content"]

def test_manifests_and_categories():
    m = store.manifest("3c")
    assert m["safety_weave"] is True and m["delivery_shape"] == "answer_first"
    assert store.category_of("s2c-b8") == "s2c"

def test_family_of_kb_ref():
    assert store.family_of_kb_ref("understanding_anxiety") == "understanding_anxiety"
    assert store.family_of_kb_ref("1f-b2") == "understanding_anxiety"
    assert store.family_of_kb_ref("nope") is None

def test_pending_script_raises():
    with pytest.raises(store.PendingClinicianScript):
        store.shared_script("human_referral_close")
    assert store.shared_script("safety_weave_script")  # ratified-source script loads fine

def test_block_hash_stable():
    h = store.block_sha256("1f-b1")
    assert len(h) == 64 and h == store.block_sha256("1f-b1")
