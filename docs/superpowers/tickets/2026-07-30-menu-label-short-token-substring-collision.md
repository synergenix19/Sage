# Ticket: bare "no" collides with a menu_label substring, re-serving a block instead of the deferred PSY-WEAVE-1 menu

**Filed:** 2026-07-30 · **Source:** psychoed Phase 3, Task 6 (F4 PSY-WEAVE-1 fixture family), first-run
characterization of `F4-002` — surfaced by fixture authoring, confirmed by reviewer, human-ruled
**Status:** open — fix requires its OWN branch and normal review (safety-adjacent surface); F4-002
disposed as strict-xfail pending this ticket, not fixed here · **Type:** mechanism gap
(`sage_poc/psychoed/resolver.py`'s menu-context matching tier) · **Not a crisis-detection miss**
(escalation/fail-closed direction is unaffected — see the verification chain below)
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/task-6-report.md`,
`tests/fixtures/psychoed/f4_weave.jsonl` (`F4-002`), `docs/superpowers/specs/
2026-07-23-psychoeducation-pathways-design.md` §6.1 (PSY-WEAVE-1)

## The gap

A weave-pending reply of bare **"no"** (a genuine PSY-WEAVE-1 clear-negative, per
`data/psychoed/weave/psy_weave_1.en.json`'s `clear_negative_patterns[0]`) is supposed to clear the
safety weave and produce the deferred menu-after-weave continuation
(`skill_match_method == "psychoed_menu_after_weave"`). Instead, for category `3c`, it re-serves
block `3c-b6` directly (`skill_match_method == "psychoed_resolver"`,
`psychoed_matched_row_id == "menu_pick"`) on 8 of the 9 `INTENT_SWEEP` labels (all but `"crisis"`,
which bypasses the mechanism entirely via crisis-intent supremacy and is unaffected).

**Mechanism:** `sage_poc/nodes/skill_select.py`'s psychoed block runs the weave evaluation (order
item 1) and, on a clear-negative verdict, sets `weave_cleared = True` but does **not** return —
it falls through to order item 2, `psy_resolver.resolve(...)`, unconditionally, on the same turn.
`resolver.py`'s active-category branch (`resolver.py:189-193`) calls `_match_menu_label` against
every block's `menu_label` in the active category. `_match_menu_label`'s substring-containment
tier (`resolver.py:93-96`: `label in target_norm or target_norm in label`, tier 1, no
word-boundary requirement) matches the normalized reply `"no"` against category `3c` block
`3c-b6`'s `menu_label`, `"Why it can feel like 'no reason'"` — because the literal string `"no"`
is a substring of `"no reason"`. That hit wins before the `weave_cleared` fallthrough branch
(`skill_select.py:764-767`) is ever reached, so the deferred-menu branch is unreachable on this
turn.

## The class, named

**Short-token substring containment in the resolver's menu-context tier.** Any menu_label that
happens to contain a clear-negative pattern (or, more generally, any short reply string the
weave-clearing turn is likely to receive) as a literal substring is a live collision candidate.
`_match_menu_label`'s tier-1 check has no minimum-token-length guard and no word-boundary
requirement — it was designed for the ordinary "menu pick" use case (user names a topic off an
offered menu), not for the co-occurring case of "user is also answering a just-asked safety
question with a short reply."

## Verification chain (pinned verbatim — each claim traced independently before filing)

**(a) Escalation is intact — the fail-closed direction is unaffected.**
`sage_poc.psychoed.weave.evaluate("no")` was called directly and returns `"proceed"`
(`is_clear_negative=True`: `"no"` fullmatches `clear_negative_patterns[0]`). PSY-WEAVE-1
evaluates the reply and correctly determines it is a clear negative BEFORE `skill_select_node`
ever consults the resolver (order item 1 runs first, per `skill_select.py`'s own ordering
comment and `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` §2.1 step 1).
The collision happens entirely on the "clear negative confirmed, what happens next" side of the
branch — it can never cause a genuine crisis reply to be missed, and it can never cause a
non-clear-negative reply to be treated as clear. Verified by tracing `skill_select_node`'s order
(items 1→2, `skill_select.py:710-767`) plus a live `run_fixture` repro across the full
`INTENT_SWEEP` (`tests/test_psychoed_fixtures_ci.py::run_fixture`, `F4-002`'s 8 non-crisis
sweep cases): every one lands in the resolver-serve branch, none in the escalation branch, and
the `crisis`-label sweep case (which never reaches `skill_select` at all) still escalates
normally.

**(b) No weave re-arm on the phantom serve — no double-screening.**
The phantom resolver hit for `3c-b6` goes through the SAME `weave_due` computation as any other
serve: `weave_due = (framing == "personal" and store_manifest_weave(hit["category"]) and not
state.get("psychoed_weave_fired"))` (`skill_select.py:741-743`). `psychoed_weave_fired` was
already set `True` on turn 1 (the original `3c-t3` serve that first armed the weave) and survives
turn-to-turn via `_PSYCHOED_CARRY` (`tests/test_psychoed_graph.py:26-31`, includes
`psychoed_weave_fired`) — the driver's `_carry` helper threads the same real, checkpoint-persisted
`SageState` channel. So `not state.get("psychoed_weave_fired")` is `False` on this turn
regardless of the phantom hit's framing, and `weave_due` computes to `False` — confirmed directly
in the observed `psychoed_serve` payload from the `F4-002` repro:
`{'category': '3c', 'block_id': '3c-b6', ..., 'weave_due': False, ...}`. The user is not asked
the safety-weave question a second time on the same reply.

**(c) Sole-corpus collision (CORPUS-DEPENDENT — must be re-verified if the clear-negative
patterns or any menu label ever changes).**
A full scan across all 6 psychoed categories' manifests (`1f`, `3c`, `4b`, `6d`, `7c`, `s2c` — 40
blocks total, every block's `menu_label`) against every literal form of every
`clear_negative_patterns` entry (both the base and maximal literal expansion of the one pattern
with a regex optional group, `"no i haven't( why)?"`) found **exactly one collision**: bare `"no"`
against `3c-b6`'s `"Why it can feel like 'no reason'"`. No other clear-negative phrase — including
the multi-word natural phrasings ("no, nothing like that", "No, alhamdulillah", "no I haven't,
why?", "no thank god") — collides with any of the other 39 labels. Script and output:

```
total blocks scanned: 40
collisions found: 1
  ('3c', '3c-b6', 'Why it can feel like "no reason"', 'no')
```

This claim is a snapshot of the current corpus, not a structural guarantee — it must be
re-verified (the same scan re-run) any time `clear_negative_patterns` in
`data/psychoed/weave/psy_weave_1.en.json` changes, or any block's `menu_label` changes, or a new
category/block is added to any manifest.

## Clinical note (FYI to Lane 3)

The interim (unfixed) behavior fires on the turn **immediately after a suicide-screening
question** (the PSY-WEAVE-1 safety-weave script asked on the original `3c` serve): a user who
replies bare "no" gets served the "no reason" depression psychoeducation block instead of the
expected menu re-offer. This is clinically awkward — it can read as a non-sequitur immediately
after a safety check — but it is **not unsafe**: no escalation is missed or wrongly suppressed
(see (a) above), and the content served is real, ratified `3c` block copy, not an error state or
off-topic material. Flagged to Lane 3 as FYI, not as a blocking safety item.

## The fix (not here)

**Fix shape:** a word-boundary and/or minimum-token-length guard on `_match_menu_label`'s tier-1
substring-containment check (`resolver.py:93-96`) — e.g. require the shorter side to be at least
N tokens/characters, or require the match to land on a token boundary, so a single short word
like `"no"` cannot satisfy containment against an unrelated multi-word label purely because the
word happens to appear inside it. Needs its own branch and normal review cycle — this is a
safety-adjacent surface (the resolver that gates PSY-WEAVE-1 continuations), never a drive-by fix
on a fixtures branch.

**Definition of done includes the fixture re-pin.** When the fix lands:
1. `F4-002`'s strict xfail (`tests/fixtures/psychoed/f4_weave.jsonl`, `pytest.mark.xfail(strict=True)`
   gated on this ticket path) turns **xpass**, which fails CI loudly (`strict=True` on an
   XFAIL-marked case that now passes is itself a failure) — forcing the re-pin rather than letting
   the fix land silently uncelebrated.
2. Re-pin `F4-002` to assert the SPEC-INTENDED outcome directly (menu-after-weave:
   `skill_match_method == "psychoed_menu_after_weave"`, `psychoed_menu_offered: true`,
   `psychoed_weave_pending: false`, audit `psychoed_weave_state: "fired"`), removing the xfail
   marker.
3. Keep the row (or add a sibling) as a **permanent regression case**: bare "no" against category
   `3c` must never again produce a bare block serve (`skill_match_method == "psychoed_resolver"`)
   — this is the exact shape that must never silently regress once fixed.
