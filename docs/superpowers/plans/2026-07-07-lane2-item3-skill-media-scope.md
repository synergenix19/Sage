# Lane 2 Item 3 — Skill-delivered media (`SkillStep.media`) — SCOPE

> **Status: SCOPE ONLY. Build gated on an Absolute-Rule-1 approval entry** (this changes the skill schema — the clinician-owned content contract). Do not implement steps until that approval is recorded. Curated media (the content this delivers) is likewise clinician-sign-off-pending (`docs/kb/2026-07-07-skill-video-curation.md`).

## Goal
Let a skill **deliver a video** when the bot offers it, per the BOT BEHAVIOUR spec's `Format: Video` skills (Box Breathing, PMR, Mindfulness Meditation, Mindfulness Body Scan, Guided Visualization). Today video only rides KB **articles** (Item 1). This wires video to **skill delivery** — a different, spec-mandated channel.

## Why this is not Item 1
Item 1 (`X-Sage-Sources`) fires on `info_request` → `knowledge_retrieve`, attaching media to retrieved KB passages. Skills run on the `skill_select` path; the spec attaches `Format: Video` to the *skill/step*, not to a retrieved article. So this needs its own field + surfacing point. It **reuses** Item 1's proven pieces: the `VideoEmbed`/`source-card` renderer (wholesale) and the header→card client pipeline.

## Architecture (proposed)
1. **Schema (`src/sage_poc/skills/schema.py`) — `media` keyed PER-LANGUAGE.** Add an optional field to `SkillStep`:
   ```python
   media: dict[str, SkillMediaItem] | None = None   # keyed by language: {"en": {...}, "ar": {...}}; null = none
   class SkillMediaItem(BaseModel):
       type: Literal["video"] = "video"
       url: str                          # full provider URL (never a bare id) — same contract as Source.url
       title: str = ""
       provider: str = ""                # attribution, e.g. "UCLA Health"
   ```
   **Per-language `{en, ar}`** mirrors the existing bilingual `examples` pattern: EN attaches now, AR (clinician-sourced Khaleeji) drops in later with no schema change. The executor selects the entry for the turn's language; if that language is absent it emits **nothing** (graceful EN-only degradation — the skill's text/guided path still delivers fully). Step-level (not skill-level) so a multi-step skill attaches the video only to the step that *is* the exercise. Additive + nullable ⇒ every existing skill JSON stays valid (byte-identical when null).
2. **Populate skill JSONs** (post-clinical-signoff) from the curation artifact: `box_breathing`, `progressive_muscle_relaxation`, `mindfulness_body_scan`, `safe_place_visualization` (+ resolve the "Mindfulness Meditation" mapping). Only the exercise step gets `media`.
3. **Surface (executor/composer) — REUSE `X-Sage-Sources`, do NOT add a new header.** When the presented step carries `media` for the turn's language, the executor **appends a `{type:"video", url, title}` entry to the existing `X-Sage-Sources` list** (same `ensure_ascii=True`, same `gate_path=="standard"` allowlist gate). Skills run on the standard path, so this rides the identical channel Item 1 already emits — maximal reuse, no new header, no new client parse. (Decision: reuse over a new `X-Sage-Skill-Media` header — the frontend already renders `type:"video"` via `VideoEmbed`.)
4. **Render (frontend) — zero new code.** The `X-Sage-Sources` forward (`route.ts`), parse (`chat-interface`), render (`message-bubble` → `VideoEmbed`), and Item-1.5 persistence (`messages.sources` + `hydrateSources`) already handle a `type:"video"` entry. Item 3 adds nothing frontend-side beyond what Items 1/1.5 shipped.

## Safety invariant (must be a test)
Skill media can **never** surface on a crisis turn: crisis bypasses `skill_select` entirely (no skill runs), AND the `X-Sage-Sources` emission is allowlist-gated to `gate_path=="standard"`. Two independent guarantees — plus a test asserting a crisis turn emits no skill-media entry. Mirrors Item 1's proven property.

## Rough task breakdown (TDD, when approved)
1. `SkillMediaItem` model + optional per-language `SkillStep.media` + schema test (existing skills still valid; a skill with `{en:{...}}` media validates; bad url rejected).
2. Executor appends the turn-language `type:video` entry to `X-Sage-Sources` when the presented step has media for that language AND `gate_path=="standard"`; crisis/other paths + missing-language → no entry (+ tests).
3. Frontend: **none** — reuses the Item 1/1.5 `X-Sage-Sources` pipeline; add a render test proving a skill-media `type:video` entry shows the card.
4. Populate the skill JSONs from the **approved** curation list (`{en}` now): `box_breathing`, `progressive_muscle_relaxation`, `mindfulness_body_scan`, `safe_place_visualization` — and `mindfulness_meditation` once authored; per-skill render E2E.
5. Persistence already generalizes (Item 1.5) — skill media survives reopen for free.

## Preconditions / open items
- **Absolute-Rule-1 approval** for the `SkillStep.media` schema addition (skill contract change) — blocks all build steps. **The signable entry below carries the two design decisions (per-language shape + reuse-`X-Sage-Sources` delivery) so nothing is discovered post-signature.**
- **Clinical sign-off on the curated videos: ✅ APPROVED 2026-07-07** (`docs/kb/2026-07-07-skill-video-curation.md`) — step 4 unblocked once Item 3 is built.
- **`mindfulness_meditation` skill: APPROVED to author as its own skill** (not fold into Body Scan — it must keep a distinct guard profile; Body Scan's dissociation contraindication must not leak onto a general seated meditation). On the content-inventory §4 new-skill backlog + clinician bundle (evidence_base proposed: Kabat-Zinn MBSR + UCLA MARC; clinician-authored steps; CMS approval before registration). Its video attaches once authored.
- **Arabic/Khaleeji media** — EN-only ships now (per-language field ready); Khaleeji set is clinician/sovereign work, later.

## Signable approval entry (Absolute Rule 1 — `SkillStep.media`)
Route this to the approvals register for signature. It fixes the design so signing is final, not provisional:
- **Change:** add optional `SkillStep.media: dict[str, SkillMediaItem]` (`SkillMediaItem = {type:"video", url, title, provider}`). Additive, nullable; existing skills byte-identical.
- **Per-language:** `media` is keyed by language (`{en, ar}`), mirroring `examples`. EN populated now; AR later without re-approval. Missing language → no media emitted (graceful degradation).
- **Delivery channel:** skill media rides the **existing `X-Sage-Sources`** header as a `type:"video"` entry (allowlist-gated to `gate_path=="standard"`); **no new header**, no new renderer.
- **Safety:** never surfaces on crisis (crisis bypasses `skill_select` + allowlist gate); asserted by test.
- **Content:** populates from the APPROVED curation list only; `mindfulness_meditation` attaches after its skill is authored + CMS-registered.

## Reuse ledger (why this is cheap once approved)
Renderer: `VideoEmbed` (Item 1) — 100% reuse. Client pipeline: header→message→card (Item 1). Persistence: `messages.sources` + `hydrateSources` guard (Item 1.5) — generalizes. Net new: one schema field, one executor emit, JSON population — **no new header, no new renderer**. The infrastructure investment from Items 1/1.5 is what makes Item 3 small.
