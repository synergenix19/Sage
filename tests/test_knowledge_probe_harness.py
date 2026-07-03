from scripts.knowledge_ar_recall_probe import recall_at_k, reciprocal_rank


def test_recall_at_k_hit_and_miss():
    assert recall_at_k(["a"], ["x", "a", "y"], k=5) == 1.0
    assert recall_at_k(["a"], ["x", "y", "z"], k=5) == 0.0
    assert recall_at_k(["a"], ["x", "y", "a"], k=2) == 0.0  # 'a' is at rank 3, outside k=2


def test_reciprocal_rank():
    assert reciprocal_rank(["a"], ["a", "b"]) == 1.0
    assert reciprocal_rank(["a"], ["b", "a"]) == 0.5
    assert reciprocal_rank(["a"], ["b", "c"]) == 0.0
