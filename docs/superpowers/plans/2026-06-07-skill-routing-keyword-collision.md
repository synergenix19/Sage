# Skill Routing: Tier 1 Keyword Collision — BA vs psychoed_depression

**Date:** 2026-06-07  
**Status:** AWAITING CLINICAL SIGN-OFF — do not apply  
**Prepared by:** engineering (skill-routing audit)  
**Requires sign-off from:** clinical lead  

---

## Finding

Tier 1 keyword sets for `behavioral_activation` and `psychoed_depression` overlap in the symptom-description space, causing routing non-determinism: the same user intent routes to BA, PD, or no match depending purely on which synonym the user chose.

**Evidence — same BA intent, 10 phrasings, 3 different T1 outcomes:**

| Phrase | T1 result |
|---|---|
| I used to enjoy things but I stopped | **psychoed_depression** ("used to enjoy") |
| I've lost interest in things I used to enjoy | **psychoed_depression** ("lost interest in") |
| I've lost interest in the things I used to do | **psychoed_depression** ("lost interest in") |
| nothing feels meaningful | **psychoed_depression** ("nothing feels meaningful") |
| I stopped doing the things I used to love | behavioral_activation (correct) |
| no motivation to do anything I used to enjoy | behavioral_activation (correct) |
| I used to love going out but I stopped doing that | no T1 match → semantic tier |
| I lost all interest in activities I used to do | no T1 match → semantic tier |
| I had hobbies but I just stopped doing them | no T1 match → semantic tier |
| activities I used to love feel pointless now | no T1 match → semantic tier |

**Root cause:** `psychoed_depression.target_presentations` contains symptom-description phrases (see below) that are behaviorally ambiguous — a user saying these phrases may need graded activity scheduling (BA) rather than explanation of the depression mechanism (PD). Since PD is at scan index 13 and BA at index 5, the mis-routing depends on whether BA's keywords catch the phrasing first; when they don't, PD wins.

**Important:** this is not semantic instability. It is Tier 1 keyword authoring: these phrases belong to at most one skill's Tier 1 set, but are currently in PD's. Fixing the overlap removes the scan-order dependency entirely.

---

## Proposed Remedy (clinical sign-off required)

### 1. Remove from `psychoed_depression.target_presentations`

These phrases describe a symptom state rather than an education-seeking intent, and are clinically ambiguous between BA and PD:

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

**Arabic equivalents to review (may route to BA or general distress, clinical call):**
```
"فاقد الاهتمام"       (loss of interest)
"حياتي فاضية"        (my life is empty)
"ما أقدر أفرح"       (I can't be happy)
"ما في شي يستاهل"    (nothing is worth it)
"ما أحس بمعنى لأي شي" (I don't feel meaning in anything)
```

**Retain in PD** (explicitly education-seeking — "why/what/how/explain"):
```
"what is depression", "depression explained", "am I depressed",
"sadness vs depression", "what is anhedonia", "depression education",
"explain depression", "what causes depression", "signs of depression",
"what does depression feel like", "am I depressed or just sad",
"difference between sadness and depression", "teach me about depression",
"how does depression work", "why do I feel flat", "why do I feel grey",
"cognitive triad", "Beck depression model", "behavioral withdrawal depression"
```

**Rationale for retaining "why do I feel flat/grey":** the "why" signals inquiry (wanting explanation), not just symptom description.

### 2. Add to `behavioral_activation.target_presentations`

Phrases removed from PD that represent BA-appropriate entry points (user is in a behavioral withdrawal state, not asking for psychoeducation):

```
"lost interest in everything"
"lost interest in things I used to"
"lost interest in the things"
"lost all interest"
"no longer interested in anything"
"used to enjoy things but"
"used to love doing things but"
"had hobbies but stopped"
"activities I used to enjoy"
"activities I used to love"
"used to love going out"
```

**Arabic (clinical judgment required on each):**
```
"فاقد الاهتمام"
"ما أقدر أفرح"
"حياتي فاضية"
```

### 3. Verify disjointness before applying

After the proposed moves, confirm no phrase appears in both `target_presentations` sets. The test:

```bash
.venv/bin/python -c "
from sage_poc.nodes.skill_select import _SKILLS
ba = set(k.lower() for k in _SKILLS['behavioral_activation'].target_presentations)
pd = set(k.lower() for k in _SKILLS['psychoed_depression'].target_presentations)
print('Overlap:', ba & pd)
"
```

Expected output: `Overlap: set()`.

A phrase in both sets means routing still depends on scan order — the fix is incomplete.

---

## Additional semantic_description correction (applied, confirm or revert)

**Commit 5f2ceef** removed "Behavioral activation rationale" from `psychoed_depression.semantic_description`. This appeared to be a copy-paste artifact — a psychoeducation skill's embedding anchor should not contain the technique name of a distinct skill (BA). 

**Clinical lead: please confirm** this was an authoring error, not an intentional choice (e.g. "PD is meant to introduce BA as a next step"). If intentional, revert the commit and add a comment explaining the design intent.

---

## Systemic finding

This is the same class of issue across multiple skills: Tier 1 keyword sets were authored without a disjointness constraint. Symptoms that are common to several skills' presentations end up in multiple `target_presentations` arrays, creating scan-order-dependent routing.

**Recommended governance addition:** before signing off any `target_presentations` edit, run the disjointness check above across all affected skill pairs. The CMS authoring form should enforce this structurally: flag a warning when a new keyword already appears in another skill's `target_presentations`.

**Retroactive explanation for mood_check_in "self-fix":** mood_check_in may have been subject to the same class — its apparent resolution under serial testing (vs. pool exhaustion under parallel load) may reflect input-sensitive Tier 1 collision rather than a pool issue. Recommend running the same phrasing sweep across mood_check_in's keyword set once the BA/PD issue is resolved.
