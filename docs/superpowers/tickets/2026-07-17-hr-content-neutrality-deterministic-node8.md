# Ticket: §5 content-neutrality as a DETERMINISTIC output_gate (Node 8) rule — Stage-2

**Origin:** HR-1 Stage 1 conformance, finding #1, ruled EDIT by Vee (clinical lead) 2026-07-17.
See `docs/superpowers/governance/2026-07-17-hr1-stage1-clinician-touchpoint-vee.md`.

**The gap the interim fix does NOT close.** The Stage-1 `psychotic_referral` terminal is
LLM-composed. The interim correction (prompt-nudge toward the "what you're describing" account frame,
landed in `psychotic_referral.json`) reduces §5 fact-assertion drift **probabilistically** — it does
not eliminate it. `paranoia#1` proved a real §5 violation can be sampled; nudging the prompt lowers
its rate but a probabilistic terminal is only ever verified by sampling, never by construction.

**The deterministic home (Vee-endorsed, matches v7 design).** In the full v7 architecture,
content-neutrality is a **Node 8 / output_gate deterministic rule**, not LLM discretion. Stage-2 must:

1. Land the HR terminal's **deterministic supportive-message copy pools** (the standardized message,
   session-hash pick, name-only interpolation, no content echo) so the neutral account-frame is
   guaranteed by construction, not generation.
2. Add an **output_gate content-neutrality check** on the HR terminal path that rejects/rewrites any
   output which states the feared content as fact-in-world (the §5 line). This is the deterministic
   assertion that CAN be tested behaviorally (unlike the probabilistic prompt-nudge).

**Pairing (do not land piecemeal).** This rides with the paired Stage-2 unit: §1 single 0-10 distress
question, §3 distress-rating 999-vs-refer split, the copy pools, and the A4 6-vs-7 escalate-only
threshold. All gated on the A7 re-engagement prerequisite. Landing the copy pools without the
distress terminal, or vice versa, leaves the terminal asking a question it cannot act on.

**Verification note carried forward.** Stage-1's "63/63" is point-in-time evidence on a probabilistic
terminal (number integrity held across 8 runs = strong evidence, not proof). Stage-2's deterministic
pool + Node 8 rule are what convert "held across 8 runs" into "cannot vary." The interim prompt-nudge's
effect is confirmed only by re-running the conformance sampling post-deploy (drift rate down, paranoia
frame report-side), NOT by a unit test — a deterministic unit test only becomes possible at Stage-2.

## Copy-pool seed — the sampled residual failure mode (input to this ticket's design)

The interim prompt-nudge shifted the paranoia frame to the clean account-frame in 3/4 post-deploy
runs. The 1/4 residual is the exact failure mode the deterministic copy pool must design against:

- **Prohibited (sampled residual):** *"Feeling like people are following and watching you can be very
  distressing…"* — restates the feared content as real in the second person, even under a "feeling
  like" prefix. Routed to Vee (touchpoint doc, two-part ask): (a) does it clear §5, (b) her preferred
  neutral frame.
- **Target (won 3/4):** *"What you're describing sounds really important…"* — marks it as the user's
  account, does not state the content as real.

**Design rule for the pool:** the standardized supportive message must use the account-frame by
construction and must NEVER interpolate or restate the user's feared content. The Node-8 check rejects
any HR-terminal output whose subject clause states the feared content as real (the deterministic
equivalent of the §5 line).

**✅ SEED RATIFIED (Vee, 2026-07-17):** the pool opens on **"What you're describing…" / "The experience
you're describing…"** with the hard invariant: **the supportive message never takes the feared content
as its subject and never restates it as occurring.** Both the "feeling like [content]" and the
"experiencing [content] happening to you" frames are ruled §5 misses (paranoia#1 + the 1/4 residual) —
the Node-8 check must reject BOTH. This is no longer blocked on a clinician answer; it is the spec.

**✅ DECISION (2026-07-17): DECOUPLED FROM A7, PROMOTED to the next deterministic piece.** The Node-8
content-neutrality CHECK is a guard on the EXISTING psychotic_referral output — it does NOT depend on
the two-turn distress terminal (the A7-blocked part). The premise that justified batching ("the
deterministic fix can't land until Stage-2") is therefore false, and what is on the other side is the
permanent fix for a clinician-RULED, live §5 miss (~1/4 of paranoia terminals). So the acceptance
window shrinks to match: build this as its own unit, ahead of the A7-blocked distress machinery.

**Sequence (do NOT reorder):** (1) loader-gate audit [DONE 2026-07-17, see
`2026-07-17-loader-gate-audit-findings.md`] → (2) build this Node-8 guard against Vee's ratified seed
with REJECT/ACCEPT fixtures → (3) confirm those fixtures actually FIRE under the gate (the Node-8 PR is
likely the first app-code PR to exercise the #350 gate fix — fold in that tripwire check) → (4) live =
residual zeroed by construction. Rest of Stage-2 stays A7-gated.

**Test spec (the upgrade over the interim — verified as ELIMINATION, not sampled reduction):** write
these fixtures BEFORE wiring. REJECT: paranoia#1's "experiencing [content]" frame AND the 1/4 "feeling
like [content]" frame (both ruled §5 misses). ACCEPT: the clean "what you're describing" frame. The
gate rejecting both ruled frames + passing the clean one IS the regression proof the accepted residual
is zeroed. Anchor on the behavior (does the guard reject/accept), never on a copy string
(see the medical-guard stale-prose-assertion finding in the audit — the failure mode of prose asserts).
