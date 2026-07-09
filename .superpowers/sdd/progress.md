# §3a Low-Mood — SDD progress ledger
Branch: feat/low-mood-3a-impl (off origin/master 140ff2d)
venv: .venv/bin/python -m pytest
Baseline: 3 pre-existing test_nodes.py Arabic-translation-mock failures on clean master (not ours).

Task 1: complete (commit ee6f4ca, flag + cross-turn state fields, inline, tests green)
Task 2: in_progress (skill_select §3a interception, EN-gated, + precision set) — subagent-driven

Task 2 review (base ee6f4ca..62ad9b5): SPEC ✅ / CODE QUALITY changes-requested.
  Findings:
  - [Important #1] is_low_mood_disclosure matches ~only its own test strings; real §3a
    paraphrases false-negative -> unscreened BA offer. Confirmed by probe (BA offerable but
    detect=False for "I have no motivation for anything anymore"). Detector also does real
    precision work ("tired after a long week": BA offerable, correctly excluded). Root cause:
    brief gave 10 e.g. phrases as if a complete set. Trigger set is CLINICIAN-OWNED ->
    ESCALATED as a decision (needs signed §3a trigger set + robust matching + data-file).
  - [Important #2] AC2 rewrite authorization recorded only in report -> closing via durable
    record (this ledger + controller verified the arabic_offer_excluded repro independently).
  - [Minor #3] stale prod comment skill_select.py:560 "today's offer path" (AR is direct-entry).
  - [Minor #4] dead `offerable` kwarg in tests (inert; tests pass via real Tier-1 keyword match).
  - [Minor #5] trigger list inline vs ocd_compulsion's CMS-JSON single-source -> fold into #1.
  STATUS: Task 2 structurally correct; NOT complete — #1 open, human decision required before Task 3.

Task 2 hardening (30de34c) REVIEW: SPEC ❌ / CODE QUALITY changes-requested — REJECTED.
  Adversarial novel-input review (verified independently by controller):
  - Novel §3a recall = 2/15 (13.3%) — same overfitting as v1; regexes fit the 10 seed paraphrases, not the family/scope discriminator. "nothing excites me anymore", "I feel hollow", "zero drive" all MISS.
  - Novel look-alike FP = 3/15 (20%) — NEW safety negative. "I feel stuck in traffic", "no energy left to clean the kitchen tonight", "nothing fun at this party" all FIRE -> SI question -> broken GL-1 card.
  - NOT single-sourced: matching runs on a hand-typed _LITERAL_PHRASES tuple + regexes, JSON only feeds tests -> clinician edits won't change behavior (the drift risk we set out to close).
  DECISION: two deterministic attempts have now failed to generalize. §3a detection is a SEMANTIC problem, not keyword/regex. Escalated to user: revisit the "deterministic only" constraint; recall likely belongs to the existing semantic BA-offerable signal, precision to a semantic filter or BA's own target_presentations. Do NOT dispatch a third regex fix. Hardening 30de34c to be reverted or redesigned per user's approach decision. Flag stays OFF regardless.
