# RT-4 evidence: the general_chat gate is an accidental matcher shield

**Date:** 2026-06-25
**Status:** WORK-SESSION FINDING / EVIDENCE RECORD. No code change. No routing change. No clinical-content change. Captures live matcher scores before they drift, and pins a trip-wire test for a future decision.
**Author:** engineering (work session)
**Origin:** Abby-vs-Sage comparison of a real production turn ("I just feel lonely i dont know what to do or how to cope", session `5f64e4e2`, prod 2026-06-25). The reply was a generic coping tip ("reach out to a friend"). Investigation traced root cause from "freeflow content quality" to "routing/matching", per RT-4.

---

## 0. Priority preamble (read first)

Nothing in this entry is the top priority. The pilot blocker is **crisis recall**:
CRADLE 37.1%, self-harm 18%, against a fail-closed KPI floor of recall >= 95%. That is a
patient-safety number. The loneliness/matcher work below is **secondary** and must not
consume engineering cycles ahead of crisis recall remediation (S2/MARBERT, CRADLE/Arabic
benches). This doc is cheap because it is documentation, not code.

---

## 1. The canonical RT-4 instance (live scores, verbatim)

RT-4 (`Docs/SageAI_Intelligence_Evaluation.md:351`) asserts rule-based matching is "too
brittle for real users." This is the reproducible instance behind that prose. Scores from
the **current working tree** matcher (`src/sage_poc/nodes/skill_select.py`), message =
`"I just feel lonely i dont know what to do or how to cope"`:

```
TIER-1 keyword hit:  problem_solving_therapy   (via keyword "dont know what to do")
TIER-2 semantic top: worry_time            0.4609   (SEMANTIC_THRESHOLD = 0.4593; clears by 0.0016)
                     grief_loss            0.4532
                     grounding_5_4_3_2_1   0.4507
                     self_compassion_break 0.4386
   behavioral_activation                   0.3654   (6th; the clinically-correct skill, far below threshold)
```

**If this turn reached skill_select, it would select `problem_solving_therapy`** (Tier-1
wins over Tier-2). PST is a structured problem-solving protocol. Offering it in response to
"I feel lonely" is the fix-it trap, i.e. the exact failure this investigation began by
criticizing. If Tier-1 had not fired, Tier-2 would select `worry_time` (rumination tool) at
a noise-level 0.0016 margin. Neither is correct for relational loneliness. The correct skill,
`behavioral_activation`, is not selectable here at any tier.

Deploy-state note: the 2026-06-16 BA anhedonia keyword expansion is **present on master**
(confirmed 2026-06-26: `behavioral_activation.json` carries "no hobbies" etc.), but still has
no "lonely"/"loneliness" keyword. So the expansion is live and the misroute persists anyway.
The conclusion "BA does not win" holds with or without that expansion.

---

## 2. The real finding: the gate is a shield by accident, not by design

In production this turn never reaches skill_select. `intent_route` labels it `general_chat`,
and `_route_after_intent` (`src/sage_poc/graph.py:208`) only admits `general_chat` to
skill_select when `emotional_intensity >= ACUTE_INTENSITY_FLOOR` (8). At intensity 6 it
falls through to freeflow. (That general_chat turns never reach skill_select is **already
documented** as flag #4 of the 2026-06-16 BA-anhedonia doc. It is not a new discovery.)

What **is** new: §1 shows that opening that gate today would not help. The matcher would
convert a generic-but-on-topic empathy reply into a confidently-wrong protocol misroute
(PST or worry_time). So:

> **`general_chat -> freeflow` is currently shielding users from a brittle misroute, not
> merely withholding good content.**

This must be recorded as a **fragile equilibrium, not a designed safeguard.** The gate is
load-bearing *by accident*: it happens to mask a matcher that would misroute this class. A
future engineer who fixes the matcher must not read "do not open general_chat to
skill_select" as settled architecture and leave it closed forever. The gate's correctness is
**conditional on matcher untrustworthiness.**

---

## 3. The three matcher defects (discrete, individually fixable)

Each is a separate work item. None is authorized here; this entry only records them with
evidence.

**(a) `behavioral_activation` cannot catch the affective word "lonely."**
The 2026-06-16 expansion added 12 *activity-deficit / anhedonia* keywords ("no hobbies",
"nothing i enjoy", etc.) but **no "lonely"/"loneliness"** keyword (verified:
`"lonely" in target_presentations == False` in the working tree). BA's Tier-2 signal is its
`semantic_description`, which is technique-identity ("graded activity scheduling protocol")
with `semantic_anchors: None`, so it scores 0.3654 on affective loneliness phrasing. Adding
lived-experience phrasings to Tier 2 is explicitly gated behind **TIER2-DUALIDX**
(`SageAI_architecture_current.md:1481`): a separate `target_presentations` embedding index
with its own threshold and Rule-1 approval. So the cheap fix (a Tier-1 "lonely" keyword,
with a false-positive guard) and the real fix (dual-index) are both known and both gated.

**(b) `problem_solving_therapy` keyword collision on "dont know what to do."**
PST owns both apostrophe variants `"dont know what to do"` / `"don't know what to do"`. This
is a generic helplessness phrase that co-occurs with almost any emotional disclosure, so it
hijacks emotional/relational content into a problem-solving protocol via longest-match
Tier-1. Same class as the pre-existing collisions tracked off the BA-anhedonia doc
(`setting limits in`, `thought records aren't helping`).

**(c) The 0.4593 threshold is near-inert at these margins.**
`worry_time` clears by 0.0016 on a loneliness message. At that margin, Tier-2 selection is a
coin-flip dominated by embedding noise, not clinical signal. Threshold calibration (or the
dual-index of defect a) should treat sub-0.005 margins as abstain, not match.

---

## 4. The gate's conditional status + pinned trip-wire test

**Decision recorded (not a code change):** the `general_chat` intensity gate **stays** as a
temporary shield, **conditional on matcher untrustworthiness.** Revisit the v7 "affective
disclosure should attempt skill matching" premise **only when RT-4 closes**, i.e. when the
matcher correctly handles this class.

**Trip-wire test (pin now; the signal that the gate is safe to revisit):**

```
message = "I just feel lonely, I don't know what to do or how to cope"
# Asserted at the skill_select layer (force the message through skill_select_node),
# NOT end-to-end: end-to-end the gate sends it to freeflow, which would mask the matcher.
assert selected_skill in {"behavioral_activation", "self_compassion_break"}
assert selected_skill not in {"problem_solving_therapy", "worry_time"}
```

**ARMED 2026-06-25** as
`tests/test_skill_select.py::test_loneliness_routes_to_connection_skill_not_problem_solving`,
marked `@pytest.mark.xfail(strict=True, ...)`. Verified status today: `XFAIL` (the message
routes to `problem_solving_therapy` via `keyword_offer`, confirmed at the `skill_select_node`
layer). It is green-by-design now. When the matcher is fixed (defects a/b/c), it XPASSes, and
`strict=True` converts that XPASS into a **hard test failure** -- the loud, non-silent signal
that the gate is now a redundant shield and is safe to revisit. Do not relax to
`strict=False`: a silent XPASS is exactly the missed signal this trip-wire exists to prevent.

---

## 5. Sequencing (blunt order)

1. **Crisis recall remediation -> pilot gate.** Everything below is secondary.
2. **This evidence entry** (done). Cheap, documentation not code, captures live scores.
3. **RT-4 matcher fixes** when they reach the queue: defect (a) BA "lonely" coverage +
   TIER2-DUALIDX, defect (b) PST "dont know what to do" collision, defect (c) threshold
   calibration. Each clinical-content or threshold change carries its own sign-off gate.
4. **Revisit general_chat intake** (the v7 premise). Gated on (3) and on the trip-wire test
   flipping to pass.

---

## 6. What is already known vs new (so this is not rediscovered)

- **Known:** general_chat never reaches skill_select (BA-anhedonia doc flag #4); BA missing
  colloquial coverage with a real prior loneliness session `40a8ba18` (2026-06-07);
  Tier-2 embeds technique identity only and novel symptom phrasings fall through both tiers
  (TIER2-DUALIDX, `SageAI_architecture_current.md:1481`, §4.3 field note line 327); RT-4 as
  the priority routing issue (`SageAI_Intelligence_Evaluation.md:351`).
- **New here:** the empirical demonstration that opening the gate *today* misroutes this
  phrasing to PST/worry_time (not BA); the "gate as accidental shield" inversion and its
  conditional status; the PST "dont know what to do" collision for affective disclosures;
  the pinned trip-wire test.

---

## 7. Cross-links (bidirectional, by design)

The failure mode this doc guards against is the gate decision and the matcher-quality work
living in separate docs that never reference each other. Both sides link here:

**Matcher / keyword workstream (defect side):**
- `docs/superpowers/governance/2026-06-16-ba-anhedonia-keyword-expansion.md` (defect a partial fix; flag #4 = the gate residual)
- `docs/SageAI_architecture_current.md:327` (§4.3 Tier-2 embedding field note) and `:1481` (TIER2-DUALIDX backlog)
- `docs/superpowers/plans/2026-06-09-semantic-routing-production-architecture.md` (matcher re-architecture / retrieval-core)
- `Docs/SageAI_Intelligence_Evaluation.md:351` (RT-4 source)

**Routing / gate decision side:**
- `src/sage_poc/graph.py:27` (`ACUTE_INTENSITY_FLOOR`) and `:208` (the gate)
- `docs/superpowers/governance/2026-06-13-overwhelm-routing-c1-conflict.md` (the C1 routing decision record)

Backlinks to this entry have been added at the head of the two governance docs above.
