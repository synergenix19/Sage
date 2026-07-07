# Lane 2 Item 3 — Skill-delivered media (`SkillStep.media`) — SCOPE

> **Status: SCOPE ONLY. Build gated on an Absolute-Rule-1 approval entry** (this changes the skill schema — the clinician-owned content contract). Do not implement steps until that approval is recorded. Curated media (the content this delivers) is likewise clinician-sign-off-pending (`docs/kb/2026-07-07-skill-video-curation.md`).

## Goal
Let a skill **deliver a video** when the bot offers it, per the BOT BEHAVIOUR spec's `Format: Video` skills (Box Breathing, PMR, Mindfulness Meditation, Mindfulness Body Scan, Guided Visualization). Today video only rides KB **articles** (Item 1). This wires video to **skill delivery** — a different, spec-mandated channel.

## Why this is not Item 1
Item 1 (`X-Sage-Sources`) fires on `info_request` → `knowledge_retrieve`, attaching media to retrieved KB passages. Skills run on the `skill_select` path; the spec attaches `Format: Video` to the *skill/step*, not to a retrieved article. So this needs its own field + surfacing point. It **reuses** Item 1's proven pieces: the `VideoEmbed`/`source-card` renderer (wholesale) and the header→card client pipeline.

## Architecture (proposed)
1. **Schema (`src/sage_poc/skills/schema.py`).** Add an optional field to `SkillStep`:
   ```python
   media: SkillMedia | None = None      # optional; null = no media (current behavior)
   class SkillMedia(BaseModel):
       type: Literal["video"] = "video"
       url: str                          # full provider URL (never a bare id) — same contract as Source.url
       title: str = ""
       provider: str = ""                # attribution, e.g. "UCLA Health" — for the curation/audit trail
   ```
   Step-level (not skill-level) so a multi-step skill can attach the video to the specific step that *is* the exercise, and leave psychoed/check-in steps text-only. Additive + nullable ⇒ every existing skill JSON stays valid (byte-identical when null).
2. **Populate skill JSONs** (post-clinical-signoff) from the curation artifact: `box_breathing`, `progressive_muscle_relaxation`, `mindfulness_body_scan`, `safe_place_visualization` (+ resolve the "Mindfulness Meditation" mapping). Only the exercise step gets `media`.
3. **Surface (executor/composer).** When the presented step carries `media`, emit a response header — **`X-Sage-Skill-Media`** (new, parallel to `X-Sage-Sources`), JSON `{type,url,title,provider}`, `ensure_ascii=True`. Gate it with the **same allowlist** as Item 1 (`gate_path == "standard"`), so it can only ride the ordinary skill path.
4. **Render (frontend).** `route.ts` forwards the header (unconditionally, like `X-Sage-Sources`); `chat-interface` parses it onto the AI message; `message-bubble` renders it through the **existing `VideoEmbed`** — no new renderer. Persistence (Item 1.5) generalizes: store on the message row alongside `sources` (or as a `sources` entry of `type:video`).

## Safety invariant (must be a test)
Skill media can **never** surface on a crisis turn: crisis bypasses `skill_select` entirely (no skill runs), AND the header is allowlist-gated to `gate_path=="standard"`. Two independent guarantees — plus a test asserting a crisis turn emits no `X-Sage-Skill-Media`. Mirrors Item 1's proven property.

## Rough task breakdown (TDD, when approved)
1. `SkillMedia` model + optional `SkillStep.media` + schema test (existing skills still valid; a skill with media validates; bad url rejected).
2. Executor emits `X-Sage-Skill-Media` when the presented step has media AND `gate_path=="standard"`; crisis/other paths emit nothing (+ crisis test).
3. Frontend: forward + parse + render via existing `VideoEmbed`; malformed header → no card (reuse the Item 1.5 guard).
4. Populate the 4–5 skill JSONs from the **clinician-signed** curation list; per-skill render E2E.
5. (Optional) fold into Item 1.5 persistence so skill media survives reopen.

## Preconditions / open items
- **Absolute-Rule-1 approval** for the `SkillStep.media` schema addition (skill contract change) — blocks all build steps.
- **Clinical sign-off** on the curated videos (`docs/kb/2026-07-07-skill-video-curation.md`) — blocks populating the JSONs (step 4).
- **"Mindfulness Meditation" skill mapping** — no dedicated skill file today; confirm target before attaching its video.
- **Arabic/Khaleeji media** — the curated set is English; source culturally-attuned equivalents before bilingual rollout.

## Reuse ledger (why this is cheap once approved)
Renderer: `VideoEmbed` (Item 1) — 100% reuse. Client pipeline: header→message→card (Item 1). Persistence: `messages.sources` + `hydrateSources` guard (Item 1.5) — generalizes. Net new: one schema field, one header, one executor emit, JSON population. The infrastructure investment from Items 1/1.5 is what makes Item 3 small.
