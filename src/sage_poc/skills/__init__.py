"""ONE accessor for every skill JSON read in the hot 9-node turn loop.

Before P2 Task 4, `load_skill` was called ~11x/turn across composer, skill_executor, and
skill_select, plus three separate module-level `_SKILLS = {sid: load_skill(sid) for sid in
SKILL_REGISTRY}` preloads (here, `skill_select.py`, `keyword_matcher.py`) that re-parsed
every skill JSON at import time. `get_skill` collapses all of that into one cache keyed by
(skill_id, path mtime, skills_dir): a file edit changes the key, so the very next call gets
a fresh parse automatically -- no stale skill after a JSON edit lands (dev-iteration benefit),
without giving up caching across the many calls a single turn makes when the file has NOT
changed.
"""
from functools import lru_cache
from pathlib import Path

from sage_poc.skill_ids import SKILL_REGISTRY
from sage_poc.skills.schema import SKILLS_DIR, Skill, _load_skill_from_path, load_skill

__all__ = ["get_skill", "SKILL_REGISTRY", "SKILLS_DIR", "Skill", "load_skill"]


@lru_cache(maxsize=None)
def _get_skill_cached(skill_id: str, mtime: float, skills_dir: Path) -> Skill:
    return _load_skill_from_path(skills_dir / f"{skill_id}.json")


def get_skill(skill_id: str) -> Skill:
    """Return the parsed `Skill` for `skill_id`, cached and keyed by (skill_id, path mtime,
    skills_dir). Value-identical to a fresh `load_skill(skill_id)` on every cache miss;
    served from cache (no file read) whenever the file's mtime is unchanged since the last
    call -- `SKILLS_DIR` is read fresh from this module's own globals on every call (not
    closed over), so it stays a live single-instance singleton even where a test needs it
    monkeypatched.

    CMS FORWARD-REQUIREMENT (register item 9): this cache is invalidation-correct ONLY as
    long as skills are file-served, because mtime is a filesystem property. Once skills
    become CMS-served (a DB write replaces the JSON-on-disk edit), mtime keying no longer
    invalidates anything -- there is no file to touch, so a stale cached Skill would be
    served forever after a CMS edit. The CMS write path MUST call `get_skill.cache_clear()`
    (or an equivalent targeted invalidation) as part of the same write, before any request
    can observe the new content. This is the single documented invalidation point for the
    skill cache; do not add a second one.

    This is not a hypothetical: it is the same failure class the 800-HOPE helpline reversal
    incident concerns -- mandatory safety copy embedded in a skill step (see
    `post_crisis_check_in.json`'s `{{crisis_number}}` placeholders, resolved by
    `sage_poc.crisis_copy`) must never be served stale after a config change. Today that
    change is a file edit and mtime keying catches it automatically; under CMS-served skills
    it is a DB write and only `get_skill.cache_clear()` catches it. Treat every deploy of the
    CMS write path as incomplete until it calls this.
    """
    path = SKILLS_DIR / f"{skill_id}.json"
    mtime = path.stat().st_mtime
    return _get_skill_cached(skill_id, mtime, SKILLS_DIR)


# Single documented invalidation point (see get_skill's docstring, register item 9).
get_skill.cache_clear = _get_skill_cached.cache_clear
get_skill.cache_info = _get_skill_cached.cache_info

# Warm the cache for every registered skill once at import time. This is NOT a second
# preload mechanism -- it is one warm-up pass through the SAME cache and the SAME
# accessor, so mtime-keyed invalidation still applies exactly as documented above; a
# post-import file edit is caught on the next call like any other. It exists because the
# retired per-module `_SKILLS` preloads had a real (if incidental) latency property: the
# JSON parse cost for all skills was paid once at process import, off the request-serving
# and readiness-warmup critical paths. `_ensure_semantic_ready()` (skill_select.py) builds
# its anchor index from every skill on the FIRST call, which is also the server's BGE-M3
# warmup task (server.py's _warmup_bge_m3) -- a cold get_skill cache there measurably
# delays `_bge_ready` (~1s locally: 27 cold parses added to the readiness-gating path).
# Warming here restores the "paid once at import" shape with a single cache instead of
# three redundant ones.
for _sid in SKILL_REGISTRY:
    get_skill(_sid)
del _sid
