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
import sage_poc.skills.schema as _schema
from sage_poc.skills.schema import Skill, _load_skill_from_path, load_skill

__all__ = ["get_skill", "SKILL_REGISTRY", "Skill", "load_skill"]

# Bounded (fix round 1, M3): mtime keying means every on-disk edit mints a NEW cache entry
# (the old one becomes unreachable, not overwritten). A long-lived watch/hot-reload process
# that edits skills repeatedly would otherwise accumulate one entry per edit forever
# (maxsize=None). 4x the registry size gives every skill room for several stale generations
# before its oldest is LRU-evicted, without ever letting the cache grow unbounded. This does
# NOT change the invalidation story: mtime keying and get_skill.cache_clear() work exactly
# the same under a bounded cache -- eviction only reclaims memory for keys nothing will ever
# ask for again (the old mtime), it never masks a stale read.
_SKILL_CACHE_MAXSIZE = 4 * len(SKILL_REGISTRY)


@lru_cache(maxsize=_SKILL_CACHE_MAXSIZE)
def _get_skill_cached(skill_id: str, mtime: float, skills_dir: Path) -> Skill:
    return _load_skill_from_path(skills_dir / f"{skill_id}.json")


def get_skill(skill_id: str) -> Skill:
    """Return the parsed `Skill` for `skill_id`, cached and keyed by (skill_id, path mtime,
    skills_dir). Value-identical to a fresh `load_skill(skill_id)` on every cache miss;
    served from cache (no file read) whenever the file's mtime is unchanged since the last
    call. Treat the returned `Skill` as immutable -- it is a process-shared cached instance,
    not a fresh copy; every caller in the same process gets the SAME object for the same
    (skill_id, mtime), so mutating a returned Skill would leak across every other call site.

    `SKILLS_DIR` is resolved via `sage_poc.skills.schema.SKILLS_DIR` (the module attribute,
    read fresh on every call, not closed over) -- the SAME global `load_skill` resolves
    against (fix round 1, N4: this package also re-exports a `SKILLS_DIR` name for external
    convenience, but that re-export is a snapshot taken at import time and is NOT what this
    function reads; monkeypatching only the re-export would silently desync `get_skill` from
    `load_skill`'s path resolution, so there is exactly one authoritative global -- patch
    `sage_poc.skills.schema.SKILLS_DIR`).

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

    SAME REQUIREMENT EXTENDS to `sage_poc.config.CRISIS_CONFIG` (fix round 1, M1): the
    resolved `{{crisis_number}}` copy above is only cache-safe today because CRISIS_CONFIG
    derives PURELY from module-level literals (CRISIS_RESOURCES -> _primary_resource /
    _emergency_resource -> CRISIS_CONFIG; no env read, no clock, no reload -- pinned
    structurally by test_crisis_config_derives_only_from_module_level_literals in
    tests/test_skill_cache.py). If CRISIS_CONFIG ever gains a runtime-mutable source (an
    env var read at request time, a remote/CMS-fetched value, a reload trigger), that new
    write path must ALSO call `get_skill.cache_clear()` -- otherwise a crisis-copy change
    could land in the source of truth while every already-cached skill keeps serving the old
    resolved number until its mtime happens to change for an unrelated reason. This is the
    exact 800-HOPE-reversal failure class the invalidation point exists to close; do not
    let a future CRISIS_CONFIG source bypass it.
    """
    path = _schema.SKILLS_DIR / f"{skill_id}.json"
    mtime = path.stat().st_mtime
    return _get_skill_cached(skill_id, mtime, _schema.SKILLS_DIR)


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
