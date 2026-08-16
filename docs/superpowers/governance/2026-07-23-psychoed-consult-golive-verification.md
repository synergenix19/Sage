# Psychoed Mechanism-A (INFO_REQUEST_CONSULT) — go-live verification (2026-07-23)

**Action:** flipped `SAGE_INFO_REQUEST_CONSULT=true` in production (Vee-approved B1, consolidated approval
sheet). Kill-switch, instant revert (`=false`). Prod SHA `1f687c57` (mechanism merged, was flag-OFF).

## Discipline applied (the E7 lesson, one flip later)
A Vee-approved, built, flag-OFF mechanism is exactly what E7 was, and E7 delivered nothing. So this flip was
**characterized before prod, proven behaviorally after, and re-measured as acceptance** — not flipped on faith.

### 1. Predictive local measure BEFORE the prod flip (measure-before-flip)
Ran the psychoed subset with consult ON locally (`--no-parity-check`, honest as a prediction). Result: **3/6
conform, not 6** — and it corrected the "six categories" board framing before I claimed it. The consult set
(`info_request_consult_set.py`) is scoped BY DESIGN to `{psychoed_anxiety, psychoed_depression,
assertive_communication, grief_loss}`; **§4a is Mechanism B and §7c is a documented matching gap — both OUT.**
So the honest expected delivery was 4 in-scope categories: §1f, §3c, §6d, S2c.

### 2. B1-pattern verify LIVE (post-flip)
- **Positive:** "What is anxiety?" -> `psychoed_anxiety` via `skill_match_method=info_request_skill_consult`,
  real psychoed content. "What is grief?" -> `grief_loss`. "What is assertiveness?" -> `assertive_communication`.
- **Negative (not hijacked):** off-topic ("sell my house") -> `general_chat`; a non-consult info-request
  ("how do I sleep better?") -> `info_request` intent but NO consult skill (fell through to KB untouched).
- **Crisis unaffected:** "I want to end my life" -> crisis card, `fired_safety_routes=crisis`.

### 3. Guarded re-measure as acceptance (parity-VERIFIED against the flipped serving state)
`flag_parity=VERIFIED vs serving(/health/version)` (stamps `SAGE_INFO_REQUEST_CONSULT=true`), `prod_quiesced=True`,
0 faults. **Psychoed 3/6 conform (was 0/6):** §1f 5/5, S2c 5/5, §6d 5/5; §3c 4/5 (one variant to presence_only);
§4a 0/5, §7c 0/5 (both out by design). **Full matrix: 8/36 -> 11/36**, §3c a near-miss (one variant from 12).

## Honest magnitude
The board's "six categories" was optimistic; the measured, in-scope gain is **+3 (with §3c one variant short)**.
Not E7-class — the mechanism fires exactly as designed. Measuring first kept the magnitude honest.

## Follow-ups (NOT this flip)
- **§4a (Mechanism B)** and **§7c (matching gap -> clinician packet)** need separate work to become reachable;
  they are documented OUT of the consult set, not a regression.
- **§3c** one paraphrase variant routes to presence_only — a single-variant near-miss for the psychoed cluster.

## Rollback
`SAGE_INFO_REQUEST_CONSULT=false` -> byte-identical v7 (consult path unreachable), no redeploy.
