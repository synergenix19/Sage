// Presence Indicator + Typewriter Reveal tunables (spec §6).
// Calibrated to the real prod latency distribution measured 2026-07-07
// (spec §1.1): PRESENCE_SLOW ≈ mid-wait of ~15s total p50; PRESENCE_DEGRADED
// ≈ total p99 (~23s) + margin, so only the ~1% tail sees the honesty phrase.
// Re-tune by editing here if the distribution shifts — no code change needed.
export const PRESENCE_PHRASE_MS = 600      // first phrase fades in and is held
export const PRESENCE_SLOW_MS = 9_000      // cross-fade to the steadier "still with you"
export const PRESENCE_DEGRADED_MS = 25_000 // honesty phrase — or on actual failure, whichever first
export const TYPEWRITER_WPS = 30           // reveal speed (25–35 range), eases faster over time
export const TYPEWRITER_MAX_MS = 2_500     // hard cap; long responses accelerate rather than wait
