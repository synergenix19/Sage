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

**Update (2026-07-21):** a second flip attempt was made and halted immediately on the live probe. This one was
**not a mechanism defect at all** — a probe-expectation error plus a test/prod configuration-parity gap, both
now fixed. What the probe flagged: a red-flag answer ("crushing pain spreading to my arm") was delivered to
the 998 medical guard by the *safety layer* one step above the screen — the correct, stronger outcome — while
our probe was looking for it on the screen's own branch. Mechanism sound; no new ruling needed. We added a
clinically meaningful case in the process: a **subtle** red-flag answer ("it feels really sharp, not like my
usual anxiety") that slips past the keyword safety layer but the **screen itself catches** and routes to 998.
That case — where the *screen*, not the keyword guard, is the safety net catching an emergency — is now driven
on every run, and its correct behavior (→998) is part of what your (c) "mechanism verified on every branch"
actually certifies.

**Next:** we re-run the full-branch probe at prod flag-parity (question served, each answer branch incl. both
the explicit and subtle red-flag, crisis-in-answer, Arabic grounding-only) before any re-flip. You'll hear the
result. "Verified" means driven on the real system — the exact word that failed, now with a mechanism behind
it.

Telling you this unprompted is what makes the next sign-off worth something.
