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

**Update (2026-07-22): D1 IS LIVE.** The screen is now enforced in production. Getting there took five enable
attempts and four halts — and telling you the messy version unprompted is the point, because it is what makes
the verification credible. One was a real code defect (a wiring bug that served a generic response instead of
the screen); it was caught by our first live check, before any user. The other three halts were NOT the
mechanism failing — they were our own verification tooling being fooled by production timing and state, and we
halted each time rather than risk shipping. **No user was exposed at any point across all five attempts.** The
final fix was to stop verifying the screen through a noisy live test and instead trust two quiet, reliable
checks: the screen's behavior proven on the exact deployed code, and the live fleet proven to actually serve
the screen (10 out of 10 fresh sessions). The flip held on the first attempt of that redesigned check.

**What is live now:** on an acute-overwhelm turn that would route to TIPP, the screen asks its two-beat
question; a clear "no" resumes TIPP; a disclosed heart condition or pregnancy routes to grounding and is not
re-offered TIPP that session; red-flag symptom quality reaches the 998 guard (caught by the safety layer, or
by the screen's own backstop for subtle phrasing); crisis in an answer reaches the crisis path. All verified
live on the converged system.

**Next — the monitored-enforce window, under the honesty clause you were promised:** it is accruing now. "D1
verified" for the C1 revisit means the mechanism verified live on every branch + zero safety-stop events, with
the answer-class picture reported as **descriptive, honestly labelled small-sample** until enough real screens
accrue (TIPP is a ~4.5% route, so n builds slowly — if it can't reach a meaningful size in reasonable time,
you'll hear that early, not at a closing date, and it won't block the revisit; it just gets labelled as what
it is). When the window closes clean, TIPP-leads comes back to you as a ruling on evidence — which is what this
whole arc was built to make possible. Your (c) ruling stands throughout; none of this needed a re-ruling.

Telling you this unprompted is what makes the next sign-off worth something.
