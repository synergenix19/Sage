// PROPOSED copy — pending clinician + native-Khaleeji sign-off (spec §5).
// Register: therapist-present, not machinery. Banned: process/promise/whimsy words.
// Arabic self-reference is ALWAYS gender-neutral (standing rule 2026-07-08): the gendered
// "موجود/موجودة" phrasing is never used. Pool is 6 DISTINCT phrases — a smaller pool of
// distinct phrases beats a larger one with near-collisions (the ~8–12 target is a post-
// sign-off aspiration). "Here with you / هنا معك" was cut because it read one filler word
// off "معك" (#2), which on consecutive turns looks like a glitchy template, not presence.
// Every phrase must read right after a crisis disclosure, a casual greeting, AND a long
// trauma story.
export const PRESENCE_POOL: { en: string[]; ar: string[] } = {
  en: [
    'Listening…',
    "I'm with you…",
    'Taking that in…',
    'One moment…',
    'Thinking about what you said…',
    'Giving this a moment…',
  ],
  ar: [
    'أسمعك…',
    'معك…',
    'أستوعب كلامك…',
    'لحظة…',
    'أفكر في اللي قلته…',
    'أعطي هذا وقته…',
  ],
}

// Phase 2 (slow) — one steadier phrase, held.
export const PRESENCE_SLOW: { en: string; ar: string } = {
  en: 'Still with you — taking a little longer…',
  ar: 'معك، بس أحتاج شوي وقت…',
}

// Phase 3 (degraded / honesty valve, ~25s p99 tail) — acknowledge the wait once, warmly.
// FIRST-PERSON COMMITMENT ONLY (2026-07-08): Sage carries the wait; NO user-directed
// imperative ("be patient / bear with me / اصبر"), which would place the burden on an
// already-anxious user at the exact moment the SYSTEM is underperforming. Also drops the
// earlier "try sending again" (input is disabled until the 58s ceiling). Honest about the
// delay without over-promising imminence.
export const PRESENCE_DEGRADED: { en: string; ar: string } = {
  en: 'Still here — this is taking me a little longer than usual…',
  ar: 'بعدني هنا — الرد ياخذ وقت أطول من المعتاد…',
}

// Random-without-repeat index generator (a "shuffle bag" degenerate to no-immediate-repeat).
// rng is injectable so tests (and the indistinguishability screenshot) are deterministic.
export function createShuffleBag(size: number, rng: () => number = Math.random): { next: () => number } {
  let prev = -1
  return {
    next() {
      if (size <= 1) return 0
      let idx = Math.floor(rng() * size)
      if (idx >= size) idx = size - 1 // guard rng() === 1
      if (idx === prev) idx = (idx + 1) % size // skip an immediate repeat deterministically
      prev = idx
      return idx
    },
  }
}

// Module-level singleton — its `prev` persists across component unmount/remount, so the
// no-repeat property holds ACROSS TURNS, not just within one mount (spec §2.2). This is what
// PresenceIndicator draws from. Do NOT create a per-mount bag in the component.
let _phraseBag = createShuffleBag(PRESENCE_POOL.en.length)
export function nextPresencePhraseIndex(): number {
  return _phraseBag.next()
}
// Test/e2e only: reseed the singleton with a deterministic rng (resets no-repeat memory).
export function seedPresenceBag(rng: () => number): void {
  _phraseBag = createShuffleBag(PRESENCE_POOL.en.length, rng)
}
