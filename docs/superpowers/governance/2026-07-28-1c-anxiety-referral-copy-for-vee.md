# §1c anxiety-track referral — terminal copy for Vee (2026-07-28)

Part A: Node-1 derealization flag (1a) → **anxiety-track referral** (1b), safety altitude, rank 4. Mechanism,
strings (1d), terminal type are ruled; the copy is the one unsigned piece. It renders ONE deterministic signed
message (no LLM); ships flag-gated OFF / inert until you ratify this, it is pinned, and flipped.

## Final recommendation (aligned to the BOT BEHAVIOUR doc + single source of numbers)

**Register/resources: National line + SAKINA 24/7, NO 999.** This is doc-grounded, not a preference:
- §1c L151: dissociation / panic-with-derealization → "**escalate to referral** rather than presenting the
  standard tools" — the see-someone-soon tier.
- L1830 reserves "**emergency services (999)**" for the crisis/danger tier and states it is for "now, **not
  'see someone soon.'**"
- This terminal is reached ONLY when the turn is not a crisis (precedence crisis > … > derealization), so
  active danger is already handled by the crisis path. Putting 999 here renders the crisis-tier resource on a
  referral-tier message — the §1c over-escalation shape, in copy form.

**Numbers: single-sourced.** Every phone number is a `{{...}}` placeholder resolved from the ONE source
(`CRISIS_CONFIG` / `CRISIS_RESOURCES`); SAKINA is now `{{crisis_alt_24_7}}`, not a literal. You ratify the
TEMPLATE; the digits cannot drift from the crisis card.

## The copy (recommended version)

**EN template:**
> «What you're describing — feeling like things around you aren't real, or feeling disconnected from
> yourself — can happen when anxiety becomes very intense. It's real, it's more common than you'd think, and
> it's something a mental health professional can help you understand and work through. In the UAE, you can
> reach the `{{crisis_label}}` on `{{crisis_number}}`, free, `{{crisis_hours}}`; and at any hour, day or night,
> the Abu Dhabi support line `{{crisis_alt_24_7}}` is available free, 24/7. You don't have to navigate this
> alone.»

**EN resolved (what the user sees):**
> «…you can reach the National Mental Support Line on 800-HOPE (800-4673), free, 8am–8pm daily; and at any
> hour, day or night, the Abu Dhabi support line 800-SAKINA (800-725462) is available free, 24/7. You don't
> have to navigate this alone.»

**AR** — the Khaleeji parallel, same placeholders, hours localised (`safety/derealization_copy.py`).

## Your call — two ticks

→ **Wording** ☐ approve (EN+AR) ☐ edit
→ **Resources** ☐ approve (National + SAKINA 24/7, no 999 — recommended, doc L151/L1830) ☐ add 999 back ☐ edit

## On approval (eng)
Pin `derealization_referral_en/ar` (provenance = this ratification + your 1a–1d), deploy the inert mechanism,
flip `SAGE_DEREALIZATION_DETECTION=true` **alone**, guarded re-measure of the §1c rows vs v5's 11/36. Then the
#0-class veto three-shapes ask (separate). Follow-up: migrate the HR referral's still-literal SAKINA to
`{{crisis_alt_24_7}}` too (needs an HR re-sign, tracked separately).
