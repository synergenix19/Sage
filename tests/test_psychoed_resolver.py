# tests/test_psychoed_resolver.py
from sage_poc.psychoed import resolver

ALL = frozenset({"1f", "3c", "4b", "6d", "7c", "s2c"})

def test_exact_hit_routes_category():
    r = resolver.resolve("What is anxiety?", active_category=None, grief_context=False,
                         enabled_categories=ALL)
    assert r and r["category"] == "1f"

def test_disabled_category_never_fires():
    r = resolver.resolve("What is anxiety?", active_category=None, grief_context=False,
                         enabled_categories=frozenset({"3c"}))
    assert r is None

def test_numb_collision_default_3c():
    r = resolver.resolve("Why do I feel numb?", active_category=None, grief_context=False,
                         enabled_categories=ALL)
    assert r["category"] == "3c" and r["collision_path"] == "default_winner"

def test_numb_collision_grief_context_s2c():
    r = resolver.resolve("Why do I feel numb?", active_category=None, grief_context=True,
                         enabled_categories=ALL)
    assert r["category"] == "s2c" and r["collision_path"] == "context_winner"

def test_subsumption_long_form_winner():
    r = resolver.resolve("Why do I feel like this for no reason?", active_category=None,
                         grief_context=False, enabled_categories=ALL)
    assert r["category"] == "3c"   # declared subsumption winner (weave-dominance)

def test_menu_context_scoped_first():
    r = resolver.resolve("the maintenance cycle one", active_category="1f",
                         grief_context=False, enabled_categories=ALL)
    assert r and r["category"] == "1f" and r["menu_pick"] is True

def test_bare_emotional_words_no_match():
    for msg in ("I'm stressed", "I feel depressed", "I feel sad"):
        assert resolver.resolve(msg, active_category=None, grief_context=False,
                                enabled_categories=ALL) is None

# --- Post-review addition (2026-07-28): ambiguous menu-label multi-match must
# fail closed to None, never resolve by manifest array position. ---

def test_ambiguous_menu_subset_match_fails_closed():
    # "the anxiety one" (1f active) subset-matches THREE 1f block labels that
    # all contain "anxiety": 1f-b1 ("What is anxiety?"), 1f-b3 ("Why anxiety
    # causes physical symptoms"), 1f-b4 ("The anxiety maintenance cycle").
    # Pre-fix, the resolver silently returned 1f-b1 (first in manifest array
    # order) -- an undeclared-first pick, the same anti-pattern this module
    # refuses at the cross-category collision tier. Post-fix, the ambiguous
    # menu tier returns None and resolve() falls through to the global
    # trigger tables; "the anxiety one" doesn't exact- or subsumption-match
    # any registered trigger phrase either, so the overall result is None.
    # (Probed directly: resolver.resolve(...) returns None, not a block_id.)
    r = resolver.resolve("the anxiety one", active_category="1f",
                         grief_context=False, enabled_categories=ALL)
    assert r is None

def test_unambiguous_menu_subset_match_still_resolves():
    # Same fixture as test_menu_context_scoped_first, re-asserted here
    # specifically as a regression guard alongside the ambiguity fix above:
    # "maintenance cycle" only appears (as a subset-tier word match) in
    # 1f-b4's label ("The anxiety maintenance cycle"), so this stays a
    # single, unambiguous match and must still resolve, not be swept up by
    # the new fail-closed rule.
    r = resolver.resolve("the maintenance cycle one", active_category="1f",
                         grief_context=False, enabled_categories=ALL)
    assert r and r["category"] == "1f" and r["menu_pick"] is True and r["block_id"] == "1f-b4"
