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

**Current threshold: `SEMANTIC_THRESHOLD = 0.459`** (calibrated 2026-05-27, gap=0.0533, cross-cluster). This value is set in `nodes/skill_select.py`.

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

## step_policy: 5 required rules

Every skill must have exactly 5 `step_policy` rules, covering:

1. `emotional_intensity > 7` → `validate_only` (acute distress gate)
2. `resistance > 6, turns 3` → `offer_skill_switch_or_break` (sustained resistance)
3. `engagement < 3, turns 3` → `check_in_micro` (low engagement)
4. `user_stop_request == true` → `exit_warm_closing` (explicit stop)
5. One skill-specific rule (prior exposure, dissociation, hopelessness, obsessive theme, etc.)

The `next_step_id` for `exit_warm_closing` rules must be `"exit"` (string), not `null`.

**`for_turns` field:** Temporal rules (resistance, engagement) use `for_turns` to require a condition to hold across N consecutive turns. Use the canonical `for_turns` field name; the legacy alias `turns` is also accepted but deprecated. `for_turns` is supported for `resistance` (uses `resistance_history` rolling buffer) and `engagement` (uses `engagement_trajectory` 4-turn window). For all other signals, `for_turns` is ignored and the current value is checked.

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
