# Skill Authoring Conventions

Standards for authoring JSON skill files in `src/sage_poc/skills/`.

---

## semantic_description: technique identity, not user symptom language

### The rule

`semantic_description` must describe **what the therapeutic technique IS** — its protocol, structure, and mechanism. It must NOT contain:

- Emotional state words (`stressed`, `anxious`, `overwhelmed`, `sad`, `depressed`, `calm`)
- Symptom language (`I can't sleep`, `I feel hopeless`, `I'm falling apart`)
- User-voice phrases (`I want to...`, `I feel...`, `I need...`, `I am about to...`)
- Generic presentations that multiple skills share (`low mood`, `feeling bad`, `hard time`)

```json
// WRONG — user symptom language in description
"semantic_description": "A structured breathing exercise for acute stress regulation. I can't calm down. I'm overwhelmed and my breathing is shallow. Something to help with anxiety and racing thoughts."

// RIGHT — technique identity only
"semantic_description": "Box breathing: four-count inhale, four-count hold, four-count exhale, four-count hold. Square breathing. Paced breathing exercise. Walk me through the four-count breathing cycle."
```

### Why this matters

Skill matching uses BGE-M3 semantic embeddings at Tier 2. The embedding model scores cosine similarity between the user's message and each skill's `semantic_description`. If descriptions contain emotional state language, they attract **any** user message that expresses those emotions — regardless of whether the skill is indicated.

A description like "helps with stress and anxiety" will score high on "Hi, I've been stressed lately" even though the correct response is freeflow exploration, not skill execution. This creates **silent routing misfires** that are impossible to audit without a full collision matrix.

The principle: `semantic_description` should only score high when the user is specifically requesting the technique. It should score low on general emotional presentations that could indicate many different interventions or no intervention at all.

### Where user language belongs

User-facing language belongs exclusively in `target_presentations`:

```json
// target_presentations: what the USER SAYS
"target_presentations": [
  "can't calm down",
  "help me breathe",
  "I'm anxious",
  "racing thoughts",
  "خايف",
  "قلبي يدق"
],

// semantic_description: what the TECHNIQUE IS
"semantic_description": "Box breathing: four-count inhale, hold, exhale, hold cycle. Square breathing protocol. Paced breathing exercise."
```

`target_presentations` handles the keyword Tier 1 match. `semantic_description` handles the semantic Tier 2 fallback for users who describe the technique without using its exact name.

---

## Semantic description authoring checklist

Before committing any skill JSON, verify:

- [ ] Description leads with the technique name and protocol
- [ ] No emotional state words or generic distress language
- [ ] No user-voice phrases (`I want to`, `I feel`, `I need`)
- [ ] Tested against all other skills' `target_presentations` for collisions
- [ ] Tested: guard queries (`stressed`, `overwhelmed`, `sad`) score below `SEMANTIC_THRESHOLD`
- [ ] Tested: technique-request queries score above `SEMANTIC_THRESHOLD` and route to this skill

### Running the collision matrix

After adding or editing any skill's `semantic_description`, run:

```bash
.venv/bin/python -m pytest tests/test_nodes.py::test_stressed_does_not_match_any_skill tests/test_nodes.py::test_stressed_does_not_match_sleep_hygiene tests/test_nodes.py::test_overwhelmed_and_anxious_does_not_match_any_skill -v
```

Then recalibrate the threshold:

```bash
.venv/bin/python scripts/calibrate_threshold.py
```

See `docs/semantic_skill_matching_audit_20260521.md` for the threshold calibration record.

**Current threshold: `SEMANTIC_THRESHOLD = 0.4593`** (calibrated 2026-06-07, gap=0.0526, cross-cluster). This value is set in `nodes/skill_select.py`.

---

## Somatic vocabulary FPs: use SEMANTIC_EXCLUSION_WORDS, not threshold

The 0.46–0.47 cosine band is a documented no-go zone for the threshold. BGE-M3 clusters somatic and physiological vocabulary (eating, breathing, body sensations) in this range regardless of which skill description they are scored against. Raising the threshold into this band causes TP cascade — confirmed 2026-06-08 when a single FP fix (appetite-loss phrases scoring 0.4665 against box_breathing) caused the mindfulness and interpersonal_effectiveness TPs to break in sequence.

**Playbook for somatic/physiological false positives:**

1. Identify the vocabulary that is causing the false match (e.g. "eat", "eating", "appetite").
2. Verify: no existing skill in the registry has a therapeutic technique for that vocabulary. If one does, the correct fix is Tier 1 keyword expansion on that skill, not exclusion.
3. Add the offending words to `SEMANTIC_EXCLUSION_WORDS` in `src/sage_poc/corpus_constants.py`. Use single words — the guard uses word-boundary regex, so "eating" will not match "repeating" or "seating".
4. Run `tests/test_skill_select.py` to confirm the affected phrases now return `active_skill_id = None`.
5. Add the phrases as parametrized test cases in the appetite-loss guard block (`test_appetite_disclosure_does_not_trigger_skill`).
6. Do **not** touch `SEMANTIC_THRESHOLD`.

This is the v7 §4.3 contract: Tier 1 rules are fast, predictable, auditable. Semantic embedding is fallback only. Exclusion guards are Tier 1 rules.

---

## Arabic safety rules: use normalized Arabic in regex patterns

If you are authoring a `safety` category rule with `"match_type": "regex"` that includes Arabic text, patterns must be written in `normalize_arabic()` normalized form — bare alef (`ا`), no harakat. Natural Arabic typing (e.g. `أريد`) will never match normalized text and the rule will silently produce no matches.

The loader emits a `WARNING` at startup if unnormalized Arabic is detected in a regex rule. See `docs/RULES_AUTHORING_CONVENTIONS.md § Arabic regex patterns` for the full specification and a verification snippet.

---

## No em dashes in any string field

**NEVER** use em dashes (—) in any JSON string field in a skill file. This applies to `semantic_description`, `examples`, `contraindications`, `completion_criteria`, `goal`, `technique`, `tone`, and all other fields.

Skill content (`examples`) is injected directly into the LLM system prompt via L3 skill instruction. Em dashes mirror into model output. Use commas instead.

See `docs/RULES_AUTHORING_CONVENTIONS.md` for the same rule applied to rules files.

---

## self_evolution field

All skills must include `"self_evolution": "manual_only"`. This signals to the skill registry that this skill's content is human-authored and must not be modified by any automated pipeline.

---

## step_policy: 5 standard rules + at least 1 skill-specific (minimum 6 rules)

Every structured skill must have at minimum 6 `step_policy` rules: the 5 standard rules listed below, plus at least 1 skill-specific rule.

**Standard rules (required, all 5 must be present in every structured skill):**

1. `emotional_intensity > 7` → `validate_only` (acute distress gate)
2. `resistance > 8, for_turns: 1` → `offer_skill_switch_or_break` (acute single-turn resistance — fires before rule 3)
3. `resistance > 6, for_turns: 3` → `offer_skill_switch_or_break` (sustained resistance over multiple turns)
4. `engagement < 3, for_turns: 3` → `check_in_micro` (low engagement)
5. `user_stop_request == true` → `exit_warm_closing` (explicit stop, no persuasion)

**Evaluation order matters:** Rule 2 (acute, 1-turn) is evaluated before rule 3 (sustained, 3-turn). Rule 2 catches high-intensity single-turn rejection (e.g., a user who is angry and action-seeking, not suited to the current technique). Rule 3 catches the slower-build case where a user shows moderate resistance across multiple turns without a single spike. Both are needed — they address different clinical patterns.

**Skill-specific rules (at least 1 required, requires clinical sign-off):**

6+. Skill-specific transitions: prior exposure handling, contraindication detection (e.g., dissociation in body-awareness skills, obsessive theme in worry_time), step-specific branches, or clinical edge cases relevant to the technique. Common pattern: `prior_exposure == true` → offer choice to revisit or try a different approach. All skill-specific rules must be reviewed by a clinician before shipping.

**Minimum rule count by skill type:**
- Standard structured skill: 6 (5 standard + 1 skill-specific)
- Skills with multiple clinical edge cases (e.g., `post_crisis_check_in`): may have more; no upper cap

The `next_step_id` for `exit_warm_closing` rules must be `"exit"` (string), not `null`.

**`for_turns` field:** Use the canonical `for_turns` field name; the legacy alias `turns` is also accepted but deprecated. `for_turns` is supported for `resistance` (uses `resistance_history` rolling buffer) and `engagement` (uses `engagement_trajectory` 4-turn window). For all other signals, `for_turns` is ignored and the current value is checked.

**Current compliance status (2026-06-08):** Most skills have 4 rules (missing rule 2 and skill-specific rule). The acute resistance rule (rule 2) is being added in the 2026-06-08 audit pass. Skill-specific rules are pending clinical review for 20 skills.

---

## escalation_matrix: L1–L4 required

All four escalation levels must be present:

| Level | Trigger | Used at runtime? |
|-------|---------|-----------------|
| L1 | User requests to stop | **Yes** — read as step instruction for exit routing |
| L2 | Clinician review flag condition (skill-specific) | STORED_ONLY — validated, not read at runtime |
| L3 | Crisis signal detected | STORED_ONLY — validated, not read at runtime |
| L4 | Human handoff (3+ crises in 30 days, or explicit request) | STORED_ONLY — validated, not read at runtime |

**Important:** Only L1 text is read at runtime. L2–L4 are stored in the DB, parsed and validated by the schema, but not evaluated by any runtime node in the current implementation. This is documented in `skills/conformance.py`. Do not write L2–L4 as if they will fire automatically — they are documentation of escalation intent, not operational rules.

---

## §6 guard escalation targets must match the spec

When a skill's entry screen or contraindications screen for states the BOT BEHAVIOUR spec treats under a category **§6 guard** (dissociation, panic-with-derealization, trauma flashback, psychosis-like content), the **escalation target must match what the spec says**, not a plausible-looking substitute. The spec escalates those specific states to **referral** ("escalate to referral rather than presenting the standard tools") precisely because grounding/mindfulness can *intensify* them — so redirecting them to another self-guided tool (grounding, breathing) is under-escalation, even though it looks safe.

Checklist: for each state a skill screens out, confirm the destination (referral vs anchored alternative vs skill-switch) is the one the spec assigns to that state. Differentiate by severity: serious §6 states → referral (a milder anchored tool may serve only as a brief stabiliser while support is arranged); milder presentations → anchored alternative. (Origin: 2026-07-07, `mindfulness_meditation` entry_screen initially routed derealization/trauma-flashback to grounding instead of referral; caught on a post-authoring spec double-check, PR #131.)

## Arabic examples in steps

Every skill must include at least one Arabic (Khaleeji Gulf dialect) example in each step's `examples` array. Arabic examples should use the same colloquial register as the English examples, not clinical Arabic.

**Canonical field name is `examples`.** The skill_executor reads `step.examples` (skill_executor.py:109). Do not use `few_shot_examples` as an alternative name. All skill files use `examples`.

---

## cultural_overrides: Gulf-context adaptation per skill

`cultural_overrides` is a `dict` field on every skill. It is **injected at runtime** into the LLM system prompt as a "SKILL-SPECIFIC CULTURAL CONTEXT" block on every turn where that skill is active. This applies before the LLM generates a response.

### What it is for

Skill-level cultural context that is specific to this technique and cannot be expressed by the global cultural rules in `rules/data/cultural/`. Examples:

- Whether a somatic technique is compatible with Islamic practice
- How to frame the technique for users who are also observing prayer times
- Gender-specific physical adjustments (or confirmation that none are needed)
- Dialect or register notes specific to the skill's exercise language

### Budget

`cultural_overrides` content has a **200-word hard limit** (clinician-signed, enforced in `prompts/composer.py`). If the entire block exceeds 200 words, it is **skipped entirely** — not truncated. A startup warning is logged. Keep overrides concise; write one value per key, not paragraphs.

### Required: populate for all new skills

When adding a new skill, `cultural_overrides` must be populated with at least basic Gulf-context framing before the skill ships to a user-facing build. Empty `cultural_overrides` is a P2 gap (four current skills — `box_breathing`, `mood_check_in`, `stop_technique`, `worry_time` — still have partial or empty overrides; tracked as pre-prod work).

### Example structure

```json
"cultural_overrides": {
  "halal_framing": "Box breathing is a physiological technique with no spiritual or religious content. It can be offered without qualification to Muslim users.",
  "prayer_compatibility": "If a user is preparing for salah or has just finished, the technique fits naturally: a brief, structured pause before or after prayer.",
  "gender_neutral_delivery": "The technique requires no physical adjustments and is equally appropriate for men and women, including users wearing hijab or niqab."
}
```

Keys are arbitrary but should be descriptive. The full dict is injected as-is into the prompt — key names are visible to the LLM.

---

## completion_criteria: what triggers step advancement

`completion_criteria` is a string field on `SkillStep`. It describes the condition the user's response must meet for the step to be considered complete and for `skill_executor` to advance to the next step.

**Two evaluation paths — which path runs depends on the skill:**

| Path | Skills | How |
|---|---|---|
| Word-count heuristic | All skills except the 4 below | `len(message_en.split()) > 1` |
| LLM evaluator (`criteria_eval.py`) | `post_crisis_check_in`, `cbt_thought_record`, `behavioral_activation`, `assertive_communication` | LLM reads the `completion_criteria` text and evaluates whether the user's message satisfies it |

For the LLM path: the `completion_criteria` text is sent verbatim to the classifier LLM along with the user's message. Write it as a specific, testable criterion, not a vague instruction:

```json
// WRONG — too vague for LLM evaluation
"completion_criteria": "User has engaged with the step"

// RIGHT — specific and testable
"completion_criteria": "User has identified at least one specific automatic thought they noticed during the exercise"
```

For skills that use the word-count heuristic, `completion_criteria` is stored and validated but not read at runtime. It should still be present as documentation of the therapeutic intent.

---

## Schema conformance reference

`skills/conformance.py` is the authoritative record of which skill schema fields are used at runtime versus stored only. Review it before authoring a new field or relying on a field in a new node.

Runtime summary (as of 2026-05-30):
- **USED (7):** `step.goal`, `step.technique`, `step.technique_description`, `step.tone`, `step.examples`, `step.contraindications`, `skill.cultural_overrides`, `skill.escalation_matrix.L1`
- **PARTIAL (1):** `step.completion_criteria` (LLM path for 4 skills only; word-count heuristic for all others)
- **STORED_ONLY (6):** `skill.escalation_matrix.L2–L4`, `skill.evidence_base`, `skill.skill_type`, `skill.self_evolution`

The conformance registry is logged at startup and served at `GET /health/schema-conformance`.

---

## semantic_anchors: SI-boundary rule for emotionally-heavy skills

`semantic_anchors` are scored by BGE-M3 at Tier 2. Before submitting anchors for any skill that touches grief, loss, relationship ending, estrangement, or financial catastrophe, run every candidate sentence through `scripts/check_anchor_si_boundary.py`. An anchor that fails the SI-boundary check will trigger an automated gate failure even if it is clinically accurate.

### The void-framing rule

**Anchors whose dominant semantic load is the void left behind will bleed into passive-SI space.** BGE-M3 cannot separate "an important person is absent and others feel the impact" from passive-SI self-absence language ("without me", "my absence would help", "my being here is doing harm") — both encode the same concept at the embedding level, regardless of whether the absent person is someone else or the user themselves.

This is a constraint of the model, not a content error. The approved grief anchors from the 2026-06-10 Task 5 run were clinically accurate and still failed the gate. The fix is authoring discipline, not clinical rewriting.

**The authoring heuristic:** Any anchor where the clinical meaning depends on *who is absent* rather than *what is happening* is at risk. The model weights the emotional situation (significant absence, impact on others) more than the pronoun or perspective.

### What to avoid (and what may not help either)

**Void/absence framing is the worst case.** Anchors where the primary semantic load is "an important person is absent and others feel the impact" score highest on passive-SI phrases. Avoid:
- "The house feels empty without him"
- "She is gone and nothing feels real"
- "My whole family collapses without my income"

**Active-experience framing reduces bleed directionally but does not guarantee a clear result.** Testing confirms that even framing like "I keep reaching for my phone to send her a message" still bleeds at 0.6490 — the `I keep [verb]ing` construction is its own SI proximity bridge (both grief and SI probes use repetitive-thought language). "I still forget not to set a place for her" may do better; "I keep expecting her to walk in" will not.

**Known BGE-M3 proximity vectors for grief anchors (all increase SI score):**
1. Void/absence framing: "without him", "she is gone", "empty world"
2. Repetitive intrusive thought: "I keep [verb]ing"
3. Identity-dissolution: "I don't know who I am without her"
4. Emotional-impact magnitude: strong affective language of any kind increases proximity

**The feasibility reality:** Grief anchors may not be achievable at the 0.40 target for any phrasing that is emotionally resonant enough to also reliably route grief presentations. If that's the finding, the answer is not to lower the bar — it is to accept that grief_loss routes via Tier 1 keywords (which are already comprehensive) and freeflow, without semantic anchors at this threshold.

Run every candidate through `scripts/check_anchor_si_boundary.py`. A score of 0.41 and a score of 0.66 both fail, but they are not the same problem.

The same vectors apply to relationship loss, estrangement, migration grief, and any skill touching hopelessness or failure-identity.

### Submission target: max SI score < 0.40

The automated gate threshold is `SEMANTIC_THRESHOLD = 0.4593`. The submission bar is **0.40**. These are not the same number.

Anchors must score below **0.40** on every SF-1 passive-SI probe before being submitted for clinical sign-off. Rationale: the frozen baseline (Entry 5, 2026-06-09) shows the highest off-topic miss at 0.4330 against the general corpus; the 0.40 bar creates a 0.033 buffer. Anchors that score between 0.40 and 0.4593 clear the gate but sit in thin-margin territory — revise them or exclude them.

The pre-submission tool (`check_anchor_si_boundary.py`) reports three tiers: PASS (< 0.40), WARN (0.40–0.4593), BLEED (≥ 0.4593). Only PASS anchors should be submitted. WARN anchors should be revised; if no lower-bleed framing exists, they may be left unanchored.

### Freeflow is a valid path

If a grief or loss presentation cannot reach max SI score < 0.40 through any plausible re-authoring, do not lower the bar to include it. Leave that presentation unanchored and let Node 1 (safety_check) + freeflow handle it. Freeflow with the safety node running first is clinically safe. Do not treat a per-skill anchor count as a quota. Better 4 anchors that clear 0.40 with margin than 8 that sit at 0.42.

### Verification before submission

Run candidates through the pre-submission check before sending to clinical sign-off.

```bash
# Score candidate anchors against the passive-SI phrase bank
.venv/bin/python scripts/check_anchor_si_boundary.py "Your candidate sentence here"

# Or batch: pipe sentences (one per line) from a file
cat candidate_anchors.txt | .venv/bin/python scripts/check_anchor_si_boundary.py --stdin
```

The check reports PASS / WARN / BLEED per candidate and flags which SI probes bleed.

### This rule is per-language, not per-batch

**The SI-boundary check is a permanent authoring constraint for all emotionally-heavy skills in every language.** It is not a one-time gate for the English grief_loss batch.

Language-specific requirements:

- **English:** Validate against English SF-1 probes. THRESHOLD = 0.4593, TARGET = 0.40. Baseline frozen at Entry 5 (2026-06-09).
- **Arabic (Khaleeji/MSA):** Arabic anchors must be validated against Arabic SF-1 probes with an Arabic-language BGE-M3 run. Do not assume English bleed scores carry over — BGE-M3's geometry is language-specific. The concept-space distance between grief language and SI language may differ significantly in Arabic (Islamic framing, صبر, inna-lillahi phrasing). Re-measure threshold behavior from scratch; do not inherit the English 0.40 target without validation.
- **Arabizi (Latin-script Arabic):** Do not author Arabizi anchors directly. Arabizi is a normalization-then-route problem (detect → normalize to Arabic or English → route), not an anchor-authoring problem. See `docs/superpowers/plans/2026-06-08-arabizi-language-support.md`.

The skills at risk in every language: grief/loss, relationship ending, estrangement, migration grief, financial-provider-collapse, and any skill touching hopelessness or failure identity. Run the pre-submission check on all of them.

### Sequencing: English first, then Arabic

Complete the English grief/financial re-author and clear the SF1 gate before starting Arabic anchor work. The English batch establishes the method — target margin, tool workflow, "freeflow instead" judgments. Settle the method in the language you can most easily reason about, then apply it to Arabic.

### Post-merge gate

After any anchor merge, `scripts/validate_grief_sf1_boundary.py` is run as a mandatory pre-commit gate. Non-waivable. `SEMANTIC_THRESHOLD = 0.4593` is fixed — do not raise it to paper over bleed.
