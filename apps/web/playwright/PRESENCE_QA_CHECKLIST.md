# Presence Indicator + Typewriter Manual QA Checklist

This checklist documents manual verification steps for the presence indicator (breathing dot) and typewriter reveal animation. Execute these steps in a live browser before declaring the feature complete.

## Setup

- Start the dev server: `npm run dev` (from `apps/web` or root)
- Open browser DevTools to a position where you can observe Network tab for latency
- Test in both light and dark themes
- Prepare test messages (both short and long) for chat

---

## English Message Flow

- [ ] Send a short English message (< 200 chars) that triggers an assistant response
  - [ ] **Breathing dot phase**: Observe the dot below the user message breathing (0.6s pulse cycle) for ~1-2 seconds
  - [ ] **Held phrase phase**: The dot becomes static; a phrase appears (e.g., "I'm thinking...") styled as neutral text; held for ~1-2 seconds
  - [ ] **Typewriter phase**: The phrase animates away; the full answer appears word-by-word, revealing at 80-120ms per word
  - [ ] **Final state**: No dot visible; answer fully rendered

- [ ] Send a longer English message that takes >5 seconds to respond
  - [ ] Confirm breathing dot is visible and uniform (no jitter, no flicker)
  - [ ] Verify "still with you" phrase appears on slow responses
  - [ ] Confirm typewriter animation remains word-by-word throughout

---

## Arabic Message Flow

- [ ] Send a short Arabic message (< 200 chars)
  - [ ] **Breathing dot phase**: Dot appears and breathes as in English
  - [ ] **Held phrase phase**: Arabic phrase appears (neutral text, RTL layout)
  - [ ] **Typewriter phase**: Answer reveals word-by-word, **right-to-left without glyph jitter**
    - [ ] No character rotation or distortion
    - [ ] No horizontal glyph shift during reveal
    - [ ] Diacritics remain correctly positioned
  - [ ] **Final state**: Full Arabic answer rendered RTL without layout reflow

- [ ] Send a longer Arabic message (slow response)
  - [ ] "still with you" equivalent (or Arabic-appropriate phrase) appears and held
  - [ ] Typewriter animation continues RTL

---

## Tap-to-Skip Interaction

- [ ] While typewriter is actively revealing (mid-animation):
  - [ ] Tap/click anywhere on the message text
  - [ ] Answer should finalize immediately (all text appears, animation stops)
  - [ ] Tap-skip should work on both EN and AR messages

---

## Type-to-Skip Interaction

- [ ] Send a new message while the previous answer is still in typewriter phase:
  - [ ] Previous answer should finalize immediately
  - [ ] New user message is sent
  - [ ] New breathing dot / reveal cycle begins

---

## Screen Reader Announcement (A11y)

- [ ] Enable screen reader (NVDA on Windows / VoiceOver on macOS)
- [ ] Send an English message and listen to announcements
  - [ ] **SR announces held phrase exactly once** (e.g., "I'm thinking...")
  - [ ] **SR announces full answer exactly once** after typewriter completes (does not repeat per-word)
  - [ ] No duplicate or overlapping announcements
- [ ] Repeat with Arabic message
  - [ ] Held phrase announced once in Arabic
  - [ ] Full answer announced once (verify RTL ordering is correct in SR output)

---

## Reduced Motion (OS Setting)

- [ ] Toggle OS reduced-motion preference
  - On macOS: System Preferences > Accessibility > Display > Reduce motion
  - On Windows: Settings > Ease of Access > Display > Show animations

- [ ] With reduced-motion **enabled**:
  - [ ] **Breathing dot is static** (no pulse animation)
  - [ ] Held phrase still appears
  - [ ] **Full answer fades in or appears immediately** (no word-by-word typewriter)
  - [ ] No jank or layout shift

- [ ] With reduced-motion **disabled**:
  - [ ] Breathing dot pulses normally
  - [ ] Typewriter animation resumes
  - [ ] Breathing dot does not interfere with answer reveal

---

## Crisis Pathway (Special Case)

- [ ] Trigger a message that routes to crisis response (or mock via feature flag)
  - [ ] Verify waiting state (breathing dot and held phrase) appears normally
  - [ ] Crisis response text appears without typewriter animation
  - [ ] No difference in waiting state between crisis and non-crisis paths
  - [ ] Breathing dot and held phrase are identical in appearance and timing

---

## Cross-Browser & Mobile (Optional but Recommended)

- [ ] Desktop browsers: Chrome/Edge, Firefox, Safari
  - [ ] Breathing dot and animations render consistently
  - [ ] Arabic text layout stable across browsers
- [ ] Mobile (iOS Safari, Android Chrome)
  - [ ] Dot and phrase visible at appropriate size
  - [ ] Typewriter animation smooth
  - [ ] Tap-to-skip responsive

---

## Performance Observations

- [ ] Breathing dot does not consume excessive CPU (check DevTools Performance)
- [ ] Typewriter animation is smooth (no dropped frames on standard hardware)
- [ ] Transition between phases (dot → phrase → reveal) is snappy (no lag)
- [ ] RTL rendering does not cause layout thrashing (no reflow per word)

---

## Sign-Off

- Date tested: ______________________
- Tester: ______________________
- All checks passed: [ ] YES  [ ] NO
- Known issues / deviations:
  ```
  
  ```

