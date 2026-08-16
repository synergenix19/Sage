# HR-1 Stage 2 — Fixed-copy candidate variants for clinician ratification

**Status: DRAFT CANDIDATES ONLY, not production code.** These are offline-authored options for
the five deterministic HR-terminal strings specified in
`docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md` ("Fixed copy" section,
lines 26-31) and the blocker-with-defaults in
`docs/superpowers/governance/2026-07-15-hr1-clinician-ratification-packet.md`. Nothing here ships
until the clinician picks winners (or edits one into a winner) and signs off, the same way
`L0_persona.json` and `crisis_content/*.json` carry `approved_by` + a sign-off note. Once ratified,
the winning strings get committed verbatim as templates (`crisis_copy_templated`-style, single
`{{crisis_*}}`-resolved placeholders for numbers, never LLM-rendered) — no paraphrasing at
delivery time.

**Placeholder convention used below** (matches `src/sage_poc/crisis_copy.py`): `{{crisis_emergency}}`
resolves to `999`, `{{crisis_number}}`/`{{crisis_label}}`/`{{crisis_hours}}` resolve to the UAE
helpline. `{{first_name}}` is the only other permitted interpolation (name-only personalization).
Per §3 of the design spec, both redirect slots (3 and 4) are followed by the existing UAE
crisis-resource block appended separately by `select_crisis_resources()` — the variants below are
only the lead-in message, not the resource list itself.

**Voice source:** `src/sage_poc/prompts/templates/L0_persona.json` (v2.5.0, approved). Pulled
forward: plain prose, short sentences, commas not dashes, no clinical jargon; validate/acknowledge
before informing; "a bridge, not a destination" language for the professional-support handoff; the
persona's own HARD LIMIT is verbatim relevant here — "never reinforce delusional or paranoid
thinking, respond with care and steer toward professional support." Register cross-checked against
`MEDICAL_REFERRAL_TEXT` (config.py) and `crisis_content/en_uae.json` for how SageAI already frames
"call now" urgency.

---

## Slot 1 — Distress question (§1, "The Only Question")

Constraint: must ask a 0-to-10 distress rating and **nothing else about the content**. Exactly one
question, per L0's "ask at most one question per turn."

**V1** — "On a scale of 0 to 10, how distressing does this feel for you right now?"
*§5-safe:* near-verbatim to the doc's own fixed copy; zero content reference, single closed
numeric question, no technique, no diagnosis.

**V2** — "{{first_name}}, if 0 means calm and 10 means unbearable, where would you put yourself right now?"
*§5-safe:* name-only personalization; anchors the scale without referencing what was disclosed;
one question.

**V3** — "I want to understand how much this is weighing on you right now. On a scale of 0 to 10, what number feels right?"
*§5-safe:* the lead-in ("how much this is weighing on you") is generic affect language, not a
reflection of the specific delusion/hallucination/mania content; still resolves to one closed
question.

**V4** — "Can you give me a number, 0 to 10, for how distressing this is for you right now?"
*§5-safe:* shortest form; no content reference; single question; no validation of belief-content
since it asks about distress level only, not the belief itself.

---

## Slot 2 — Supportive message (§2 semantic commitments)

Constraint: must carry (a) thank-you/acknowledgment that they told us, (b) acknowledgment that
what they're describing is difficult, (c) a bridge to professional support — without echoing the
specific content, diagnosing, or offering a technique.

**V1** — "Thank you for telling me what's going on for you. What you're describing sounds really difficult, and I want to make sure you get support from someone who can help properly with this."
*§5-safe:* doc's own fixed copy (verbatim baseline); "what you're describing sounds difficult" is
a content-neutral acknowledgment of difficulty, not a reflection of the specific belief/experience;
no diagnosis; bridges to "someone who can help properly," not a technique.

**V2** — "Thank you for trusting me with this. I can hear how hard it's been, and I want you to have support from someone who can really help."
*§5-safe:* "trusting me with this" and "how hard it's been" stay generic; no echo of content; bridge
language matches persona's "bridge, not destination" register.

**V3** — "{{first_name}}, thank you for telling me. This sounds like a lot to carry right now, and I want to make sure you get help from someone who's trained for this."
*§5-safe:* name-only personalization; "a lot to carry" is affect-only, not content-specific;
explicit hand-off to trained support, no attempt at coping-skill delivery.

**V4** — "I'm glad you told me what's going on. It sounds really hard right now, and you deserve support from someone who can properly help with this."
*§5-safe:* thank-you equivalent ("glad you told me"), difficulty acknowledgment, professional
bridge; no validation of belief-as-real, no condition name.

---

## Slot 3 — Higher-severity redirect (§3, encourage 999 / nearest ER now)

Constraint: urgency present, still warm; no content echo; followed separately by the UAE
resource block.

**V1** — "Please call {{crisis_emergency}} right now, or get to your nearest emergency department. This needs help in person, right away, and I want you safe."
*§5-safe:* directive urgency without naming why; "I want you safe" is warmth without minimizing
urgency; no content reference, no diagnosis.

**V2** — "{{first_name}}, I think this needs more help than I can give right now. Please call {{crisis_emergency}}, or go to the nearest emergency room as soon as you can."
*§5-safe:* frames Sage's own limit honestly (matches persona's "not a medical professional" stance)
rather than describing the user's state; name-only personalization; no content echo.

**V3** — "This is serious enough that I want you to get help in person now. Call {{crisis_emergency}}, or head to your nearest ER, please don't wait on this."
*§5-safe:* urgency carried by "don't wait," not by restating what was disclosed; still warm via
"I want you"; no coping technique offered.

**V4** — "Right now, the safest step is calling {{crisis_emergency}} or going straight to the nearest emergency department. Please do that now, I'm glad you're not alone in this."
*§5-safe:* action-first framing; "I'm glad you're not alone" is relational warmth without touching
content; no diagnosis, no argument for/against the belief.

---

## Slot 4 — Lower-severity redirect (§3, see a doctor / mental health professional promptly)

Constraint: prompt but non-emergency framing; no content echo; followed separately by the UAE
resource block.

**V1** — "This is something a doctor or mental health professional should look at with you soon. Please reach out to one in the next day or so."
*§5-safe:* doc's own fixed copy (verbatim baseline); no content reference; names the referral
target as a professional, never a diagnosis for the user.

**V2** — "{{first_name}}, I'd feel better knowing a doctor or mental health professional is looking at this with you soon. Can you reach out to one in the next few days?"
*§5-safe:* name-only personalization; frames urgency through Sage's own concern, not through
restating the user's content; single soft ask, no technique offered.

**V3** — "I think it's worth getting this in front of a doctor or mental health professional soon, they can help in ways I can't."
*§5-safe:* explicit bridge/limit language ("in ways I can't") matching persona's non-therapist
identity; no content echo, no diagnosis.

**V4** — "This deserves a closer look from a doctor or mental health professional. Please try to see one soon."
*§5-safe:* shortest form; content-neutral "this," no technique, no urgency-inflation into
emergency framing (keeps the severity tiers distinct from Slot 3).

---

## Slot 5 — Gentle re-ask (single re-ask, used once, never probes content)

Constraint: warm re-ask of the SAME distress question only; must not ask about content, must not
stack a second question, must not appear twice (T3 defaults to higher-severity regardless of
answer per the design spec's step-counter guarantee).

**V1** — "I hear you. Just so I understand, on a scale of 0 to 10, how distressing is this for you right now?"
*§5-safe:* "I hear you" acknowledges the reply without evaluating or echoing its content; still one
closed numeric question.

**V2** — "{{first_name}}, I just need one number from you, 0 to 10, for how distressing this feels right now."
*§5-safe:* name-only personalization; explicitly narrows the ask to a number, ruling out a second
content probe; single question.

**V3** — "Take your time. Somewhere between 0 and 10, how distressing is this for you right now?"
*§5-safe:* softens pace without adding a second question or referencing content; stays a pure
re-ask of the same scale.

**V4** — "One more time, just so I know where you're at: 0 to 10, how distressing is this right now?"
*§5-safe:* signals this is the final ask (matches the two-turn-max scope guard's spirit) without
probing further; note the colon here reads as a list lead-in, not an em dash, and can be swapped
for a comma if the clinician prefers stricter punctuation parity with the other variants.

---

## Notes for the clinician pass

- Slot 1 and Slot 5 are close in shape by design (both are the *same* question, once cold and once
  as a re-ask) — if you prefer, you can ratify one Slot-1 winner and reuse a warmed version of it
  for Slot 5 rather than picking independently.
- Slot 3 and Slot 4 deliberately avoid naming *why* ("psychosis," "mania," "dissociation," "this
  belief") anywhere — that omission is the load-bearing §5 property, not an oversight. If any
  variant reads as too vague to you clinically, the fix is warmer relational framing (as drafted),
  never adding a content reference back in.
- All numbers are `{{crisis_*}}` placeholders per the project's single-source convention
  (`src/sage_poc/crisis_copy.py`); winners should be committed with placeholders intact, not
  hardcoded digits.
