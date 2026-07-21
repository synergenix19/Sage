# Short note to Vee — D1 flip attempted, defect caught, rolled back (no ruling needed)

**Telling you before you ask. No action required from you.**

We attempted the D1 enforce flip under your (c) ruling today. On the very first live probe, a **mechanism
defect** surfaced: the screen decided correctly but a graph wiring gap meant the question wasn't actually
served — an acute-overwhelm turn got a generic response instead of the screen. **Rollback was immediate**
(the pre-authorized flag), and prod is back on the shadow state (TIPP with its existing delivery-side
caveat — status quo ante).

**No user was affected** — the ~15-minute window caught only our synthetic test turns (zero real users hit
it, consistent with TIPP's low base rate), and the defect failed *toward not serving TIPP*, so there was no
contraindicated exposure at any point.

**Your ruling still stands and needs no revisiting.** (c) was correct; what it required — the mechanism
proven live end-to-end — simply hadn't actually been established, and we mistakenly believed it had. The gap
was in our verification, not in your decision. The fix is defined and landed (the wiring gap closed, plus a
new automated test that drives the full screen flow on the real graph — the test whose absence let this
through, so it can't recur silently).

**Next:** we re-run the same full-branch probe (question served, each answer branch, crisis-in-answer, Arabic
grounding-only) before any re-flip. You'll hear the result. When the flip does go live, "verified" will mean
driven on the real system, because that's the exact word that failed this time.

Telling you this unprompted is what makes the next sign-off worth something.
