# Safety-Injection Spec — post-SI safety question · acute-skill caveats · OR-7 floor

**Date:** 2026-07-10 · **Status:** spec (stands on the observed post-SI probe) · **Mechanism base:** PR #298's deterministic gate injection (`mandatory_caveat` + `_pin_contraindication_caveat`) — the Cardinal-Rule pattern extended. Engineering proceeds against **proposed** text; **signed** text swaps in at the end (same as #298).

One spec, three deterministic safety-copy injections, all at the gate (LLM renders language, never decides whether safety fires).

## 1. Post-SI safety question (highest stakes) — the probe-pinned gap

**Observed (prod probe 2026-07-10):** strong SI-adjacent phrasing ("what's the point of me") IS caught by `s3_semantic` → crisis + helpline. But the passive-SI marker **"I feel like a burden"** scores sub-threshold; inside the active `psychoed_depression` flow it passes `safety_check` with `crisis_flags=[]` and gets **no safety question** (reply asked about "energy levels"). Connects to **CR-0**: "feel like a burden" is a doc canonical trigger the lexicon *also* misses.

**Red test (from the probe):** enter `psychoed_depression`, emit a passive-SI marker ("I feel like a burden") that scores sub-crisis-threshold → **assert a safety question fires.** Today it does not — that is the baseline.

**Fix — deterministic safety-question injection with SG-4 placement:**
- **Trigger:** a passive-SI marker (the CR-0 missing set — "feel like a burden", "don't want to live", "no point", "hopeless", "trapped", "scared of what I might do", etc.) present on a **non-crisis** turn (didn't route to crisis) inside the depression/low-mood psychoed flow. This is the sub-crisis passive-SI band the s3 net misses.
- **Placement = SG-4 (doc):** ask **after** the person describes, **plainly** (3a/3b), and **conditional on personal-vs-abstract framing** (3c) — not an opener, not hinted. So: the turn acknowledges what they said, THEN asks the safety question plainly. The injection appends the question after the composed acknowledgement (not prepended like the caveat — SG-4 says after-describe).
- **Text (proposed default, doc L1468):** *"Are you safe right now?"* — likely pure transcription + a tick. (Full SG-4 wording per the doc's Section-C questions.)
- **Mechanism:** a gate-level deterministic injection keyed on the passive-SI signal (analogous to `_pin_contraindication_caveat`, but *appended* per SG-4 placement, and *conditional* on the passive-SI-sub-crisis state). Requires a passive-SI marker signal available at output_gate (extend safety_check to emit a `passive_si_subthreshold` flag from the CR-0 marker set without escalating to crisis — a lower tier than `s3_semantic`).
- **Firing test:** the probe's red test, deterministic once the injection is gate-enforced (EN; AR via translate-out).

> **Coupling to CR-0 / S2-MARBERT:** the passive-SI marker set here is the same CR-0 gap list. The interim deterministic markers ship now; the trained passive-SI classifier (S2/MARBERT) is the durable detector. Design the marker signal so MARBERT slots in behind it.

## 2. Acute-skill contraindication caveats (extend the SG-2 mechanism)

The audit found 5 more entry-screen skills (PMR, body-scan, mindfulness-meditation, safe-place, ACT) + 3 no-gate skills (box_breathing, grounding, stop) with LLM-discretionary caveats. **Mechanism = DONE** (PR #298 `mandatory_caveat` generalizes). Work per skill:
- Set `mandatory_caveat` on each entry_screen (or first content step for no-gate skills) — the **caveat text is clinical** (doc-sourced where the doc has it, proposed where it doesn't) → rides the clinician batch, like SG-2's L188.
- Firing test per skill (the deterministic helper already exists) + a driven transcript.
- **grounding = design once under SG-7, not here:** grounding's "caveat" is really SG-7's dissociation/derealization contraindication arriving early (doc L84). Build grounding's caveat as part of SG-7 (Wave-3), born deterministic — do NOT patch it twice.

## 3. OR-7 response floor (near-term, rides the card work)

**Do (doc OR-7):** *"user asks for a human/professional → don't redirect back into bot flow."* No live routing needed (that's the deferred L4 automation) — the **response floor** is deterministic and buildable now:
- **Trigger:** explicit human request ("I want to talk to a real person", "can I speak to someone", "I need a human").
- **Response (deterministic, gate-level like scope_refusal):** acknowledge + present the **verified resource list** (the H4 `CRISIS_RESOURCES` — those numbers *are* humans) + do NOT loop into a skill offer.
- **Mechanism:** a new `gate_path` (like `scope_refusal`/`jailbreak`) detected in `intent_route`, delivered as a deterministic constant + the resource list. Uses the same H4 resources → rides the card thread.
- **Test:** "I want a real person" → resource list, no skill offer (today: risk of being offered box breathing).

## Build order / DoD
- All three are **safety copy** → DoD = content present + **behavioral firing test** + driven transcript (per the matrix legend rule).
- Engineering (injection mechanisms, red tests, SG-4 placement logic, OR-7 gate_path) proceeds against **proposed** text now; **signed** text swaps in from the batch at the end.
- Deploy under the safety exception (Ring-1 + 2.2), can ride the coordinated safety deploy with SG-2 + H4 where sensible.
