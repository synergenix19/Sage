# Ticket (design ruling needed, not a bug report): PSY-WEAVE-1 precedence makes the diagnosis guard's push-further/consent turn structurally unreachable on weave-enabled categories

**Filed:** 2026-07-31 · **Source:** psychoed Phase 3, Task 8 (F10 diagnosis-split fixture family),
first-run characterization while authoring `F10-002`/`F10-003`/`F10-004` — surfaced by fixture
authoring, independently confirmed by reviewer with a live repro, human-ruled
**Status:** open — **this ticket asks a clinical/design QUESTION, it does not report a defect.**
The current behavior may well be the CORRECT fail-closed precedence (crisis screening always
outranks a content-consent continuation) — that determination belongs to clinical sign-off, not
engineering. No fixture is authored against a "should" behavior here; `F10-002`/`F10-003`/`F10-004`
all deliberately use category `1f` (no weave) specifically so they test the diagnosis-guard
mechanism without this interaction confounding the result.
**Type:** DESIGN RULING NEEDED
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/task-8-report.md`,
`tests/fixtures/psychoed/f10_diagnosis.jsonl` (`F10-001`'s `source` field notes the co-firing;
`F10-002`'s `source` field notes the category choice made to avoid this), `docs/superpowers/specs/
2026-07-23-psychoeducation-pathways-design.md` §5.5 (diagnosis guard) and §6.1 (PSY-WEAVE-1)

## The observed interaction

`skill_select.py` ~L710-717 evaluates PSY-WEAVE-1 (order item 1) BEFORE resolver matching (order
item 2) on any turn where `psychoed_weave_pending` is `true`:

```python
if state.get("psychoed_weave_pending"):
    verdict = psy_weave.evaluate(state.get("message_en") or "")
    if verdict == "crisis":
        return {"psychoed_weave_pending": False, "psychoed_weave_escalation": True,
                "skill_match_method": "psychoed_weave_escalation", ...}
    weave_cleared = True   # clear negative: proceed
```

For a category that both weaves (`safety_weave: true` in its manifest) AND carries a personally
framed diagnosis trigger row (both `direct_diagnostic` and `formal_diagnosis` routes are personal
framing by design — see `data/psychoed/trigger_tables/en/3c.json`'s `3c-t1`/`3c-t5`), the
diagnosis-triggering turn ITSELF sets `psychoed_weave_pending: true` (personal framing +
`safety_weave: true` + fresh `weave_fired: false` → `weave_due: true`, `serve.py`'s trailing
`if payload.get("weave_due")` branch). So the VERY NEXT reply — whatever it is, including a
push-further phrase or a plain "yes" consenting to the guard's own "Want me to walk through that?"
question — is evaluated by PSY-WEAVE-1 first, not treated as an answer to the diagnosis guard at
all.

PSY-WEAVE-1's own matching semantics (design doc §6.1): only a reply matching the
`clear_negative_patterns` allowlist proceeds; everything else — including "kind of", deflection,
AND a plain affirmative like "yes" — fails closed to `crisis`. Neither "yes" nor an ordinary
push-further phrase is a clear negative. **Result: the diagnosis guard's own continuation turn
escalates to crisis instead of ever reaching the guard's push-further/consent logic.**

## Verification (live repro, before filing)

Full-graph, `PSYCHOED_PATHWAYS_ENABLED=true`, category `3c`:

```
turn 1 "do I have depression" (3c-t5, formal_diagnosis): psychoed_weave_pending=True
turn 2 "yes":
  gate_path='crisis', weave_pending=False (consumed by the escalation),
  skill_match_method='psychoed_weave_escalation', active_category=None (pathway cleared)
  response: "I'm really concerned about what you've shared. Please reach out for support now..."
turn 2 "please just tell me, I really need to know": IDENTICAL shape — escalates to crisis
```

Both a genuine consent reply and a genuine push-further reply escalate identically. Confirmed
this is `3c`-specific (or more precisely, any weave-enabled + personally-framed-diagnosis category
— `3c` is the only category currently combining both, per a grep of every trigger table's `route`
column against every manifest's `safety_weave` field): category `1f` (`safety_weave: false`) does
NOT reproduce this — the same "yes"/push-further replies reach `skill_select`'s resolver/fallthrough
normally.

## The question for clinical/design ruling

Is this the CORRECT precedence? Two readings, both defensible, neither decided here:

1. **Correct fail-closed precedence (no fix needed).** A reply immediately following a
   personally-framed, high-risk-adjacent question (design doc §6.1 explicitly names diagnosis-
   seeking as high-risk phrasing warranting the weave) SHOULD be screened by the safety weave
   before anything else, full stop — including before a content-consent question the SAME turn
   also implicitly raised. Under this reading, the diagnosis guard's push-further/consent flow is
   simply UNREACHABLE BY DESIGN on any category that also weaves, and `formal_diagnosis`/
   `direct_diagnostic` should never be paired with `safety_weave: true` in the SAME manifest without
   an explicit clinical decision about which of the two safety-adjacent flows takes the next turn.
2. **Unintended collision, needs a design fix.** The guard's own consent question ("Want me to walk
   through that?") is a DIFFERENT kind of question than the weave's own safety-check question, and
   the two should not silently collapse into "whichever fires first wins" — e.g. the guard's consent
   state should be tracked independently and consulted, or the weave and the guard should be
   sequenced explicitly (weave first are already how it works; the design gap is that there is no
   SECOND chance for the guard's own question once the weave clears).

## Not filed as a fix

No code change is proposed or requested by this ticket. If reading 1 above is ratified, this ticket
closes as "confirmed, working as intended, no fixture needed" (and design doc §5.5 should be
annotated to note the interaction explicitly, since it currently reads as if the guard's
push-further/consent flow is universally reachable). If reading 2 is ratified, it becomes a design
task with its own scope, likely coupled to `2026-07-31-diagnosis-guard-consent-to-serve-unbuilt.md`
(since a fix to one may need to account for the other).

## RULING (2026-08-04, human — design ruling requested above, now made)

**Reading 1 ratified, with a composition corollary.** The ruled weave turn-boundary is
"weave question, full stop": nothing shares the turn with a pending safety question — this
is exactly why the menu defers. The current precedence is CORRECT and unchanged; PSY-WEAVE-1
semantics change not at all.

The defect this ticket observed is not evaluation but composition: the guard's consent close
created a two-question turn with the weave, making the user's next reply ambiguous — and an
ambiguous reply to a suicide-screening question fail-closes to crisis by ruled design. So a
"yes" meaning "yes, walk me through" crisis-routes: fail-closed in the right direction, but
wrong-question-attributed.

**Fix shape (composition, not evaluation):** the consent close defers behind the weave exactly
as the menu does. Weave-due `formal_diagnosis` turns emit framing + guard body + weave question
only; on clear-negative, the continuation re-offers the walk-through.

**Implementation note:** stage-1 is single-sourced ratified copy, so deferring its close means
segmenting the script into body/close fields — a data-schema segmentation with NO wording
change, but it touches signed clinical data, so the split RIDES THE PACKET ROUND for
ratification before any branch implements it.

**Closure:** this ticket closes as "current precedence is correct; composition must stop
creating two-question turns." The same ruling resolves
`2026-07-31-framing-question-clips-guard-consent-question.md` under the same segmentation
(same principle, violated twice). Implemented in neither this plan nor a drive-by — own
branch, normal review, after packet ratification of the copy split.
