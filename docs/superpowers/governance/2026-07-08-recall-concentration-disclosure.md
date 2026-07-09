# Recall-Concentration Disclosure — to PO + Clinical Lead (files with #202, relay with PR #204)

**This is a disclosure, not a re-litigation.** The V2 aggregate gate numbers were true, the gates held, there is **no rollback**. This discloses a finding that reframes the *distribution assumption* underneath a number you signed — the same honesty rule as the deploy note.

## What you signed vs what the audit found
The −4.7pp in_scope recall acceptance was framed as an **aggregate** cost with "19 of 28 lost cases recoverable soft-abstains → Node 3 empathic clarification." The BOT BEHAVIOUR Layer-1 audit (spec_version_sha=56fde86) shows the loss is **concentrated, not diffuse**:
- **§3a Low mood / withdrawal → 0/5** (fully suppressed), plus the same shape across **§7b, §1e, §6c, §6b, §7c**.
- Diagnosed cause (per-case trace): the reranker scores natural depression/withdrawal phrasing below τ and vetoes the legitimate `behavioral_activation` keyword match (`keyword_rerank_veto`). Not a safety leak — these abstain to Node 3.

## Why this reframes the acceptance
A depressed, withdrawing user population that can **never reach behavioral_activation** — only warm clarification, turn after turn — is clinically different from a diffuse recall haircut. For that presentation specifically, **endless empathic holding without a pathway to activation is not neutral.** The aggregate number was accurate; it hid this failure *shape*.

## The criterion implication (the proactive part — for signature)
**Add a per-pathway recall floor** for core clinical pathways alongside the aggregate 51.77% tripwire. Rationale: the aggregate demonstrably hides a fully-suppressed pathway. With a per-pathway floor, the next concentrated gap is a **gate failure**, not an audit discovery. This is the structural fix that makes this class non-recurring.

## What is NOT asked of the humans
Nothing about the engineering fix waits on you. The fix (BA exemplar enrichment, #202) ships on the standing pipeline this week under the full signed gate. The clinician's role is **~30 seconds**: confirm the depression-withdrawal vs passive-SI phrasing boundary IF the fix touches it (same channel as the two veto sign-offs). PO+clinician: this disclosure + the per-pathway floor for signature.

## Packet order (severity-first)
1. THIS §3a concentration disclosure + per-pathway floor.
2. The three presence_only Class-A rulings (PR #204 backlog): §3d offload, §7a company, S2a grief.


## RESOLVED 2026-07-09 — fix deployed prod 7f2b30d (BA recall recovered, id_oos held). Per-pathway floor signed + in gate criteria.
