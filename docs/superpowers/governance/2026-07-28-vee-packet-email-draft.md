# Vee Packet — Dispatch-Ready Email Text (recipient + send held by product owner)

Status: Gmail draft creation blocked (insufficient auth scopes on the connected
account) and no verified clinician address exists in-repo (rohansarda@gmail.com is
a TEST account). Paste-ready body below; content mirrors
`2026-07-28-vee-packet-emr.md`.

Subject: Clinical sign-off packet — Sage explicit-modality-request / §1a (screen
design, chronic-case ruling, offer precedence)

Hi Vee,

This is the consolidated clinical decision packet for the explicit-modality-request
workstream (the "user asks for an exercise and doesn't get one" defect).
Architecture review is complete and signed; the four items below are yours. Nothing
ships until you sign, and each ruling is isolated so either answer is a small change.

1) CONDENSED SCREEN WORDING (before any tool offer at the Mild tier)
The screen is adaptive: it only asks what the conversation hasn't already supplied,
max two clauses in one conversational turn. Onset and duration are the unconditional
pair (duration is the "more than mild" discriminator).
Draft copy for your review:
"Happy to share one. Quick check first so I point you at the right thing: did this
start after something today, or has it been building for a while, like weeks or
more?"
Ask: is this wording acceptable at the Mild tier, and is one combined onset+duration
clause acceptable, or should they be sequential single questions?

2) CONDITIONAL RED-FLAG CLAUSE
Per the BOT BEHAVIOUR doc, the quality check runs "only if physical symptoms are
mentioned" — the screen never raises crushing/spreading pain or one-sided numbness
to someone with a non-somatic presentation (health-anxiety amplification concern).
Draft conditional clause:
"And since you mentioned your chest, is this the same kind of tight feeling you have
had with anxiety before, or anything different, like sharp or crushing pain, or pain
moving to your arm, jaw, or back?"
Ask: confirm the conditional design (never blanket), and review the clause wording.

3) OPEN SPEC QUESTION — the chronic case (a genuine conflict in the ratified doc)
Section 6 guard: long-standing (weeks+) or impairing anxiety routes to a
professional-support/referral message INSTEAD OF self-guided tools.
Section 2 routing logic: chronic without red flags: still offer a skill if the user
wants one, with the referral ALONGSIDE the skill, not instead of it.
The implementation currently takes "alongside" (the more specific passage, and the
user has explicitly asked for a tool), but this is our adjudication of a
contradiction, not spec compliance.
Ask: which reading governs the explicit-request case, (a) skill offered with
referral alongside, or (b) referral only, no self-guided tool?

4) OFFER PRECEDENCE (architecture-signed, yours to confirm clinically)
When a user asks for an exercise while an offer is already on the table: if what
they asked for is among the offered options, we treat it as accepting that option;
otherwise the old offer is released (not marked declined) and the request is
answered with the first-line pair (Box Breathing / 5-4-3-2-1 Grounding). Released
offers stay eligible to come up again later; only explicit declines are never
re-offered.
Ask: confirm this matches clinical intent, or pick an alternative (we documented
three, including "ask the user to clarify" if you prefer that despite the added
friction).

SCOPE CONFIRMATIONS
- Version 1 covers the Mild tier only; Moderate keeps its condensed direct-offer
  path for a later change; High continues through the existing acute machinery.
- Arabic phrasings are drafted but inactive pending the Arabic validation track
  (Khaleeji register review); the feature is disabled for Arabic sessions until
  then.

Context on weight: the defect is live in production across three distinct
mechanisms; the fix is deterministic and consent-gated; this screen is what stands
between an explicit request and an unscreened tool offer.

Full documents (with citations to the ratified doc by line) are in the repo on
branch 1a-gap-phase0, and we can walk through any of it on a call if easier.

Thanks,
Sage engineering
