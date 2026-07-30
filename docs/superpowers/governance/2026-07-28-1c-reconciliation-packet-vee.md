# §1c reconciliation — one packet to Vee (2026-07-28)

> **✅ RULED — Vee, 2026-07-30 (five ticks via PO relay).**
> **Item 1**: No — derealization stays REFERRAL; panic_override scopes back to pure panic (closes the four
> HR-family overlaps in the annex). **Copy**: re-affirmed (was already ratified + pinned 2026-07-28,
> `aea60720`). **Item 2**: the "going to die + can't breathe" class STAYS AT CRISIS — a knowing residual
> (Ruling-3 fail-safe reading; no downgrade without a clean screen). **Item 3 (registry)**: approved as the
> pre-sign-off gate — this PR's merge is its adoption. **K3/K4 clauses**: she authors; sentences pending.
> Execution: increment 1 (CF-010 flip) LIVE + re-measured 2026-07-30; increment 2 (scope-back + cardiac
> deference) merged `ada1855a`; this merge is increment 3; increment 4 awaits her sentences.

Two §1c Part A mechanisms were built in parallel and dispose the same utterance oppositely (HALT record:
`2026-07-28-1c-derealization-disposition-conflict-HALT.md`). Both are flag-OFF/inert — no live conflict. Three
items: one clinical confirm, one clinical finding, one process fix. Neither mechanism flips until item 1 rules.

> **[2026-07-30: "both flag-OFF" is no longer true — panic_override is LIVE on prod under your 07-28
> signature; CF-010 remains OFF pending your copy sign-off. See the STATUS UPDATE (2026-07-30) at the end
> before ruling. Items 1–3 are otherwise unchanged.]**

---

## 1. Derealization — a SCOPE confirm, not a re-deliberation (one line)
You adjudicated derealization **once**, on **07-21** (1a–1d): you saw the doc's §1c **L151** guard —
*"grounding/mindfulness can intensify dissociative states; escalate to **referral** rather than presenting the
standard tools"* — and you ruled **referral**. CF-010 implements that.

On **07-28**, the panic-grounding sheet (`part-a-1c-boundary-to-vee.md`) asked you about **panic** force-grounding.
Its proposed §1c-A paraphrase set did include the words *"detachment / derealization"* (which you approved "as
proposed") — but **it never surfaced derealization as its own question, and never referenced L151 or your 07-21
referral ruling**, so the terms `"unreal"`, `"not real"`, `"derealiz"`, `"detached"`, `"outside my body"`,
`"watching myself"` rode into that mechanism's match set as lexical neighbors of panic. So `"everything feels unreal"` now force-**grounds** under it — the exact state L151 says grounding can
intensify. This is not "you ruled twice, differently." It is one ruling (referral) plus a later mechanism that
captured territory its sheet never put to you.

> **Did you intend the 07-28 panic sheet to reverse your 07-21 derealization ruling?**
> ▢ **No — derealization stays REFERRAL (expected).** panic_override keeps PURE-PANIC only; CF-010 and
>   panic_override become complementary; each flips alone.
> ▢ Yes — I intend derealization to ground now (please note why, so L151 is consciously overridden).

The doc points one way regardless: L151's guard exists *because* grounding intensifies dissociation, so
force-grounding derealization is that named contraindication implemented as a feature. Default reading =
scope-creep, not reversal.

**Broader than derealization (the new disposition-ownership check surfaced the full extent):** panic_override's
match list also swept terms owned by the HR mechanisms — CF-008 dissociation (`detached`, `outside my body`,
`watching myself`), CF-009 psychosis (`detached`), CF-007 mania (`thoughts are racing`) — all `hr_referral`, not
grounding. Runtime precedence preempts these when the HR flag matches, but the sweep is the same scope-creep.
So the clean remediation is: **panic_override keeps PURE-PANIC terms only (breathing / heart / dizzy / panic
attack) and drops everything owned by CF-007/008/009/010.** One scoping edit closes all four overlaps at once.

### Evidence annex — the full territory the sweep captured (mechanical check, not manual review)
The disposition-ownership check extracted panic_override's actual `_PANIC_TERMS` and found it overlaps **all
four high-risk flag families — every one an `hr_referral` disposition**, not just derealization:

| HR flag family | its disposition | terms panic_override's surface shares |
|---|---|---|
| CF-010 derealization | anxiety-track referral | `unreal` (⊂ "everything feels unreal") |
| CF-008 dissociation (§HR-11) | HR referral | `detached`, `outside my body`, `watching myself` |
| CF-009 psychosis | HR referral | `detached` (⊂ "i feel detached from reality") |
| CF-007 mania | HR referral | `thoughts are racing` |

**Why this is a disposition risk, not just a copy overlap.** panic_override force-grounds only on a CLEAN
safety_check turn — i.e. precisely when the HR keyword detector did NOT fire (a recall miss). So an HR-class
presentation phrased so the HR lexicon misses it but panic_override's surface catches it — a mania disclosure
*"my heart's racing and I feel unstoppable,"* a psychosis-adjacent *"I feel detached and something's
watching"* — would be handed a **grounding exercise**. That is the doc's **§HR no-skill rule** AND **L151's
grounding-intensifies contraindication** violated in one move, under a sheet that presented itself as a panic
mechanism. So item 1's confirm is a **correction, not a courtesy**: what the 07-28 sheet *authorized* (force-
ground panic when clean) and what the code *does* (force-ground anything in a surface spanning the whole HR
lexicon) differ; "pure-panic only" aligns the code to what you actually signed.

---

## 2. panic_override's downgrade precondition — a cardiac finding (your call)
Separate from derealization, and it should not wait. panic_override downgrades a case from crisis when there are
**no medical_flags** — i.e. **"D1 didn't fire."** A live prod probe proved D1's red-flag surface does **not**
intercept panic air-hunger ("can't breathe"). So a cardiac event presenting as *"going to die + can't breathe"*
(no chest word, no harm word) → D1 empty → **force-grounded**, losing the crisis card's 999 prompt. The 07-28 sheet
weighed the passive-SI residual (and you set the conservative dial for it) but did not surface **this** one.

> **The downgrade precondition for the "going to die + can't breathe" class:**
> ▢ must be **actually medically screened clean**, not merely "D1 silent" (needs a screen — a two-turn ask, its own build); or
> ▢ that case **stays at crisis** as a knowing residual — the fail-safe reading of your own Ruling 3 (downgrade
>   permitted *with a clean screen*; no single-turn clean screen exists → no downgrade → keep crisis). ▢ discuss

(The earlier three-shapes veto ask is superseded by panic_override existing; its *content* — the shapes and the
actually-screened-clean requirement — is the review standard panic_override now has to meet.)

---

## 3. Process fix — a disposition-ownership registry (Vee + PO)
This is the **second** time two parallel sessions built overlapping safety mechanisms against the same doc
section, each with a clinician sheet, neither aware of the other, caught only at deploy time (the E7 pattern, now
with *conflicting signed rulings*). Memory notes have not stopped it. The durable fix is structural: a single
**disposition-ownership registry** (`docs/superpowers/governance/disposition_ownership.json` + a check) that
declares which mechanism owns which utterance class, so a colliding sheet is caught **before** it reaches your
signature — you are never asked to sign two sheets that overlap without being told.

Proposed as the project's **third refusal-property**: the conformance runner refuses a config-mismatched
measurement; the corpus guard refuses draft normativity; **sign-off prep refuses un-reconciled disposition
overlap.** A v1 registry + `scripts/check_disposition_ownership.py` (flags any two safety mechanisms whose match
sets overlap without a declared, precedence-resolved owner) is proposed alongside this packet — the derealization
conflict is its first caught case, added as a regression fixture.
> ▢ approve the registry as the pre-sign-off gate  ▢ discuss

---

**On item 1's confirm:** CF-010 flips alone (its clean delta: §1c derealization row moves), panic_override is
remediated to pure-panic scope, item 2 rules its precondition, and each re-measures separately — the
two-clean-deltas sequence restored.

---

## STATUS NOTE (2026-07-29) — the §1c premise SHIFTED under you; read before ruling item 1
A prod-HTTP conformance measurement (served number of record, prod `09013f19`) plus a §1c stability drive
(5 rows × 3, deterministic) found that **the §1c crisis over-escalation — the iatrogenic crisis card that
made Part A urgent — is GONE.** The `a16b0a02` classifier pins (`SAGE_CLASSIFIER_SEED` + provider pin) made
intent_route deterministic and it no longer misfires panic/derealization → crisis. All five §1c rows now show
**zero crisis, stable across runs.**

But it did NOT settle §1c *correctly* — it traded over-firing for **under-firing**: 3/5 rows (including the #2
derealization row "everything feels unreal and I can't take this") now route to **presence_only**, not a skill
or referral. So:
- **CF-010 (derealization → anxiety referral) is still the doc-correct disposition (L151)** — nothing about
  that changed. Ruling item 1 (derealization is referral, not panic_override's grounding) still stands on the doc.
- **What changed is the URGENCY, not the direction.** §1c's live problem is no longer an iatrogenic crisis card;
  it's under-response (presence). Part A becomes *correct-by-construction replacing correct-by-luck* — the
  Rule-4 point holds (an LLM incidentally not misfiring is not a deterministic guarantee), so CF-010 is still
  architecturally right, but its FLIP is now a scheduling decision, not a safety fix.
- **You are not ruling on a premise that shifted:** item 1 (referral vs ground) is unaffected; only the
  before/after urgency framing is. This note is here so that's explicit.

---

## STATUS UPDATE (2026-07-30) — one side of item 1 is now LIVE on prod; this packet is now post-flip reconciliation

Since the note above, the served state changed. Read this last, rule at this urgency:

- **`SAGE_PANIC_GROUNDING_OVERRIDE` is `true` on prod.** It is recorded in the flag register
  (`config/prod_flags.yaml`, value seeded 2026-07-29 from the serving readback and readback-verified), shipped
  by the owner-commanded parallel stream (RCA closure PR#388). **`SAGE_DEREALIZATION_DETECTION` (CF-010)
  remains OFF** pending your copy sign-off. So the interim served disposition for a safety-check-clean
  derealization disclosure that the LLM re-flags as crisis is **ground** — the direction L151 names as the
  contraindication — wherever the predicate fires.
- **This is signature-covered, not rogue.** Your signed 07-28 sheet approved the §1c-A set "as proposed," and
  that set contains *"detachment / derealization."* The question is therefore not "did engineering ship past
  you" — it is item 1 exactly as written: the sheet never connected that set to L151 or your 07-21 ruling, and
  there are now **two of your signatures pointing opposite ways on the same presentation slice, one of them
  serving.** Item 1 asks which governs.
- **Live exposure is narrow but real.** The classifier pins mean intent_route now rarely re-flags §1c rows as
  crisis (the 07-29 note: most derealization rows land presence_only, the override never firing). The override
  grounds only the residual phrasings the pinned classifier still over-flags. Narrow is not none; the
  mechanism serves.
- **Item 2 (cardiac precondition) is live on the same flip.** The signed sheet's trade-off paragraph weighed
  the passive-SI residual; the *"going to die + can't breathe, D1 silent"* class it did not surface is now
  serving behavior. Item 2's ask is unchanged, upgraded from latent to live.
- **No interim flag-off is requested.** The served state carries your 07-28 signature and the deploy owner's
  command; unwinding it ahead of your ruling would itself contradict a signed record. The ask is instead:
  rule items 1 and 2 at served-behavior urgency.
- **What unblocks CF-010 — item 1 alone (CORRECTED 2026-07-30, second verification):** your copy
  ratification is **already recorded and pinned** — `derealization_referral_en/ar` sit in
  `signed_clinical_fields.json` (commit `aea60720`, "Vee ratified 2026-07-28 — copy signed, flip-ready"),
  wording + resource set (National + SAKINA 24/7, no 999) with full signoff provenance. An earlier revision
  of this note claimed the fields were "never pinned" — that was a verification error on our side (the check
  read the manifest wrong, and the ask-doc's checkbox section was never updated to reflect the recorded
  ratification; a doc-hygiene fix rides the flip PR). **Nothing further is needed from you on the copy.**
  With item 1 confirmed: CF-010 flips **alone** at its higher precedence (crisis > medical > hr >
  derealization > panic-grounding; the two-mechanism composition was measured with both flags on) → grounding
  is confined to pure panic → the pure-panic scoping edit of panic_override's match set closes the four
  HR-family overlaps in the annex.

*(Register hygiene, not for Vee: the register row carries the 07-28 signature only as a `note:`; a follow-up
register PR should add `signed_value: "true"` + `signature_ref:` pointing at the signed boundary sheet so CI
pins it — and if item 1 rules referral, that same PR records the scoping remediation.)*
