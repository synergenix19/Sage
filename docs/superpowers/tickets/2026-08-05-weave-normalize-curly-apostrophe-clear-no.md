# Ticket: PSY-WEAVE-1's `_normalize` deletes (not spaces) curly apostrophes, silently merging contractions and missing genuine clear-no replies

**Filed:** 2026-08-05 · **Source:** psychoed Phase 3, final whole-branch review, Important 3 —
first characterized 2026-07-30 (Task 3 re-review, informational parked finding, progress.md:32),
live-verified at flip tier 2026-08-05 via `F4-006`
**Status:** open — fix requires its OWN branch and normal review (safety-adjacent surface: it
changes what counts as a clear-no on a PSY-WEAVE-1 safety reply); parked as a characterization-
only row, not fixed here · **Type:** bug (`sage_poc/psychoed/weave.py::_normalize`) · **Not a
crisis-detection miss** (failure direction is fail-closed/over-escalation, not a missed escalation
— see below)
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/progress.md:32` (the parked
production finding this ticket formalizes), `tests/fixtures/psychoed/f4_weave.jsonl` (`F4-006`'s
`source` field — the characterization row and regression pin), `docs/superpowers/specs/
2026-07-23-psychoeducation-pathways-design.md` §6.1 (PSY-WEAVE-1), `docs/2026-08-05-psychoed-
phase3-closeout-145c4e43.md` (close-out ticket list, this entry)

## The gap

`src/sage_poc/psychoed/weave.py::_normalize`:

```python
def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s']", "", text.lower()).strip()
```

`\w` does not include U+2019 (RIGHT SINGLE QUOTATION MARK, the "curly"/"smart" apostrophe — the
default on iOS/macOS keyboards and in Word/Docs autocorrect), and the character class's only
apostrophe literal is the straight ASCII `'` (U+0027). The regex **deletes** any character outside
`[\w\s']` — it does not replace it with a space. So:

- straight apostrophe: `"can't"` → `"can't"` (preserved, matches `\w\s'`)
- curly apostrophe: `"can’t"` → `"cant"` (U+2019 deleted outright, the two word-halves silently
  fuse into one token)

On a PSY-WEAVE-1 reply turn, `is_clear_negative` requires a full-match against
`clear_negative_patterns` (e.g. `"no i haven't( why)?"`) after normalization. A genuine clear-no
reply typed with a curly apostrophe — `"no I haven’t, why?"`, the exact spelling a user typing on
a default iOS/macOS keyboard produces — normalizes to `"no i havent why"`, which matches neither
`clear_negative_patterns[0]` (`"no"`, exact fullmatch only) nor the contraction pattern (which
requires the literal straight apostrophe). `evaluate()` falls through to `"crisis"`.

## Failure direction and clinical framing

**Fail-closed (over-escalation), not a missed escalation.** The gap can only cause a genuine
clear-no to be treated as ambiguous and routed toward crisis protocol — it can never cause a real
crisis signal to be missed or a non-clear-negative reply to be treated as clear (the normalizer
only ever *loses* information via deletion; it never manufactures a false match). So this is safe
in the sense the project's fail-closed standard requires, but it is real user-facing harm: the
failure lands on the turn **immediately after a suicide-screening question** (the PSY-WEAVE-1
weave script), so a distressed user who genuinely answers "no" gets routed to crisis-escalation
copy instead of the menu they were owed — wrong-question-attributed UX at the worst possible
moment in the conversation, even though the direction is the safe one.

## Discovery and verification timeline

- **2026-07-30 (Task 3 re-review, informational):** first characterized as a parked production
  finding, out of this plan's scope (`progress.md:32`). Same bug class as the fixture-guard's own
  `_normalize_phrase` hole in `tests/test_psychoed_fixtures_ci.py`, independently found and fixed
  the same day in commit `351c552c` ("harden phrase normalization against unicode quote
  variants") — that fix protects the **corpus-authoring guard** (trigger-phrase reuse detection);
  it does not touch `weave.py`, which is separate, unmodified `src/` code (no mechanism changes
  in this plan).
- **2026-08-05 (Task 6, `F4-006`, live-verified):** `F4-006` pins the as-built `escalate_crisis`
  outcome directly — confirmed via `sage_poc.psychoed.weave._normalize`/`is_clear_negative`/
  `evaluate` in isolation (`_normalize("no I haven’t, why?")` → `"no i havent why"`,
  `is_clear_negative` → `False`, `evaluate` → `"crisis"`), and via a full-graph `run_fixture`
  reproduction across the entire `INTENT_SWEEP`: escalates to crisis on every swept intent label,
  including the `"crisis"` label itself (via ordinary crisis-intent supremacy, not this bug).
- **2026-08-05 (final whole-branch review, Important 3):** flagged that the finding survived only
  as a ledger line plus a fixture comment, absent from the close-out doc and with no ticket filed
  — this ticket and the close-out cross-reference close that gap.

`F4-006` is the mechanism witness at **both** tiers: it is a CI-tier fixture (pins the observed
outcome on every swept intent, `strict=True` xfail-free — it pins what master actually does, not
the spec-intended outcome), and per `docs/2026-08-05-psychoed-phase3-closeout-145c4e43.md` §7 the
F4 family reproduces its xfail (`F4-002`) at prod parity in the same flip-tier run that exercised
`F4-006`'s category/turn shape — the bug is characterized live, not merely by unit-level code
inspection.

## Fix shape (not implemented here)

Normalize quote variants to the straight ASCII apostrophe **before** the strip, mirroring the
approach `tests/test_psychoed_fixtures_ci.py::_normalize_phrase` already uses for the same class
of bug (`_QUOTE_VARIANTS`, a `str.maketrans` table covering U+2018/U+2019/U+201B/U+02BC/U+02BB/
acute-accent/backtick, applied after `unicodedata.normalize("NFKC", ...)` and before the
alnum-strip regex). The shape for `weave.py::_normalize` is the same translate-then-strip
sequence; it should not import the test module's table directly (test code must not become a
runtime dependency), but the mapping and ordering (NFKC first, then quote-variant translation,
then the character-class strip) should mirror it exactly so the two normalizers do not drift
apart on which quote variants are covered.

This is a safety-adjacent surface — it changes what counts as a clear-no on a PSY-WEAVE-1 safety
reply — so it needs its own branch and normal (not drive-by) review, per this project's standing
"safety-adjacent = never a drive-by fix" convention (see the sibling `2026-07-30-menu-label-
short-token-substring-collision.md` and `2026-07-31-weave-vs-guard-consent-precedence.md`
tickets, both disposed the same way).

## Definition of done

1. **`F4-006` re-pins.** Today it pins the as-built `escalate_crisis` outcome (`expect.disposition:
   "escalate_crisis"`, audit `psychoed_weave_state: "escalated"`) — a characterization row, not an
   endorsement, per its own `source` field. Once the fix lands, `F4-006` must re-pin to the
   spec-intended outcome: `skill_match_method == "psychoed_menu_after_weave"`,
   `psychoed_menu_offered: true`, `psychoed_weave_pending: false`, audit
   `psychoed_weave_state: "fired"` — matching `F4-005`'s straight-apostrophe companion row shape
   exactly (`F4-005` is the identical utterance spelled with a straight apostrophe; the two rows
   should converge on the same outcome once fixed). If `F4-006` is authored under a strict-xfail
   marker gated on this ticket's path (the same pattern used for `F4-002`), the strict pin forces
   the re-pin the moment the fix lands: an XPASS on a `strict=True` xfail fails CI loudly, so the
   fix cannot land silently uncelebrated.
2. **Permanent regression case.** Keep `F4-006` (or add a sibling row) as a standing regression
   case asserting the curly-apostrophe clear-no spelling produces the SAME menu-after-weave
   outcome as its straight-apostrophe counterpart (`F4-005`) — this is the exact shape that must
   never silently regress once fixed.
3. Re-verify the fix does not change behavior on any of the corpus's other clear-negative
   phrasings (natural multi-word forms, "no thank god", "No, alhamdulillah", etc.) — same
   verification discipline as `351c552c`'s regression cases for the fixture-authoring guard.

## Cross-references

- Parked ledger line: `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/progress.md:32`
  ("PARKED FINDING (production, out of scope...)").
- `F4-006`'s `source` field (`tests/fixtures/psychoed/f4_weave.jsonl`) carries the full mechanism
  trace this ticket summarizes (verbatim `_normalize` output, `is_clear_negative`/`evaluate`
  results, full-sweep confirmation).
- Same bug class, different call site, already fixed: commit `351c552c` (`tests/
  test_psychoed_fixtures_ci.py::_normalize_phrase`'s `_QUOTE_VARIANTS` table).
