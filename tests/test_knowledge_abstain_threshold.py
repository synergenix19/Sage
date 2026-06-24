def test_threshold_is_nonzero_and_filters_weak_passages():
    from sage_poc.knowledge import postgres_repository as pr
    assert pr.KNOWLEDGE_ABSTAIN_THRESHOLD > 0.0, "POC 0.0 default must be raised"
    # a weak single-list rank-20 RRF score (1/80 = 0.0125) must NOT pass
    assert pr._passes_abstain(0.0125) is False
    # a dual-list rank-1 RRF score (1/61 + 1/61 = 0.0328) must pass
    assert pr._passes_abstain(0.0328) is True
