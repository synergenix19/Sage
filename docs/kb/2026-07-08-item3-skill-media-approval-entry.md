# Item 3 (skill-media) — approval entry [DRAFT, awaiting signature]

**Status:** DRAFT prepared by engineering (prep-not-sign). Signature below enables the governance gate; it does NOT itself flip anything. On signature, the separate action is `SAGE_SKILL_MEDIA_ENABLED=true` in prod (its own explicit trigger, prod-verified).

**What is being approved:** delivery of five specific, engineer-curated psychoeducational videos as **skill-step media** on the skill-delivery channel — *not* a category, *not* the KB source-card channel. Sign-off is per-video content plus the channel/schema/guard/accessibility decisions below, so no post-sign amendment is needed.

---

## 1. The five videos — by identity
oembed-verified (public + embedding-enabled) **2026-07-07**; media confirmed wired into the skill JSON at the named step, **2026-07-08**. All **English-only** (per the curation doc's English-only-video decision; the skill's full delivery stays bilingual via the text/guided path).

| BOT_BEHAVIOUR skill | Skill file / delivering step | Video title | Source | URL | oembed | Lang |
|---|---|---|---|---|---|---|
| Box Breathing | `box_breathing.json` / `inhale_hold` | Box Breathing for Stress | CHI Health (health system) | https://www.youtube.com/watch?v=G25IR0c-Hj8 | ✅ 2026-07-07 | en |
| Progressive Muscle Relaxation | `progressive_muscle_relaxation.json` / `breathe_and_settle` | Progressive Muscle Relaxation: An Essential Anxiety Skill #27 | Therapy in a Nutshell (Emma McAdam, LMFT) | https://www.youtube.com/watch?v=SNqYG95j_UQ | ✅ 2026-07-07 | en |
| Mindfulness Meditation | `mindfulness_meditation.json` / `settle_and_anchor` | Meditation for Working with Difficulties | UCLA Health (MARC) | https://www.youtube.com/watch?v=XInJoYvy_ew | ✅ 2026-07-07 | en |
| Mindfulness Body Scan | `mindfulness_body_scan.json` / `lower_body` | A Body Scan with Diana Winston | Mindful.org / UCLA (Diana Winston) | https://www.youtube.com/watch?v=K06KxR-w4HU | ✅ 2026-07-07 | en |
| Guided Visualization | `safe_place_visualization.json` / `introduce_safe_place` | Safe and Peaceful Place Visualization | Clarity Psychological Services | https://www.youtube.com/watch?v=G1bxxiiXc48 | ✅ 2026-07-07 | en |

## 2. Media schema shape + delivery channel
- **Schema (`SkillStep.media`):** per-step, per-language map —
  `media: { "en": { "type": "video", "url": "...", "title": "...", "provider": "..." } }`.
  The backend emits the item for the turn's `detected_language` only; a missing language = no media (honest degradation, not a gap).
- **Channel:** `X-Sage-Skill-Media` response header — **distinct from `X-Sage-Sources`** by design. Skill media is NOT a retrieved KB passage, so it must not ride the sources channel (whose invariant is `sources ⊆ session_audit.knowledge_passage_ids`). Skill media audits to `active_skill_id` (already recorded) against this approved list. Frontend maps the header → a `video` Source → the same SourceCard/VideoEmbed facade.

## 3. Guard inheritance — clinically load-bearing
**A video step renders ONLY when the executor delivers that step.** By that point the BOT_BEHAVIOUR gating has already run upstream in the flow: red-flag screens, the dissociation/psychosis **withholding** for grounding-/mindfulness-class content (spec §6 guards — grounding/mindfulness "can intensify these states"), and the deterministic crisis override (Node 1). **Video delivery inherits the flow's gating; it does not create a bypass around it.** This is the entire architectural argument for putting video on the skill-delivery channel rather than the KB source channel — stated here where the signature lands.

## 4. Accessibility — captions/subtitles (explicit, not silence)
WCAG-in-spirit applies at least as strongly to a *delivered intervention* as to a reading card: a video-delivered technique a hearing-impaired user cannot follow is an **intervention-access gap**, not polish.

- **Caption status — KNOWN (verified per video via each video's player-response `captionTracks`, 2026-07-08):**

  | Video | Skill | Captions |
  |---|---|---|
  | Box Breathing for Stress (CHI Health) | box_breathing | ❌ **NONE** |
  | PMR #27 (Therapy in a Nutshell) | progressive_muscle_relaxation | ✅ ar, de, en, es, fil, hi |
  | Meditation for Working with Difficulties (UCLA Health) | mindfulness_meditation | ✅ en |
  | A Body Scan with Diana Winston (Mindful.org) | mindfulness_body_scan | ✅ en |
  | Safe and Peaceful Place Visualization (Clarity) | safe_place_visualization | ✅ en |

  4/5 have caption tracks; **Box Breathing (CHI Health) is the sole gap.** Caveat: some of the four include auto-generated (ASR) tracks — present, but not human-verified; adequate-beats-absent for POC, flag human-caption verification for Full Build.
- **Signer decision (the question narrows to Box Breathing):**
  - [x] **Accept** Box Breathing uncaptioned at POC — **SELECTED (signer, 2026-07-08)** — condition recorded: *"Box Breathing shipped without captions at POC; captioned or replaced before Full Build."* Other four clear.
  - [ ] Require Box Breathing captioned/replaced before enable. (not selected)

## 5. Provenance + rollback
- **Channel decision provenance:** `docs/kb/2026-07-08-video-channel-fork-resolution.md` (Item 3, not KB source cards).
- **Content curation authority:** `docs/kb/2026-07-07-skill-video-curation.md`.
- **Rollback mechanism:** `SAGE_SKILL_MEDIA_ENABLED` (default-OFF kill-switch) — unset/false instantly withdraws all skill-media delivery, no deploy.

---

## Signature
- **Decision:** ☑ **Approved with conditions** (§4 Box Breathing choice)
- **Signer (name + role):** Product Owner (synergenix.global@gmail.com) — *recorded onto the artifact from the signer's direct in-session confirmation, 2026-07-08 ("the entry is signed; I had given the approval"). Register holder: stamp exact name/title if the register standard requires more than role.*
- **Date:** 2026-07-08
- **Conditions / notes:** §4 = **ACCEPT Box Breathing uncaptioned at POC** (CHI Health video has no captions); condition — *"Box Breathing captioned or replaced before Full Build."* Other four videos captioned. Rollback = `SAGE_SKILL_MEDIA_ENABLED` unset/false.

*Signed → flag already `true` in prod (legitimate under this approval) → prod-verify at `/health/version` (needs the observability field, PR #170) → behavioral smoke (box breathing renders the video step through the facade in the guided flow; crisis turn withholds it; transcript attached) before "live" is claimed.*
