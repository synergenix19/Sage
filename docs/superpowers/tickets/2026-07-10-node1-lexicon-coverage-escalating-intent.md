# Ticket: Node-1 lexicon coverage for escalating-intent phrasing (adjacent to #219 Group A)

**Filed:** 2026-07-10 · **Status:** open — needs clinician ruling · **Type:** crisis-detection coverage · **Links:** #219 (harm-to-others Group A), `tests/test_phase2_t3_crisis_supremacy.py`

## The datum (empirical, surfaced by T3's AC-CRISIS-SUPREMACY work)
While building the T3 crisis-supremacy test, the pre-registered overlapping fixture —
harm-intrusive phrasing escalating into intent/command, e.g. *"intrusive images of harming my
baby and tonight I might actually do it"* — was run through the deterministic crisis rules
engine. **It does NOT fire any crisis flag.** The `#219` Group A patterns are specific explicit
forms (`going/planning/want to hurt him/them/someone`); "tonight I might actually do it" (intent
carried by an anaphoric "it" pointing back to the harm image) matches none of them. So crisis
detection for this phrasing class rests on the **semantic/S7 layer** (BGE-semantic S1 and the
MARBERT/LLM classifier), not the lexicon.

## Why it does not break T3 (but still deserves a home)
T3's guarantee is POSITIONAL: crisis wins whenever ANY detector fires, because the crisis
short-circuit is upstream of the containment router. So it does not matter for T3 *which* layer
catches it — the test correctly asserts the positional invariant, not a keyword. But the fact
underneath ("this class is not deterministic-caught") is a real Node-1 coverage datum, and it
should not live only inside a test comment.

## The clinician question (needs a ruling — do not resolve by engineering)
Adjacent to #219's Group-A boundary and its inverted FP asymmetry (a false positive here is a
crisis card served to someone venting — trust-damaging). Two dispositions, pick one:
- **(a) Deterministic-catch it** — escalating-intent anaphora ("I might actually do it", "I think
  I'm going to", "I don't know if I can stop myself") becomes a #219 Group-A extension candidate,
  WITH the same negation_check + FP-asymmetry caution (figurative "I could just die" must not fire).
  Risk: anaphoric intent is exactly where a lexicon over-fires or under-fires.
- **(b) Semantic coverage is the designed posture** — record as INTENTIONAL: intent that is not
  lexically explicit is the semantic/S7 layer's job, and the lexicon deliberately stays narrow to
  protect the FP asymmetry. Then the open dependency is that this class rests on the UNMEASURED
  MARBERT (see the passive-SI / negation recall gaps) — so it inherits their measurement debt.

Either ruling is fine; the point is that it is RECORDED, not left implicit. If (a), it is a
crisis-sprint work item; if (b), it strengthens the case that the MARBERT bilingual eval is the
critical measurement (it now also owns escalating-intent recall).

→ **clinician queue item; ruling (a) extend / (b) intentional-semantic / other.**
