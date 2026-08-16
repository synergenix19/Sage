# ⛔ HALT — two parallel §1c Part A mechanisms give derealization OPPOSITE dispositions (2026-07-28)

> **✅ HALT LIFTED 2026-07-30 — Vee ruled (five ticks, PO relay; see the packet's RULINGS banner).**
> Derealization = REFERRAL (item 1). Resolution executed as four owner-ordered increments:
> **1** CF-010 flipped alone (register change #3, PR#397; live + verified + re-measured, execution record
> `2026-07-30-cf010-flip-execution-record.md`); **2** panic_override remediated to its signed scope
> (pure-panic + cardiac deference, PR#398); **3** this PR merges the disposition-ownership registry as the
> pre-sign-off gate; **4** K3/K4 description clauses await Vee's authored sentences. This document stays as
> the record of the conflict; nothing below is edited.

**The CF-010 flip is HALTED pending Vee reconciliation.** Two sessions built §1c Part A in parallel without
cross-awareness, and they dispose the SAME utterance oppositely — both citing a Vee sign-off.

## The conflict (same utterance, opposite disposition)
| utterance | mechanism (this session) | mechanism (parallel session) |
|---|---|---|
| "everything feels unreal and I can't take this" (§1c corpus #2) | **CF-010 derealization flag → anxiety-track REFERRAL** (safety altitude) | **panic_override → force-GROUND** (post-intent) |
| sign-off cited | Vee 1a–1d, **2026-07-21** (approval sheet); doc §1c **L151** | Vee §1c-A boundary, **2026-07-28** (part-a-1c-boundary-to-vee.md) |

Confirmed in code: `panic_override._PANIC_TERMS` contains `"unreal"`, `"not real"`, `"derealiz"`, `"detached"`,
`"outside my body"`, `"watching myself"`; `_has_panic_signature("everything feels unreal and I can't take this")`
= True, harm = False → it force-grounds. CF-010 fires the `derealization` flag on the same string → referral.

## Which is right? The doc points one way
BOT BEHAVIOUR **§1c L151**: "signs of dissociation, panic attack with derealization … **grounding/mindfulness
exercises can sometimes intensify these states; escalate to referral rather than presenting the standard
tools.**" The doc says derealization → **REFERRAL** *specifically because grounding can intensify it*. So the
parallel force-ground of derealization runs **against the doc**; CF-010's referral is doc-aligned. The parallel
07-28 boundary sheet never mentions CF-010 or the 07-21 referral ruling — strong evidence the derealization
terms were swept into the panic force-ground set without the referral context, not a deliberate reversal.

## Runtime note (why this is a disposition conflict, not just a race)
If both flags flip, CF-010 wins mechanically — it exits at the safety altitude BEFORE intent_route, where
panic_override runs — so derealization would go to referral regardless. But the parallel session's INTENT
(Vee 07-28) was grounding. So even with CF-010 winning at runtime, shipping it asserts a disposition the 07-28
ruling contradicts. Both flags are currently OFF (inert), so there is NO live conflict yet — which is exactly
why this must be reconciled BEFORE either flips.

## Recommendation (Vee's call — do not resolve unilaterally)
- **Derealization → REFERRAL** (CF-010), per doc §1c L151 and the 07-21 ruling.
- **panic_override REMOVES the derealization terms** (`"unreal"`, `"not real"`, `"derealiz"`, `"detached"`,
  `"outside my body"`, `"watching myself"`) from its force-ground set — it handles PURE PANIC (breathing / heart
  / dizzy / "going to die + can't breathe" without derealization); derealization is CF-010's referral territory.
- Then CF-010 and panic_override are complementary, not conflicting, and each can flip on its own delta.

## Also flagged (separate, lower severity)
`panic_override`'s downgrade precondition is `no medical_flags` = **"D1 didn't fire," not "medically
screened clean"** — the exact gap the §1c design note (2026-07-22-1c-partA-design-notes-and-1cB.md L23-35) and
the veto three-shapes ask warned about. The 07-28 boundary sheet surfaced the passive-SI residual (and Vee set
the conservative dial for it) but did not explicitly surface the **cardiac** residual (a missed-cardiac "can't
breathe", D1 empty, no harm word → grounded, losing the crisis card's 999 prompt). Worth confirming Vee
weighed the cardiac angle, not only the passive-SI one.

## Process
This is a concrete instance of the cross-session ownership gap already filed as highest process severity
(master commit 88e12c40). My veto three-shapes ask (2026-07-28-1c-0class-veto-three-shapes-for-vee.md) is
SUPERSEDED by the parallel panic_override — do not send it.
