# Clinician Sign-off — Batched Relay (2026-07-10)

**One relay, every open decision.** Clinician turnaround is the only clock on this thread we don't control, so it is paid **once** here rather than per item. Ordered by urgency; each item is **tick / edit / reject**; evidence files linked. Route: same channel as prior copy sign-offs; PO relays.

> **STATUS — clinical sign-off APPROVED by Vee, 2026-07-10** (batch doc-verified against BOT BEHAVIOUR.docx by a 4-agent QA pass; no safety defects; 4 accuracy fixes applied pre-approval).
> - **ITEM 1 (OF-1 15 blurbs):** clinically approved → matrix rows move PARTIAL → CONFORMS-content (CONFORMS pending driven transcript).
> - **ITEM 2 (Wave-2 5 collapsed scripts):** clinically approved → clear to re-author the 5 skills.
> - **ITEM 0 (H4 crisis composition):** clinical accuracy of the doc's list confirmed. The **live-value change stays gated** — reversing GL-1 + verify-before-launch + the crisis-freeze lift are PO/operational decisions, not clinical-only. Not cleared to deploy by this approval alone.
> - **ITEM 3 (H3 ST-6 target):** confirm whether Vee's approval filled this blank or it remains open.

---

## ⚠️ ITEM 0 — URGENT (latency has a safety cost): crisis-resource composition (H4)

**Why this is first and urgent:** the live crisis card currently shows a **single** number (`800 46342`, labelled 24/7) that appears **nowhere** in the doc's canonical crisis table, and the doc's *primary* line is **8am–8pm, not 24/7**. A user in distress at 02:00 could be shown a number whose hours don't hold. The structure to fix this is built and value-preserving (PR #288); it is inert until this composition is ruled.

**Doc's canonical 5-entry table** (BOT BEHAVIOUR L2130–2146; doc flags *"verify before launch"*):

| Resource | Number | Hours (per doc) | Scope |
|---|---|---|---|
| Emergency | 999 | — | immediate danger |
| National Mental Support Line | 800-HOPE (800-4673) | 8am–8pm daily | national (primary) |
| Abu Dhabi 24/7 crisis line (800-SAKINA) | 800-725462 | 24/7, psychological first aid | regional |
| Dubai Health Authority | 800 111 | 24/7 | regional |
| Sharjah Child & Youth | 800 51115 | 9am–5pm Mon–Fri | youth |
| Nearest ER | — | out-of-hours / danger | fallback |

**Decisions needed (PO + clinical lead):**
1. ☐ Adopt this 5-entry composition  ☐ edit: ____________  ☐ keep current single `800 46342`
2. ⚠ This **REVERSES GL-1** (2026-07-09 ruling: `800 46342` + 24/7 correct/final). ☐ reversal confirmed intentional (doc is normative)  ☐ no — keep GL-1
3. **Verify-before-launch** (doc L2130 — numbers/hours can change): ☐ each number + hours verified current  ☐ verification call needed first

Full evidence: `docs/2026-07-10-section-H-clinician-queries.md` §H4. Frontend `crisis-config.ts` must mirror any change (separate consumer).

---

## ITEM 1 — Offer blurbs, 15 skills (OF-1)
Tick/edit each: current blurb beside its doc source. Until ticked these matrix rows are PARTIAL.
→ `docs/2026-07-10-OF-1-blurb-signoff-packet.md`

## ITEM 2 — Collapsed video-skill copy, 5 skills (Wave-2) — EN [Vee-APPROVED]
New all-at-once delivery scripts (H2 ruling): box breathing, PMR, mindfulness meditation, body scan, safe-place visualization. Tick/edit each proposed script.
→ `docs/2026-07-10-wave2-collapsed-copy-packet.md`

## ITEM 2b — Wave-2 collapsed copy, ARABIC translation (the Wave-2 re-land gate)
AR equivalents of the approved EN scripts. Wave-2 re-lands only when EN **and** AR are both signed. **Three cross-cutting rulings needed** (not just per-script ticks): (1) gender — feminine variants for female users; (2) safe-place **Islamic framing** — add prayer-space/mosque to the AR example list?; (3) mindfulness **back-off wording** is now the only in-delivery safety on the acceptance step — confirm AR strength.
→ `docs/2026-07-10-wave2-collapsed-copy-AR-signoff.md`

## ITEM 3 — ST-6 ceiling human-support target (H3)
A genuine blank: when High-tier TIPP shows no improvement, what concrete non-crisis resource is offered? Doc specifies none.
→ `docs/2026-07-10-section-H-clinician-queries.md` §H3

---

## Already answered (recorded, no action)
- **H1** — TIPP psychoed opener filled ("…don't push yourself beyond what feels safe") → **shipped** (PR #280).
- **H2** — Format=Video all-at-once delivery rule **ticked** → Wave-2 engineering built (PR #284).
