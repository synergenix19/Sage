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
3. **Surface (executor/composer) — SEPARATE `X-Sage-Skill-Media` header (AMENDED 2026-07-07, see approval entry).** When the presented step carries `media` for the turn's language and `gate_path=="standard"`, the server emits a NEW `X-Sage-Skill-Media` header (JSON `{type:"video", url, title, provider}`, `ensure_ascii=True`), looked up from `active_skill_id` + the executed/active step + `detected_language`. **It does NOT ride `X-Sage-Sources`** — that channel enforces the Item 1 audit invariant (sources ⊆ that turn's `knowledge_passages`), and skill media is not a retrieved passage. Skill media audits instead to `active_skill_id` (already recorded) + the approved curation list. The new header inherits X-Sage-Sources' allowlist gate + ensure_ascii **by test, not assumption**.
4. **Render (frontend) — zero new code.** The `X-Sage-Sources` forward (`route.ts`), parse (`chat-interface`), render (`message-bubble` → `VideoEmbed`), and Item-1.5 persistence (`messages.sources` + `hydrateSources`) already handle a `type:"video"` entry. Item 3 adds nothing frontend-side beyond what Items 1/1.5 shipped.

## Safety invariant (must be a test)
Skill media can **never** surface on a crisis turn: crisis bypasses `skill_select` entirely (no skill runs), AND the `X-Sage-Sources` emission is allowlist-gated to `gate_path=="standard"`. Two independent guarantees — plus a test asserting a crisis turn emits no skill-media entry. Mirrors Item 1's proven property.

## Rough task breakdown (TDD, when approved)
1. `SkillMediaItem` model + optional per-language `SkillStep.media` + schema test (existing skills still valid; a skill with `{en:{...}}` media validates; bad url rejected).
2. Executor appends the turn-language `type:video` entry to `X-Sage-Sources` when the presented step has media for that language AND `gate_path=="standard"`; crisis/other paths + missing-language → no entry (+ tests).
3. Frontend: parse the `X-Sage-Skill-Media` header and merge its entry into the message's `sources` (so it renders through the SAME `VideoEmbed` and persists via Item 1.5 for free); crisis → null (same guard). A few lines of client parse; renderer + card pipeline + persistence reused wholesale.
4. Populate the skill JSONs from the **approved** curation list (`{en}` now): `box_breathing`, `progressive_muscle_relaxation`, `mindfulness_body_scan`, `safe_place_visualization` — and `mindfulness_meditation` once authored; per-skill render E2E.
5. Persistence already generalizes (Item 1.5) — skill media survives reopen for free.

## Preconditions / open items
- **Absolute-Rule-1 approval** for the `SkillStep.media` schema addition (skill contract change) — blocks all build steps. **The signable entry below carries the two design decisions (per-language shape + separate-header delivery) so nothing is discovered post-signature.**
- **Clinical sign-off on the curated videos: ✅ APPROVED 2026-07-07** (`docs/kb/2026-07-07-skill-video-curation.md`) — step 4 unblocked once Item 3 is built.
- **`mindfulness_meditation` skill: APPROVED to author as its own skill** (not fold into Body Scan — it must keep a distinct guard profile; Body Scan's dissociation contraindication must not leak onto a general seated meditation). On the content-inventory §4 new-skill backlog + clinician bundle (evidence_base proposed: Kabat-Zinn MBSR + UCLA MARC; clinician-authored steps; CMS approval before registration). Its video attaches once authored.
- **Arabic/Khaleeji media** — EN-only ships now (per-language field ready); Khaleeji set is clinician/sovereign work, later.

## Signable approval entry (Absolute Rule 1 — `SkillStep.media`)
Route this to the approvals register for signature. It fixes the design so signing is final, not provisional:
- **Change:** add optional `SkillStep.media: dict[str, SkillMediaItem]` (`SkillMediaItem = {type:"video", url, title, provider}`). Additive, nullable; existing skills byte-identical.
- **Per-language:** `media` is keyed by language (`{en, ar}`), mirroring `examples`. EN populated now; AR later without re-approval. Missing language → no media emitted (graceful degradation).
- **Delivery channel (AMENDED 2026-07-07, post-signature):** skill media rides a **NEW `X-Sage-Skill-Media`** header (allowlist-gated to `gate_path=="standard"`, `ensure_ascii=True`), NOT `X-Sage-Sources`. **Rationale:** `X-Sage-Sources` enforces the Item 1 audit invariant — every shown source ⊆ that turn's retrieved `knowledge_passages` — and skill media is not a retrieved passage, so riding that channel would silently corrupt the clinical audit trail. Separate header is honest audit by construction (skill media traces to `active_skill_id` + curation list). Renderer, card pipeline, and persistence are still reused. *Attribution: the original reuse recommendation was my (engineering) miss, recommended without checking the invariant, caught pre-build. Behaviour is identical and audit strictly stronger, so recorded as a post-signature amendment under the clinician's blanket approval — no re-signature cycle.*
- **Safety:** never surfaces on crisis (crisis bypasses `skill_select` + allowlist gate); asserted by test.
- **Content:** populates from the APPROVED curation list only; `mindfulness_meditation` attaches after its skill is authored + CMS-registered.

## Reuse ledger (why this is cheap once approved)
Renderer: `VideoEmbed` (Item 1) — 100% reuse. Client pipeline: header→message→card (Item 1). Persistence: `messages.sources` + `hydrateSources` guard (Item 1.5) — generalizes. Net new: one schema field, one executor emit, JSON population — **no new header, no new renderer**. The infrastructure investment from Items 1/1.5 is what makes Item 3 small.
