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

## ⚠️ PRE-FLIP MEASUREMENT (2026-07-18): the allowlist gate rejects 100% — it is a TEMPLATE SWAP
Measured the built gate against the live terminal (12 samples, 4 HR classes × 3): **12/12 rejected.**
Most rejections are NOT §5 violations — neutral outputs ("Hearing voices... is important to discuss",
"Feeling amazing... is something important") that simply don't carry the ratified "what you're describing"
phrase. So the allowlist gate does not CORRECT drift; it REPLACES the LLM-composed psychosis referral
with the fixed template EVERY time. Allowlist-over-denylist inverts the failure economics: any neutral
phrasing off the ratified list is rejected. **This is a product/clinical decision (template-swap vs
targeted guard), NOT eng's to flip silently** — routed to Vee: `2026-07-18-vee-open-decisions-approval-sheet.md`
Decision 2. WIRING PAUSED until she rules A (accept template swap; eng+arch rec) or B (targeted denylist
guard, keeps LLM variety). The measurement is the point of "measure before flip": at 100% the gate is a
template swap, which may be the right outcome for the highest-stakes terminal but must be a KNOWING choice.
