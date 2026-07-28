# §1c anxiety-track referral — terminal copy for Vee's ratification (2026-07-28)

Part A builds the Node-1 derealization flag (1a) → **anxiety-track referral** (1b), routed at safety altitude,
rank 4 (crisis > medical > hr > derealization). Mechanism, strings (1d), terminal *type* are ruled; this is the
one thing unsigned: the terminal's copy. It renders ONE deterministic signed message (no LLM); ships flag-gated
OFF / inert until you ratify this + it is pinned + flipped (mirrors HR-1 / Node-8).

## What you ratify: the TEMPLATE (numbers stay owned by the single source)
Every phone number is a `{{...}}` placeholder resolved at render from the ONE source of truth
(`config.CRISIS_CONFIG` / `CRISIS_RESOURCES`) — NOT a literal in this copy. So what is pinned + drift-guarded is
the template; the digits cannot drift from the crisis card. (Integrity fix 2026-07-28: SAKINA was a hardcoded
literal; it is now `{{crisis_alt_24_7}}`, derived from the same source.)

**EN template:**
> «What you're describing — feeling like things around you aren't real, or feeling disconnected from
> yourself — can happen when anxiety becomes very intense. It's real, it's more common than you'd think, and
> it's something a mental health professional can help you understand and work through. In the UAE, you can
> reach the `{{crisis_label}}` on `{{crisis_number}}`, free, `{{crisis_hours}}`; and at any hour, day or night,
> the Abu Dhabi support line `{{crisis_alt_24_7}}` is available free, 24/7. If you or someone else is in
> immediate danger, call emergency services on `{{crisis_emergency}}`. You don't have to navigate this alone.»

**EN resolved (what the user sees today):**
> «…you can reach the National Mental Support Line on 800-HOPE (800-4673), free, 8am–8pm daily; and at any hour,
> day or night, the Abu Dhabi support line 800-SAKINA (800-725462) is available free, 24/7. If you or someone
> else is in immediate danger, call emergency services on 999. You don't have to navigate this alone.»

**AR template / resolved** — the Khaleeji parallel, same placeholders, hours localized (in
`safety/derealization_copy.py`).

## The register decision — YOURS, name it don't inherit it (severity/tier call)
The template above carries the **full HR resource stack**: National line + hours, SAKINA 24/7, **and 999
emergency**. But this terminal is deliberately the SOFTER tier — its register is "anxiety can do this, worth
talking to someone soon," not a psychiatric/emergency referral. It is also reached ONLY when the turn is NOT a
crisis (precedence crisis > … > derealization), so active danger is already handled by the crisis path. The
doc's §1c guard says "escalate to referral," not "render the full emergency stack." So the resource set is a
real clinical choice, not a single-sourcing default:

- ☐ **B — HOPE + SAKINA, drop the 999 emergency line (RECOMMENDED).** Fits the see-someone-soon tier; avoids an
  emergency framing on a message that is explicitly not an emergency (the over-escalation shape in copy form).
- ☐ **A — keep the full stack (HOPE + SAKINA + 999).** Belt-and-suspenders universal safety footer.
- ☐ edit

## Copy sign-off
→ ☐ approve template wording (EN+AR) ☐ edit

## On approval (eng)
Apply your register choice (drop the `{{crisis_emergency}}` line if B), pin `derealization_referral_en/ar`
(provenance = this ratification + your 1a–1d), deploy the inert mechanism, then flip
`SAGE_DEREALIZATION_DETECTION=true` **alone** (one safety change), guarded re-measure of the §1c rows vs v5's
11/36. Follow-up (not this sign-off): migrate the HR referral's still-literal SAKINA to `{{crisis_alt_24_7}}`
too, so both terminals single-source it (needs an HR re-sign, tracked separately).
