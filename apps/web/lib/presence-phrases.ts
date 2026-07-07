// PROPOSED copy — pending clinician + native-Khaleeji sign-off (spec §5).
// Register: therapist-present, not machinery. Banned: process/promise/whimsy words.
// Arabic is self-reference-neutral; the gendered "موجود/موجودة" pair is held out
// until the persona-gender review resolves (spec §2.2). Pool should reach ~8–12
// items after sign-off. Every phrase must read right after a crisis disclosure,
// a casual greeting, AND a long trauma story.
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

// Phase 3 (degraded / honesty valve) — acknowledge the wait once, warmly.
export const PRESENCE_DEGRADED: { en: string; ar: string } = {
  en: 'This is taking longer than it should. Give me one more moment, or try sending again.',
  ar: 'هذا ياخذ وقت أطول من المتوقع. لحظة وحدة بعد، أو جرّب ترسل مرة ثانية.',
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
