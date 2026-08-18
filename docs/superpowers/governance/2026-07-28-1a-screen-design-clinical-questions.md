# §1a Skill-Request Screen — Clinical Questions for Sign-off (pre-packet draft)

Status: DRAFT for clinician (Vee) review. These questions gate Task 5 Step 3b of
`docs/superpowers/plans/2026-07-28-1a-skill-request-delivery.md` (v3). Phase 0
characterization is running in parallel; nothing here ships before the packet is signed.

## Background (one paragraph)

When a user in an anxiety context explicitly asks for an exercise, the bot currently
deflects into exploration (conformance matrix §1a, 2/5, `presence_only`). The fix offers
the §1a Tier-1 choice (box_breathing, grounding_5_4_3_2_1) through the existing consent
gate, but only after the §1a screen is satisfied. Review of the fix surfaced the three
screen-design questions and one spec adjudication below.

## Q-A. Condensed screen wording (C1a, C1c)

The screen is adaptive: it asks only what the session has not already supplied, max two
clauses in one conversational turn. Unconditional clause pair: **onset/trigger** and
**duration** (duration is the "more than mild" discriminator per §1a section 6; a user
who never volunteers a duration word must be asked, or a six-month impairing presentation
receives a self-guided tool). Draft copy for review (em-dash-free, per rule-content rule):

> "Happy to share one. Quick check first so I point you at the right thing: did this
> start after something today, or has it been building for a while, like weeks or more?"

Ask: is this wording acceptable at the Mild tier, and is one combined onset+duration
clause acceptable, or should they be sequential single questions?

## Q-B. Conditional red-flag quality clause (C1b)

§1a: quality check "only if physical symptoms are mentioned", and §1a warns against
screening on symptom presence alone. The screen therefore raises crushing/spreading
pain and one-sided numbness ONLY when the session mentioned physical symptoms
(heart/breathing/chest markers). Rationale: blanket cardiac framing to a non-somatic
anxious presentation is a health-anxiety amplifier. Draft conditional clause:

> "And since you mentioned your chest, is this the same kind of tight feeling you have
> had with anxiety before, or anything different, like sharp or crushing pain, or pain
> moving to your arm, jaw, or back?"

Ask: confirm the conditional design (never blanket), and review the clause wording.

## Q-C. OPEN SPEC QUESTION: chronic case, "instead of" vs "alongside" (C2)

BOT BEHAVIOUR §1a is internally inconsistent for the long-standing/chronic case:

- **Section 6 guard:** anxiety "described as constant, long-standing (weeks+), or
  significantly impairing daily functioning" routes to "a professional-support/referral
  message **instead of** self-guided tools."
- **Section 2 routing logic:** "Long-standing / chronic (weeks or more) or worsening
  over time, without red flags: still offer a skill if the user wants one in the moment,
  but ... surface a professional-referral message **alongside** the skill, not instead
  of it."

The implementation currently takes the section-2 reading ("alongside") on the grounds
that it is the more specific passage and the user has explicitly asked for a tool. This
is an adjudication of a spec conflict, not spec compliance, and it is isolated to a
single branch so your ruling either way is a one-branch change.

Ask: which reading governs the explicit-request case? (a) skill offered with referral
alongside, or (b) referral only, no self-guided tool.

## Q-D. Scope confirmations

- v1 binds Mild tier only. Moderate (§B condensed direct-offer) and High (existing acute
  machinery) are out of scope for this change; confirm.
- Arabic phrasings ship inert pending Lane-3 validation (Khaleeji register); the binder
  is disabled for Arabic sessions until then; confirm.
