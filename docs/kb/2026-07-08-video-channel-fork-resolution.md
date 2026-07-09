# Video channel — fork resolution (2026-07-08)

**Decision:** sample/technique videos ride the **skill-media channel (Lane 2 Item 3, `SkillStep.media` → `X-Sage-Skill-Media`)**, NOT the KB source-card channel (`X-Sage-Sources`). The improved video facade renders in its spec-correct home.

## Why (authority)
`docs/kb/2026-07-07-skill-video-curation.md` is the behavioral authority. The 5 approved videos map one-to-one onto the BOT BEHAVIOUR `Format: Video` skills; content, approval, and the behavioral spec all point at the skill-delivery channel. The KB info-request article path was ruled off-spec 2026-07-07 (`Format: Video` = skill delivery, not KB articles) and its placeholder videos pulled. **There is currently zero approved psychoeducational-video content for KB source cards** — so the "re-add to KB articles" option (A′) has no content to add; the question is moot. No reversal of the off-spec pull.

## State — Item 3 is BUILT, gated (not unbuilt)
Verified 2026-07-08:
- **Skill JSONs** — 5 approved videos wired into step-level `media` (per-language `en`). e.g. `box_breathing.json` step `inhale_hold` → `G25IR0c-Hj8` (CHI Health). ✓
- **Backend** — `server.py:_skill_media_header` emits `X-Sage-Skill-Media`; gates: default-OFF kill-switch `SAGE_SKILL_MEDIA_ENABLED`, `standard`-only gate_path allowlist, skill+step present, `step.media[lang]`. Audits to `active_skill_id` (not the sources channel, whose invariant is `sources ⊆ knowledge_passage_ids`). ✓
- **Frontend** — `chat-interface.tsx` reads the header → maps to a `video` `Source` → renders through the **same SourceCard / VideoEmbed** (the improved click-to-play facade). ✓ **Facade-compatibility CONFIRMED.**

## Remaining gates (neither is code)
1. **Item-3 approval entry SIGNED** — governance (PO/clinician). Schema shape + delivery-channel choice must be in the approval entry before signature (per the curation doc, avoids a post-sign amendment).
2. **Flip `SAGE_SKILL_MEDIA_ENABLED=true`** in prod (Railway env) — gated on #1. Rollback = unset/false.

Then: a video-format skill (e.g. box breathing) delivers its video step and the facade renders. Engineering critical path is unchanged (Lane 1 E7 Part 2 / MARBERT); this does not jump the queue.
