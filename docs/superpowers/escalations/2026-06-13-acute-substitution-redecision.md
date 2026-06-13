# Clinical Re-decision — Acute Direct-Entry: substitute a declined skill, do not override the decline

**Date:** 2026-06-13
**Severity:** Sign-off blocker for `skill_matching_rules.json` (PR #4). Code is HELD pending this decision.
**Owner / action required:** Clinical lead — review the evidence, then either re-affirm the original `ignore_declined` design or accept the substitution amendment. Both are governance-clean. Engineering implements after the decision.
**Source:** PR #4 audit finding S2 (acute consent) → [sign-off alignment check](../audits/2026-06-13-signoff-alignment-check.md) §1.
**Why this is a re-decision and not a new ask:** the `ignore_declined` clause was introduced in the first engagement review on the reasoning that "direct entry is not a re-offer; the consent friction was the thing being respected." That reasoning protects cognitive load (correct) but additionally overrides a *specific remembered refusal of a specific technique* (the half that was missed). This doc routes the corrected understanding, with the literature, back to you so the signature rests on the full picture.

---

## What is being signed today (the original)

`acute_direct_entry` rule, fires when `emotional_intensity ≥ 8` AND the matched skill is one of the four acute somatic skills (`box_breathing`, `grounding_5_4_3_2_1`, `stop_technique`, `dbt_tipp`):

```json
"action": {"type": "enter_direct", "ignore_declined": true}
```

`ignore_declined: true` means: even if the user declined this exact skill earlier in the session, enter it directly anyway. "Safety over preference."

## The evidence against `ignore_declined` (the same-technique override only)

The no-menu *entry* at panic intensity is well-supported — not making someone parse options mid-panic is a real cognitive-load protection (PFA directiveness; Project BETA; PanicToCalm). The narrow problem is overriding the remembered "no" to the *same* technique:

1. **Project BETA de-escalation consensus** (PubMed 22461917) lists *"offer choices and optimism"* as one of its ten domains. Choice is part of de-escalation for agitated patients, not an obstacle to it.
2. **Trauma-informed care** (wtcs nursingmhcc 15-3): choice during overwhelm is the recovery mechanism; overriding a remembered refusal is the textbook failure mode.
3. **Bioethics** (Karger 30/1/17; AMA J Ethics 2016-09): overriding a refusal is grounded in *incapacity*, not distress intensity. Panic 8/10 is not incapacity.
4. **The "low-risk" assumption is unsafe for one of the four skills specifically:** breath-focused work can be *activating* rather than calming for trauma survivors (suffocation/choking histories → hyperventilation). A prior decline of `box_breathing` may be clinical signal, not friction — which is precisely what entry screens exist to catch.

Internal-consistency point: the `default_offer` rule makes declines session-scoped (never re-offered until a 4h gap). `ignore_declined` silently nullifies that guarantee for exactly the acute skills — the two rules contradict each other as signed.

## The proposed amendment — substitution within the acute set

No menu at intensity ≥8 (preserved). If the matched acute skill was declined this session, enter the **first non-declined member of the acute set** instead; enter the declined matched skill **only if all acute-set members were declined** (safety floor — at panic intensity, some de-escalation outweighs a full-set decline, because the alternatives, a menu mid-panic or nothing, are worse). This satisfies BETA's choice domain, trauma-informed care, and the consistency objection at once, while never leaving an acutely distressed user without de-escalation.

### The one assumption you must affirm explicitly

**The four acute skills are clinically substitutable for acute down-regulation** — i.e., if a user declined `box_breathing`, routing them into `grounding_5_4_3_2_1` (or `stop_technique`, or `dbt_tipp`) is a clinically appropriate substitute rather than a different intervention. The amendment rests entirely on this. If you judge them *not* freely substitutable, the substitution order (or pool membership) is yours to set in the data — see below.

**Reassurance:** substitution cannot route around a contraindication. The substituted skill still runs its own `entry_screen` on the next executor turn (e.g., TIPP's cold-water cautions, PMR's pain/injury screen). Substitution only changes *which* acute skill is entered, not *whether* its safety screening runs.

---

## The diff the clinical lead is signing the shape of (HELD — not yet applied)

**1. `src/sage_poc/rules/data/skill_matching/skill_matching_rules.json`** — the acute rule action and its description. The substitution pool and its order are data (clinician-ownable):

```json
// BEFORE
"action": {"type": "enter_direct", "ignore_declined": true}

// AFTER
"action": {
  "type": "enter_direct",
  "on_declined": "substitute",
  "substitute_pool": ["box_breathing", "grounding_5_4_3_2_1", "stop_technique", "dbt_tipp"]
}
```
Description updated to: direct entry at panic intensity (no menu); a declined match is replaced by the first non-declined pool member in listed order; the declined match is entered only if the whole pool was declined (safety floor); substitutes still pass their own entry_screen. The pool order IS the substitution priority — reorder in data to change clinical preference.

**2. `src/sage_poc/nodes/skill_select.py` `_resolve_entry`** — replace the `ignore_declined` branch:

```python
# BEFORE
if action["type"] == "enter_direct":
    if action.get("ignore_declined") or primary not in declined:
        skill = _SKILLS[primary]
        return { ...activate primary..., "path": state["path"] + audit_markers }
    audit_markers.append("enter_direct_declined_fallback")
# ...falls through to offer path

# AFTER
if action["type"] == "enter_direct":
    if primary not in declined:
        skill = _SKILLS[primary]
        return { ...activate primary..., "path": state["path"] + audit_markers }
    on_declined = action.get("on_declined", "offer")   # legacy enter_direct rules default to offer-fallback
    if on_declined == "substitute":
        pool = action.get("substitute_pool", [])       # deterministic order = data order
        substitute = next((s for s in pool if s not in declined and s in _SKILLS), None)
        if substitute is not None:
            skill = _SKILLS[substitute]
            return { ...activate substitute...,
                     "path": state["path"] + audit_markers + ["acute_substitute_declined"] }
        # whole pool declined — safety floor: enter the matched (declined) skill directly
        skill = _SKILLS[primary]
        return { ...activate primary...,
                 "path": state["path"] + audit_markers + ["acute_safety_floor_all_declined"] }
    audit_markers.append("enter_direct_declined_fallback")   # on_declined == "offer"
# ...falls through to offer path
```

`ignore_declined` is removed entirely. The default `on_declined == "offer"` preserves the existing `enter_direct_declined_fallback` behavior for any future non-acute `enter_direct` rule. Two new audited path markers — `acute_substitute_declined` and `acute_safety_floor_all_declined` — make the trail explain why a non-matched (or previously-declined) skill was entered, following the `enter_direct_declined_fallback` precedent.

**3. Schema validator** (`SkillMatchingRule`, `rules/schemas.py`) — dead-signal guard: `on_declined` must be `"substitute"` or `"offer"`; `on_declined == "substitute"` requires a non-empty `substitute_pool` list. A `substitute` action without a pool would be silently inert — reject at load.

**4. Test inversion (flagged as part of the change, not a follow-up)** — `tests/test_skill_select_offer.py`:
- `test_acute_direct_entry_ignores_declined` (currently: declined `box_breathing` at intensity 9 → enters `box_breathing`) **inverts** to `test_acute_declined_substitutes_within_pool`: declined `box_breathing` at intensity 9 → enters the next non-declined pool member (`grounding_5_4_3_2_1`), path contains `acute_substitute_declined`, `active_skill_id != "box_breathing"`.
- **New** `test_acute_all_declined_safety_floor`: all four acute declined, `box_breathing` matched at intensity 9 → enters `box_breathing` (the matched declined skill), path contains `acute_safety_floor_all_declined`.
- `test_acute_somatic_high_intensity_enters_directly` (non-declined direct entry) is unchanged.

---

## Decision

- [ ] ~~**Re-affirm the original** (`ignore_declined: true`)~~ — not chosen.
- [x] **Accept the amendment** (substitution + safety floor).

**Reasoning capture (completed 2026-06-13, clinical lead).**

- **Decision: ACCEPT THE AMENDMENT** (substitution + safety floor over `ignore_declined`). Decided by: clinical lead, recorded 2026-06-13.
- Evidence reviewed (acknowledged): ☑ Project BETA (choices are a de-escalation domain) ☑ trauma-informed care (overriding a remembered refusal; breath work can be activating) ☑ capacity-based ethics (intensity ≠ incapacity) ☑ internal-consistency (session decline scope vs `ignore_declined`)
- Reasoning for the call: overriding a remembered decline of a specific technique is not grounded by panic intensity (intensity is not incapacity), and the "low-risk" assumption fails specifically for breath work, which can be activating for trauma survivors — which is why `box_breathing` carries an entry screen. Substituting a different acute skill preserves the no-menu directiveness while honoring the decline, and resolves the contradiction with the session-scoped decline rule.
- **Substitutability: affirmed WITH a constraint.** The acute skills are substitutable for acute down-regulation EXCEPT TIPP's cold-water / intense-exercise component, which may not be a clean swap for a breathing/grounding exercise. **Open sub-item requiring explicit closure:** does TIPP stay in the auto-substitution pool (reached only if all others were declined) or is it excluded entirely? Until closed, the amendment is implemented conservatively with **TIPP last** in the pool.
- **Substitution order (activation-risk, grounding-first):** `grounding_5_4_3_2_1, stop_technique, box_breathing, dbt_tipp`. Consequence of decision C1 (grounding is the safer first move for ambiguous acute presentation; the pool inherits the lowest-activation-risk-first logic). `box_breathing` is mid-pool (breath focus is higher-activation than grounding/STOP, lower than TIPP's cold water); `dbt_tipp` last.

On decision, engineering applies the diff (one commit, with the test inversion), pool ordered as above.

## Status

**DECIDED 2026-06-13 — amendment accepted; code being applied** with the grounding-first pool order. **One open sub-item before the `skill_matching_rules.json` sign-off is recorded:** explicit closure of TIPP's place in the auto-substitution pool (stays-last vs excluded — a one-line data edit). The other four PR #4 sign-offs are unaffected.
