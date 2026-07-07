/**
 * Task 9 — Crisis-vs-normal waiting-state indistinguishability (spec §2.4/§7).
 *
 * WHAT THIS REALLY GUARDS: pre-first-byte, the CLIENT cannot know the turn's path — crisis
 * detection is entirely server-side (safety_check / CRISIS_SIGNAL) and no response bytes have
 * arrived yet. So today this byte-diff is "trivially" equal: there is no code path by which a
 * crisis-bound utterance could render differently from a normal one before the stream starts.
 * Its value is as a REGRESSION GUARD: if anyone later introduces client-side, path-dependent
 * waiting behavior — e.g. sniffing the typed text for crisis keywords to pre-warn the user, or
 * varying the presence phrase/animation based on the outgoing message content — this test
 * fails immediately. Do NOT delete this test as trivially-true; its entire purpose is to keep
 * being trivially true (spec §2.4).
 *
 * Flake control:
 *   (a) `emulateMedia({ reducedMotion: 'reduce' })` — the breathing dot is otherwise a 4s CSS
 *       keyframe animation (see presence-indicator.tsx); freezing it makes the captured frame
 *       byte-stable regardless of exactly when within the animation loop the screenshot lands.
 *   (b) NEXT_PUBLIC_E2E deterministic phrase seed (chat-interface.tsx, Task 9 wiring) — both
 *       captures re-seed the module-singleton phrase bag with the same LCG(1) on `page.goto`
 *       (a fresh module instance per navigation), so both turns draw the SAME first phrase.
 *       This lets the diff cover the FULL frame including the phrase region, rather than
 *       masking it out (spec §7 chose deterministic-seed over region-masking).
 *   (c) Wait for the presence indicator to contain visible text (i.e. past the 600ms
 *       PRESENCE_PHRASE_MS boundary — see lib/presence-constants.ts) before EITHER capture, so
 *       neither screenshot races the dot-only -> dot+phrase transition.
 *
 * Requires NEXT_PUBLIC_E2E=true on the dev server this test runs against (wires the
 * deterministic seed — see chat-interface.tsx's mount effect). Without it, both turns still
 * draw from the same live-random module singleton in most runs (no-repeat shuffle bag), but
 * the phrase itself would differ between captures, and the assertion would need to fall back
 * to the pixelmatch/region-mask path described below.
 *
 * QA note (spec §5, eval-scenario checklist item): "waiting-state screenshot review after a
 * crisis-path turn — must equal a normal turn." This automated test is the regression-guard
 * form of that manual QA checklist item.
 *
 * Run (from apps/web), against a dev server started with NEXT_PUBLIC_E2E=true:
 *   NEXT_PUBLIC_E2E=true npx playwright test playwright/waiting-state-indistinguishability.spec.ts
 */
import { test, expect } from '@playwright/test'

test('waiting state is identical for a normal vs a crisis-bound turn', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' }) // (a) static dot — byte-stable

  // Never fulfill /api/chat — both turns stay parked in the waiting state indefinitely,
  // so the capture below is guaranteed to observe the presence indicator, not a response.
  await page.route('**/api/chat', () => {
    /* intentionally never fulfilled/continued */
  })

  const capture = async (utterance: string) => {
    // Full navigation reloads the JS module graph, so presence-phrases.ts's module-singleton
    // shuffle bag is fresh each time — the NEXT_PUBLIC_E2E mount effect in chat-interface.tsx
    // re-seeds it deterministically on this load (chat-interface.tsx: seedPresenceBag(makeLcg(1))).
    await page.goto('/chat')
    await page.getByRole('textbox').fill(utterance)
    await page.getByRole('button', { name: /send/i }).click()

    // (c) Wait deterministically for the phrase to appear (past the 600ms PRESENCE_PHRASE_MS
    // boundary) before capturing — otherwise a fast capture could land while both turns are
    // still dot-only, which would pass trivially without exercising the phrase region at all.
    const indicator = page.getByTestId('presence-indicator')
    await expect(indicator).toContainText(/\S/, { timeout: 5_000 })
    return indicator.screenshot()
  }

  const normal = await capture('I feel a bit low today')
  const crisis = await capture('I want to end my life') // crisis-BOUND; path is unknown client-side pre-byte

  // Fallback if anti-aliasing noise ever appears (e.g. a font-rendering change across runs):
  // replace the exact byte-compare below with
  //   const { default: pixelmatch } = await import('pixelmatch')
  //   expect(pixelmatch(normal, crisis, null, width, height, { threshold: 0.1 })).toBe(0)
  // decoding both PNGs to raw RGBA buffers of the same width/height first. Byte-compare is
  // preferred while it holds — it has zero tolerance for any divergence, which is exactly
  // what this regression guard is for.
  expect(Buffer.compare(normal, crisis)).toBe(0)
})
