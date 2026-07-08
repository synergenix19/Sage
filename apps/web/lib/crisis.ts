import { CRISIS_SIGNAL } from './constants'

// Single source of truth for the in-band crisis sentinel handling, used on BOTH sides of the
// boundary: the persist path (route.ts — sentinel must never reach storage) and the render path
// (chat-interface.tsx — sentinel must never render as plain text). Centralizing the strip is a
// step away from the "every path must independently remember to strip" root cause of #191; the
// class-level fix is Phase 0b out-of-band signaling.

/** True if content still carries the in-band `[[CRISIS_DETECTED]]` prefix. */
export function hasCrisisSignal(content: string): boolean {
  return content.startsWith(CRISIS_SIGNAL)
}

/** Remove the in-band crisis sentinel prefix (and its leading whitespace); idempotent. */
export function stripCrisisSignal(content: string): string {
  return content.startsWith(CRISIS_SIGNAL)
    ? content.slice(CRISIS_SIGNAL.length).trimStart()
    : content
}
