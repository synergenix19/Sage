// apps/web/lib/sage-headers.ts
//
// Shared parsing for the X-Sage-* response headers the backend attaches to a
// chat turn. Both the persist path (app/api/chat/route.ts) and the render
// path (components/chat/chat-interface.tsx) import extractSageMetadata from
// here so stored and rendered metadata can never diverge — one parse
// implementation, two call sites (Task 6a).
//
// Crisis sentinel handling (hasCrisisSignal / stripCrisisSignal on the
// streamed message BODY, and the isCrisis derivation it feeds) is NOT part
// of this module and does not move here — it stays in lib/crisis.ts and each
// call site's own stream-accumulation loop (Global Constraint). This module
// only parses response HEADERS; crisis-turn suppression of `sources` in the
// persisted row is still applied by route.ts itself, keyed off its own
// content-derived isCrisis flag.

import type { Json, Source } from '@cdai/types'

export const SAGE_HEADERS_WHITELIST = [
  'x-sage-node-path',
  'x-sage-gate-path',
  'x-sage-prompt-layers',
  'x-sage-intent',
  'x-sage-emotional-intensity',
  'x-sage-turn-number',
]

export function parseJsonHeader<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try { return JSON.parse(raw) as T } catch { return fallback }
}

export function parseIntHeader(raw: string | null): number | null {
  if (!raw) return null
  const n = parseInt(raw, 10)
  return Number.isNaN(n) ? null : n
}

export function parseFloatHeader(raw: string | null): number | null {
  if (!raw) return null
  const n = parseFloat(raw)
  return Number.isNaN(n) ? null : n
}

// Skill-delivered media (X-Sage-Skill-Media) is a SEPARATE header from
// X-Sage-Sources (skill media is not a retrieved KB passage; see sage-poc
// _skill_media_header). Converts the parsed header payload into the same
// Source shape KB source cards use so it renders through the same
// SourceCard / VideoEmbed.
export function skillMediaToSource(parsed: { type: Source['type']; title?: string; url: string; provider?: string }): Source {
  return { type: parsed.type, title: parsed.title ?? '', url: parsed.url, citation: parsed.provider ?? '' }
}

export interface SageMetadata {
  intentClassification: string | null
  secondaryIntentClassification: string | null
  sageModel: string | null
  skillId: string | null
  stepId: string | null
  gatePath: string | null
  sageNodePath: string[] | null
  crisisFlags: string[] | null
  sageClinicalFlags: string[] | null
  emotionalIntensity: number | null
  semanticScore: number | null
  promptLayers: string[] | null
  // #553 (concurrent) generated the DB Insert column type for token_usage as
  // `Json | null` (see database.types.ts). Typed to match here rather than
  // `object | null`, its pre-#553 shape.
  tokenUsage: Json | null
  turnNumber: number | null
  crisisState: string | null
  direction: 'ltr' | 'rtl' | undefined
  // Raw JSON parsed from X-Sage-Sources, merged with skill-delivered media if
  // present — typed as `Json`, not `Source[]`, because it is untrusted external
  // data whose shape is only ever confirmed by "did JSON.parse succeed", never
  // structurally validated. The persist path (route.ts) writes this straight
  // into the `messages.sources` `Json` column as-is. The render path narrows it
  // to `Source[]` at its own point of use (chat-interface.tsx / Task 6d) — the
  // same informal assumption JSON.parse's `any` return always made, now made
  // explicit there instead of implicit here. Crisis-turn suppression of this
  // value is NOT applied here — see module header.
  sources: Json | null
}

// Parses every X-Sage-* metadata header off a single Headers object (the
// upstream sage-poc Response headers). Called once per turn from both the
// persist path and the render path — see module header for the invariant
// this exists to make structural.
export function extractSageMetadata(headers: Headers): SageMetadata {
  const intentClassification          = headers.get('X-Sage-Intent') || null
  const secondaryIntentClassification = headers.get('X-Sage-Secondary-Intent') || null

  const sageModel = headers.get('X-Sage-Model')
  const skillId    = headers.get('X-Sage-Skill-Id') || null
  const stepId     = headers.get('X-Sage-Step-Id') || null
  const gatePath   = headers.get('X-Sage-Gate-Path') || null

  const sageNodePath      = parseJsonHeader<string[] | null>(headers.get('X-Sage-Node-Path'), null)
  const crisisFlags       = parseJsonHeader<string[] | null>(headers.get('X-Sage-Crisis-Flags'), null)
  const sageClinicalFlags = parseJsonHeader<string[] | null>(headers.get('X-Sage-Clinical-Flags'), null)

  const emotionalIntensity = parseIntHeader(headers.get('X-Sage-Emotional-Intensity'))
  const semanticScore      = parseFloatHeader(headers.get('X-Sage-Semantic-Score'))

  const promptLayers = parseJsonHeader<string[] | null>(headers.get('X-Sage-Prompt-Layers'), null)
  const tokenUsage    = parseJsonHeader<Json | null>(headers.get('X-Sage-Token-Usage'), null)
  const turnNumber    = parseIntHeader(headers.get('X-Sage-Turn-Number'))

  const crisisState = headers.get('X-Sage-Crisis-State') || null

  // Authoritative text direction from the backend (drives RTL rendering).
  const directionRaw = headers.get('X-Sage-Direction')
  const direction: 'ltr' | 'rtl' | undefined =
    directionRaw === 'rtl' || directionRaw === 'ltr' ? directionRaw : undefined

  // KB source cards (X-Sage-Sources) — a raw JSON string forwarded verbatim
  // from the backend. Parsed once here so persist and render read the exact
  // same value (Lane 2 Item 1.5: stored == rendered). A malformed header
  // must never crash the render, so a parse failure silently falls back to
  // "no sources".
  const sourcesHeader = headers.get('X-Sage-Sources')
  let sources: Json = null
  if (sourcesHeader) {
    try { sources = JSON.parse(sourcesHeader) } catch { sources = null }
  }

  // Merge skill-delivered media into sources so it renders via the same
  // SourceCard (Item 1.5). Malformed → skip, keep whatever KB sources parsed.
  //
  // DISCLOSED BEHAVIOR CHANGE (fix round 1, PR body): before this extraction,
  // the persist copy guarded this merge with `Array.isArray(parsedSources) ?
  // parsedSources : []` — a non-array-but-valid-JSON X-Sage-Sources value was
  // discarded and replaced with just `[mediaEntry]`. The render copy had no
  // such guard. This extraction adopted the RENDER copy's (unguarded)
  // behavior for BOTH call sites — deliberately, since stored==rendered is
  // the entire point of the unification, and the render copy's behavior is
  // no less defensible. The explicit throw below reproduces that exact
  // behavior in a type-safe way: if `sources` parsed to a non-null,
  // non-array JSON value, the merge is skipped entirely and `sources` is
  // left as that raw non-array value (the media entry is silently NOT
  // merged in that edge case) — see sage-headers.test.ts for the pinning
  // test.
  const skillMediaHeader = headers.get('X-Sage-Skill-Media')
  if (skillMediaHeader) {
    try {
      const m = JSON.parse(skillMediaHeader)
      const mediaEntry: Json = { ...skillMediaToSource(m) }
      if (sources !== null && !Array.isArray(sources)) {
        throw new Error('sources is a non-array JSON value — skip the media merge')
      }
      sources = [...(sources ?? []), mediaEntry]
    } catch { /* malformed header OR sources is non-array → sources stays as parsed above */ }
  }

  return {
    intentClassification,
    secondaryIntentClassification,
    sageModel,
    skillId,
    stepId,
    gatePath,
    sageNodePath,
    crisisFlags,
    sageClinicalFlags,
    emotionalIntensity,
    semanticScore,
    promptLayers,
    tokenUsage,
    turnNumber,
    crisisState,
    direction,
    sources,
  }
}
