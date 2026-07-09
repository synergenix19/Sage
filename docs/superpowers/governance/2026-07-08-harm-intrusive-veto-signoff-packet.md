# Harm-Intrusive Veto — Clinician Sign-Off Packet (expedited)

**Date:** 2026-07-08 · **STATUS: APPROVED by clinical lead 2026-07-08** (broad lexicon approved as written; safeguarding endorsed as #1 production family; see Sign-off Record + Clinical boundaries below) · **Channel:** same expedited path as the OCD-compulsion veto sign-off · **Branch:** `feat/harm-intrusive-veto` @ `5852ea1` (PR-ready, not merged, not deployed) · **Asking for:** clinician sign-off on the pattern lexicon (below), plus a dated ruling on the safeguarding interim (§4).

## What this is
A deterministic Stage-1 veto (mirrors the OCD-compulsion veto exactly) that stops postpartum/parental harm-intrusive disclosures being routed to a self-help skill (worry_time / imagery) — the iatrogenic routing found live in prod, which is also a **documented BOT BEHAVIOUR spec deviation** (spec: OCD/intrusive content → professional referral, "Worry Tree can reinforce compulsive patterns"). Destination for now = today's bare abstain → Node 3 (empathic clarification). No schema change.

**This is a PERMANENT Tier-1 deterministic guardrail**, not a stopgap — like the OCD veto and crisis keywords, it stays in production. A semantic classifier (S2-MARBERT, Gap #65) is added LATER as a second layer for generalization (defense in depth); it does not replace the deterministic floor. Both coexist.

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
- (c) **The safeguarding family is built as a proper production family — no interim, no clock, no temporary signpost.** It is the **#1 priority family** in the containment backlog. Until it ships, the current behavior (harm-intrusive veto incidentally catching some safeguarding phrasings → safe abstain to Node 3, never a self-help skill) simply IS the current state, not interim work; when the real family lands it takes precedence. Pre-registered as a known-priority Class-A row. **Clinician rules the tier (recommend L3-adjacent).**

## Deploy plan the sign-off unblocks
On sign-off: command merges → deploy behind the standing gates (ancestry-contains-veto, `/health` routing_mode + reranker + build_sha, prod probe) → **live probe pair:** (1) worry-framed harm-intrusive → **abstains** (leak closed); (2) ordinary parenting worry → **still routes** to a skill (no over-suppression). Then the verdict artifact is annotated with the expanded-corpus numbers.

## The ask
1. Sign the lexicon (or rule broad-now vs tightened per §2).
2. Confirm safeguarding as the #1 production family + rule its tier (recommend L3-adjacent). No interim.


## Clinical boundary — the ego-syntonic / psychosis line (clinician-added)
Intrusive thoughts are **ego-DYSTONIC** — the person is aware of and distressed by them; this distinguishes them from the delusional thoughts of **psychosis** (a medical emergency). **Inversion that matters:** "it scares me so much" is a **reassuring feature** — the distress marks the thought ego-dystonic (no infant risk). The danger signal is the OPPOSITE: **absence of distress about the harm thought, ego-syntonic framing, or command-hallucination language** → this is a **crisis-path signal, NOT a containment continuation.** Split: first-person ego-dystonic intrusion → containment/referral; third-party or behavioural-indication report → safeguarding. Sage **screens and escalates; it never adjudicates** (professional-assessment territory — reinforces no-autonomous-clearance).

## Sign-off Record
- **2026-07-08 — Clinical lead: APPROVED.** (1) Broad 40-pattern lexicon approved as written — epidemiology-backed (harm-intrusive thoughts occur in ~half of parents of infants; disclosure is hard-won; the response determines re-disclosure; asymmetry favours broad). Permanent-Tier-1-guardrail framing approved. (2) Safeguarding endorsed as #1 production family; tier = **referral-with-urgency + mandatory L2-style clinician review, distinct from the suicide-crisis protocol** (clinician rules exact placement; L3-adjacent). **Priority carries a target date on the record** (below). (3) Ego-syntonic/psychosis boundary added (above) — one deterministic branch in the Stage-2 template. (4) Phasing approved; psychoeducation is itself therapeutic (parents appreciating these thoughts are common → they diminish).
- **Safeguarding family TARGET DATE (on the record):** **2026-07-31** — the first family delivered by the containment pathway; PO to confirm. (Dated per the project's dated-ruling discipline — a #1 priority without a date becomes a #4.)
