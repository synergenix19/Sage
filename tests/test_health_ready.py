"""Task 1 (make-v2-live plan): /health/ready must report the TRUE routing mode.

The inert-flag hazard: prod/staging had SKILL_ROUTING_V2=1 / SKILL_RERANK_ENABLED=1 set while
running a V1 build with no reranker path — the env advertised a reranker the code did not contain.
`compute_routing_mode()` derives the mode from CODE CAPABILITY, not the raw flag, so a set flag can
never advertise v2 on a build that lacks the selector path.
"""


def test_routing_mode_is_v1_when_reranker_path_absent(monkeypatch):
    # On a V1 build (no _rerank_enabled selector path), the mode is "v1" EVEN with the flag set.
    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    from server import compute_routing_mode

    assert compute_routing_mode() == "v1"


def test_routing_mode_matches_flag_when_reranker_path_present(monkeypatch):
    # Tree-agnostic contract: when the reranker selector path exists in the build, the mode tracks
    # the flag. On V1/master the import fails and the branch is skipped (v1 asserted above).
    try:
        from sage_poc.nodes.skill_select import _rerank_enabled  # present only on V2 builds
    except ImportError:
        import pytest

        pytest.skip("V1 build: no reranker selector path (expected on master)")
    from server import compute_routing_mode

    monkeypatch.setenv("SKILL_RERANK_ENABLED", "1")
    assert compute_routing_mode() == ("v2" if _rerank_enabled() else "v1")
