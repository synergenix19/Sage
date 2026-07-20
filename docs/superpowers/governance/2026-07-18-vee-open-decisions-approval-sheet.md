# Clinician approval sheet — Vee — open decisions (2026-07-18)

Two decisions need your ruling. Everything else on the board is engineering-done and needs no clinician
input (medical-P0 disclosure fix = PR#353 green; Node-8 gate CORE = PR#354, inert). Each item below is
approve / edit / reject, with a recommendation aligned to the BOT BEHAVIOUR doc, our architecture, and
best practice. Nothing ships until you rule.

---

## DECISION 1 — §1c derealization routing (4 sub-rulings)
Full detail + verbatim doc quotes: `2026-07-18-cf008-dissociation-ratify-list-vee.md`. Summary of what
needs your signature (the strings + the doc-vs-design conflict are clinical, not eng):

- **1a MECHANISM** — new Node-1 clinical flag routed at the safety altitude (NOT extend the verbatim §HR
  CF-008 list, NOT a post-intent guard). Rec: **approve** (keeps §HR-11 verbatim + closes the Rule-4
  violation deterministically). → ☐ approve ☐ edit ☐ reject
- **1b TERMINAL** — the softer **anxiety-track referral**, reserve the HR terminal for the §HR-11 register.
  (Refines your earlier "HR referral" — on the doc these are §1c anxiety phrases.) → ☐ approve ☐ edit ☐ HR terminal instead
- **1c DOC-vs-DESIGN CONFLICT** — the doc §1c guard sends "panic attack with derealization" to REFERRAL;
  the HR-1 design control says "§1c, not HR." Opposed. Rec: **doc wins → anxiety-track referral; correct
  the design control.** → ☐ doc wins (rec) ☐ grounding skill (correct the doc) ☐ edit
- **1d SIGN THE STRINGS** — a Node-1 lexicon reads raw input and CANNOT read context, so your line must be
  STRING-separable. Add `everything feels unreal`, `i feel disconnected from my body`; keep panic-context
  ("everything felt unreal DURING the panic attack") as §1c controls. → ☐ ratify strings ☐ edit list

---

## DECISION 2 — Node-8 §5 neutrality gate: it is a TEMPLATE SWAP, not a guard (NEW, from measurement)

**Context.** The interim prompt-nudge left a ruled §5 drift live at ~1/4 of paranoia terminals. The
permanent fix is a deterministic Node-8 gate that enforces the account-frame you ratified. Before flipping
it, we measured its real effect on the live terminal: **it rejects 100% (12/12) of current HR-referral
outputs and replaces them with the fixed templated message.** Most rejected outputs are NOT §5 violations
— they are perfectly neutral ("Hearing voices that others can't hear is something important to discuss…",
"Feeling amazing and unstoppable… is something important…"); they simply don't use the exact ratified
"what you're describing" phrasing. So the gate as built does not *correct drift* — it *replaces the
LLM-composed psychosis referral with one deterministic templated message, every time.*

**That is a real product/clinical choice, and it's yours + PO's to make, not a silent side-effect:**

- **Option A — ACCEPT the template swap.** The psychosis referral becomes ONE deterministic, signed,
  clinician-authored message every time. Pros: §5-neutrality guaranteed BY CONSTRUCTION (the actual goal);
  aligns with the architecture's safety-exit terminal class (crisis/medical/HR-Stage-2 are all templated
  copy); no LLM variance on the highest-stakes terminal. Cons: loses the LLM's warmth/personalisation —
  every psychosis-referral user reads the same words. **Eng+arch recommendation: A** — deterministic copy
  on the highest-stakes safety terminal is the defensible, arguably desirable outcome, and it's what
  "cannot vary" actually means. If A, you approve the ONE templated message text (draft = the terminal's
  own ratified account-frame copy; your seed ratification already carries its accuracy).
  → ☐ approve template swap (rec) + the message text

- **Option B — TARGETED guard instead (keep the LLM terminal).** Reject only outputs that actually state
  the feared content as fact (a denylist of the ruled fact-in-world frames), accept varied neutral
  openers. Pros: preserves LLM warmth/variety. Cons: a denylist is open-ended — it corrects the frames
  we've seen and can miss novel violation phrasings, so the §5 guarantee is weaker than A (reduction, not
  elimination, on unseen frames). → ☐ prefer B (targeted guard, keep LLM variety)

- ☐ discuss

*Whichever you pick changes what the user receives in the COMMON case, not just the drift case — which is
exactly why it's surfaced here before the flip rather than discovered from audit rows afterward.*

---

**After your rulings:** Decision 1 → build the Node-1 flag + anxiety referral (loader test gated day one,
both-direction fixtures). Decision 2 → wire Node-8 per A or B, flag-gated, rejections audit-logged, flip.
The Node-8 flip is the last thing standing between the ruled §5 drift and its elimination.
