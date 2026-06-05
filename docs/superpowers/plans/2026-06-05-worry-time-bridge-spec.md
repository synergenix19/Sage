# Spec: Worry Time Bridge Amendment (Option A)

**Date:** 2026-06-05
**Status:** Awaiting implementation approval
**Type:** Amendment to existing skill (worry_time.json), not a new skill
**Approach:** Option A soft bridge -- JSON-only changes, no code changes, no new signals
**Maps to:** §9 skill schema; §4.3 (routing); no graph changes
**Preceded by:** Signal reconciliation 2026-06-05; PST spec; ACT spec (same date)

---

## What this is and is not

**Is:** A change to the `sort_and_act` step's `goal` and first two `examples` fields, plus additions to PST and ACT `target_presentations`, so that the LLM closing language after worry sorting guides the user toward the right next skill.

**Is not:** A step_policy branch. Custom signals for `actionable_worry_identified` and `hypothetical_worry_identified` are not wired at runtime (R6 documented gap). Adding them to the JSON would produce dead rules. The soft bridge achieves the same clinical routing through LLM instruction and `target_presentations` keyword matching rather than executor-level branching.

**Is not:** The SRA complementary-skill-retrieval engine (v7 Full Build item). That feature does not exist and is not being built here.

**Mechanism:**
1. `sort_and_act` step is the last step in Worry Time. When criteria are met, Worry Time completes and `active_skill_id = None`.
2. On the next user message, `skill_select` runs fresh (keyword tier first, then semantic).
3. If the `sort_and_act` closing language named the right next skill and the user responds with matching language, `target_presentations` keyword matching activates PST or ACT.
4. If the user's response does not use matching language, `skill_select` runs normally and routes to whatever best fits.

**Risk acknowledged:** The bridge is soft. If the LLM omits the handoff language, or the user ignores it, the routing falls through to normal skill_select behavior. This is graceful degradation, not a failure. The clinical downside is that the user lands in freeflow rather than the wrong skill.

---

## Changes to worry_time.json

### sort_and_act step: goal field (replace existing)

**Current:**
```
Help the user sort their worries into actionable vs. hypothetical, and respond to each type
```

**New:**
```
Help the user sort their worries into actionable vs. hypothetical. Once the worry is sorted, close with a clear direction: for actionable worries, bridge toward structured problem-solving by naming it explicitly and inviting the user to try it; for hypothetical what-if worries, bridge toward acceptance or defusion work by naming the approach and inviting the user to try it. The closing should feel like a natural handoff, not a prescription.
```

### sort_and_act step: replace first two examples

The executor injects `step.examples[:2]` into the LLM step instruction on rule-fired turns. The composer uses `_select_few_shot_examples` on normal turns — for Arabic users it selects `arabic[0] + english[0]`; for English users it uses `[:2]`. Both paths must see sort behavior, not just handoff. Each example must demonstrate the sort first, then name the appropriate next skill.

**New example 1 (Arabic — sort question + both directions):**
```
وش نوع هالقلق؟ لو كان مشكلة حقيقية تقدر تسوي فيها شي، عندنا أسلوب منظم نشتغل فيه على المشكلة خطوة خطوة — قوللي 'أبي نحل هالمشكلة' ونبدأ سوا. لو كان ماذا لو وما في حل واضح، الأسلوب مختلف: نتعلم نحمل عدم اليقين بدل ما يسيطر علينا — قوللي 'ساعدني مع الماذا لو'.
```

**New example 2 (English — sort both types + both handoffs):**
```
Let's look at what kind of worry this is before we go further. If it is a real, practical problem — something you could take action on — there is a structured problem-solving approach that works well for exactly this: say 'help me problem solve this.' If it is a what-if thought without a real solution, the approach is different: learning to carry the uncertainty so it loses its grip, say 'help me with the what-if.'
```

**Keep existing examples 3-5 in their current positions** (they handle the general sorting question and remain valid for the step; they are not injected but are accessible in the full examples list).

---

## Required target_presentations additions

These phrase additions are what make the soft bridge work. The user's response to the handoff language must trigger keyword matching.

### Additions to problem_solving_therapy.json target_presentations

(Already included in the PST spec document. Listed here for cross-reference.)

```
"help me problem solve this",
"problem solve this",
"let me try problem solving",
"work through this systematically",
"structured approach to this problem",
"I want to try problem solving",
"let's problem solve"
```

### Additions to act_psychological_flexibility.json target_presentations

(Already included in the ACT spec document. Listed here for cross-reference.)

```
"help me with the what-if",
"learn to carry the uncertainty",
"help me with acceptance",
"carry it differently",
"I want to try that acceptance technique",
"let go of the what-if",
"try acceptance",
"try defusion"
```

---

## Step_policy: no changes required

The existing five rules in `worry_time.json` step_policy remain unchanged. No new rules are added. The bridge is entirely in the `goal` and `examples` fields.

---

## Escalation matrix: no changes

The existing L1-L4 matrix is unchanged.

---

## Cultural overrides: consider adding

The existing `worry_time.json` `cultural_overrides` is noted in SKILL_AUTHORING_CONVENTIONS as having "partial or empty overrides" (tracked as pre-prod work). This amendment is an opportunity to add the missing content.

**Proposed addition:**
```json
"cultural_overrides": {
  "tawakkul_framing": "[existing content unchanged]",
  "arabic_example_language": "[existing content unchanged]",
  "practical_identity_framing": "[existing content unchanged]",
  "bridge_framing": "When bridging to problem-solving for actionable worries in Gulf context, name family consultation and seeking advice from trusted figures as valid first steps in the problem-solving process. When bridging to acceptance work for hypothetical worries, the tawakkul frame applies naturally: some things are in God's hands, and the skill is trusting that without the worry consuming the present."
}
```

Note: adding `bridge_framing` brings total cultural_overrides word count to approximately 180 words, within the 200-word runtime limit enforced by `composer.py`.

---

## Option B upgrade path (post-Gitex)

When the R6 signal infrastructure is built (executor extended, signals dict expanded, signal evaluation added), the soft bridge can be upgraded to a hard branch:

1. Add `actionable_worry_identified` and `hypothetical_worry_identified` as wired signals (computed by a keyword classifier or LLM call on the user's sort_and_act response)
2. Add `actionable_bridge` and `hypothetical_bridge` steps to `worry_time.json`
3. Add step_policy rules at `sort_and_act` routing to the appropriate bridge step based on the wired signal
4. Bridge steps complete Worry Time with handoff language, PST/ACT activate on next message

The soft bridge's `target_presentations` additions remain valid in Option B: they are required regardless of how the bridge fires.

---

## Implementation order dependency

The Worry Time bridge amendment depends on the PST and ACT specs being implemented first, because:
- The `target_presentations` additions referenced in this spec live in those skill JSON files
- If PST and ACT are not in the registry, users reach the end of Worry Time, follow the handoff language, and land in freeflow with no match

**Required order:**
1. PST JSON written and registered
2. ACT JSON written and registered
3. Worry Time sort_and_act step amended
4. Calibration run across all three new/amended files

---

## Authoring checklist

- [ ] PST and ACT skills confirmed registered before this amendment is merged
- [ ] Verify `worry_time` `sort_and_act` examples[:2] are exactly the two handoff examples above (executor injects only the first two)
- [ ] Confirm `goal` field update does not exceed any length limit in schema (field is `str`, no cap in schema)
- [ ] Verify cultural_overrides total word count for worry_time stays under 200 words if bridge_framing is added
- [ ] Manual QA: run a simulated Worry Time session, identify an actionable worry, confirm the LLM response includes the PST handoff language, confirm next message routes to PST
- [ ] Manual QA: run same session with hypothetical worry, confirm ACT handoff language, confirm next message routes to ACT
- [ ] Run full test suite: expect >= 718 passing
