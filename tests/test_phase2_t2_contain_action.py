"""Phase 2 T2 — `contain` disposition (contain SUPERSEDES abstain), dormant on master.

The consumer branch + params reader exist; NO family declares skill_select_disposition 'contain' yet
(T4), so on master this is behavior-identical (the branch never fires). This asserts the mechanism is
wired AND dormant, and that contain would take precedence over abstain when a family declares it.
"""
from sage_poc.nodes import skill_select as ss


def test_dormant_on_master_no_contain_flags():
    # inert: no flag on master declares disposition 'contain'
    assert ss._flag_contain_params() == {}, "T2 must be dormant on master (no family declares contain until T4)"


def test_contain_supersedes_abstain_in_source():
    # the consumer branch places contain BEFORE the abstain early-return (contain supersedes)
    import inspect
    src = inspect.getsource(ss.skill_select_node) if hasattr(ss, "skill_select_node") else inspect.getsource(ss)
    ci = src.find("clinical_flag_contain")
    ai = src.find("clinical_flag_abstain")
    assert ci != -1 and ai != -1 and ci < ai, "contain branch must precede abstain (design §2: contain supersedes bare abstain)"
