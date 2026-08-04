# Ticket: one-question-cap silently drops the diagnosis guard's own consent question when the category's framing_statement also asks one

**Filed:** 2026-07-31 · **Source:** psychoed Phase 3, Task 8 (F10 diagnosis-split fixture family),
first-run characterization while authoring `F10-002` — surfaced by fixture authoring, independently
confirmed by reviewer with a live repro, human-ruled
**Status:** open — fix requires its own branch and normal review (touches Node-8's MIND-SAFE
question-discipline, a cross-cutting safety surface, not psychoed-specific code); `F10-002` documents
and mechanically proves the observed behavior (`test_f10_formal_diagnosis_guard_question_clipped_by_
one_question_cap`) but does not assert against a "should" behavior, since no ruling exists yet on
which question should survive
**Type:** BUG
**Links:** `.superpowers/sdd/2026-07-30-psychoed-phase3-fixtures-plan/task-8-report.md`,
`tests/fixtures/psychoed/f10_diagnosis.jsonl` (`F10-002`'s `source` field),
`tests/test_psychoed_fixtures_ci.py::test_f10_formal_diagnosis_guard_question_clipped_by_one_
question_cap`, `tests/test_psychoed_f5_flow.py`'s own prior "ONE-QUESTION-CAP NOTE" (module
docstring) — same underlying mechanism, a DIFFERENT and more consequential instance

## The gap

`output_gate.py`'s `_limit_to_one_question` (~L326-339, Node 8, MIND-SAFE discipline) keeps only
the FIRST question sentence across an entire composed turn and silently drops every later one.
This is a pre-existing, general, cross-cutting discipline — NOT psychoed-specific, and already
known to reshape psychoed copy in at least one other instance
(`tests/test_psychoed_f5_flow.py`'s "ONE-QUESTION-CAP NOTE": `1f`'s own `check_in` text loses its
second question sentence on an ordinary menu-pick serve).

This ticket documents a DIFFERENT, more consequential instance: category `1f`'s own
`framing_statement` ends in a question ("What would be most useful to explore?"). When
`formal_diagnosis` fires on `1f` (`serve.py`'s branch: `framing_statement + diagnosis_guard_stage1`),
the combined text has TWO question sentences — `framing_statement`'s own, and
`diagnosis_guard_stage1`'s trailing "Want me to walk through that?", which is the SPECIFIC
consent-eliciting question the entire two-stage guard mechanism (design doc §5.5) exists to ask.
`_limit_to_one_question` keeps the FIRST (framing's) and drops the SECOND (the guard's own).

**Net effect:** the guard's statement content (the disclaimer, "I can't diagnose...", "What I can
do is explain what it generally involves...") reaches the user intact, but the question that is
supposed to elicit consent — the entire hinge of the two-stage guard design — is never actually
asked, whenever the category's own `framing_statement` also happens to end in a question.

## Verification (live repro, before filing)

Full-graph, `PSYCHOED_PATHWAYS_ENABLED=true`, category `1f`, turn `"do I have GAD"` (`1f-t3`):

```
response: "...What would be most useful to explore? I can't diagnose, that needs a proper
           evaluation from a doctor or mental health professional who can ask the right
           questions and rule other things out. What I can do is explain what it generally
           involves, so you've got a clearer picture going into that conversation if you
           decide to have it."
           [note: NO "Want me to walk through that?" — the guard's own question is gone]
path: [..., 'output_gate', 'question_discipline_applied']   # the discipline DID fire this turn
```

Confirmed mechanically (not just by inspection) via
`test_f10_formal_diagnosis_guard_question_clipped_by_one_question_cap`:
`"question_discipline_applied" in result["path"]` is `True`, and
`store.shared_script("diagnosis_guard_stage1") not in result["response"]` is `True` (the FULL
script, trailing question included, is genuinely absent — not merely unasserted).

**Scope note:** does NOT reproduce on `3c` — `3c`'s own `framing_statement` (the disclaimer-carrying
one used for `F10-001`) does not itself end in a question, so `diagnosis_guard_stage1`'s trailing
question is the ONLY question in that combined text and survives (confirmed: `F10-002` deliberately
avoids `3c` for OTHER reasons — see the sibling `resolver-pick-block-unconditional-false-mismatch.md`
ticket — but this specific one-question-cap interaction happens not to reproduce there either,
since `3c`'s framing_statement is question-free).

## The fix (not here)

**Not decided here** — several shapes are plausible and this needs review, not a drive-by call:
- Category-content fix: rephrase `1f`'s `framing_statement` to not end in a question when
  `formal_diagnosis`/`direct_diagnostic` rows exist for that category (a data/content change,
  clinician-editable, not a code change) — but this doesn't generalize to any FUTURE category with
  the same shape.
- Mechanism fix: `_limit_to_one_question` could special-case the guard-script's own trailing
  question as higher-priority-to-keep than a framing statement's incidental question (order-of-
  composition awareness) — but this is a cross-cutting Node-8 discipline serving many callers, not
  psychoed-specific, so any change needs to be proven safe for every OTHER caller too.
- Compose-time fix: `serve.py`'s `formal_diagnosis` branch could compose the guard's question as
  the DELIBERATE single surviving question by ensuring `framing_statement`'s own trailing question
  (if any) is stripped or reworded to a statement BEFORE the join, so the guard's question is
  always what's left standing.

Needs its own branch and normal review cycle — this touches a general safety discipline
(`output_gate.py`'s MIND-SAFE question cap), not an isolated psychoed code path.

**Definition of done includes a permanent regression case:** once a fix/ruling lands, a
`formal_diagnosis` serve on ANY category whose `framing_statement` also ends in a question must
still deliver the guard's own consent question to the user (a positive presence assertion, not
merely "no false mismatch") — author this as a sibling to `F10-002` once the fix shape is decided.

## RULING (2026-08-04, human — attached from the weave-vs-guard precedence ruling)

Same principle as `2026-07-31-weave-vs-guard-consent-precedence.md`, violated twice: a second
question sharing the turn with (or colliding into) a pending question makes the user's reply
ambiguous. Ruled fix is COMPOSITION: the guard's consent close is segmented into body/close
fields (data-schema segmentation, no wording change) and composed so exactly one question owns
the turn; the one-question cap then has nothing to clip. Because stage-1 is single-sourced
ratified copy, the segmentation rides the packet round for ratification before implementation.
See the full ruling text in the precedence ticket. The permanent regression case defined above
(consent question positively delivered on framing-question categories) stands as this ticket's
definition-of-done.
