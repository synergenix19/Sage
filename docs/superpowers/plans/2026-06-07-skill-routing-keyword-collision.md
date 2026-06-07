# Skill Routing: Tier 1 Keyword Collision — BA vs psychoed_depression

**Date:** 2026-06-07  
**Status:** AWAITING CLINICAL SIGN-OFF — do not apply  
**Prepared by:** engineering (skill-routing audit)  
**Requires sign-off from:** clinical lead  

---

## Summary

`psychoed_depression.target_presentations` contains symptom-description phrases that are ambiguous between psychoeducation (PD) and behavioral activation (BA). The same BA-intent input routes to three different skills depending on which synonym the user chooses. The fix — moving these phrases from PD to BA — is a clinical routing judgment that requires clinician sign-off. This document is the evidence package for that review.

The full-pairwise collision check (run as part of this audit) also found 26 pre-existing collisions across other skill pairs. Those are logged separately and require their own clinical review — they are NOT in scope for this change.

---

## Finding: BA vs psychoed_depression routing non-determinism

**Evidence — same BA intent, 10 phrasings, 3 different T1 outcomes:**

| Phrase | T1 result (current) |
|---|---|
| I used to enjoy things but I stopped | **psychoed_depression** ("used to enjoy") |
| I've lost interest in things I used to enjoy | **psychoed_depression** ("lost interest in") |
| I've lost interest in the things I used to do | **psychoed_depression** ("lost interest in") |
| nothing feels meaningful | **psychoed_depression** ("nothing feels meaningful") |
| I stopped doing the things I used to love | behavioral_activation ✓ |
| no motivation to do anything I used to enjoy | behavioral_activation ✓ |
| I used to love going out but I stopped doing that | no T1 match → semantic tier |
| I lost all interest in activities I used to do | no T1 match → semantic tier |
| I had hobbies but I just stopped doing them | no T1 match → semantic tier |
| activities I used to love feel pointless now | no T1 match → semantic tier |

**Root cause:** `psychoed_depression.target_presentations` contains symptom-description phrases that belong in at most one skill. These phrases are scan-order-dependent today — which skill a user gets depends on whether their particular wording matches BA's keywords first or PD's keywords first.

**This is not semantic instability.** It is a Tier 1 keyword authoring issue. Fixing it means making the phrase sets disjoint: each phrase lives in exactly one skill's `target_presentations`. The goal is routing that is correct regardless of which skill appears at which scan index.

---

## Proposed Remedy (clinical sign-off required)

### Scope

English phrases only. Three Arabic phrases currently in PD ("فاقد الاهتمام", "ما أقدر أفرح", "حياتي فاضية") are held pending Arabic-specific native-speaker clinical review (per eval doc §8.2). Until that review is complete, those phrases remain in PD only and are not added to BA — leaving them disjoint (one skill) is the correct interim state.

### Atomicity requirement

BA additions and PD removals must be in a single commit. Two failure modes if applied separately:
- **Add to BA before removing from PD:** phrase exists in both — double-match, scan-order dependent again
- **Remove from PD before adding to BA:** phrase exists in neither — coverage hole

Both failure modes are wrong routing, just in opposite directions.

### Remove from `psychoed_depression.target_presentations`

Clinical routing judgment required: does a user saying these phrases need to understand what's happening to them first (PD), or re-engage with activities (BA)?

```
"feel flat", "feeling flat"
"feel grey", "feeling grey", "grey and flat"
"everything feels heavy", "feel heavy"
"lost interest in"
"no interest in"
"used to enjoy"
"used to love doing"
"loss of interest in everything"
"I've lost interest in things I used to love"
"nothing feels meaningful"
"nothing feels worthwhile"
"low mood that won't lift", "mood won't lift"
```

**Retain in PD** (education-seeking phrases — "why/what/how/explain"):
All "what is", "explain", "teach me", "how does", "signs of", "am I depressed" forms. Retain "why do I feel flat" and "why do I feel grey" — the "why" signals inquiry, not just symptom description.

### Add to `behavioral_activation.target_presentations`

Phrases for users in behavioral withdrawal needing activation scheduling, not psychoeducation:

```
"lost interest in everything"
"lost interest in things i used to"
"lost interest in the things"
"lost all interest"
"no longer interested in anything"
"used to enjoy things but"
"used to love doing things but"
"used to love doing but"
"had hobbies but stopped"
"activities i used to enjoy"
"activities i used to love"
"used to love going out"
```

### Post-change disjointness (verified by engineering)

Combined post-change check (BA additions + PD removals applied together, English only) was run against all 25 matching skills. Result: **zero new collisions introduced**. The 6 pre-existing duplicates (see below) are unchanged by this commit.

Run the disjointness test before applying to confirm:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, 'src')
from sage_poc.nodes.skill_select import _SKILLS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP
kw_to_skills = {}
for sid, skill in _SKILLS.items():
    if sid in KEYWORD_SEMANTIC_SKIP: continue
    for kw in skill.target_presentations:
        kw_to_skills.setdefault(kw.lower(), []).append(sid)
dupes = {kw: skills for kw, skills in kw_to_skills.items() if len(skills) > 1}
ba_kws = set(k.lower() for k in _SKILLS['behavioral_activation'].target_presentations)
pd_kws = set(k.lower() for k in _SKILLS['psychoed_depression'].target_presentations)
print('BA ∩ PD:', ba_kws & pd_kws or 'none')
print('All-skills dupes:', dupes if dupes else 'none')
"
```

Expected:
- `BA ∩ PD: none`
- All-skills dupes: only the 6 pre-existing ones (not BA or PD) — see pre-existing collision table below

---

## target_presentations field scope (confirmed)

`target_presentations` is **routing-only** in the POC — consumed exclusively at `skill_select.py:140` for Tier 1 keyword matching. No other node reads it for clinical metadata or as a semantic-fallback anchor (`semantic_description` is the separate embedding anchor, built from different text). Editing `target_presentations` is a routing decision. Routing decisions for psychologically sensitive skills are clinician-owned content — hence the sign-off gate.

**v7 architecture note:** Per v7 §5.5, skill-matching keywords belong in the Rules Service (Node 4, Cosmos DB, CMS-managed with draft→review→approve→publish). In the POC they live in `target_presentations` as a shortcut. The disjointness governance rule (each phrase in exactly one skill's Tier 1 set) must migrate to the Rules Service layer in Full Build — it should not remain bolted onto skill JSON. The CMS authoring form should enforce disjointness structurally, flagging when a keyword already appears in another skill's matching rules.

---

## semantic_description correction (commit 5f2ceef — confirm or revert)

Commit `5f2ceef` removed "Behavioral activation rationale" from `psychoed_depression.semantic_description`. This appeared to be a copy-paste artifact. **Clinical lead: confirm this was an authoring error.** If intentional (PD was meant to introduce BA as a concept), revert `5f2ceef`.

**Re-embedding:** The POC builds `_semantic_embeddings` in-memory on server startup — no persistent vector index. The live embedding regenerated automatically on deploy. Cosine similarity between old and new description = 0.987 (nearly identical at embedding level). Run `scripts/calibrate_threshold.py` after deploy to confirm threshold unchanged (near-inert, but flagged per protocol — not a blocker).

---

## Regression tests required before applying

Add to test suite. The structural invariant test covers all skills; the per-phrase tests pin the evidence cases:

```python
# tests/test_skill_routing_ba_pd.py
import pytest
from sage_poc.nodes.skill_select import _SKILLS
from sage_poc.corpus_constants import KEYWORD_SEMANTIC_SKIP

def _tier1_match(phrase: str) -> str | None:
    phrase_lower = phrase.lower()
    for sid in (s for s in _SKILLS if s not in KEYWORD_SEMANTIC_SKIP):
        for kw in _SKILLS[sid].target_presentations:
            if kw.lower() in phrase_lower:
                return sid
    return None


def test_no_cross_skill_keyword_duplicates():
    """Structural invariant: no phrase appears in more than one skill's target_presentations.
    Catches any future keyword edit that creates scan-order-dependent routing."""
    kw_to_skills: dict[str, list[str]] = {}
    for sid, skill in _SKILLS.items():
        if sid in KEYWORD_SEMANTIC_SKIP:
            continue
        for kw in skill.target_presentations:
            kw_to_skills.setdefault(kw.lower(), []).append(sid)
    dupes = {kw: skills for kw, skills in kw_to_skills.items() if len(skills) > 1}
    assert not dupes, f"Keywords appear in multiple skills (scan-order dependent): {dupes}"


@pytest.mark.parametrize("phrase,expected_skill", [
    # BA-intent phrases — must route to BA after fix
    ("I used to enjoy things but I stopped",         "behavioral_activation"),
    ("I've lost interest in things I used to enjoy", "behavioral_activation"),
    ("I've lost interest in the things I used to do","behavioral_activation"),
    ("I stopped doing the things I used to love",    "behavioral_activation"),
    ("no motivation to do anything I used to enjoy", "behavioral_activation"),
    ("I lost all interest in activities",            "behavioral_activation"),
    ("activities I used to love feel pointless",     "behavioral_activation"),
    # PD education-seeking — must still route to PD after fix
    ("what is depression",                           "psychoed_depression"),
    ("am I depressed or just sad",                   "psychoed_depression"),
    ("explain the cognitive triad",                  "psychoed_depression"),
    ("why do I feel flat",                           "psychoed_depression"),
    ("teach me about depression",                    "psychoed_depression"),
])
def test_ba_pd_routing(phrase, expected_skill):
    result = _tier1_match(phrase)
    assert result == expected_skill, (
        f"'{phrase}' → {result!r}, expected {expected_skill!r}"
    )
```

**Arabic regression cases** — add once native-speaker clinical review is complete:
```python
    # Arabic BA-intent (pending Arabic-specific review)
    ("ما أسوي شي",    "behavioral_activation"),
    ("ما عندي خلق",   "behavioral_activation"),
    # Arabic PD education-seeking (must remain in PD)
    ("شو هو الاكتئاب",             "psychoed_depression"),
    ("وش الفرق بين الحزن والاكتئاب","psychoed_depression"),
```

Note: `test_no_cross_skill_keyword_duplicates` will fail today because of the 6 pre-existing duplicates below. It should be marked `xfail` until those are resolved, then promoted to a hard gate when the pre-existing cleanup ships.

---

## Pre-existing collisions — separate finding, separate review

Full pairwise check found 26 collisions unrelated to BA/PD. These are not in scope for this change. Each requires its own clinical routing judgment before resolution. Surfaced here for completeness; clinical lead should prioritize and assign.

**Exact keyword duplicates (6) — phrase exists identically in two skills; first-scanned wins:**

| Keyword | Skill A (lower idx wins) | Skill B |
|---|---|---|
| "can't switch off" | sleep_hygiene | psychoed_stress |
| "catastrophizing" | cbt_thought_record | worry_time |
| "flooded" | stop_technique | dbt_tipp |
| "self-blame" | cbt_thought_record | self_compassion_break |
| "setting limits" | assertive_communication | interpersonal_effectiveness |
| "triggered" | stop_technique | safe_place_visualization |

**Substring collisions — shorter keyword in higher-priority skill catches phrases intended for lower-priority skill (20 instances):**

| Short keyword (wins) | Skill (idx) | Shadowed phrase | Skill (idx) | Notes |
|---|---|---|---|---|
| "failure" | cbt_thought_record (0) | "i am a failure" | act (24) | CBT vs ACT defusion — different clinical approach |
| "worthless" | cbt_thought_record (0) | "i am worthless" | act (24) | Same |
| "فاشل" | cbt_thought_record (0) | "أنا فاشل" | act (24) | Arabic equivalent |
| "مو كافي" | cbt_thought_record (0) | "الراتب مو كافي" | financial_anxiety (21) | Salary anxiety → financial skill more specific |
| "مو زين" | cbt_thought_record (0) | "نومي مو زين" | sleep_hygiene (2) | "My sleep is bad" → sleep skill more appropriate |
| "مو زين" | cbt_thought_record (0) | "مزاجي مو زين" | mood_check_in (4) | "My mood is not good" → check-in more appropriate |
| "مو زين" | cbt_thought_record (0) | "تفكيري مو زين" | cognitive_restructuring (19) | Cognition → CBT plausible |
| "panic attack" | grounding_5_4_3_2_1 (1) | "panic attack explained" | psychoed_anxiety (12) | "explained" = inquiry → psychoed_anxiety appropriate |
| "panic attack" | grounding_5_4_3_2_1 (1) | "why do i get panic attacks" | psychoed_anxiety (12) | "why" = inquiry |
| "panic attack" | grounding_5_4_3_2_1 (1) | "explain panic attacks" | psychoed_anxiety (12) | "explain" = inquiry |
| "panic" | grounding_5_4_3_2_1 (1) | "what is panic" | psychoed_anxiety (12) | "what is" = inquiry |
| "panic" | grounding_5_4_3_2_1 (1) | "why do i panic" | psychoed_anxiety (12) | "why" = inquiry |
| "panic" | grounding_5_4_3_2_1 (1) | "panic attack explained" | psychoed_anxiety (12) | Same |
| "panic" | grounding_5_4_3_2_1 (1) | "why do i get panic attacks" | psychoed_anxiety (12) | Same |
| "panic" | grounding_5_4_3_2_1 (1) | "explain panic attacks" | psychoed_anxiety (12) | Same |
| "خايف" | grounding_5_4_3_2_1 (1) | "خايف أخسر شغلتي" | financial_anxiety (21) | "Afraid I'll lose my job" → financial more specific |
| "تعبان" | mood_check_in (4) | "جسمي تعبان من التوتر" | pmr (9) | "Body tired from stress" → PMR more appropriate |
| "تعبان" | mood_check_in (4) | "دايم تعبان وما في طاقة" | psychoed_stress (14) | "Always tired, no energy" → stress plausible |
| "how to say no" | assertive_communication (16) | "i don't know how to say no" | interpersonal_effectiveness (20) | Adjacent skills; assertive probably fine |
| "i know it's irrational but" | cognitive_restructuring (19) | "i know it's irrational but i still feel it" | act (24) | "Still feel it" is ACT territory (acceptance vs challenging) |

**Most critical for prioritization:**
1. `"مو زين"` (CBT idx=0) shadowing sleep and mood check-in Arabic phrases
2. `"panic"` / `"panic attack"` (grounding idx=1) shadowing inquiry-intent psychoed_anxiety phrases
3. `"failure"` / `"worthless"` (CBT idx=0) shadowing ACT-framed self-label phrases

---

## Checklist before applying

- [ ] Clinical lead reviewed English phrase list and confirmed BA vs PD assignment for each
- [ ] Arabic phrases (3: "فاقد الاهتمام", "ما أقدر أفرح", "حياتي فاضية") **not in this change** — held for Arabic-specific native-speaker review
- [ ] Post-change disjointness test confirms BA ∩ PD = empty after combined commit
- [ ] `test_skill_routing_ba_pd.py` written, passing, added to CI
- [ ] `test_no_cross_skill_keyword_duplicates` added (mark `xfail` until pre-existing dupes cleaned up)
- [ ] Applied atomically — BA addition and PD removal in single commit
- [ ] `approved_by` set on both `behavioral_activation.json` and `psychoed_depression.json`
- [ ] Confirm or revert commit 5f2ceef (semantic_description correction)
- [ ] Run `scripts/calibrate_threshold.py` after deploy to confirm threshold unchanged
- [ ] Pre-existing 26 collisions logged as separate governance item — do NOT fix in this PR
