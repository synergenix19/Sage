# Harm-Intrusive Veto — Clinician Sign-Off Packet (expedited)

**Date:** 2026-07-08 · **Channel:** same expedited path as the OCD-compulsion veto sign-off · **Branch:** `feat/harm-intrusive-veto` @ `5852ea1` (PR-ready, not merged, not deployed) · **Asking for:** clinician sign-off on the pattern lexicon (below), plus a dated ruling on the safeguarding interim (§4).

## What this is
A deterministic Stage-1 veto (mirrors the OCD-compulsion veto exactly) that stops postpartum/parental harm-intrusive disclosures being routed to a self-help skill (worry_time / imagery) — the iatrogenic routing found live in prod, which is also a **documented BOT BEHAVIOUR spec deviation** (spec: OCD/intrusive content → professional referral, "Worry Tree can reinforce compulsive patterns"). Destination for now = today's bare abstain → Node 3 (empathic clarification). No schema change.

**It is a stopgap, by design.** Keyword patterns are a deterministic *guardrail*; they are brittle across phrasing (the same weakness that caused the leak). The aligned target is a **semantic classifier (S2-MARBERT, Gap #65)** trained on the audit's paraphrase data — the keyword lexicon buys safety now while that is built. Do not read this list as the destination.

## Before / after evidence
Expanded harm corpus (fixture commit `9642846`; the failing worry-framed phrasing + paraphrases + a terse control added). Harm-domain skill-absorptions:

| Arm | before veto | after veto |
|---|---|---|
| V1 (flags-off) | leaking | **0** |
| V2 (fp32, sep 11.07) | 4 | **0** |

Zero self-help absorptions of harm-intrusive disclosures on both arms. Tests: veto suite 23, combined byte-identical + OCD + routing_eval 184.

## The lexicon (40 patterns), grouped so boundary cases read as classes

**Group A — intrusive-framed (8), unambiguous self-disclosure, near-zero false-positive:**
`intrusive image(s) of harming` / `... of hurting`, `intrusive thought(s) of harming` / `... of hurting`.

**Group B — bare harm-to-child (26), broad-but-safe:**
`harm(ing)/hurt(ing) my baby / newborn / child / son / daughter / the baby`, `images/thoughts of harming/hurting my baby / child`. These are the ones that also match negation and third-party (see §2/§4).

**Group C — specific-method (6):**
`smother(ing) my baby`, `drowning my baby`, `dropping my baby on purpose`, `throwing my baby`, `stabbing my baby`.

## Two review notes

### §2 — Negation / scope: broad-now vs tightened (recommend broad-now)
Group B matches "I would **never** harm my baby" (reassurance) → over-vetoes to Node 3. **Safe** (abstain, never a skill), mildly odd UX. The decision is an asymmetry, not a preference:
- **Tighten** (require intrusive-framing) → fewer false-positive abstains, but **reopens false-negative risk** on phrasings the tighter patterns don't enumerate — and the postpartum finding just proved phrasing variance is exactly where this class leaks.
- **Broad-now** → some odd-but-safe abstains, zero reopened leak.
**Engineering recommendation: broad-now.** Tightening is available later through the CMS on the **audit's paraphrase data** (and folds into the semantic classifier), not by a guess today. Clinician has final say; the risk direction on each side is stated so the ruling is informed.

### §4 — Safeguarding: a named interim gap, NOT a reviewer's-choice curiosity ⚠️
"My partner is harming my baby" is caught by Group B → currently abstains to Node 3. This is **not** an over-veto oddity — it is a **report of possible active child harm**, a different territory from anything Stage 1 was scoped for.
- (a) **Current behavior:** generic abstain → Node 3's empathic clarification (holds space, never misroutes to self-help).
- (b) **Correct disposition:** a **safeguarding/referral family with its own escalation posture** — arguably **L3-adjacent, not L2** (clinician rules the tier).
- (c) **This is flagged NOW as a named, dated interim gap.** The interim (abstain, holds space) is acceptable *as an interim* precisely because it doesn't misroute — but the clinician is asked to **rule its acceptable duration (a clock, days-not-weeks)** and to **prioritize the safeguarding family's design**, not leave it to be "mapped by the audit eventually." A safeguarding gap parked silently in a backlog reads very differently in retrospect. It is **pre-registered as a known-priority row** in the audit family backlog.

## Deploy plan the sign-off unblocks
On sign-off: command merges → deploy behind the standing gates (ancestry-contains-veto, `/health` routing_mode + reranker + build_sha, prod probe) → **live probe pair:** (1) worry-framed harm-intrusive → **abstains** (leak closed); (2) ordinary parenting worry → **still routes** to a skill (no over-suppression). Then the verdict artifact is annotated with the expanded-corpus numbers.

## The ask
1. Sign the lexicon (or rule broad-now vs tightened per §2).
2. Rule the §4 safeguarding interim: acceptable-for-how-long + prioritize the safeguarding family design.
