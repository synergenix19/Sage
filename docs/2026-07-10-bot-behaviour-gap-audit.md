# BOT BEHAVIOUR — Skill Delivery Gap Audit (verified)
**Current implementation vs. the latest clinician spec (`BOT BEHAVIOUR.docx`, 2218 lines)**
Date: 2026-07-10 · **Every finding below was re-verified against code/data after an initial scout pass; three findings changed materially on verification — noted inline.**

---

## Executive summary

The product owner's box-breathing complaint is correct and **systemic** — it is a missing architectural concept, not a box-breathing bug. But two of the harsher first-pass findings did **not** survive verification (the offer/psychoed flow *does* exist for English; the videos *are* live in prod). The real, verified gaps are:

1. **No delivery-model field** — the spec picks delivery per skill via a "Format" column (`Video` = all-at-once vs `Guided conversation` = turn-by-turn); the engine has no such concept and delivers everything one-step-per-turn. **(CRITICAL, verified)**
2. **Five experiential skills the spec marks `Video` are delivered as multi-turn chat** — box breathing, PMR, mindfulness meditation, body scan, safe-place imagery. **(HIGH, verified)**
3. **The psychoed→offer→permission flow exists for English but is bypassed for Arabic** — Arabic sessions start the skill directly, no offer, no permission. **(HIGH, verified — this replaces the first-pass "flow missing everywhere," which was wrong.)**
4. **Skill videos are live in prod but English-only** — no Arabic video on any skill. **(MEDIUM, verified — first-pass "videos likely not showing" was wrong; the prod flag is ON.)**
5. **Severity-tier routing is a 2-tier subset of the spec's 3-tier system**, and step-up / step-down / ceiling→human-support are absent. **(MEDIUM, verified)**
6. **Presence-only: venting is force-fed a skill** — raw grief correctly stays presence, but "I just need to vent" imposes `box_breathing` (no consent) via `acute_direct_entry`. **(MEDIUM, verified behaviorally on prod.)**

**Bottom line:** the fix is a small schema change (a delivery-format field) + re-authoring 5 skills + closing the Arabic offer/video gap — not a rewrite. Every copy/clinical change needs clinical sign-off.

---

## Finding 1 — No delivery-model field (CRITICAL) — VERIFIED

`schema.py`: `Skill` and `SkillStep` have **no** `delivery`/`format`/`all_at_once` field. The only step-count-adjacent knobs are `criteria_hold_budget` and `hold_ceiling` (they soften/limit *holding*, not batch delivery). `skill_executor_node` runs **once per turn**, advances exactly one step (`step_ids[current_idx+1]`), and every step has a non-empty `completion_criteria` gating on a typed reply. The **only** way to deliver all-at-once is a **single-step** skill (only `psychotic_referral`). So `Format = Video` cannot be represented.

## Finding 2 — Five `Video` skills delivered step-by-step (HIGH) — VERIFIED

Doc Format labels (verified in the doc): Box Breathing `Video` (L109), PMR `Video` (L122), Mindfulness Meditation `Video` (L125), Body Scan `Video/audio guided` (L913), Guided/Safe-Place Imagery `Video` (L979, *"no activity required"*). Implementation:

| skill | impl | delivery gap |
|---|---|---|
| box_breathing | 2 steps (inhale_hold → *"let me know when you've done that"* → exhale_hold) | typed reply demanded **between breath holds** |
| progressive_muscle_relaxation | 5 steps, one region per turn | typed between tensing cycles |
| mindfulness_meditation | 5 steps (*"I will be quiet for a moment while you do it"* then waits) | meditation chopped into turns |
| mindfulness_body_scan | 5 steps, one region per turn | body scan chopped into turns |
| safe_place_visualization | 4 steps (build the place across turns) | doc wants a passive short video ("no activity required"); impl is active multi-turn co-construction |

Each carries its video, but the **text still coaches turn-by-turn** alongside it — contradicting `Format = Video`.
**Correctly step-by-step (NOT gaps, do not change):** `dbt_tipp` (spec: *"one instruction at a time… never all at once"*), `grounding_5_4_3_2_1` (typing what you perceive is the interaction), `stop_technique`.

## Finding 3 — Offer/psychoed/permission: exists for EN, bypassed for AR (HIGH) — CORRECTED ON VERIFICATION

**First-pass claim ("only 1 of 28 skills asks permission") was wrong.** The flow lives **upstream of the skill JSON**:
- `prompts/offer_descriptions.json` carries a **per-skill one-line psychoed blurb** (25 skills). Box breathing: *"a short guided breathing exercise where you breathe in, hold, out, and hold again to an even count, to help your body settle."*
- `composer.py:_build_offer_options_block` renders a numbered offer from these; `default_offer` is *"a consent gate — every match is offered, never imposed."* So **psychoeducate → offer → consent exists for English.**
- **BUT it is hard-gated English-only** (`skill_select.py:459`): for `detected_language == "ar"` the offer is bypassed and the skill **starts directly** (documented as a known limitation — *"the Arabic accept-parse is audit-confirmed broken… until S2-2 ships a tested Khaleeji accept path"*). Offer blurbs are `ar: null`.

**Verified gap:** Arabic users get **no offer, no per-skill psychoed, no permission** — the skill is imposed directly. English is spec-aligned here.

## Finding 4 — Skill videos live but English-only (MEDIUM) — CORRECTED ON VERIFICATION

**First-pass claim ("videos likely not showing — default-OFF") was wrong.** Verified: **prod `SAGE_SKILL_MEDIA_ENABLED = true`** — the videos surface in prod. The `media` schema **supports `ar`** (`dict[str, SkillMediaItem]`). Verified gaps:
- Exactly 5 skills carry media, **all `en`-only** (`media langs=[en]`) — **Arabic users get no video** on any skill.
- Placement: box breathing's video is on its delivery step (fine); the 4 `entry_screen` skills put it on the first content step (step 2) after the safety gate — mid-sequence. If Finding 2 is fixed (collapse to one delivery step), the video lands on that one turn.
- The S1b spec night-rule (*don't hand a long reading resource to someone trying to sleep*) is not represented.

## Finding 5 — Severity tiers: a 2-tier subset; step-up/down/ceiling absent (MEDIUM) — VERIFIED

Only **2 skill-matching rules** exist:
- `acute_direct_entry` (*"Direct entry at panic intensity, no menu"*) — acute skills (box_breathing, grounding, stop, dbt_tipp) enter **directly** at high intensity.
- `default_offer` — everything else is **offered** (≤2 + keep-talking).

This is a **2-tier intensity model** (panic→direct / else→offer), a subset of the spec's **3-tier** system (mild = *choice of two*, moderate = *one offered directly*, high = *TIPP one-step*). **Not implemented:** the spec's **step-up** (worsening check-in → next tier's skill), **step-down** (improvement → optional lighter skill), and **ceiling** (High TIPP + no improvement → route to human support, don't loop) — doc Sections B–E. (The `STEP_DOWN` in `safety_check` is crisis-monitoring clearance; the `hold_ceiling` in the executor is a per-step exit ramp — neither is the tier logic.)

## Finding 6 — Presence-only categories: raw grief OK, venting broken (MEDIUM) — VERIFIED behaviorally (prod)

Spec: raw grief (S2a), venting (3d), loneliness-company (7a) → **no skill; listening is the intervention** (*"hold off on skills/advice/reframing entirely unless asked"*).
- **Raw grief — CORRECT:** "my mother passed away last week… I just feel numb" → `skill=<none>`, freeflow presence response. Presence honored. ✓
- **Venting — GAP:** "I just need to vent… everything is piling up and I can't take it anymore" → **`box_breathing` imposed directly** (`skill=box_breathing, step=inhale_hold`) via `acute_direct_entry`. Two problems: (a) the doc wants venting → presence, no skill; (b) it was **imposed, not offered** — `acute_direct_entry` bypasses the consent gate on high-intensity wording. The **"I just need to vent" / "don't fix it" signal is not detected** as a presence trigger; distress wording alone routes to a coping skill.

**Implication:** `acute_direct_entry` over-triggers — high-distress *venting* is force-fed a skill without consent. Needs a venting/"just listen" detector that suppresses skill imposition (and, per Finding 3, the consent gate should not be bypassed for these).

---

## Recommendations (prioritized)

**P0** — Add a `delivery_format` field (`video_all_at_once` | `guided_conversation` default | `single_message`); make the executor deliver `video_all_at_once` in one turn (technique + video → check-in). Re-author the 5 experiential skills to it (collapse steps; keep the `entry_screen` gate). **Clinical sign-off on collapsed copy.**
**P1** — Close the **Arabic offer/consent gap** (S2-2 Khaleeji accept path) and **add Arabic videos** — no skill should be EN-only for a bilingual product.
**P2** — Extend routing to the spec's 3-tier + step-up/down + ceiling→human-support; add the S1b night-rule; behaviorally verify presence-only (F6).

**Doc hygiene (to the clinician):** the "box breathing ≠ step-by-step" intent is encoded *only* as `Format = Video`, with no prose rule — add one. Line 187 is a truncated sentence (*"…Please note, don't "*). Header typo: *"SUICIDEAL IDEATION."*

---

## Verification log (what changed from the first pass)
- **F1** confirmed (read `schema.py`).
- **F2** confirmed (doc Format labels L109/122/125/913/979; step counts; executor one-step-per-turn).
- **F3 CORRECTED** — offer/psychoed/consent **exists for EN** (`offer_descriptions.json` + `composer.py` + `default_offer`), **bypassed for AR** (`skill_select.py:459`). First pass wrongly said "missing everywhere."
- **F4 CORRECTED** — prod `SAGE_SKILL_MEDIA_ENABLED=true` (videos live); real gap is EN-only media. First pass wrongly said "likely not showing."
- **F5** verified (2 rules only; no step-up/down/ceiling at skill tier).
- **F6 VERIFIED behaviorally on prod** — raw grief correctly presence-only; venting ("I just need to vent") force-fed `box_breathing` via `acute_direct_entry` (imposed, no consent). Real gap.
