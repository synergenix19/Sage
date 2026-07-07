import type { Source } from '@cdai/types'

// Lane 2 Item 1.5 (c): malformed-data safety guard. Renders through the same
// source-card / video-embed as the live turn, with the same invariant: stored
// jsonb of an unexpected shape (older schema version pre-migration-016 where the
// column is NULL, a hand-edited row, or a stray non-array value) must degrade to
// no card, never a crashed bubble. Only a non-empty array is passed through.
export function hydrateSources(raw: unknown): Source[] | undefined {
  return Array.isArray(raw) && raw.length > 0 ? (raw as Source[]) : undefined
}
