# A1 Boundary — FROZEN (boundary.md)

**Date frozen:** 2026-06-23
**Approval:** Clinical lead approved the §1–§5 recommendations (relayed via coordinator, 2026-06-23). Supersedes `2026-06-22-A1-boundary-freeze-DRAFT.md`.
**Audit note:** the named clinical signatory must be recorded in the governance log for Test Content Guardrails completeness (date + role captured here; name to be appended).
**Scope of freeze:** the two boundary edges + crisis-exclusion + referral ruling + ID-OOS exemplar are FROZEN and unblock A2 labeling. **§3a (crisis-adjacent dialect line) is NOT resolved here** — per the approved recommendation it is *routed onward* to a native-dialect clinician cross-checked against the task #21 bench; it does not block routing-slice labeling but gates the crisis-adjacency handoff to task #21.
**Source of truth:** `src/sage_poc/skill_ids.py` (27 skills).

---

## FROZEN decisions

**§1 Skill edge** — in-scope = subjective psychological/emotional distress and coping in a non-crisis user, addressable by one of the 27 skills' technique constructs (construct-family map in the draft). ✅ approved.

**§2 Domain edge** — in-domain = subjective emotional/psychological distress (mood, anxiety, stress, sleep, grief, relationships, motivation, self-worth, coping). Far-OOS = medical/diagnostic, medication advice, legal/financial transactions, general info, off-topic. ID-OOS = genuine wellbeing concern unmatched by the 27 (body-image, anger management, OCD-specific, phobias, perfectionism, parenting stress) → ABSTAIN. ✅ approved (§2a confirmed).

**§3 Crisis-exclusion (3 rules)** — (1) crisis is never a routing target; (2) crisis-adjacent Khaleeji dialect → task #21; (3) any crisis utterance present asserts path-invariance only. ✅ approved.

**§4 Referral ruling** — `psychotic_referral` and `post_crisis_check_in` are EXCLUDED as `skill_select` targets; reached via deterministic/clinical-state paths only; exclusion is **measured** adversarially (A2.8). ✅ approved as default. §4a (whether `psychotic_referral` is ever free-entry, under what guard) — clinical lead affirms the exclusion default; no free-entry guard authorized at this time.

**§5 Flag-free ID-OOS exemplar** — *"Lately I keep comparing my body to others and feel bad about how I look"* (body-image; in-domain, uncovered, no Node-1 flag). ✅ approved.

## OPEN sub-item (does not block A2 routing-slice labeling)

**§3a — crisis-adjacent dialect line** — routed to a **native-dialect clinician + task #21 cross-check**. Recorded methodological guidance (not a clinical decision): draw conservatively toward escalation; OR-fusion already biases that way; residual = which dialectal phrasings count as a crisis signal at all. Owner: native-speaker clinician on the task #21 track.

## Sign-off

```
§1–§5 approved — clinical lead (name: __________)              Date: 2026-06-23
§3a resolved — native-dialect clinician (task #21)             Date: __________ (open)
```
