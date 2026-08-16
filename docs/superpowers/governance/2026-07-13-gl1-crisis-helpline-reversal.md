# Decision Record — GL-1 Crisis-Helpline Reversal (2026-07-13)

**Decision (PO, this session):** GL-1 is **REVERSED**. The UAE crisis helpline adopts the BOT BEHAVIOUR doc's verified 6-entry directory, replacing the prior `800 46342 / 24-7` single number with the National Mental Support Line `800-HOPE (800-4673)` (8am–8pm) leading a full multi-resource, hours-aware list.

**This document is the primary record.** It exists because the coordinated deploy agent correctly HALTED (Primary-Record-Over-Inference): the reversal existed only in-conversation + in the flip PRs' own bodies, while `config.py`, `crisis-config.ts`, the 2026-07-08 plan, the SDD ledger, and MEMORY all still said "46342 verified final / do not ship 4673." That stop was right; this record closes the gap.

**Supersedes (explicitly):**
- The 2026-07-08 PO verification *"800 46342 VERIFIED FINAL; 46342-vs-4673 RESOLVED to 46342"* (`config.py` comment; `docs/superpowers/plans/2026-07-08-crisis-helpline-centralisation.md`).
- The 2026-07-03 signed clinician packet's "4673 flip + dial-test parked until external milestone" (G8).
- The 2026-07-09 MEMORY note *"commit-2 (→4673) must NOT ship."*

**Gates cleared (PO-attested this session, 2026-07-13):**
- **Dial-test** — all 5 doc numbers confirmed current/dialable; a NEW dial-test resolved the National line to `800-HOPE / 800-4673`, superseding the 07-08 resolution.
- **GL-1 reversal** — confirmed intentional by the PO ("(A) is correct").
- **Clinical sign-off** — Vee approved the 5-entry composition.
- **Crisis-freeze** — lifted.

**Adopted composition (doc-verified):** National Mental Support Line `800-HOPE (800-4673)` 8am–8pm · Emergency `999` 24/7 · Abu Dhabi `800-SAKINA (800-725462)` 24/7 · DHA `800 111` 24/7 · Sharjah `800 51115` 9–5 Mon–Fri · Nearest ER. `CRISIS_RESOURCES` is the single source; `CRISIS_CONFIG` derives from it.

**Deploy discipline:** coordinated, frontend-first → value flip; cross-stack entry-for-entry parity (manual — the CI gate skips single-repo, two-repo wiring is a fast-follow); the 24-hour always-24/7 property test ("no stranded 02:00 user"); Ring-1 + 2.2; driven EN+AR; **live browser verification on prod**; the 46342 exposure closed only once the corrected card is confirmed rendered live.

**Ripple / fast-follows:** the value change made 5 files claim a false "24/7" next to the 8am–8pm National number — fixed (labels → `{{crisis_label}}`, `psychotic_referral`/`post_crisis_check_in` → true hours + 999-led per PO ruling; availability-consistency guard test added). Pending clinician **tone-confirm** (not a blocker): the `psychotic_referral`/`post_crisis_check_in` rewrites; the AR service-name drafts; the AR "8am–8pm daily" i18n string.

**Authority:** Product Owner, 2026-07-13. Recorded by the command session.
