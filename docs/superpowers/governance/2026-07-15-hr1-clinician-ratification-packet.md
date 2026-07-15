# HR-1 Stage 1 — Clinician ratification packet (approve / amend / reject)

**What this gates:** the flip that makes SageAI detect high-risk psychiatric presentations (psychosis, mania, dissociation) and route them to the professional referral instead of offering a self-help skill. The code is built, flag-gated OFF, and fully tested; it does nothing in production until you ratify and we flip it. **Every trigger phrase below is copied verbatim from BOT BEHAVIOUR §HR.0** — your task is to confirm the doc's own table (and the boundary controls), not to author new content.

## ★ RECOMMENDATION (approve / edit / reject this)
> **Ratify the §HR.0 trigger table as the detector's phrase list, and flip HR detection ON.** It closes a live safety miss: today a manic user is offered a breathing exercise and a dissociating user is offered grounding — both of which the doc separately marks as *contraindicated* for these states. The detected-hallucination case already refers correctly; this extends that same working referral to the other high-risk presentations. **Two items below need your judgment (not a rubber-stamp); one question needs your ruling.**

## What you are ratifying
The detector fires on these verbatim §HR.0 phrases (+ minimum word-order variants), setting a clinical flag that routes to the existing professional referral:
- **Psychosis (15 phrases)** — "people are following me", "someone is watching me", "people are trying to hurt me", "I don't think I can trust anyone", "I hear voices", "I hear people talking when no one is there", "the voices won't stop", "I see things other people don't see", "I think people are reading my thoughts", "I think someone is controlling my thoughts", "the TV is sending me messages", "everything feels like a sign", "I don't know what's real anymore", **"I think everyone is against me"**, "I feel detached from reality". *(The doc header says "14" but the list holds 15; we caught the miscount and included all 15.)*
- **Mania (10 phrases)** — "I haven't slept for days but I feel amazing", "I don't need sleep", "my mind is going a million miles an hour", "I have so much energy", "I feel unstoppable", "I feel invincible", "I'm taking huge risks", "I've been spending loads of money", "I keep talking and can't stop", "my thoughts are racing all the time".
- **Dissociation (11 phrases)** — "I don't feel real", "nothing feels real", "I feel detached from myself", "I feel outside my body", "I feel like I'm watching myself", "the world doesn't feel real", "everything feels like a dream", "I lose chunks of time", "I feel disconnected from reality", "I feel completely numb and absent", "I don't know where I am sometimes".

And the **must-NOT-fire boundary** — these deliberately do NOT route to high-risk (confirm the boundary is right): grief ("I feel numb since he died", "nothing's felt real since the funeral"), panic-derealization ("everything felt unreal during the panic attack"), idiom/good-news ("this promotion doesn't feel real"), ordinary excitement ("I'm so energized about this project").

## Two items that need your judgment
1. **Mania "I have so much energy" — a known recall gap.** This bare phrase is a literal substring of the benign control "I have so much energy today after the gym," so no keyword can catch the bare phrase without also firing on someone who's just energized. We chose **precision over recall**: the phrase only fires when it co-occurs with another mania marker (e.g. "...and I haven't slept in days"). **Confirm this trade is acceptable**, or tell us to accept the false-positives on bare energy language.
2. **Dissociation at the referral tier.** "Nothing feels real" spans panic-adjacent derealization (lower acuity) to psychotic dissociation (high). The doc routes all dissociation to referral. The false-positive cost is a referral surfaced to a panicking user; the false-negative is a dissociating-from-psychosis user handed grounding. **Confirm dissociation belongs at the referral tier** (our default, per doc), or specify a lower tier for a subset.

## One ruling (blocker-with-default — the doc has already answered; you are ratifying or amending it)
The doc's §HR section names dissociation as one of its three high-risk classes with 11 triggers — so **the default is: dissociation routes to professional referral, per the doc.** You are not deciding this fresh. The genuine question is whether you want to **amend** the doc's answer — e.g. split panic-derealization to a lower tier — not to re-derive settled content. **Ratify the doc's default, or specify the amendment.**

## What happens between your ratification and Stage 2 (sign knowing this)
On flip, all five high-risk classes route to the **existing referral, which is LLM-rendered** — the doc grades this as non-conforming to §HR: it has no fixed standardized copy and does not ask the distress-0-10 question. You are ratifying **detection into an imperfect terminal.** This is a deliberate, honest trade: the contraindicated-skill harm (breathing to a manic user, grounding to a dissociating user) stops *immediately*, and delivery conformance — the doc's fixed §2 message + the §1 distress question — follows in **Stage 2, a committed build immediately behind this one.** You sign the detection now; the terminal upgrade is already scheduled, not aspirational.

## Scope / what this does NOT cover (stated, not hidden)
- **Arabic: zero coverage.** These are English triggers; Khaleeji renderings + Arabic must-NOT-fire controls go to the AR probe. This ships English-first with the AR gap on the record (same pattern as the B1 medical guard).
- **Keyword-only.** Naturalistic disclosures that don't contain a listed phrase won't fire (the #65-class limitation). Semantic detection is future work.
- **The referral copy is the current LLM-rendered one.** Stage 2 replaces it with the doc's fixed standardized message + the distress-0-10 question — a separate build immediately behind this.

## On your approval we (engineering) then:
flip CF-007/008/009 to `active:true`, add your sign-off (`approved_by`), reconcile the signed-fields manifest, and set `SAGE_HIGH_RISK_DETECTION=true` in prod — with a live post-flip verification of the four drives, exactly as B1 was verified.

## Second ask (unblocks the Arabic measurement, routed here so it lands in one conversation)
The Arabic/Khaleeji coverage for these HR triggers — and for the medical red-flag, venting, and unsigned SK-AR rules — is **zero** today, and the plan to measure it (the AR conformance probe) has one hard dependency only you can supply: **who is the native-Khaleeji validator?** Corpus labels are clinical assertions, so the validator must be clinically credentialed and a native Gulf-Arabic speaker; engineering cannot source or assess that credential. **Please name the validator.** No validator, no Arabic corpus, no probe — this is the single blocker on the entire AR measurement track, so naming them now starts it.
