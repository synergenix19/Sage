# Clinician touchpoint — Vee — §1c crisis over-escalation: the somatic-vs-harm line

**Context (sized, not abstract).** The graph routes 2/5 §1c "high anxiety" panic utterances to the
**full crisis card** (helpline + **999** + "reach out NOW") when the spec prescribes a grounding skill.
A "can't breathe" panic user is told they're in an emergency — iatrogenic for panic, and crying-wolf on
the crisis path. Pinned cause: the **LLM intent classifier** labels them `intent=crisis` despite its own
prompt already excluding these symptoms; safety_check (deterministic) is clean. Fix = a **deterministic
veto** that moves the crisis-routing decision off the LLM (this closes a live Cardinal-Rule-4 violation,
not just an FP). The veto downgrades `intent=crisis`→grounding ONLY on a clean somatic-only match. **The
somatic-vs-harm boundary is yours to draw — that's this ask.** Diagnosis:
`docs/superpowers/tickets/2026-07-17-1c-crisis-over-escalation-diagnosis.md`.

**Overriding rule the veto is built on: FAIL TOWARD CRISIS.** Anything not on your clean-somatic list,
any harm token, any ambiguity → KEEP crisis. Recall ≥95% dominates the false-positive; we would rather
leave a §1c over-escalation than nick one true crisis. So the lists below define what is SAFE to
downgrade; everything else stays crisis by default.

---

## Ruling 1 — SOMATIC-DISTRESS set (veto MAY downgrade to grounding when the utterance has NO harm token)
The prompt's own list: **panic, hyperventilation / "can't breathe", racing heart, derealization /
"everything feels unreal", depersonalization, "losing it" / "losing my mind", "out of control".**
Rec: **approve as the downgrade set** — clinically these are panic/dissociation presentations whose
correct response is grounding, not an emergency line.
→ ☐ approve  ☐ edit (add/remove: __________)  ☐ reject

## Ruling 2 — HARM set (veto NEVER fires; ALWAYS routes crisis)
Explicit suicidal intent ("want to die/kill myself/end my life/end it"), self-harm intent, plans to
hurt others, AND passive-SI ("don't want to be here", "want it to stop", "can't go on", "want it to
end"). Rec: **approve — the veto must never touch these**, and any of them present overrides a somatic match.
→ ☐ approve  ☐ edit  ☐ reject

## Ruling 3 — the AMBIGUOUS phrases in the actual §1c corpus (place each: somatic-downgrade OR keep-crisis)
These are the two that decide whether §1c fully recovers or only partly:
- **"I feel like I'm going to die"** (a classic panic-attack cognition, co-occurring with "can't
  breathe"). Rec: **somatic-downgrade** IN panic context — it is the somatic fear, not stated SI.
- **"I can't take this" / "I can't do this anymore"** (overwhelm, no explicit harm). Rec: **KEEP CRISIS**
  (fail-toward-crisis) — "can't take this" is close enough to passive-SI that downgrading it risks recall.
  Consequence you should see clearly: this leaves the §1c utterance *"Everything feels unreal and I
  can't take this"* routing to crisis (a residual conformance miss) — we accept that over a recall risk.
→ "going to die": ☐ somatic-downgrade  ☐ keep-crisis  ☐ edit
→ "can't take this / can't do this anymore": ☐ keep-crisis (rec)  ☐ somatic-downgrade  ☐ edit

## Ruling 4 — MIXED / CO-OCCURRENCE case
Somatic + harm in one utterance ("I can't breathe **and I want it to stop**") → **KEEP CRISIS** (harm
wins; the veto requires ZERO harm tokens). Rec: **approve.** This is the utterance most likely to break
a naive veto — the fixture set guards it hardest.
→ ☐ approve  ☐ edit  ☐ reject

---

**What your answers produce:** the exact downgrade-set + harm-set + ambiguous placements become the
deterministic veto's match conditions AND the reject/accept fixtures (somatic-only downgrades;
harm-only + mixed still route crisis). No veto code is written until you rule — the somatic/harm line is
clinical, not eng. Then: fixtures (mixed case guarded hardest) → gate → live.
