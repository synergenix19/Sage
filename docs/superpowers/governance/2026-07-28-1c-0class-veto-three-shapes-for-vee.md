# §1c #0-class veto — three shapes for Vee (design check BEFORE any code)

**This ask comes AFTER the CF-010 derealization flip is shipped + re-measured** (one safety change at a
time). It is the second, higher-stakes half of §1c Part A, and it touches the CRISIS path — so the design is
put to you before a line is written, not surfaced from audit rows afterward.

## The finding that reframes Ruling-3
Ruling-3 permits downgrading the "going to die + can't breathe" case from crisis to §1c **with somatic
co-occurrence AND a clean medical screen**. A live prod probe (2026-07-22) established a hard engineering
fact: **D1's medical red-flag surface does NOT intercept panic air-hunger** — "can't breathe" went to crisis,
never to the medical screen (D1 is tuned for cardiac/emergency strings like chest pain). This cuts both ways:

- **"D1 didn't fire" is NOT clearance** — a real cardiac event presenting as "can't breathe / going to die"
  is exactly what D1 misses, so treating D1-silence as a medical all-clear would downgrade a cardiac
  emergency to a grounding skill. (This is the fixture requirement already recorded.)
- **There may be no single-turn mechanism that affirmatively clears "can't breathe" as non-cardiac.** The
  doc's own medical screen distinguishes real trouble-breathing from anxious breathing **via a question** —
  not from the utterance alone.

So the honest question is not "how do we build the veto" but "does a clean single-turn screen even exist —
and if not, what did Ruling-3 actually license?"

## Three shapes — approve / pick / discuss

**Option C — keep crisis, accept the residual (RECOMMENDED).** "Going to die + can't breathe" STAYS at crisis,
a knowing documented residual alongside §1c-B. **This is the fail-safe reading of your own Ruling-3:** the
downgrade is permitted *with a clean screen*; the engineering finding is that no clean screen exists
single-turn for panic air-hunger; therefore no clean screen → no downgrade → keep crisis. The cost is real but
in the SAFE direction — a panicking user gets an over-cautious crisis referral; the dangerous direction (a
cardiac event downgraded to grounding) is exactly what C avoids. The crisis path is untouched, zero new risk.
→ ☐ C (recommended)

**Option A — two-turn screening veto.** The veto ASKS the doc's screening question ("is it hard to get air /
any chest pressure, or does it feel like a wave of panic passing?") and downgrades only on a panic-consistent
answer. This is the only shape that *affirmatively* clears — but it is a NEW interaction shape on the crisis
path (a question before a crisis decision), which is high-stakes and needs your sign-off on both the question
wording and the two-turn flow.
→ ☐ A (I'll approve the screening question + flow)

**Option B — stricter single-turn lexical precondition.** Downgrade only when the utterance carries an
affirmative panic marker ("panic attack") AND no cardiac-adjacent token ("chest", "crushing", "arm",
"sweating"). Single-turn and simple, but a lexical precondition is NOT a medical screen: "going to die, can't
breathe" with no cardiac word can still be cardiac (the person just didn't name it). **Eng advises against —
it is a false clearance on the crisis path.**
→ ☐ B

→ ☐ discuss

## Recommendation
**C.** Ruling-3 conditioned the downgrade on a clean screen; the honest finding is there is no single-turn
clean screen for panic air-hunger, so the conservative reading of your rule is keep-crisis. **A** is the only
real clearance but I would build it only on your explicit ruling (new crisis-path interaction). **B** I advise
against (false clearance). If C: the §1c #0 row is logged as a documented residual with §1c-B, and Part A
closes with the CF-010 derealization fix as its shipped delta.
