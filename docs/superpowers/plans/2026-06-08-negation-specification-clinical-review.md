# Negation Check — Clinical Specification Package
**Date:** 2026-06-08
**Author:** Engineering
**Requires sign-off:** Clinical lead
**Status:** DRAFT — not in production

---

## Background

The S1 rules engine uses a `negation_check` modifier on several SI rules (SK-EN-001, SK-EN-002, SK-AZ-002). When active, it looks backward 6 tokens from the matched pattern and suppresses the match if any negation word appears in that window.

This mechanism correctly suppresses denial statements ("I don't want to die, I love my life") and idioms ("I could kill for a coffee"). However, it creates **false negatives in two specific disclosure patterns** where the negation refers to the user's own internal attempt to suppress the thought, not a denial of the disclosure.

Current recall impact: 2 of the 12 documented FNs (negation_check_fn). These 2 cases are not enough alone to close the 95% KPI gap, but the negation gap is the highest-risk FN class because:
- The user has already disclosed the thought (it is present in the message)
- The system is actively suppressing a correct detection
- The failure is deterministic (not a vocabulary miss)

---

## The Two Cases

### NC-01

**Test case:** `tp_passive_si|en` — fixture line 200

**Full phrase:**
> "I don't want to hurt myself, I just keep having these thoughts constantly"

**What fires:** SK-EN-001 matches "hurt myself" (pattern: `hurt myself`).

**Why it's suppressed:** The 6 tokens immediately preceding "hurt myself" are: `["i", "don't", "want", "to"]`. The token "don't" is in `_NEGATION_WORDS`. The engine suppresses the match.

**Why the suppression is wrong:** The user is not denying having SI. They are expressing that they do not *want* to act on it while simultaneously disclosing that the thoughts are present and persistent. "I don't want to hurt myself" + "I just keep having these thoughts" = minimized disclosure, not denial.

**Clinical framing:** This is a recognizable presentation pattern — a user who has ideation but is trying to reassure both themselves and the listener that they won't act on it. Suppressing the detection removes the user from crisis protocol when they are explicitly describing ongoing SI.

---

### NC-02

**Test case:** `tp_passive_si|en` — fixture line 207

**Full phrase:**
> "I keep telling myself not to think about ending it but the thoughts won't stop"

**What fires:** SK-EN-001 matches "ending it" (pattern: `ending it`).

**Why it's suppressed:** The 6 tokens immediately preceding "ending it" include "not". The token "not" is in `_NEGATION_WORDS`. The engine suppresses the match.

**Why the suppression is wrong:** "Not" here is part of "not to think about ending it" — a self-instruction. The user is explicitly stating that they are *trying* to suppress thoughts about "ending it." The "not" is not a denial of the thought; it presupposes the thought exists and is recurring. "The thoughts won't stop" makes this explicit.

**Clinical framing:** "I keep telling myself not to [SI content]" is a minimization pattern that engineers often encode as denial. Clinically, it is a disclosure: the SI thought is active and the user is fighting it. Suppressing detection here means the user receives no crisis intervention despite an explicit ongoing SI statement.

---

## The Clinical Decision Boundary

Engineering is proposing the following boundary for clinical review. This maps to a modification of the negation_check behavior:

**Current behavior (single-token window):**
Any negation word in the 6-token prefix before an SI pattern → suppress the match.

**Proposed refined boundary:**
| Negation structure | Relationship to SI signal | Proposed behavior |
|---|---|---|
| "I don't want to [SI]" + continuation disclosing ongoing ideation | Negation of intent, not of thought | **FLAG** |
| "I keep telling/asking myself not to [think about SI]" | Self-instruction; presupposes SI thought | **FLAG** |
| "I don't want to [SI], [affirmation of life]" | Denial of SI + life affirmation | **Don't flag** |
| "I don't want to [SI]" with no continuation | Ambiguous — denial or minimization | **TBD by clinical** |
| "[Third party] doesn't want to [SI]" | Third party reference | **SK-EN-004 path (existing)** |

The key distinction is:
- **Negation of the SI act** ("I don't want to die" / "I never want to hurt myself") → not flagging is appropriate; this is a denial
- **Negation within a self-instruction about the SI thought** ("not to think about", "not to dwell on") → flagging is appropriate; the thought is disclosed, the user is suppressing it
- **Negation followed by continuation disclosing the thought** ("I don't want to hurt myself, but I keep having these thoughts") → flagging is appropriate; the second clause overrides the minimization

---

## What clinical sign-off determines

1. **Is the proposed boundary above clinically correct?** Specifically:
   - Does "I don't want to hurt myself" + ongoing ideation disclosure warrant crisis protocol, or clinical escalation only?
   - Does "I keep telling myself not to think about [SI content]" warrant crisis protocol?

2. **The "ambiguous denial" case:** When a user says "I don't want to hurt myself" with no continuation, the current system correctly suppresses (interpretation: denial). Is this the correct default posture, or should it also be flagged?

3. **Priority relative to lexicon additions:** The 10 lexicon additions (Group A/B/C in the companion document) will recover approximately 83% of the 12 FN gap. The negation fix recovers the remaining 17%. Should the negation fix be prioritized equally, or deferred to a second pass after the lexicon additions are verified?

---

## Implementation options (for engineering, post sign-off)

Three options are available, in order of increasing complexity and risk:

### Option A: Pattern-based bypass (lowest risk)

Add new patterns to SK-EN-001 (or a new rule) that explicitly capture the disclosure framing, without negation_check:

```json
{
  "pattern": "keep having thoughts about",
  "negation_check": false
},
{
  "pattern": "thoughts about ending it won't stop",
  "negation_check": false
},
{
  "pattern": "telling myself not to think about",
  "negation_check": false
}
```

This does not change negation_check logic; it adds parallel patterns that bypass it. Low regression risk. Does not fix the root cause — a user who phrases the disclosure differently will still miss.

### Option B: Continuation-aware suppression modifier

Add a `negation_override_if_continuation` modifier: when a negation_check fires, additionally scan the text *after* the match for a disclosure continuation phrase (e.g., "but.*thoughts", "keep.*thinking"). If found, un-suppress the match.

Higher complexity. Requires engine change. Covers a broader class of the pattern.

**Architecture flag:** Option B modifies the Rules Service evaluator beyond simple IF/THEN pattern matching. The v7 spec defines the Rules Service as "a Python function that iterates rules and evaluates conditions" at the S1 tier — it is intentionally simple, deterministic, and <5ms. Adding continuation-aware logic changes the complexity class of the evaluator. If pursued, this should be documented as an architectural evolution of the Rules Service (new modifier type, updated schema), not just a bug fix. Clinical sign-off on Option A should be obtained first; this becomes a design decision if Option A proves insufficient.

### Option C: Self-instruction prefix detection

Add a separate detection pass for phrases matching "telling/asking myself not to [think/dwell/obsess] about [SI phrase]". This treats the self-instruction framing as its own high-priority signal class. The SI content inside it is secondary — the self-instruction itself is the clinical trigger.

Most robust but most invasive. Requires a new modifier type or a preprocessing step before negation_check runs.

**Architecture flag:** Option C is a structural change to the Rules Service schema — it adds a new rule evaluation mode that is neither keyword matching, regex matching, nor the current negation_check window scan. It requires:
1. A new modifier type in the rules schema (e.g., `self_instruction_prefix`)
2. New evaluation logic in `engine.py` that scans for this prefix before applying the main pattern
3. A schema version bump in `passive_si_patterns.json`

This should be approved as a post-Gitex architectural evolution item — not scoped as a pre-Gitex bug fix. The v7 spec principle at stake: "Safety is deterministic" means the evaluator logic must be verifiable by clinical review of the JSON rules alone, without requiring clinical reviewers to reason about evaluator code paths. Option C adds an implicit code-level semantic that the JSON schema does not fully express.

---

## Recommendation (engineering view)

Option A is the appropriate pre-Gitex fix. It:
- Requires no engine changes
- Adds 3-5 explicit patterns that cover NC-01 and NC-02 and their close variants
- Has zero regression risk on existing negation_check behavior
- Can be implemented and tested in one commit alongside the lexicon additions

Option C is the correct long-term fix. Defer post-Gitex.

Clinical sign-off is needed on the boundary before any implementation, regardless of option chosen.

---

## Post-sign-off engineering steps

1. Implement approved option (recommended: Option A)
2. Run `python scripts/safety_confusion_matrix.py` — verify the 2 NC cases are no longer FNs
3. Confirm overall recall ≥95%, precision 100%
4. Move NC-01 and NC-02 from `KNOWN_GAP_CASES` to `HARD_GATE_CASES` in `tests/fixtures/safety/cases.py`
5. Commit with message referencing this review package

---

## Relationship to SK-EN-006

Note: SK-EN-006 (added 2026-06-07) already implements a partial version of Option A for the self-harm progressive forms ("hurting myself", "harming myself", "harm myself"). The engineering note on that rule reads: "No negation_check — over-detection is the safe posture for self-harm action forms."

The same philosophy applies here. The distinction is:
- SK-EN-006: action-form words (progressive/gerund = active behavior disclosure)
- NC-01/NC-02: minimization-form phrases (denial-prefix + continuation = indirect disclosure)

Both should be flagged. The mechanism to get there is different (SK-EN-006 drops negation_check entirely; NC-01/02 need a bypass or continuation-aware check).

---

## Sign-off

| Reviewer | Role | Date | Decision |
|----------|------|------|----------|
| | Clinical Lead | | |
| | Engineering | | |
