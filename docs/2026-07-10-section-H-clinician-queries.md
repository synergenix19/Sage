# Section-H — Clinician Decision Record (BOT BEHAVIOUR.docx spec queries)

**Date:** 2026-07-10 · **Route:** same channel as the copy sign-offs (PO relays) · **Format:** one item per query; **tick** (accept proposed default) / **edit** (reword) / **fill** (author supplies missing text) / **reject**.
**Why now:** H1 gates SG-2's full conformance (the truncated sentence sits beside the shipped cardiac caveat); H2 gates Wave-2 delivery semantics; H3 gates Wave-4 ceiling routing; H4 is a cross-normative crisis-config reconciliation. These are on the clinician-latency critical path — answers unblock work already staged.

---

## H1 — Complete the truncated High-tier TIPP psychoeducation sentence  ·  **FILL** (genuine blank)

**Question:** The High-Anxiety TIPP psychoeducation opener ends mid-sentence at *"Please note, don't "*. What is the intended full instruction?

**Verbatim evidence** (Category 3: High Anxiety → *3. Psychoeducation*):
- L185: `3. Psychoeducation`
- L186: `Folded into the skill itself, one sentence max:`
- L187: `"We're going to shock your system into calming down, step by step — just follow along. Please note, don't "`  ← **truncated here**
- L188 (already shipped verbatim as SG-2): `"Please check before trying this: the temperature step ... If you have a heart condition, an irregular heartbeat, or you're pregnant, please skip those two steps or check with a doctor first."`

**What we need:** the completed L187 sentence — what should the user be told *not* to do? And: is L187 a **separate** instruction, or should it merge into the L188 cardiac caveat (already live)? *(Note: L118 — cited earlier — is unrelated; it is a `STOPP` skill-table cell. The only truncation is L187.)*

**Decision (2026-07-10, PO):** ☑ **FILLED** → *"We're going to shock your system into calming down, step by step, just follow along. Please note, don't push yourself beyond what feels safe."* — a separate opener line preceding the L188 caveat. **Shipped:** dbt_tipp entry (commit `a6c0771`, PR #280).

---

## H2 — Is "Format = Video" a delivery rule?  ·  **TICK / EDIT** (proposed default below)

**Question:** When a skill's Format column says "Video", is it delivered all-at-once (whole asset in one turn) rather than turn-by-turn? Or is "Video" only a table label with no delivery semantics?

**Verbatim evidence:** "Video" appears as a Format-column value (Box Breathing, PMR, Mindfulness; Body Scan "Video/audio guided") **and** in incidental prose (the offer-ordering "lead with the video" note; the Guided Visualization *"short guided imagery video ... no activity required"* description). **None of it defines a delivery *cadence* for "Video"** — the only cadence prose in the doc is TIPP-specific. The only cadence prose is skill-specific and does *not* reference the label: L200 (TIPP, "Visual + guided conversation") *"one instruction at a time ... never all at once."*

**Proposed default sentence (for the clinician to tick or reword):**
> *"A skill whose Format is 'Video' or 'Video/audio guided' is delivered as a single all-at-once turn — the technique framing and its video together, then straight to the check-in — not the turn-by-turn, one-instruction-per-turn delivery used for guided-conversation skills such as TIPP. The five Video skills are: box breathing, progressive muscle relaxation, mindfulness meditation, body scan, guided/safe-place visualization."*

**Decision (2026-07-10, PO):** ☑ **TICKED** — adopted verbatim as the Wave-2 `delivery_format` rule. The five Video skills (box breathing, PMR, mindfulness meditation, body scan, guided/safe-place visualization) deliver **all-at-once** (technique framing + video → straight to check-in), vs. turn-by-turn for guided-conversation skills like TIPP. **Unblocks the Wave-2 build.**

---

## H3 — Name the ST-6 ceiling human-support target  ·  **FILL** (genuine blank)

**Question:** When High-tier TIPP produces no improvement and the loop-prevention ceiling fires (Section E), what concrete human-support target should be offered? The spec names none.

**Verbatim evidence** (Section E — Loop Prevention / Ceiling):
- L78: `... do not cycle back through lower tiers or repeat TIPP indefinitely. Instead:`
- L79: `"It sounds like this isn't easing up with the tools here ... Want me to share some options for reaching a person right now?"`
- L80: `This routes to human/professional support ... This is separate from the crisis guard below.`

**What we need:** the concrete resource(s) for a **non-crisis** TIPP-ceiling case (L80 says this is explicitly *not* the crisis path). Reuse the UAE crisis list? A separate non-emergency referral (e.g. National Mental Support Line)? A named service/number?

**Decision (2026-07-10, PO):** ☑ **reuse the crisis-resource composition (`CRISIS_RESOURCES`) message for now** — interim. ST-6 ceiling routes to the same resource list as the crisis path (the National Mental Support Line is an appropriate general human-support target). A dedicated non-emergency referral can replace this later. *(Note: this pragmatically links ST-6 to the crisis composition despite the doc framing Section E as "separate from the crisis guard" — an interim, PO-approved.)*

---

## H4 — Crisis-resource reconciliation (doc vs. production config)  ·  **CROSS-NORMATIVE CALL** (no recommendation)

**Question:** Which crisis-resource set is authoritative for production? The normative doc and the live config disagree — and this reopens ground GL-1 touched but did not fully cover (GL-1 adjudicated **46342 vs. 4673**; the doc actually mandates a **5-entry list** in which 46342 appears nowhere).

**Doc's canonical table** (Section C → *3. Resources (UAE)*, L2130-2146; L2130 flags *"verify before launch"*):

| Resource | Number | Hours (per doc) |
|---|---|---|
| Emergency (immediate danger) | 999 | — |
| National Mental Support Line | 800-HOPE (800-4673) | **8am–8pm daily**, AR/EN, WhatsApp |
| Abu Dhabi 24/7 crisis line (800-SAKINA) | 800-725462 | 24/7, psychological first aid |
| Dubai Health Authority | 800 111 | 24/7 |
| Sharjah Child & Youth | 800 51115 | 9am–5pm Mon–Fri |
| Nearest ER | — | out-of-hours / immediate danger |

Lead-logic (L2146): *lead with 999 only on indication of immediate danger; otherwise lead with the National Mental Support Line, 999/ER always available for escalation.*

**Production config** (`config.py` CRISIS_CONFIG): single entry **`800 46342`**, label "MoHAP Counselling Line", hours **"24/7"**, emergency 999.

**Observed discrepancies (stated, not judged):**
1. `800 46342` matches none of the five doc numbers (not 800-4673, not 800-725462).
2. The doc's *primary/lead* line (National) is **8am–8pm**, not 24/7. The only 24/7 doc lines are SAKINA (800-725462) and DHA (800 111) — different numbers.
3. Config exposes one number; the doc mandates a 5-entry list with 999 lead-logic and ER fallback.

**Night-hours scenario (why this matters operationally):** a user in distress at 02:00, not in immediate danger. Under the doc, the "primary" National line is closed (8pm), so lead-logic would route to a 24/7 line (SAKINA/DHA) or ER. Under config, the single `800 46342 / 24/7` is presented. If 46342 is genuinely 24/7 this is safe; if it inherited the National line's hours, it is not.

**What we need (cross-normative — PO + clinical lead, no eng recommendation):** (a) the authoritative primary number + its *true* hours; (b) whether prod carries the full 5-entry list + lead-logic; (c) explicit reconciliation of `800 46342 / 24-7` against the doc — is it correct, or a mistaken entry to replace?

**Decision (2026-07-10, PO):** ☑ **adopt the doc's list exactly, config-driven.** ⚠ **REVERSES GL-1** (2026-07-09 PO ruling: `800 46342` + 24/7 correct, config authoritative) — now superseded because the doc is normative. **HELD BEFORE PROD** on three gates: (a) the doc's own *"verify numbers/hours before launch"* check (L2130); (b) clinical sign-off (crisis-path change); (c) crisis-freeze lift. Config-driven refactor to be built on a branch, **not deployed**, pending these + an explicit reversal confirmation.

> **Constraint:** crisis config is under change-freeze and PO-owned. This item is **findings + decision-request only** — no edit is proposed or will be made without an explicit PO/clinical ruling recorded here.
