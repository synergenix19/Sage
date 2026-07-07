# Skill-video curation (BOT BEHAVIOUR `Format: Video`) — 2026-07-07

**✅ APPROVED 2026-07-07.** The five videos below are signed off for use. They were engineer-curated from reputable sources and technically verified (real, public, embeddable), then approved. Because they deliver *as therapy*, this record stands as the signed known-list; any future swap is a diff against it.

## What this is
The BOT BEHAVIOUR spec marks certain **skills** with `Format: Video` — the bot *delivers* the skill as a video when it offers it. This is **Lane 2 Item 3 (`SkillStep.media`)**, not the KB-article source-card path (Item 1). This table is the media set for Item 3; wiring is scoped separately (`docs/superpowers/plans/2026-07-07-lane2-item3-skill-media-scope.md`).

## The 5 video-skills → curated links

| Spec skill | Skill file | Video (title) | URL | Source | oembed |
|---|---|---|---|---|---|
| Box Breathing | `box_breathing.json` | Box Breathing for Stress (4-4-4-4) | https://www.youtube.com/watch?v=G25IR0c-Hj8 | CHI Health (health system) | ✅ embeddable |
| Progressive Muscle Relaxation | `progressive_muscle_relaxation.json` | PMR: An Essential Anxiety Skill #27 | https://www.youtube.com/watch?v=SNqYG95j_UQ | Therapy in a Nutshell (Emma McAdam, LMFT) | ✅ |
| Mindfulness Meditation | *to author `mindfulness_meditation.json` (approved — see open items)* | Meditation for Working with Difficulties | https://www.youtube.com/watch?v=XInJoYvy_ew | UCLA Health (MARC) | ✅ |
| Mindfulness Body Scan | `mindfulness_body_scan.json` | A Body Scan with Diana Winston | https://www.youtube.com/watch?v=K06KxR-w4HU | Mindful.org / UCLA's Diana Winston | ✅ |
| Guided Visualization | `safe_place_visualization.json` | Safe and Peaceful Place Visualization (4 min) | https://www.youtube.com/watch?v=G1bxxiiXc48 | Clarity Psychological Services | ✅ |

## Verification method (technical, not clinical)
Each URL was checked via the YouTube **oembed** endpoint (`/oembed?url=…&format=json`) — it returns a title + author + iframe only for videos that are public **and** embedding-enabled; embedding-disabled/private/deleted videos fail it. So each entry is confirmed **real, public, and embeddable** (won't show "video unavailable" in the card). This does NOT verify clinical appropriateness of the content — see the review gate above.

## Decisions (2026-07-07) & clinician-bundle queue
- **Gentle & evidence-based (settled).** The Wim Hof placeholder was pulled — an intense hyperventilation+cold practice that can provoke anxiety, unsuitable as a default. Box Breathing (CHI Health) + diaphragmatic techniques are the gentle standard used above.
- **`mindfulness_meditation` → its own skill (APPROVED).** The spec lists it as a distinct Tier-2 anxiety skill; `mindfulness_body_scan.json` is Body Scan only. Decisive reason: Body Scan carries a **dissociation contraindication** (spec §6 guards are load-bearing — grounding/mindfulness "can intensify these states"); a general seated meditation must **not** inherit or tempt loosening of that guard. Separate skills keep separate guard profiles. **Queue:** joins the content-inventory §4 new-skill backlog with the standing obligations — `evidence_base` mandatory (proposed: Kabat-Zinn MBSR lineage + UCLA MARC), clinician-authored steps, CMS approval before registration. Same class as the earlier orphan-signal finding (a spec-referenced skill missing from the 27-skill registry) → **on the clinician queue alongside this video sign-off.**
- **English-only video, `media` keyed per-language `{en, ar}` (APPROVED both halves).** EN-only is honest degradation, not a gap — the skill's full therapeutic delivery stays bilingual via the text/guided path; auto-sourcing Arabic video would repeat the placeholder mistake. Khaleeji media is clinician work (or sovereign Sage-produced media, already on the before-external-exposure checklist). Per-language field mirrors the existing bilingual `examples` pattern. **Both this schema shape and the delivery-channel choice must be in the Item-3 approval entry before signature** (avoids a post-sign amendment) — see the scope doc.
- **Length fit.** Body-scan/meditation run longer than the "few minutes" the spec suggests; acceptable per clinician.

## Status
**Videos: APPROVED 2026-07-07.** This makes Item 3 drop-in-ready **once the Item-3 approval entry is signed** — it does not jump the queue. Engineering critical path remains Lane 1 (E7 Part 2, MARBERT data-readiness).

## Provenance
Curated 2026-07-07 during the Lane 2 video-model correction (article-path placeholders pulled; see [[../kb/2026-07-07-seeded-sample-media-manifest.md]]). Replaces the notion that the 4 seeded KB articles were "the bot videos."
