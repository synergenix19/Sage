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
   only if that tier has zero matches -- a stopword-filtered token-SUBSET
   check (e.g. "the maintenance cycle one" resolving to menu_label "The
   anxiety maintenance cycle"). This is still exact token containment, no
   scoring/ranking/fuzzy matching: it is a boolean subset test over a small
   fixed stopword list, never a distance/embedding comparison.

   Post-review fix (2026-07-28, reviewer Medium finding): a tier that finds
   MORE THAN ONE matching block label no longer resolves by manifest array
   position. Array-position picking is exactly the "undeclared_first" pattern
   this module refuses at the cross-category collision tier (see point 1
   above) -- it had quietly reappeared one tier down, inside per-category
   block selection. E.g. "the anxiety one" against the 1f manifest
   subset-matches b1 ("What is anxiety?"), b3 ("Why anxiety causes physical
   symptoms"), and b4 ("The anxiety maintenance cycle") -- all three contain
   "anxiety" -- and the old code silently returned whichever came first in
   `manifest["blocks"]`. Now: if the substring tier itself yields >1 match,
   that is ALSO treated as ambiguous (verified empirically: no such case
   exists in the current 6 manifests' labels today, but nothing prevents a
   future/longer label set from producing one, so the rule is enforced
   unconditionally rather than assumed safe) and the tier fails closed to
   None; only when substring yields zero matches does the token-subset tier
   run, and if THAT yields zero-or-many, it also fails closed to None. In
   `resolve()`'s menu-context step, None from this tier falls through to the
   ordinary global trigger-table match (never silently answers from the
   wrong block). In `_pick_block` (answer-first delivery), None from this
   tier falls back to the category's first block via the pre-existing,
   documented default-block rule -- never via an ambiguous tier pick.
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


def _match_menu_label(labels: list[tuple[str, str]], target_norm: str) -> str | None:
    """Pick the single block_id whose menu_label matches target_norm.

    Exact-token containment only, in two tiers, run in strict priority order:
      1. substring containment, either direction
      2. stopword-filtered word-set subset (target's content words subset of
         label's content words)
    Whichever tier fires first is authoritative; the other tier is not
    consulted. Within a tier, more than one matching label is ambiguous and
    fails closed to None -- it is NEVER resolved by manifest array position
    (that is the undeclared-first pattern this module refuses elsewhere; see
    module docstring point 1 and the 2026-07-28 fix note). No scoring, no
    fuzzy distance, no similarity: every check here is boolean containment.
    """
    if not target_norm:
        return None

    substring_hits = [bid for bid, label in labels
                       if label and (label in target_norm or target_norm in label)]
    if len(substring_hits) == 1:
        return substring_hits[0]
    if len(substring_hits) > 1:
        return None  # ambiguous even at the substring tier -- fail closed

    target_words = set(target_norm.split()) - _STOPWORDS
    if not target_words:
        return None
    subset_hits = [bid for bid, label in labels
                   if target_words <= (set(label.split()) - _STOPWORDS)]
    if len(subset_hits) == 1:
        return subset_hits[0]
    return None  # zero or ambiguous -- fail closed


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


def _labels_for(category: str) -> list[tuple[str, str]]:
    man = store.manifest(category)
    return [(bid, _norm(store.get_block(bid)["psychoed"]["menu_label"])) for bid in man["blocks"]]


def _pick_block(category: str, phrase_norm: str) -> str | None:
    man = store.manifest(category)
    if man["delivery_shape"] != "answer_first":
        return None
    match = _match_menu_label(_labels_for(category), phrase_norm)
    if match is not None:
        return match
    return man["blocks"][0]  # documented default-block rule, not an ambiguous tier pick


def resolve(message_en: str, *, active_category: str | None, grief_context: bool,
            enabled_categories: frozenset[str]) -> dict | None:
    if not enabled_categories:
        return None
    norm = _norm(message_en)
    if not norm:
        return None

    if active_category and active_category in enabled_categories:
        menu_match = _match_menu_label(_labels_for(active_category), norm)
        if menu_match is not None:
            return {"category": active_category, "row_id": "menu_pick", "route": "standard",
                     "framing": None, "block_id": menu_match, "collision_path": None, "menu_pick": True}
        # ambiguous or no menu-label match -> fall through to the global trigger tables

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
