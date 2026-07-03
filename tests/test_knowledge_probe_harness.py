import pytest

from scripts.knowledge_ar_recall_probe import recall_at_k, reciprocal_rank, score_probe


def test_recall_at_k_hit_and_miss():
    assert recall_at_k(["a"], ["x", "a", "y"], k=5) == 1.0
    assert recall_at_k(["a"], ["x", "y", "z"], k=5) == 0.0
    assert recall_at_k(["a"], ["x", "y", "a"], k=2) == 0.0  # 'a' is at rank 3, outside k=2


def test_reciprocal_rank():
    assert reciprocal_rank(["a"], ["a", "b"]) == 1.0
    assert reciprocal_rank(["a"], ["b", "a"]) == 0.5
    assert reciprocal_rank(["a"], ["b", "c"]) == 0.0


@pytest.mark.asyncio
async def test_score_probe_buckets_by_overall_and_dialect_variance():
    """score_probe must split into 'overall' plus one '{dialect_tag}/{variance_type}'
    bucket per row, with correct n/recall_at_5/mrr per bucket — no DB required,
    retrieve_fn is stubbed."""
    rows = [
        {"query": "q-msa", "dialect_tag": "msa", "variance_type": "baseline", "gold_article_ids": ["a1"]},
        {"query": "q-ortho", "dialect_tag": "khaleeji", "variance_type": "orthographic", "gold_article_ids": ["a2"]},
        {"query": "q-lex", "dialect_tag": "khaleeji", "variance_type": "lexical", "gold_article_ids": ["a3"]},
    ]

    # msa/baseline: hit at rank 1 (recall=1.0, mrr=1.0)
    # khaleeji/orthographic: miss entirely (recall=0.0, mrr=0.0)
    # khaleeji/lexical: hit at rank 2 (recall=1.0, mrr=0.5)
    canned = {
        "q-msa": ["a1", "x", "y"],
        "q-ortho": ["x", "y", "z"],
        "q-lex": ["x", "a3", "y"],
    }

    async def stub_retrieve_fn(query, language):
        assert language == "ar"
        return canned[query]

    result = await score_probe(rows, stub_retrieve_fn)

    assert set(result.keys()) == {"overall", "msa/baseline", "khaleeji/orthographic", "khaleeji/lexical"}

    assert result["msa/baseline"] == {"n": 1, "recall_at_5": 1.0, "mrr": 1.0}
    assert result["khaleeji/orthographic"] == {"n": 1, "recall_at_5": 0.0, "mrr": 0.0}
    assert result["khaleeji/lexical"] == {"n": 1, "recall_at_5": 1.0, "mrr": 0.5}

    assert result["overall"]["n"] == 3
    assert result["overall"]["recall_at_5"] == pytest.approx(2 / 3)
    assert result["overall"]["mrr"] == pytest.approx((1.0 + 0.0 + 0.5) / 3)


@pytest.mark.asyncio
async def test_cosine_distributions_buckets_by_dialect_and_variance():
    from scripts.knowledge_ar_recall_probe import cosine_distributions
    rows = [
        {"query": "a", "dialect_tag": "msa", "variance_type": "baseline"},
        {"query": "b", "dialect_tag": "en", "variance_type": "negative"},
    ]
    async def search_fn(query, language):
        return 0.8 if query == "a" else 0.1  # returns top_similarity
    dist = await cosine_distributions(rows, search_fn)
    assert dist["msa/baseline"]["max"] == 0.8
    assert dist["en/negative"]["max"] == 0.1
