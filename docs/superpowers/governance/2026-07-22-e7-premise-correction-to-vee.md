# CORRECTION to Vee — your E7 ratification was obtained on a false premise (2026-07-22)

**Unprompted, same day. No new ask attached.** This follows the #324 precedent (`2026-07-07-v1-comparator-correction.md`):
when a signature was obtained on incorrect information, the premise is corrected in front of the clinician,
the fact is stated plainly, and we stop. You will rule on the real mechanism when one exists.

## What you were told, and what was actually true
You ticked **E7 go-live** on the packet's claim that the mechanism was **built, recall-gated at 100/100, and
would close the demonstrated iatrogenic coercive-control gap.** Two of those three were wrong in the way that
mattered:

1. **The recall figure was not a recall figure.** The "100/100" was measured on a fixture
   (`ipv_e7_recall.json`) whose utterances **are the 19 verbatim §6a sentences the matcher substring-matches.**
   A detector scored against fixtures identical to its own patterns is a **tautology, not a measurement** —
   trivially perfect on the fixture, ~zero on real language.
2. **The mechanism does not close the gap.** E7 detects by exact substring over those 19 full sentences (e.g.
   `"They control the money so I can't really say no"`). Real users paraphrase ("he controls all our money"),
   which contains none of them. So E7 fires on ~nothing a real user types.

## What we did, and what it showed (measured, on prod)
E7 was **enabled** (`SAGE_IPV_PREEMPTION=true`, health-verified 5/5 uniform), then probed behaviorally on the
target cases. **It changed nothing.** The "controlling boyfriend" discloser was still coached the DESC
assertiveness method verbatim; the money/phone/isolation discloser still got generic empathy with no flag.
E7 was **reverted** the same session (`=false`, baseline restored). **No user was ever exposed to a
regression** — with E7 on or off, behavior on real language is byte-identical.

## The four facts, stated plainly
- E7 was enabled; **it changed nothing on the target cases; it is back off.**
- The **§6a/§6b guard you authorized closing remains open in production.** What catches abuse today is CF-005
  `domestic_situation`, which catches explicit physical-abuse phrasing and **misses coercive control** — the
  presentation class §6a's own recognition table centers on.
- **Your ratification is not spent.** It stands available for a mechanism that actually delivers the guard.
  You are not being asked to re-decide anything now.
- When a real mechanism exists (a semantic tier, or clinician-authored paraphrase patterns), it returns to you
  with a **naturalistic-disclosure** recall number — never a verbatim-fixture one.

## I own my part in this
I framed the escalation on "recall gate 100/100, one signature away" and pressed for speed — including in the
sheet I wrote for you. **I took a recall number at face value without asking what corpus it was measured
against** — the exact question this project has asked correctly about every other number for weeks (the lost
324-case corpus, the synthetic-fixture harness, the branch-trapped matrix). A recall figure measured on
fixtures identical to the detector's own patterns is not a recall figure, and I should have caught it in the
packet before it reached you. The correction is mine to carry, not yours to have chased.

## Records
E7 post-enable outcome + root cause (`2026-07-22-e7-ipv-live-gap-escalation.md`, ⛔ POST-ENABLE OUTCOME
section); precedent (`2026-07-07-v1-comparator-correction.md`); the earned rule
(`ARCHITECTURE_BOUNDARIES.md` — recall fixtures must be independent of the detector's pattern source).
