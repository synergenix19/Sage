# §1c reconciliation — one packet to Vee (2026-07-28)

Two §1c Part A mechanisms were built in parallel and dispose the same utterance oppositely (HALT record:
`2026-07-28-1c-derealization-disposition-conflict-HALT.md`). Both are flag-OFF/inert — no live conflict. Three
items: one clinical confirm, one clinical finding, one process fix. Neither mechanism flips until item 1 rules.

---

## 1. Derealization — a SCOPE confirm, not a re-deliberation (one line)
You adjudicated derealization **once**, on **07-21** (1a–1d): you saw the doc's §1c **L151** guard —
*"grounding/mindfulness can intensify dissociative states; escalate to **referral** rather than presenting the
standard tools"* — and you ruled **referral**. CF-010 implements that.

On **07-28**, the panic-grounding sheet (`part-a-1c-boundary-to-vee.md`) asked you about **panic** force-grounding.
It **did not surface derealization as a question** — but the terms `"unreal"`, `"not real"`, `"derealiz"`,
`"detached"`, `"outside my body"`, `"watching myself"` rode into that mechanism's match set as lexical neighbors of
panic. So `"everything feels unreal"` now force-**grounds** under it — the exact state L151 says grounding can
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
