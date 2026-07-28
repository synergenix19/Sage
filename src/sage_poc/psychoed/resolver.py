"""Node-4 psychoed trigger resolver (spec §2.1/§5.1/§5.2). Deterministic only:
normalized exact-phrase matching, menu-context scoping, collision-table winners.
NEVER similarity/embedding logic, under any circumstances.

Block mapping v1 (answer-first delivery_shape only): matched phrase -> the
category's first block whose menu_label is contained in (or contains) the
phrase, else the category's first block (fixture-pinned in Phase 3 F1).

Deviations from the Task-6 brief's starting implementation (documented per
brief rule (d) -- internals iterated, public signature/shape/collision-table
sourcing unchanged):

1. Subsumption resolution is scoped to the collision table, not a corpus-wide
   substring sweep. The starting implementation's fallback walked every
   registered phrase across every enabled category looking for a containment
   hit, picked whichever it found first in dict-iteration order, and inside
   the tie-break it read `e["phrase"]` off `subsumption_collisions` entries --
   a KeyError, since those entries carry `short_phrase`/`long_phrase`, not
   `phrase` (see data/psychoed/collisions/collision_table.json). `_subsumption_winner`
   here instead checks containment ONLY against the `long_phrase` values
   declared in `subsumption_collisions`, and reads the winner ONLY from that
   entry's `resolution.winner` field. This keeps "collision winners come only
   from the collision table" true for the fallback path too, and removes the
   only path that could non-deterministically pick a category based on dict
   insertion order.
2. The flat `collisions` tie-break now distinguishes `default_winner` from
   `interim_default_winner` in the returned `collision_path` (the starting
   code labelled both "default_winner"), since the collision table marks the
   interim case `"safe_before_disambiguation": false` / `"pending": "clinician"`
   -- worth keeping auditable which kind of default fired.
3. Menu-context scoping (and answer-first block picking) matches a block's
   menu_label against the message using substring containment first, and --
   only if that misses -- a stopword-filtered token-SUBSET check (e.g. "the
   maintenance cycle one" resolving to menu_label "The anxiety maintenance
   cycle"). This is still exact token containment, no scoring/ranking/fuzzy
   matching: it is a boolean subset test over a small fixed stopword list,
   never a distance/embedding comparison.
"""
from __future__ import annotations
import re
from sage_poc.psychoed import store

_STOPWORDS = frozenset({"the", "a", "an", "one", "this", "that", "it", "of", "to"})

# Containment fallback only ever looks at these collision-table-declared long
# forms -- never a scan of the general trigger corpus.
_MIN_SUBSUMPTION_LEN = 12


def _norm(t: str) -> str:
    return re.sub(r"[^\w\s']", "", t.lower()).strip()


def _label_hits(label_norm: str, target_norm: str) -> bool:
    """Exact-token containment: substring either direction, else a
    stopword-filtered word-set subset. No scoring, no fuzzy distance."""
    if not label_norm or not target_norm:
        return False
    if label_norm in target_norm or target_norm in label_norm:
        return True
    label_words = set(label_norm.split()) - _STOPWORDS
    target_words = set(target_norm.split()) - _STOPWORDS
    return bool(target_words) and target_words <= label_words


def _phrase_index(enabled: frozenset[str]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for row in store.trigger_rows():
        if row["category"] not in enabled:
            continue
        for ph in row["phrases"]:
            idx.setdefault(_norm(ph), []).append(row)
    return idx


def _row_for(rows: list[dict], category: str) -> dict | None:
    return next((r for r in rows if r["category"] == category), None)


def _flat_collision_winner(norm: str, rows: list[dict], grief_context: bool) -> tuple[dict, str] | None:
    """Cross-category exact-phrase ties, resolved ONLY via collision_table.json's
    `collisions` list -- never similarity, never a hardcoded category."""
    for e in store.collision_entries().get("collisions", []):
        if _norm(e["phrase"]) != norm:
            continue
        res = e["resolution"]
        if grief_context and res.get("context_winner"):
            win, path = res["context_winner"], "context_winner"
        elif res.get("default_winner"):
            win, path = res["default_winner"], "default_winner"
        else:
            win, path = res["interim_default_winner"], "interim_default_winner"
        row = _row_for(rows, win)
        if row is not None:
            return row, path
    return None


def _subsumption_winner(norm: str, enabled: frozenset[str]) -> tuple[dict, str] | None:
    """Declared long-form/short-form subsumption pairs, resolved ONLY via
    collision_table.json's `subsumption_collisions` list. Only reachable when
    the message contains the declared long form as a substring but isn't an
    exact match on any registered phrase (an exact match already resolves via
    the phrase index before this is ever called)."""
    for e in store.collision_entries().get("subsumption_collisions", []):
        long_norm = _norm(e["long_phrase"])
        if len(long_norm) < _MIN_SUBSUMPTION_LEN or long_norm not in norm:
            continue
        winner = e["resolution"]["winner"]
        if winner not in enabled:
            continue
        row = next(
            (r for r in store.trigger_rows()
             if r["category"] == winner and any(_norm(p) == long_norm for p in r["phrases"])),
            None,
        )
        if row is not None:
            return row, "subsumption_winner"
    return None


def _pick_block(category: str, phrase_norm: str) -> str | None:
    man = store.manifest(category)
    if man["delivery_shape"] != "answer_first":
        return None
    for bid in man["blocks"]:
        label = _norm(store.get_block(bid)["psychoed"]["menu_label"])
        if _label_hits(label, phrase_norm):
            return bid
    return man["blocks"][0]


def resolve(message_en: str, *, active_category: str | None, grief_context: bool,
            enabled_categories: frozenset[str]) -> dict | None:
    if not enabled_categories:
        return None
    norm = _norm(message_en)
    if not norm:
        return None

    if active_category and active_category in enabled_categories:
        for bid in store.manifest(active_category)["blocks"]:
            label = _norm(store.get_block(bid)["psychoed"]["menu_label"])
            if _label_hits(label, norm):
                return {"category": active_category, "row_id": "menu_pick", "route": "standard",
                        "framing": None, "block_id": bid, "collision_path": None, "menu_pick": True}

    idx = _phrase_index(enabled_categories)
    rows = idx.get(norm)
    path: str | None = None
    if rows:
        cats = {r["category"] for r in rows}
        if len(cats) > 1:
            hit = _flat_collision_winner(norm, rows, grief_context)
            if hit is None:
                return None  # audit signal: undeclared cross-category exact tie
            row, path = hit
        else:
            row = rows[0]
    else:
        hit = _subsumption_winner(norm, enabled_categories)
        if hit is None:
            return None
        row, path = hit

    return {
        "category": row["category"],
        "row_id": row["row_id"],
        "route": row["route"],
        "framing": row.get("framing"),
        "block_id": _pick_block(row["category"], norm),
        "collision_path": path,
        "menu_pick": False,
    }
