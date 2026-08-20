"""P2 Task 4: the mtime-keyed `get_skill` accessor (sage_poc.skills).

Four ship-gate properties (task-4-brief.md Step 1):
  (a) value-identity   -- get_skill(x) deep-equals a fresh load_skill(x) for every registry id.
  (b) caching          -- a second call performs no file read (monkeypatched read_text counter).
  (c) mtime honesty    -- touching/modifying a skill file changes its mtime -> the very next
                           call (no cache_clear() needed) returns a fresh parse. This is BOTH the
                           dev-iteration benefit and the CMS-readiness proof: mtime keying is what
                           makes the cache safe to ship before CMS-served skills exist.
  (d) crisis-placeholder freshness -- LOAD-BEARING (the 800-HOPE helpline-reversal incident
                           class): a CRISIS_CONFIG-derived placeholder change is invisible to the
                           cache until get_skill.cache_clear() runs (proving the documented single
                           invalidation point is necessary), and IS reflected immediately after it
                           runs (proving it is sufficient). Mandatory safety copy embedded in a
                           skill step must never be served stale after a config change.
"""
import pathlib

import pytest

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills import get_skill
from sage_poc.skills.schema import Skill, load_skill


@pytest.fixture(autouse=True)
def _clear_skill_cache_around_test():
    """Every test starts and ends with a clean get_skill cache -- prevents one test's cached
    entries (or a monkeypatched CRISIS placeholder) from leaking into the next."""
    get_skill.cache_clear()
    yield
    get_skill.cache_clear()


# ── (a) value-identity ───────────────────────────────────────────────────────

@pytest.mark.parametrize("skill_id", SKILL_REGISTRY)
def test_get_skill_deep_equals_fresh_load_skill(skill_id):
    cached = get_skill(skill_id)
    fresh = load_skill(skill_id)
    assert cached == fresh
    assert cached.model_dump() == fresh.model_dump()


# ── (b) caching: second call performs no file read ──────────────────────────

def test_second_call_performs_no_file_read(monkeypatch):
    calls: list[pathlib.Path] = []
    original_read_text = pathlib.Path.read_text

    def _counting_read_text(self, *args, **kwargs):
        calls.append(self)
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", _counting_read_text)

    get_skill("cbt_thought_record")
    reads_after_first = len(calls)
    assert reads_after_first >= 1, "first call (cold cache) must read the file"

    get_skill("cbt_thought_record")
    assert len(calls) == reads_after_first, (
        "second call must be served from cache -- no additional read_text() call"
    )


def test_caching_is_per_skill_id(monkeypatch):
    """A cache hit on one skill_id must not suppress a cold miss on a different one."""
    calls: list[pathlib.Path] = []
    original_read_text = pathlib.Path.read_text

    def _counting_read_text(self, *args, **kwargs):
        calls.append(self)
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", _counting_read_text)

    get_skill("cbt_thought_record")
    n1 = len(calls)
    get_skill("box_breathing")  # different id -- must be a fresh read
    assert len(calls) > n1


# ── (c) mtime honesty: a file edit invalidates automatically, no cache_clear() ──

_MINIMAL_SKILL = {
    "skill_id": "test_mtime_skill",
    "skill_name": "Mtime Test Skill v1",
    "skill_type": "structured",
    "evidence_base": "test",
    "target_presentations": ["test phrase"],
    "steps": [],
    "step_policy": [],
    "escalation_matrix": {"L1": "exit", "L2": "flag", "L3": "crisis", "L4": "handoff"},
}


def test_mtime_change_returns_fresh_parse_without_cache_clear(tmp_path, monkeypatch):
    """The dev-iteration benefit AND the CMS-readiness proof: editing the file on disk is
    enough -- get_skill needs no explicit invalidation call to see the new content, because
    the (skill_id, mtime, skills_dir) cache key changes with the file."""
    import json
    import time

    skill_file = tmp_path / "test_mtime_skill.json"
    skill_file.write_text(json.dumps(_MINIMAL_SKILL), encoding="utf-8")

    # Point get_skill at the tmp directory (module-level global, looked up fresh on every
    # get_skill() call -- see get_skill's docstring).
    monkeypatch.setattr("sage_poc.skills.SKILLS_DIR", tmp_path)

    first = get_skill("test_mtime_skill")
    assert first.skill_name == "Mtime Test Skill v1"

    # Re-fetch immediately, unmodified: must be the cached object (no file read needed --
    # covered directly by test_second_call_performs_no_file_read; here we only need the
    # VALUE to still be v1 as the pre-edit control).
    assert get_skill("test_mtime_skill").skill_name == "Mtime Test Skill v1"

    # Edit the file AND force the mtime forward explicitly -- some filesystems have coarse
    # (1s) mtime resolution, so a same-second edit could otherwise alias the old cache key.
    updated = dict(_MINIMAL_SKILL, skill_name="Mtime Test Skill v2 (edited)")
    skill_file.write_text(json.dumps(updated), encoding="utf-8")
    new_mtime = skill_file.stat().st_mtime + 5.0
    import os
    os.utime(skill_file, (new_mtime, new_mtime))

    # No cache_clear() call here -- this is the whole point of mtime keying.
    second = get_skill("test_mtime_skill")
    assert second.skill_name == "Mtime Test Skill v2 (edited)", (
        "get_skill must return a fresh parse once the file's mtime changes, with no "
        "explicit invalidation call"
    )
    assert second != first


# ── (d) crisis-placeholder freshness (load-bearing: helpline-reversal incident class) ──

def test_crisis_placeholder_change_requires_cache_clear_then_is_reflected(monkeypatch):
    """post_crisis_check_in.json carries {{crisis_number}} placeholders resolved at load time
    from sage_poc.crisis_copy._PLACEHOLDERS (itself derived from config.CRISIS_CONFIG). This
    pins BOTH halves of the invalidation contract documented on get_skill:

      1. Necessity: a placeholder-source change is NOT visible through a warm cache entry --
         proves the cache would otherwise serve a stale (possibly wrong/retracted) crisis
         number forever, exactly the 800-HOPE-reversal failure class.
      2. Sufficiency: calling get_skill.cache_clear() (the single documented invalidation
         point) is enough to make the next call see the new value -- no second mechanism
         needed.

    Uses an injected sentinel value, never a real/production crisis number, so this does not
    assert on copied prod safety strings -- only on behavior around the test's own marker.
    """
    from sage_poc import crisis_copy

    before = get_skill("post_crisis_check_in")
    before_dump = before.model_dump_json()
    assert "{{crisis_" not in before_dump, "sanity: placeholders must already be resolved"

    sentinel = "SENTINEL-SF-CRISIS-LINE-0000-TEST"
    mutated_placeholders = dict(crisis_copy._PLACEHOLDERS)
    mutated_placeholders["{{crisis_number}}"] = sentinel
    monkeypatch.setattr(crisis_copy, "_PLACEHOLDERS", mutated_placeholders)

    # Necessity: still cached (mtime unchanged, no cache_clear()) -- the mutation must be
    # INVISIBLE right now, proving the cache does not silently pick up a config change.
    stale = get_skill("post_crisis_check_in")
    stale_dump = stale.model_dump_json()
    assert sentinel not in stale_dump
    assert stale_dump == before_dump

    # Sufficiency: the single documented invalidation point makes it visible immediately.
    get_skill.cache_clear()
    fresh = get_skill("post_crisis_check_in")
    fresh_dump = fresh.model_dump_json()
    assert sentinel in fresh_dump, (
        "get_skill.cache_clear() is the documented single invalidation point -- a crisis-copy "
        "config change must be reflected the next call after it runs"
    )


# ── invalidation-point plumbing ──────────────────────────────────────────────

def test_cache_clear_is_exposed_and_callable():
    assert hasattr(get_skill, "cache_clear")
    get_skill("cbt_thought_record")
    get_skill.cache_clear()  # must not raise


def test_get_skill_docstring_names_the_cms_forward_requirement():
    """The CMS forward-requirement (register item 9) must be discoverable at the invalidation
    point itself -- the docstring is its carrier, per the owner amendment. Behavior marker
    (a documented obligation exists at this exact object), not a copy of the prose."""
    doc = (get_skill.__doc__ or "")
    assert "cache_clear" in doc
    assert "CMS" in doc
