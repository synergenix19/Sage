# Psychoeducation Pathways — Clinician Sign-off Packet

**Packet status: DRAFT-FOR-CLINICAL**
**Assembly date: 2026-07-28** · **Design spec:** `docs/superpowers/specs/2026-07-23-psychoeducation-pathways-design.md` (§9 Governance records)
**Ratified source:** `docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md`
**Artifacts pinned at:** this branch (`docs/psychoed-pathways-design`) @ `a13c2718`

---

## How to read this packet

This is **one packet, everything by name** (spec §9). It enumerates every artifact produced by the Phase-1 content build — 40 blocks, 18 pathway scripts, 4 shared single-sourced scripts, 6 trigger tables (31 rows), 1 collision table, 1 PSY-WEAVE-1 data file — and routes each to a clinical ruling. **Block content is NOT reproduced here** — the 40 blocks carry title + per-block scrub classification only (ask-section 1a). The 18 pathway scripts and 4 shared scripts ARE reproduced in full (ask-sections 1c, 2b) since their full text is itself the signable artifact. Ratification is against the pinned artifacts at this branch (`docs/psychoed-pathways-design`) @ `969c802e` (supersedes the original assembly pin `a13c2718`; the only post-`a13c2718` `data/` change is one metadata-only scrub edit — an em dash → comma inside `collision_table.json`'s `subsumption_collisions[0].resolution.rationale`, landed in `969c802e`, no resolution semantics changed).

Each of the 12 ask-sections below carries a **ruling line**: `☐ approve ☐ edit ☐ reject`. Sub-items that need their own adjudication (inferred rows, pending collisions, design-added extensions) carry their own ruling lines.

**Standing rule (binding): no category flips until its asks in this packet are signed.** Per spec §7.3, each per-category flag flip is gated on *this packet signed* alongside the fixture gates. A category with an unresolved inferred row, an unratified collision, or an unsigned block set does not flip.

**Scope: EN-only.** All 40 blocks, 18 scripts, 4 shared scripts, 6 trigger tables and the collision/weave data in this packet are English. The Arabic chain (58 AR artifacts, AR trigger tables, AR weave data, AR fixtures) is **gated per ask-section 10** and does not begin until a validator is named. Never quote an EN ruling as system (bilingual) conformance.

**Provenance of the copy:** every block and every framing/menu/check-in script was extracted from `bot_behaviour_full.md`, em-dash-scrubbed at ingestion (§3.6 standing rule), and the scrubbed copy is what is signed (verbatim pin anchors on the signed artifact, not the raw docx). The doc→artifact diffs are in ask-section 1. Assembly verification: all 40 blocks are **letter-for-letter identical to source** (0 non-dash edits); every difference is a dash transform.

---

## Ask-section 1 — Blocks & scripts ratification (40 blocks + 18 scripts, with scrub diffs)

**What is being ratified:** the verbatim copy of all 40 KB-article blocks and all 18 pathway scripts as the signable artifacts (the verbatim pin and Node-8 hash gate will anchor on exactly these strings, §6.2).

**Scrub-diff summary (mechanically verified this assembly):** every block is scrub-only — letters identical to `bot_behaviour_full.md`, the only changes being em-dash (—) → comma or → period+capital. **60 dash sites across the 40 blocks: 58 → comma, 2 → period+capital** (1f-b3, 6d-b2 — see transform-variant notes below). No block contains any non-dash edit. **Across the 18 pathway scripts, a further 8 dash sites: 6 → comma, 2 → period+capital** (§3c framing / F3c, §6d framing / F6d — see ask-section 1b for the per-script breakdown). **Combined across the 40 blocks + 18 scripts: 68 dash sites total, 64 → comma, 4 → period+capital.**

**Transform-variant notes (period+capital sites — these read differently from the comma default, called out for explicit review):**
- **1f-b3** — dash site 2 (`'…just in your head' — they're your body…'`) scrubs to **period + capital** (`…'just in your head'. They're your body…`); dash site 1 (`slows down —`) scrubs to comma. *(Controller-flagged.)*
- **6d-b2** — dash site 3 (`…fixed personality trait — most people shift…`) scrubs to **period + capital** (`…a fixed personality trait. Most people shift…`); dash sites 1–2 scrub to comma. **NOTE: this is a THIRD period+capital site found during assembly, beyond the two the controller pre-named. Surfaced here for the same explicit review as 1f-b3.**
- **§3c framing statement** (a script, see below) — dash site 1 (`…what's going on — low mood…`) scrubs to **period + capital** (`…what's going on. Low mood…`); dash site 2 (`…might help — but I'm not able…`) scrubs to comma. *(Controller-flagged.)*
- **§6d framing statement (F6d)** (a script, see below) — its one dash site (`…to want to understand — assertiveness isn't…`) scrubs to **period + capital** (`…to want to understand. Assertiveness isn't…`), not comma as the ask-section 1b table previously stated. **NOTE: this is a FOURTH period+capital site, found during final-review verification against `bot_behaviour_full.md` line 1606, beyond the three previously named (1f-b3, 6d-b2, §3c framing). Surfaced here for the same explicit review.**

**Ruling — all 40 blocks + 18 scripts as verbatim signable artifacts (scrub-only, letters-identical):** ☐ approve ☐ edit ☐ reject
**Ruling — the 4 period+capital transform sites specifically (1f-b3, 6d-b2, §3c framing, §6d framing):** ☐ approve ☐ edit ☐ reject

### 1a — The 40 blocks by ID + title (scrub diff per block)

**§1f Understanding Anxiety — 5 blocks (menu-first)**
| Block | Title | Scrub |
|---|---|---|
| 1f-b1 | What is anxiety? | scrub-only (1 dash → comma) |
| 1f-b2 | Fight, flight, or freeze | scrub-only (3 dashes → comma) |
| 1f-b3 | Why anxiety causes physical symptoms | scrub-only (2 dashes: 1 → comma, **1 → period+capital**) |
| 1f-b4 | The anxiety maintenance cycle | scrub-only (1 dash → comma) |
| 1f-b5 | What is worry? | scrub-only (2 dashes → comma) |

**§3c Understanding Depression — 7 blocks (answer-first + weave)**
| Block | Title | Scrub |
|---|---|---|
| 3c-b1 | What is depression? (bio-psycho-social model) | scrub-only (1 dash → comma) |
| 3c-b2 | Why can't I just "snap out of it"? | scrub-only (1 dash → comma) |
| 3c-b3 | Why depression affects motivation and energy | scrub-only (1 dash → comma) |
| 3c-b4 | Why things can feel numb or empty (anhedonia) | scrub-only (1 dash → comma) |
| 3c-b5 | Sadness vs. depression | scrub-only (1 dash → comma) |
| 3c-b6 | Why it can feel like "no reason" | scrub-only (1 dash → comma) |
| 3c-b7 | Why seeking help is worth it (destigmatizing) | scrub-only (2 dashes → comma) |

**§4b Understanding Emotions — 7 blocks (answer-first)**
| Block | Title | Scrub |
|---|---|---|
| 4b-b1 | Why we have emotions at all | scrub-only (1 dash → comma) |
| 4b-b2 | What different emotions are signaling | scrub-only (1 dash → comma) |
| 4b-b3 | Why reactions differ in intensity (comparison to others) | scrub-only (2 dashes → comma) |
| 4b-b4 | Getting "triggered" | scrub-only (2 dashes → comma) |
| 4b-b5 | Why your body reacts before you can think | scrub-only (2 dashes → comma) |
| 4b-b6 | Responding vs. reacting | scrub-only (2 dashes → comma) |
| 4b-b7 | Shutting down or avoiding | scrub-only (1 dash → comma) |

**§6d Understanding Assertiveness — 6 blocks (answer-first)**
| Block | Title | Scrub |
|---|---|---|
| 6d-b1 | What is assertiveness? | scrub-only (3 dashes → comma) |
| 6d-b2 | The four communication styles (assertive vs. aggressive vs. passive vs. passive-aggressive) | scrub-only (3 dashes: 2 → comma, **1 → period+capital**) |
| 6d-b3 | Why people-pleasing or conflict-avoidance patterns develop | scrub-only (1 dash → comma) |
| 6d-b4 | How to build assertiveness as a skill | scrub-only (2 dashes → comma) |
| 6d-b5 | Assertiveness and boundaries | scrub-only (1 dash → comma) |
| 6d-b6 | Culture and assertiveness | scrub-only (3 dashes → comma) |

**§7c How Do I Connect — 7 blocks (answer-first, how-to)**
| Block | Title | Scrub |
|---|---|---|
| 7c-b1 | How to start conversations | scrub-only (1 dash → comma) |
| 7c-b2 | How to make friends as an adult | scrub-only (2 dashes → comma) |
| 7c-b3 | How to deepen existing relationships | scrub-only (1 dash → comma) |
| 7c-b4 | How to maintain friendships over time | scrub-only (1 dash → comma) |
| 7c-b5 | Feeling awkward / social skills | scrub-only (1 dash → comma) |
| 7c-b6 | Belonging / community | scrub-only (2 dashes → comma) |
| 7c-b7 | Connecting with family specifically | scrub-only (2 dashes → comma) |

**S2c Understanding Grief — 8 blocks (answer-first + weave)**
| Block | Title | Scrub |
|---|---|---|
| s2c-b1 | What is grief? | scrub-only (1 dash → comma) |
| s2c-b2 | Why grief comes in waves | scrub-only (1 dash → comma) |
| s2c-b3 | The "stages" of grief | scrub-only (2 dashes → comma) |
| s2c-b4 | Is there a "right" way to grieve? | scrub-only (1 dash → comma) |
| s2c-b5 | Physical and cognitive symptoms of grief | scrub-only (1 dash → comma) |
| s2c-b6 | Grief-related guilt | scrub-only (1 dash → comma) |
| s2c-b7 | Grief-related anger | scrub-only (1 dash → comma) |
| s2c-b8 | How long does grief last? | scrub-only (1 dash → comma) · **carries block-guard `prolonged_grief_support_note`, see ask-section 2** |

*(S2c serve is flag-gated OFF independent of this ratification — see ask-section 12, item 12-e / spec §5.7.)*

### 1b — The 18 pathway scripts by category + role

All 18 are **verbatim-in-doc, scrub-only.** Three per category: framing statement (F), menu-offer (M), check-in/close (C).

| Category | Framing (F) | Menu-offer (M) | Check-in (C) |
|---|---|---|---|
| 1f | F1f — scrub-only (1 dash → comma) | M1f — scrub-only (1 dash → comma) | C1f — verbatim (0 dashes) |
| 3c | F3c — scrub-only (2 dashes: **1 → period+capital**, 1 → comma) | M3c — verbatim (0 dashes) | C3c — verbatim (0 dashes) |
| 4b | F4b — scrub-only (1 dash → comma) | M4b — verbatim (0 dashes) | C4b — verbatim (0 dashes) |
| 6d | F6d — scrub-only (1 dash → **period+capital**) | M6d — verbatim (0 dashes) | C6d — verbatim (0 dashes) |
| 7c | F7c — scrub-only (1 dash → comma) | M7c — verbatim (0 dashes) | C7c — scrub-only (1 dash → comma) |
| s2c | Fs2c — verbatim (0 dashes) | Ms2c — verbatim (0 dashes) | Cs2c — verbatim (0 dashes) |

Full script text is reproduced under ask-section 2 (manifests), where each script is the manifest's `framing_statement` / `menu_offer` / `check_in` field.

### 1c — The 4 shared single-sourced scripts (#321 constants module)

These live once in a constants module and are referenced by templates; a CI single-source check asserts they appear nowhere else in served copy (§3.5 / §6.4).

1. **`diagnosis_guard_stage1`** (source §1f Guard, formal-diagnosis bullet, opening script — reused verbatim in §3c per §3.5): *"I can't diagnose, that needs a proper evaluation from a doctor or mental health professional who can ask the right questions and rule other things out. What I can do is explain what it generally involves, so you've got a clearer picture going into that conversation if you decide to have it. Want me to walk through that?"* — verbatim scrub-only.
2. **`diagnosis_guard_stage2`** (source §1f Guard, formal-diagnosis bullet, push-further script): *"I really can't say either way, I'm only seeing a slice of what you're dealing with, and a diagnosis needs a full picture that a professional is trained to assess. What I've noticed is [reflect back the specific pattern they've described], that might be worth bringing to a doctor or therapist directly, since they can actually tell you what's going on."* — verbatim scrub-only.
3. **`safety_weave_script`** (source §3c Safety Check (woven), quoted script): *"When you're describing feeling this [hopeless / numb / empty, reflect their own word], I want to check something: have you had any thoughts of hurting yourself, or not wanting to be here?"* — scrub-only. **NOTE: the em-dash the scrub removed is INSIDE the clinician's bracket token** — source is `[hopeless / numb / empty — reflect their own word]`, scrubbed to `[hopeless / numb / empty, reflect their own word]`. The bracket is an authoring instruction to the bot ("reflect their own word"), not literal output; flagged so clinical can confirm the comma reads correctly inside that instruction token.
4. **`human_referral_close`** — **PENDING-CLINICIAN (no source string exists).** No single quoted universal human-referral close exists anywhere in `bot_behaviour_full.md`. The guard family states the behavior in **prose only** ("The user explicitly asks for a human/professional → don't redirect back into the bot flow"), recurring throughout the doc (e.g. §1e Guard) with no quoted bot-voice script attached at any of its sites. Controller adjudication 2026-07-28: **no candidate in the doc may stand in as a universal close** — specifically, 3c-b7's destigmatizing paragraph ("Reaching out for support…") is authored as *depression psychoeducation*, a ratified servable §3c menu topic, and is **explicitly NOT repurposed or pointered** as a cross-category referral script. Clinical to **author or designate** the universal close. *(Also in ask-section 12, item 12-f.)*

**Ruling — shared scripts 1–3 as verbatim #321 constants:** ☐ approve ☐ edit ☐ reject
**Ruling — `human_referral_close`: clinical authors/designates the universal close (do NOT repurpose 3c-b7):** ☐ approve ☐ edit ☐ reject

---

## Ask-section 2 — Manifests: delivery shapes, weave scopes, bridge maps, per-block guard

Per category: `delivery_shape`, `safety_weave` (weave-scope field, clinician-owned per §3.2/§5.4), the three scripts (F/M/C), ordered block list, guard references, bridge map.

### 2a — Delivery shapes & weave scopes

| Category | delivery_shape | safety_weave | Notes |
|---|---|---|---|
| 1f | menu_first | **false** | menu-first: framing + menu, no answer-first block on turn 1 |
| 3c | answer_first | **true** | weave fires on first personally-framed block |
| 4b | answer_first | false | |
| 6d | answer_first | false | |
| 7c | answer_first | false | how-to shape |
| s2c | answer_first | **true** | weave on; **serve flag-gated OFF** pending reunification lexicon (§5.7) |

**Confirm the weave scope: §3c + S2c ON, all others OFF** (spec §3.2 "§3c and S2c set at minimum; clinician owns it"). The `safety_weave` field is governed at safety-rule rigor (§5.4) — turning it on/off for any category is a clinical decision, not a content edit.

**Ruling — delivery shapes + weave scope (3c & S2c weave ON, 1f/4b/6d/7c OFF):** ☐ approve ☐ edit ☐ reject

### 2b — Framing / menu / check-in scripts (full text, per category)

**§1f** — F: *"It can really help to understand what's going on when anxiety shows up, knowing why your body and mind react this way often makes it feel less alarming. What would be most useful to explore?"* · M: *"Present as selectable options rather than launching into one topic, let the person pick what's relevant to them:"* · C: *"Does that make sense? Want to explore another topic, or would it help to try something related now?"*

**§3c** — F: *"It makes sense you'd want to understand what's going on. Low mood or depression can be confusing, especially when it doesn't feel like straightforward sadness. Just to note - I'm here to help you understand what you're experiencing and offer tools that might help, but I'm not able to diagnose any mental health condition. A diagnosis needs a full picture from a qualified professional who can properly assess what's going on. If you're wondering whether something has a clinical name, that's worth bringing to a doctor or therapist directly. Let's start with what you're asking, and I can go deeper into anything else that would help."* (carries the diagnosis disclaimer in-framing per §5.5; the `Just to note -` hyphen is an ASCII hyphen unchanged from source) · M: *"Want to go deeper into any of this? I can walk through: what depression actually is, why 'snap out of it' doesn't work, why it hits motivation and energy, why things can feel numb, how it's different from ordinary sadness, why it can happen with no clear reason, or why reaching out for support is worth it."* · C: *"Does that help make sense of things? Want to explore another topic, or is there something else on your mind?"*

**§4b** — F: *"It makes sense you'd want to understand your reactions a bit better, emotions can feel like they come out of nowhere, but there's usually a real reason behind the size and shape of a reaction, even when it feels confusing in the moment. Let's start with what you're asking."* · M: *"Want to go deeper into any of this? I can walk through: why we have emotions at all, what different emotions are actually signaling, why intensity varies so much between people, what getting 'triggered' really means, why your body reacts before you can think, the difference between responding and reacting, or why shutting down/avoiding is a real protective response rather than a flaw."* · C: *"Does that help make more sense of it? Want to explore another topic, or is there something specific going on right now you'd want help with?"*

**§6d** — F: *"It's a great thing to want to understand. Assertiveness isn't about being blunt or pushy, it's about finding a way to express what you need that still feels like you. Let's start with what you're asking."* · M: *"Want to go deeper into any of this? I can walk through: what assertiveness actually is, the four communication styles, why people-pleasing patterns develop in the first place, how to build assertiveness as a skill, how it connects to boundaries, or how culture shapes what 'assertive' even looks like."* · C: *"Does that help clarify things? Want to explore another angle, or would it help to actually practice this with a specific situation you're facing?"*

**§7c** — F: *"Wanting to build stronger connections is such a worthwhile thing to work on, let's start with what you're asking, and I can go deeper into whatever would help most."* · M: *"Want to go deeper into any of this? I can walk through: starting conversations, making friends as an adult, deepening existing relationships, keeping friendships going over time, feeling less awkward socially, building a sense of belonging, or connecting more with family specifically."* · C: *"Does that help? Want to explore another angle, or would it help to think through a specific situation, like a particular friendship, or a conversation you'd like to have with someone?"*

**S2c** — F: *"Grief can feel really confusing, especially because it doesn't behave the way people expect. Let's start with what you're asking, and I can go deeper into anything else that would help."* · M: *"Want to go deeper into any of this? I can walk through: what grief actually is, why it comes in waves, the truth behind the 'stages' of grief, whether there's a right way to do it, the physical and cognitive symptoms, grief-related guilt, grief-related anger, or how long it typically lasts."* · C: *"Does that help make more sense of it? Want to explore another angle, or is there something going on for you right now that would help to talk through?"*

**Ruling — the 18 scripts as manifest content:** ☐ approve ☐ edit ☐ reject

### 2c — Bridge maps (doc block→skill offers; optional-not-automatic, fixture F5)

| Category | Bridge entry | skill_id | doc target/route | Status |
|---|---|---|---|---|
| 1f | 1f-b2 (fight/flight) → skill | `box_breathing` | doc §1f | optional, OK |
| 1f | 1f-b4 (maintenance cycle) → skill | **null** | doc target **"Worry Tree"** | **PENDING — no `worry_tree` skill in registry** |
| 4b | 4b-b6 (responding vs reacting) → skill | `box_breathing` | doc route **1a** | optional, OK (entry 1 of 2) |
| 4b | 4b-b6 (responding vs reacting) → skill | `grounding_5_4_3_2_1` | doc route **1a** | optional, OK (entry 2 of 2) |
| 7c | specific-person/message → skill | `assertive_communication` | doc route **6c** | optional, OK |
| 3c / 6d / s2c | — | — | — | no bridges |

**Bridge item 2-i — 1f-b4 "Worry Tree" bridge shipped as `skill_id: null`.** The doc's §1f maintenance-cycle block bridges to *"Worry Tree"*, but **no `worry_tree` skill exists in the registry** (`worry_time` is a different technique — Worry Tree is a guided triage flow, Worry Time is a scheduled-worry containment skill; they are not interchangeable). The bridge is encoded with `skill_id: null`, `status: pending_clinician_no_registry_skill`, so it cannot mis-route. **Resolution needed:** either build a `worry_tree` skill, or clinical designates an existing alternative as the bridge target. *(Controller item 1; also ask-section 12, item 12-a.)*
**Ruling — 1f-b4 bridge: build `worry_tree` vs designate alternative:** ☐ approve ☐ edit ☐ reject

**Bridge item 2-ii — 4b-b6 encoded as TWO optional bridges.** The doc routes 4b-b6 "to 1a"; category 1a offers a *choice* of skills, so the bridge is encoded as **two entries** (`box_breathing` + `grounding_5_4_3_2_1`), both `doc_route: 1a`, both optional. Ratify the two-entry encoding (vs collapsing to one). *(Controller item 9.)*
**Ruling — 4b-b6 two-entry (box_breathing + grounding) encoding:** ☐ approve ☐ edit ☐ reject

### 2d — Per-block guard (`s2c-b8`)

**`s2c-b8` "How long does grief last?"** carries `block_guard`:
- id: `prolonged_grief_support_note`
- behavior: `append_support_note_no_diagnosis_naming`
- note: *"If it's been a long time and things feel just as intense and unchanging as at the start, with real impact on daily life, that's worth extra support rather than something to just wait out."*

This is the doc's prolonged-grief support note — **appended without naming a diagnosis** (deliberately not "prolonged grief disorder"). It is the only per-block guard in the library; F5 asserts sibling blocks do NOT carry it.
**Ruling — `s2c-b8` prolonged-grief support note (no diagnosis naming):** ☐ approve ☐ edit ☐ reject

### 2e — §6d guard is relationship-safety / E7-adjacent (NOT encoded here)

The §6d guard family includes an **unsafe-reaction pattern → relationship-safety resources** clause (if asserting a boundary would put the person at risk from another person's reaction). This is **relationship-safety / E7-adjacent territory and is NOT encoded in the psychoed artifacts** — the psychoed manifest guards are only `acute_distress`, `diagnosis_guard`, `crisis_override`. **The §6d serve flip should be gated alongside the existing §6a-guard / E7 launch-blocker**, not flipped on psychoed-artifact readiness alone. Confirm this gating. *(Controller item 6; also ask-section 12, item 12-g.)*
**Ruling — §6d flip gated behind the §6a-guard/E7 launch-blocker:** ☐ approve ☐ edit ☐ reject

---

## Ask-section 3 — Trigger tables + collision table (incl. `pending: clinician` resolutions)

### 3a — Trigger tables (31 rows across 6 categories)

Each row: `type` / `framing` / `route` / `row_provenance`. `doc_table` = transcribed 1:1 from a real §0 Type|Examples pipe table. `inferred` = row typing/framing/route reconstructed where the source lacked a Type column or the row was sourced from a Guard bullet. **Inferred rows are ask-section 6 territory (safety-rule governance) and carry their own rulings there.**

**§1f — 3 rows. ⚠ Source §1f recognition section is a BULLETED phrase list with NO Type column; all 3 rows are INFERRED.**
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| 1f-t1 | curiosity_abstract | abstract | standard | **inferred** | "What is anxiety?" · "Can you explain fight or flight?" · "What's the difference between worry and anxiety?" |
| 1f-t2 | curiosity_personal | personal | standard | **inferred** | "Why do I feel this way?" · "What's happening to me?" · "Why does my body react like this?" · "Why do I keep worrying?" |
| 1f-t3 | formal_diagnosis_request | personal | formal_diagnosis | **inferred** (from §5 Guard formal-diagnosis bullet, not the recognition list) | "do I have GAD" · "do I have panic disorder" |

**§3c — 5 rows** (rows 1–3 doc_table; rows 4–5 inferred)
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| 3c-t1 | Direct diagnostic questions | personal | direct_diagnostic | doc_table | "I think I might be depressed." · "Could I have depression?" · "How do I know if I'm depressed?" · "Is this depression or just stress?" |
| 3c-t2 | Abstract/academic questions | abstract | standard | doc_table | "What is depression?" · "Can you explain depression?" · "What's the difference between feeling sad and being depressed?" |
| 3c-t3 | Symptom-confusion questions | personal | standard | doc_table | 16 phrases: "Why am I so low?" · "Why can't I just snap out of it?" · "Why do I have no motivation?" · "Why don't I enjoy anything anymore?" · "Why am I always so tired?" · "Why do I feel empty?" · **"Why do I feel numb?"** · "Why can't I get out of bed?" · "Why do I keep withdrawing from people?" · "Why does everything feel so hard?" · "Why do I feel hopeless?" · "Why do I feel like this for no reason?" · "Why do I feel like I've lost myself?" · "Why does depression affect motivation?" · "Why do I have no energy?" · "Why do I feel disconnected from everything?" |
| 3c-t4 | General understanding-seeking | personal | standard | **inferred** (framing) | "I want to understand depression." · "I want to understand my symptoms." · **"What's happening to me?"** |
| 3c-t5 | formal_diagnosis_request | personal | formal_diagnosis | **inferred** (from §7 Guard formal-diagnosis bullet, not §0 table) | "do I have depression" |

**§4b — 5 rows, all doc_table** (all first-person "why do I", unambiguously personal; no diagnosis-seeking phrase, all route standard)
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| 4b-t1 | General why-questions | personal | standard | doc_table | "Why do I feel like this?" · "Why do I react like this?" · "I don't understand my reactions." · "I don't understand my emotions." · "Why do I keep responding like this?" |
| 4b-t2 | Intensity / control | personal | standard | doc_table | "Why am I so emotional?" · "Why can't I control my emotions?" · "Why do my emotions feel so intense?" · "Why do I feel so strongly?" · "Why do I feel so overwhelmed?" |
| 4b-t3 | Specific reaction patterns | personal | standard | doc_table | "Why do I get upset so easily?" · "Why do I cry so easily?" · "Why do I get angry so quickly?" · "Why do I overreact?" · "Why can't I let things go?" · "Why do I get triggered so easily?" · "Why do I shut down?" · "Why do I avoid things?" · "Why do I always get defensive?" |
| 4b-t4 | Comparison to others | personal | standard | doc_table | "Why do I react differently to other people?" · "Why can't I cope like everyone else?" |
| 4b-t5 | Body-first reactions | personal | standard | doc_table | "Why does my body react before I can think?" · "Why does this affect me so much?" |

**§6d — 6 rows, all doc_table** (no diagnosis-seeking possible — no clinical label to seek; all standard)
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| 6d-t1 | Abstract/definitional | abstract | standard | doc_table | "What is assertiveness?" · "Can you explain assertiveness?" · "What's the difference between assertive and aggressive?" |
| 6d-t2 | Self-assessment | personal | standard | doc_table | "Am I being too passive?" · "I don't know if I'm being too nice." · "I think I'm a people pleaser." |
| 6d-t3 | Skill-building goal | personal | standard | doc_table | "How do I become more assertive?" · "I want to learn how to be more assertive." · "I want to communicate better." · "I want to be more confident in conversations." · **"I want to become more confident."** |
| 6d-t4 | Specific struggles | personal | standard | doc_table | "I struggle to stand up for myself." · "I find it hard to express my needs." · "I don't know how to communicate confidently." · "I always avoid conflict." · "I don't know how to speak up for myself." · "I worry about saying the wrong thing." · "I don't know how to say no." · "I don't know how to ask for what I need." |
| 6d-t5 | Boundaries-related | personal | standard | doc_table | "How can I set healthy boundaries?" · "How do I stop people walking all over me?" · "I want to stop people pleasing." |
| 6d-t6 | Balance-seeking | personal | standard | doc_table | "How do I stand up for myself without being rude?" · "I don't want to be aggressive, but I don't want to stay quiet either." |

**§7c — 4 rows, all doc_table** (all first-person self-facing; all standard)
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| 7c-t1 | How-to / practical | personal | standard | doc_table | "How do I make friends?" · "How do I meet new people?" · "How do I build relationships?" · "How do I connect with people?" · "How do I create meaningful connections?" · "How do I stop feeling disconnected?" |
| 7c-t2 | Goals / desires | personal | standard | doc_table | 10 phrases: "I want to make more friends." · "I want to feel more connected." · "I want deeper relationships." · "I want closer friendships." · "I want to expand my social circle." · "I want to feel like I belong." · "I want to strengthen my relationships." · "I want better relationships." · "I want to connect more with my family." · "I want to feel closer to people." |
| 7c-t3 | Specific struggles | personal | standard | doc_table | "I don't know how to start conversations." · "I struggle to connect with people." · "I find it hard to make friends." · "I don't know how to get to know people." · "I feel awkward around people." · "I don't know how to keep a conversation going." · "I find it hard to open up." · "I don't know how to build meaningful relationships." · "I don't know how to maintain friendships." |
| 7c-t4 | Confidence / skills | personal | standard | doc_table | "I want to improve my social skills." · **"I want to become more confident socially."** |

**S2c — 8 rows, all doc_table** (grief-coded crisis phrasing deliberately excluded → Node-1/crisis-lexicon territory, §5.7)
| Row | type | framing | route | provenance | phrases |
|---|---|---|---|---|---|
| s2c-t1 | Abstract/definitional | abstract | standard | doc_table | "What is grief?" · "Can you explain grief?" · "What are the stages of grief?" · "Is there a right way to grieve?" · "How long does grief last?" |
| s2c-t2 | Normalcy-checking | personal | standard | doc_table | "Is what I'm feeling normal?" · "Is this part of grief?" · "I don't understand why I'm reacting this way." |
| s2c-t3 | Wave-like nature | personal | standard | doc_table | "Why does grief come in waves?" · "Why do I feel okay one day and awful the next?" · "Why hasn't it got easier?" |
| s2c-t4 | Persistent emotional symptoms | personal | standard | doc_table | "Why am I still grieving?" · "Why do I still feel so sad?" · "Why do I keep crying?" · "Why do I miss them so much?" · "Why do I keep thinking about them?" · "Why does grief affect me so much?" · "Why do I feel so emotional?" |
| s2c-t5 | Numbness | personal | standard | doc_table | **"Why do I feel numb?"** (collides with 3c-t3 — see collision table) |
| s2c-t6 | Guilt | personal | standard | doc_table | "Why do I feel guilty?" |
| s2c-t7 | Anger | personal | standard | doc_table | "Why am I angry since they died?" |
| s2c-t8 | General understanding-seeking | personal | standard | doc_table | "I want to understand grief." · "I want to understand what I'm going through." |

**Ruling — the doc_table rows (transcribed 1:1, no judgment):** ☐ approve ☐ edit ☐ reject
*(Inferred rows 1f-t1/t2/t3, 3c-t4, 3c-t5 carry their own rulings in ask-section 6.)*

### 3b — Collision table

**Mechanisms allowed (spec §5.2):** (a) declared session context; (b) scripted clarifying question. **NEVER embedding-similarity tie-break.** Safe-before-disambiguated: where both colliding categories carry the weave, the safety check fires on either branch.

**Exact-phrase collisions:**

**Collision 3-i — "Why do I feel numb?"** (§3c ∩ S2c; both personally framed) — **RESOLVED.**
- context signal `grief_disclosure_or_recent_s2_pathway` → winner **s2c**; else default winner **3c**.
- `safe_before_disambiguation: true` (both categories carry weave).
**Ruling:** ☐ approve ☐ edit ☐ reject

**Collision 3-ii — "What's happening to me?"** (§1f ∩ §3c) — **PENDING CLINICIAN.**
- Guard postures differ: **§3c carries the personally-framed safety weave; §1f does not.** The doc offers no disambiguation.
- Interim default: **3c** (fail-toward-weave — the weave-carrying category wins while ratification is pending). `safe_before_disambiguation: false` (postures differ).
- Likely ratified resolution: a **scripted clarifying question** (§5.2 mechanism b).
**Ruling — resolve via scripted clarifying question (vs confirm 3c default):** ☐ approve ☐ edit ☐ reject

**Subsumption collisions (resolved by the engineering-proposed WEAVE-DOMINANCE RULE):**

> **Weave-dominance rule (needs ratification):** *"longest-exact-match wins iff the winning category's guard posture is equal-or-stronger (weave dominance); otherwise pending clinician."*

**Collision 3-iii — "Why do I feel like this?" ⊂ "Why do I feel like this for no reason?"** (§4b ∩ §3c)
- short-form exact match = **4b**; long-form utterance winner = **3c** (3c carries the weave — fail-toward-weave holds, so longest-match is allowed to win).
**Collision 3-iv — "I want to become more confident." ⊂ "I want to become more confident socially."** (§6d ∩ §7c)
- short-form = **6d**; long-form winner = **7c** (equal weave-less posture — longest-match allowed).

**Ruling — the weave-dominance rule itself:** ☐ approve ☐ edit ☐ reject
**Ruling — the two subsumption resolutions (3-iii, 3-iv):** ☐ approve ☐ edit ☐ reject

*(§4b-⊂-3c and §6d-⊂-7c are the controller's "TWO subsumption pairs"; the numb/what's-happening pair are the controller's exact-phrase collisions. Controller item 4.)*

---

## Ask-section 4 — PSY-WEAVE-1 data (deflection→crisis is a design-added extension)

PSY-WEAVE-1 is the highest-stakes rule in this design (§6.1): on a weave-pending turn, a reply that is not a clear negative → crisis protocol. Data file: `data/psychoed/weave/psy_weave_1.en.json` (v0.1.0-draft, status draft-pending-clinician). All patterns are normalized (resolver case/punctuation normalization); markers are substring hits on the normalized reply; patterns are regex fullmatch.

**Evaluation order:** `contradiction_markers_first`, then `clear_negative_patterns_fullmatch`. **Default: `fail_closed_to_crisis`.**

**Clear-negative patterns (allowlist — these PASS, no crisis):** `no` · `no nothing like that` · `no not at all` · `no alhamdulillah` · `no i haven't( why)?` · `no never` · `nothing like that` · `no thank god`

**Contradiction / ambiguity markers (any hit → fail closed to crisis, even after a leading "no"):** `but` · `sometimes` · `kind of` · `maybe` · `a little` · `not really`

**⚠ DESIGN-ADDED EXTENSION — named for ratification (Absolute Rule 1, spec §6.1/§10):**
**Deflection → crisis.** The doc's branch is **binary yes/no**. This design treats **deflection / topic-change** on a weave-pending turn (e.g. replying "actually, what is anxiety?" to the safety question) as a **non-negative → fail closed to crisis** — a stricter-than-doc standard. This is **not carried silently in data**; it is presented here BY NAME. Softening the deflection branch is a clinician edit to signed data, not an engineering call.

**Ruling — deflection→crisis extension (fail-closed):** ☐ approve ☐ edit ☐ reject
**Ruling — the clear-negative allowlist (8 patterns):** ☐ approve ☐ edit ☐ reject
**Ruling — the contradiction/ambiguity marker list (6 markers):** ☐ approve ☐ edit ☐ reject

*(Controller item 8.)*

---

## Ask-section 5 — Diagnosis-guard row-split mapping (direct_diagnostic vs formal_diagnosis)

Per spec §5.5 the doc routes diagnosis-adjacent phrasing **two ways**:
- **`direct_diagnostic`** ("I think I might be depressed", "Is this depression or just stress?") → **normal answer-first flow** with the disclaimer-carrying framing (§3c builds the can't-diagnose disclosure into its framing statement, see ask-section 2b).
- **`formal_diagnosis`** ("do I have GAD / depression / panic disorder") → **two-stage guard script** (`diagnosis_guard_stage1` initial + `diagnosis_guard_stage2` push-further, ask-section 1c), **category-agnostic**, single-sourced.
- Guard-script yes-branch ("Want me to walk through that?" → consent) → serve the relevant concept block through the same audited path.
- Personally-framed diagnosis-seeking is high-risk phrasing: **weave ordering applies to guard-script emissions exactly as to block emissions** (no emission path skips Classifier B).

**Row assignments per table:**
| Row | Route | Table provenance |
|---|---|---|
| 3c-t1 (Direct diagnostic questions) | **direct_diagnostic** | doc_table |
| 3c-t5 ("do I have depression") | **formal_diagnosis** | inferred (from §7 Guard bullet) |
| 1f-t3 ("do I have GAD" / "panic disorder") | **formal_diagnosis** | inferred (from §5 Guard bullet) |
| all other rows (4b/6d/7c/s2c, 3c-t2/t3/t4) | n/a (standard) | — |

**Item 5-i — `diagnosis_guard` is armed CATEGORY-AGNOSTIC.** The two-stage guard is armed on **every** category's manifest guard list (`1f, 3c, 4b, 6d, 7c, s2c`), including 4b/6d/7c whose own doc §-guard sections **lack an explicit diagnosis clause**. Rationale: spec §5.5 posture (formal-diagnosis routing is category-agnostic) — a "do I have X" that lands in any psychoed category should hit the guard, not be answered. Confirm this category-agnostic arming. *(Controller item 10.)*

**Ruling — the direct_diagnostic vs formal_diagnosis row split:** ☐ approve ☐ edit ☐ reject
**Ruling — `diagnosis_guard` armed category-agnostic (incl. 4b/6d/7c):** ☐ approve ☐ edit ☐ reject

---

## Ask-section 6 — Framing-row mappings (safety-rule governance)

Per spec §5.4, Classifier B (personal vs abstract framing) is **called at Node 4 but GOVERNED as a safety rule** — its output decides whether the safety weave fires. **The framing mappings below take safety-rule review rigor: clinical sign-off is required for any future edit; a trigger-table content edit must not be able to silently reclassify a personal row as abstract.**

**Abstract-framed rows (weave-eligible = NO):** 1f-t1 · 3c-t2 · 6d-t1 · s2c-t1
**Personal-framed rows (weave fires where category `safety_weave: true`):** all other 27 rows.

**⚠ INFERRED framing/typing rows — ratify or edit the inferred labels:**

**Item 6-i — §1f rows all INFERRED.** The doc's §1f recognition section is a **bulleted phrase list with NO Type column** (unlike the other five categories' pipe tables). All 3 rows' `type` / `framing` / `route` were **inferred** during assembly (`row_provenance: inferred` on each): 1f-t1 → abstract/standard, 1f-t2 → personal/standard, 1f-t3 → personal/formal_diagnosis. Ratify or edit these inferred labels. *(Controller item 2.)*
**Ruling — §1f inferred rows (t1 abstract, t2 personal, t3 formal_diagnosis):** ☐ approve ☐ edit ☐ reject

**Item 6-ii — 3c-t4 framing inferred.** Row kept the doc_table Type name ("General understanding-seeking") but **framing was marked inferred** — its phrases mix self-facing ("I want to understand my symptoms") and topic-facing ("What's happening to me?"), so personal-vs-abstract was not obvious from the Type name alone. Assembled as **personal** (fail-toward-weave). Ratify. *(Controller item 3.)*
**Ruling — 3c-t4 framing = personal:** ☐ approve ☐ edit ☐ reject

**Item 6-iii — 3c-t5 sourced from the §7 Guard bullet, not the §0 table.** Row is **not in the recognition table at all**; it was reconstructed from §3c's §7 Guard formal-diagnosis bullet (same pattern as 1f-t3). Assembled as personal/formal_diagnosis. Ratify. *(Controller item 3.)*
**Ruling — 3c-t5 (Guard-sourced formal_diagnosis row):** ☐ approve ☐ edit ☐ reject

---

## Ask-section 7 — Classifier A structural-signal thresholds (ENGINEERING PROPOSAL — clinical sets values)

Classifier A (§5.3) is the acute-distress precedence rule: deterministic inputs only (existing safety-route state + distress-marker lexicon + **structural signals**), fail direction **"on ambiguity, treat as acute."** The lexicon and safety-route inputs are settled; the **structural-signal thresholds** are placeholders that clinical must set.

**ENGINEERING PROPOSAL — placeholder values, clinical sets the real numbers:**
- **Message fragmentation:** ≥ **3 fragments** each under **12 chars** in one turn → structural acute signal.
- **Numeric self-report intensity:** any **"N/10" with N ≥ 7** → structural acute signal.

These implement the doc's Routing-§A tier-recognition signals (S2c's "in the middle of something right now" is often carried structurally, not by panic vocabulary). The values above are **not clinically derived** — they are engineering placeholders so the mechanism and its fixtures (F3, incl. mixed-pull turns) can be built; clinical owns the final thresholds.

**Ruling — fragmentation threshold (≥3 fragments <12 chars):** ☐ approve ☐ edit ☐ reject
**Ruling — numeric self-report threshold (N/10, N≥7):** ☐ approve ☐ edit ☐ reject

---

## Ask-section 8 — §7c ruled amendment (answer-first KB category)

**Ruled amendment (spec §9):** §7c moves from a **skill_select target** to an **answer-first KB category** — an inventory correction, consistent with the doc's "same shape as the other psychoeducation categories." This **supersedes the sibling-pathways provisional match** (`interpersonal_effectiveness`, previously flagged "least-bad"). The amendment is **routed past clinical for ratification, not silently dissolved.**
- Bridge target (specific person/message → 6c, `assertive_communication`) is in the §7c bridge map (ask-section 2c).
- Aligns with the Mechanism-A record's "§7c = matching-gap → clinician-packet" disposition.
- **§4a stays open on the clinical queue untouched** (space-holding category; Mechanism-B territory; not psychoed; out of this design's scope).

**Item 8-i — §7c guard routes summarized, not encoded (symmetric back-references).** The §7c guard's routes (to 7a / 7b / anxiety / worthlessness) are **summarized in prose, not encoded** in the psychoed artifacts (7a/7b are not built categories yet). **When 7a/7b categories are built, check the symmetric back-references** (7c↔7a, 7c↔7b) are wired both directions. Flagged so it is not lost. *(Controller item 7; also ask-section 12, item 12-h.)*

**Ruling — §7c reclassification to answer-first KB category (supersedes interpersonal_effectiveness):** ☐ approve ☐ edit ☐ reject
**Ruling — defer 7a/7b symmetric back-reference check to when those categories are built:** ☐ approve ☐ edit ☐ reject

---

## Ask-section 9 — Surface-2 `kb_ref` additions list

**Scope note:** Surface 2 is the in-flow, step-3 psychoed inside `skill_executor` steps (skills 1a–1e, 2a, 2b, 3a, …). Each skill's 1–3 sentence psychoed script is **distinct signed copy** (skills-framing text, clinician-authored separately — verified against the doc as NOT abridgements of the Understanding-X blocks). The addition here is a **pointer (`kb_ref`), never a copy** — each step-3 script gains a `kb_ref` to its matching Understanding-X article family. The one-line per-skill strings in the doc's Skills tables are Surface-2 presentation copy, **out of this capability's scope** (fixtures must not read them as missing blocks).

**Doc-explicit cross-wirings (confirmed in `bot_behaviour_full.md` — these terminate into §1f "Give options from 1f"):**
| Surface-2 skill section | Doc line | kb_ref target family |
|---|---|---|
| 1a–1c Anxiety Management (Offer Second: "Psychoeducation \| Info") | doc L167 | `understanding_anxiety` (1f) |
| 1d Worry Loops/Rumination (Offer third: "Psychoed anxiety factsheets") | doc L349 | `understanding_anxiety` (1f) |
| 1e Anticipatory Anxiety (Offer third: "Psychoeducation") | doc L417 | `understanding_anxiety` (1f) |

**Design pointer additions (the full `kb_ref` set — ENGINEERING-PROPOSED family assignments, finalized as signed-field edits to the Surface-2 step-3 scripts):** every Surface-2 step-3 psychoed script gains a `kb_ref` to the family matching its skill domain — anxiety skills → `understanding_anxiety`; depression/low-mood skills (3a/3b) → `understanding_depression`; emotion skills (4a/4c) → `understanding_emotions`; assertiveness skills (6a/6b/6c) → `understanding_assertiveness`; connection skills (7a/7b) → `how_do_i_connect`; grief skills (S2a/S2b) → `understanding_grief`. Only the three §1f wirings above are doc-explicit; the remaining family assignments are the design's pointer additions, pending this ratification and the Surface-2 signed-field pass.

**Ruling — the three doc-explicit §1f kb_ref wirings:** ☐ approve ☐ edit ☐ reject
**Ruling — the engineering-proposed family-assignment rule for the remaining Surface-2 kb_refs:** ☐ approve ☐ edit ☐ reject

---

## Ask-section 10 — AR validator naming (first domino for the entire AR chain)

**This is the schedule-critical AR ask. The AR clock does not start until it is answered.**

Per spec §3.7 / §7.3, the **entire Arabic measurement track is blocked on clinical naming a native-Khaleeji, clinically-credentialed validator.** Today:
- **No named validator.**
- No AR corpus, no AR psychoed artifacts (the 40 AR block pairs + 18 AR script pairs = 58 AR artifacts are not built).
- No AR trigger tables, no AR weave data.
- The AR fixture families (F1–F10 in AR) queue behind the same unnamed validator.

**Dependency chain (each step blocked on the prior):** name validator → AR artifact authoring → faithfulness grading of all 58 AR artifacts (cbt-001-ar lesson: nothing ships ungraded) → AR trigger tables + AR weave data → AR fixtures F1–F10 green in AR → AR flag flip. **Validator naming is the first domino; nothing downstream has a clock until it falls.**

The AR flag is **separate** and its preconditions require **all fixture families green in AR** (not graded-artifacts-plus-EN-measurement). Never quote EN-only results as system conformance.

**Ruling — clinical names the native-Khaleeji clinically-credentialed AR validator:** ☐ approve ☐ edit ☐ reject
**Named validator: ______________________________  Date: ____________**

*(Controller item 12.)*

---

## Ask-section 11 — F1 naturalistic-recall acceptance bar (clinical sets it)

Per spec §7.1/§7.3, fixture **F1** has two sets (fixture-independence rule, PR#361): a **wiring set** from the trigger tables (verifies data is read; **never quoted as recall**) and an **independently-authored naturalistic-paraphrase set** (the only set recall claims may cite). The per-category flip precondition (§7.3) reads: *"F1 wiring set green + naturalistic baseline meeting the clinician-set bar."*

**The bar is unset.** Clinical must set the F1 naturalistic-recall acceptance bar — **per category or global, their call.** Gate rationale (§7.1): psychoed is the lowest-precedence pathway; a recognition miss degrades to today's RAG/freeflow behavior, not harm — so importing the 95% safety bar into F1 would be false rigor. F4/F6/F8 remain 100% hard safety gates regardless.

**Without this number, the §7.3 flip precondition dangles on a value nobody was asked to set** — no category can flip on "naturalistic baseline meeting the clinician-set bar" while the bar is undefined.

**Ruling — clinical sets the F1 naturalistic-recall acceptance bar:** ☐ approve ☐ edit ☐ reject
**Bar (per-category or global): ______________________  Scope: ☐ global ☐ per-category**

*(Controller item 11.)*

---

## Ask-section 12 — Open questions (all `pending: clinician` items, cross-referenced)

Every item flagged `pending: clinician` during the build run, collected here. Each links to its home ask-section where the ruling lives.

| # | Open item | Home section | State |
|---|---|---|---|
| 12-a | **1f-b4 bridge**: doc targets "Worry Tree" but **no `worry_tree` skill exists** (`worry_time` is a different technique); shipped `skill_id: null`. Build `worry_tree` OR clinical designates alternative. | §2c (2-i) | PENDING |
| 12-b | **§1f trigger rows all inferred**: no Type column in the doc's §1f recognition bullet list; 3 rows' type/framing/route inferred. Ratify/edit. | §6 (6-i), §3a | PENDING |
| 12-c | **3c-t4 / 3c-t5 inferred**: t4 framing inferred (mixed phrasing); t5 sourced from §7 Guard bullet not §0 table. Ratify. | §6 (6-ii, 6-iii) | PENDING |
| 12-d | **Collision "What's happening to me?" (1f∩3c)**: guard postures differ; interim default 3c (fail-toward-weave); likely resolution = scripted clarifying question. | §3b (3-ii) | PENDING |
| 12-d2 | **Weave-dominance rule** ("longest-exact-match wins iff winning category's guard posture equal-or-stronger; else pending") governing the two subsumption pairs (4b⊂3c, 6d⊂7c). Rule itself needs ratification. | §3b (3-iii/iv) | PENDING |
| 12-e | **S2c serve flag-gated OFF**: gated on the reunification-ideation lexicon landing (its own P0 clock, §5.7), independent of block ratification. S2c is Mechanism-A-live today with no weave against zero Node-1 reunification coverage. | §2a, §5.5 | PENDING (P0, safety queue) |
| 12-f | **`human_referral_close` PENDING-CLINICIAN**: no single quoted universal human-referral close exists in the doc (guard family is prose-only, recurs throughout); clinical to author/designate one. 3c-b7 explicitly NOT repurposed. | §1c (script 4) | PENDING |
| 12-g | **§6d guard is relationship-safety/E7-adjacent** ("unsafe-reaction pattern → relationship-safety resources"); NOT encoded in psychoed artifacts; §6d serve flip should be gated alongside the §6a-guard/E7 launch-blocker. Confirm. | §2e | PENDING |
| 12-h | **§7c guard routes (7a/7b/anxiety/worthlessness) summarized not encoded**; when 7a/7b built, check symmetric back-references. | §8 (8-i) | DEFERRED (to 7a/7b build) |
| 12-i | **Deflection→crisis in PSY-WEAVE-1 is design-added** (doc branch is binary yes/no); named by name for ratification. | §4 | PENDING (design-added) |
| 12-j | **4b-b6 two-bridge encoding** (box_breathing + grounding_5_4_3_2_1, doc_route 1a) since 1a offers a choice. Ratify two-entry encoding. | §2c (2-ii) | PENDING |
| 12-k | **`diagnosis_guard` armed category-agnostic** (also 4b/6d/7c whose own guard sections lack a diagnosis clause; spec §5.5 posture). Confirm. | §5 (5-i) | PENDING |
| 12-l | **AR validator unnamed**: first domino for the entire AR chain; AR clock does not start until named. | §10 | PENDING (blocking AR) |
| 12-m | **F1 naturalistic-recall bar unset**: clinical sets it (per category or global); §7.3 flip precondition dangles without it. | §11 | PENDING (blocking flip) |
| 12-n | **Classifier A structural thresholds** are engineering placeholders (fragmentation ≥3<12chars; N/10 with N≥7); clinical sets values. | §7 | PENDING |
| 12-o | **Fourth period+capital transform site (§6d framing statement, F6d)** found during final-review verification against `bot_behaviour_full.md` line 1606, beyond the three previously identified (1f-b3, 6d-b2, §3c framing — 6d-b2 was itself the third, found during assembly beyond the two the controller pre-named). Four sites total. Surfaced for the same explicit review. | §1 | FLAGGED |

**Recorded decisions (not open — logged for visibility, spec §10 deviations register):**
- Weave-pending session expiry: pending state does NOT survive session exit (a stale flag crisis-routing a next-day "good morning" is the worse failure). Safety-adjacent recorded decision.
- Em-dash copy transformation: ratified via the doc→artifact diff (this packet, ask-section 1).
- Per-category flag structure: doc is silent on rollout; per-category enablement is a design decision.
- `delivery_shape` as per-category attribute + per-article-family `prior_exposure` granularity: named schema extensions (not doc deviations), spec §10.

**Ruling — open-questions register reviewed; each sub-item ruled in its home section:** ☐ approve ☐ edit ☐ reject

---

## Sign-off

**Packet status: DRAFT-FOR-CLINICAL** · EN-only · artifacts pinned at this branch @ `a13c2718`.
No category flips until its asks above are signed (standing rule). S2c additionally gated on the reunification-ideation P0. AR gated on ask-section 10.

Clinician: ______________________________  Date: ____________
