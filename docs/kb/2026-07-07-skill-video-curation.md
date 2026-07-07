# Skill-video curation (BOT BEHAVIOUR `Format: Video`) — 2026-07-07

**⚠️ CLINICAL REVIEW: PENDING.** These are curated by an engineer from reputable sources and technically verified (real, public, embeddable). They are delivered *as therapy* (a distressed user is shown these when offered a skill), so **clinician sign-off is required before they go live** — the standing rule for therapeutic content. This doc is the "known list" to be signed as a diff, not an approval.

## What this is
The BOT BEHAVIOUR spec marks certain **skills** with `Format: Video` — the bot *delivers* the skill as a video when it offers it. This is **Lane 2 Item 3 (`SkillStep.media`)**, not the KB-article source-card path (Item 1). This table is the media set for Item 3; wiring is scoped separately (`docs/superpowers/plans/2026-07-07-lane2-item3-skill-media-scope.md`).

## The 5 video-skills → curated links

| Spec skill | Skill file | Video (title) | URL | Source | oembed |
|---|---|---|---|---|---|
| Box Breathing | `box_breathing.json` | Box Breathing for Stress (4-4-4-4) | https://www.youtube.com/watch?v=G25IR0c-Hj8 | CHI Health (health system) | ✅ embeddable |
| Progressive Muscle Relaxation | `progressive_muscle_relaxation.json` | PMR: An Essential Anxiety Skill #27 | https://www.youtube.com/watch?v=SNqYG95j_UQ | Therapy in a Nutshell (Emma McAdam, LMFT) | ✅ |
| Mindfulness Meditation | ⚠️ *no dedicated skill file — confirm mapping* | Meditation for Working with Difficulties | https://www.youtube.com/watch?v=XInJoYvy_ew | UCLA Health (MARC) | ✅ |
| Mindfulness Body Scan | `mindfulness_body_scan.json` | A Body Scan with Diana Winston | https://www.youtube.com/watch?v=K06KxR-w4HU | Mindful.org / UCLA's Diana Winston | ✅ |
| Guided Visualization | `safe_place_visualization.json` | Safe and Peaceful Place Visualization (4 min) | https://www.youtube.com/watch?v=G1bxxiiXc48 | Clarity Psychological Services | ✅ |

## Verification method (technical, not clinical)
Each URL was checked via the YouTube **oembed** endpoint (`/oembed?url=…&format=json`) — it returns a title + author + iframe only for videos that are public **and** embedding-enabled; embedding-disabled/private/deleted videos fail it. So each entry is confirmed **real, public, and embeddable** (won't show "video unavailable" in the card). This does NOT verify clinical appropriateness of the content — see the review gate above.

## Curation notes / open items for the clinician
- **Deliberately gentle & evidence-based.** The earlier placeholder (Wim Hof Method breathing) was pulled — Wim Hof is an intense hyperventilation+cold practice that can provoke anxiety and is unsuitable as a default. Box Breathing (CHI Health) and diaphragmatic techniques are the gentle standard.
- **"Mindfulness Meditation" has no dedicated skill file** (`mindfulness_body_scan.json` is the Body Scan). Confirm whether Mindfulness Meditation is delivered by an existing skill or needs its own — this affects where its video attaches.
- **Sources skew Western/English.** For the bilingual AR/Khaleeji audience, Arabic-language or culturally-attuned equivalents should be sourced before broad rollout (parallels the KB Arabic work).
- **Length fit.** Spec wants short clips ("a few minutes"). Confirmed short where possible; body-scan/meditation run longer — clinician to confirm acceptable durations per skill.

## Provenance
Curated 2026-07-07 during the Lane 2 video-model correction (article-path placeholders pulled; see [[../kb/2026-07-07-seeded-sample-media-manifest.md]]). Replaces the notion that the 4 seeded KB articles were "the bot videos."
