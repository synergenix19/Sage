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
