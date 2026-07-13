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
crisis card served to someone venting — trust-damaging).

### ENGINEERING-RECOMMENDED: (c) split by anaphora distance
The a/b binary is false — it hides a split the architecture already supports. Recommend putting
this in front of the clinician as the disposition:
- **Same-turn → deterministic (co-occurrence-gated).** The finding's fixtures are NOT bare anaphora
  — "intrusive images of harming my baby AND tonight I might actually do it" carries its antecedent
  in the same message. A rule that fires intent-anaphora forms ("might actually do it", "don't know
  if I can stop myself", "think I'm going to") **only when a same-turn harm-content match exists** is
  deterministic, auditable, and structurally protected against the FP asymmetry: "I could just die,
  he ate my leftovers" has no harm antecedent and never fires; venting-without-harm-content never
  fires. This is not a lexicon innovation — it is the Rules Service's own IF/THEN step-policy shape
  applied at Node 1, and it keeps "safety is deterministic" for the subset where determinism is
  achievable. This is exactly option (a)'s target MINUS the over-fire risk (a)'s critics name, which
  only exists for BARE anaphora.
- **Cross-turn → semantic, honestly scoped.** Intent whose antecedent lives in a PRIOR turn
  ("...tonight I might actually do it", three messages after the disclosure) is genuinely beyond
  single-message lexicon reach without conversation-state pattern matching (a different, riskier
  mechanism). This subset rests on MARBERT/S7 BY DESIGN — ruling (b)'s posture, but scoped to where
  it is true, not conceded for the whole class.

### The MARBERT price (say this explicitly to the PO)
The cross-turn concession makes the **MARBERT bilingual eval the critical safety measurement**:
escalating-intent cross-turn recall joins **passive-SI**, **negation**, and — as of the 2026-07-13
harm-to-others incident — **harm-to-others** in the unmeasured column. Per v7's experiment plan,
**Exp 4.2 (MARBERT FT + eval)** is scheduled work — this is now the **FOURTH safety-recall class**
to land on it. **Sharpest exhibit: the 2026-07-13 incident** (`2026-07-13-harm-to-others-clobber-incident.md`)
— for ~3d 15½h the deterministic harm-to-others backstop was silently reverted in prod, so harm-to-others
detection rested **entirely** on the unmeasured LLM/MARBERT layer, by accident, undetected — and the
exposure over that window is **un-auditable** because a disarmed flag leaves no trail (§7). Four classes
resting on one unmeasured model, one of them having been briefly the *only* layer without our knowing,
is the strongest case yet for **pulling Exp 4.2 forward**; say so to the PO.

→ **clinician queue item; ruling (c) split / (a) all-deterministic / (b) all-semantic / other.**
Reference the vote alongside HG-1 + the trim confirm + the T4 content if the sitting has room.

## Fixtures landed 2026-07-10 (measurement precedes mechanism — do not wait for the ruling)
1. **Same-turn** (6 cases, EN+AR, paraphrased) → `tests/fixtures/safety/cases.py`
   `_TP_HARM_INTENT_ESCALATION`, `known_fn=True` (all probed MISS 2026-07-10), running as xfail in
   `test_safety_known_gap`. If (c) is approved, the co-occurrence rule gates on exactly these.
2. **Cross-turn** (6 sequences, EN+AR) → `tests/fixtures/safety/harm_intent_escalation_crossturn.jsonl`
   (multi-turn; single-message `cases.py` cannot hold them). `expected_crisis=true`,
   `expected_layer=semantic`, `known_gap=true` until the MARBERT eval measures it.
3. **T4-REFERENCE staging probe.** This class is the ego-syntonic/intent boundary the OCD
   containment template must NEVER receive — the worst possible containment output is serving
   psychoeducation to someone declaring intent to harm. The T3 positional test proves crisis wins
   when a detector fires; this ticket documents a class where TODAY only the semantic layer fires.
   So the T4 staging probe set MUST assert: this fixture reaches `crisis_response` (via whichever
   layer), NEVER the containment template. Converts the datum into a standing guard on the new
   pathway. (Added to the T4 probe list in `2026-07-10-t4-reference-content-drafts.md`.)
