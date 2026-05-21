# Rules Service Authoring Conventions

Standards for authoring JSON rule files in `src/sage_poc/rules/data/`.

---

## Formatting in action `content` strings

### No em dashes

**NEVER** use em dashes (—) in `action.content` strings.

Rule content is injected directly into the LLM system prompt. Em dashes in prompts are a known source of em-dash mirroring — the model copies punctuation patterns from its instructions into its responses. All prompt-level formatting was standardised to comma-separated prose in the Fixes A–D sprint.

```json
// WRONG
"content": "Use concepts of sabr (صبر — patient perseverance) and tawakkul (توكّل — trust in God)."

// RIGHT
"content": "Use concepts of sabr (صبر, patient perseverance) and tawakkul (توكّل, trust in God)."
```

The `output_gate` `_FORMAT_VIOLATIONS` regex will catch em dashes in the final response, but prevention at the source is required.

### No markdown in content strings

Do not use `**bold**`, `*italic*`, or bullet lists inside `content` strings. The PERSONA explicitly bans markdown in LLM output. Injecting markdown into prompts reintroduces the pattern.

---

## Layer assignment

Use the correct v7 §5.6.1 layer tag in `action.layer`:

| Layer | Purpose | Budget |
|-------|---------|--------|
| `L0` | Static persona (never injected via rules) | Always present |
| `L1` | Crisis/safety override | When triggered |
| `L2` | Intent instruction | ~50 words |
| `L3` | Skill instruction | When skill active |
| `L4` | Knowledge snippet | When info_request |
| `L5` | User context / cultural adaptations | ~100 words |

Cultural rules (`cultural` category) inject at `"layer": "L5"`. Intent instructions inject at `"layer": "L2"`. Never mark a cultural rule as `"L2"`.

---

## Priority for cultural rules

All `cultural` category rules must include `"priority": N` in their `action` dict. Priority controls which rules are included first when multiple rules fire simultaneously and the total injection exceeds the ~150-word L5 budget (lower number = higher priority):

| Priority | Rules |
|----------|-------|
| 1 | CU-SH-001 (shame, most specific emotional signal) |
| 2 | CU-DM-001 (dialect, identity signal) |
| 3 | CU-CS-001 (code-switching, register) |
| 4 | CU-IS-001, CU-RR-001 (specific faith / temporal context) |
| 5 | CU-CO-001 (collectivist, general relational) |
| 6 | CU-RG-001 (generic religious, broadest) |

New rules: assign priority based on specificity. A more specific trigger (narrower condition, more targeted instruction) gets a lower number.

---

## Additive injections

Rules injecting at `L5` must be **additive** relative to the L0 PERSONA baseline. The PERSONA already contains:
- Default Islamic framing (sabr, tawakkul, ibtila)
- Default collectivist framing (hold space for individual feelings AND family roles)

Cultural rules must add **turn-specific guidance** on top of the baseline, not re-state the definitions. The phrase "CONTEXT (this turn):" in the content label signals this.

```json
// WRONG — duplicates L0 PERSONA content
"content": "ISLAMIC CULTURAL CONTEXT: Use concepts of sabr (patience), tawakkul (trust in God), and ibtila (hardship as test). Do not pathologize faith."

// RIGHT — additive, turn-specific
"content": "ISLAMIC CONTEXT (this turn): Apply your Islamic framing to what the user expressed here. If they express spiritual guilt, explore gently without reinforcing shame."
```

---

## Authoring checklist

Before committing any new or edited rule file:

- [ ] No em dashes in any `content` field
- [ ] No markdown formatting in any `content` field
- [ ] Layer tag is correct (`L5` for cultural, `L2` for intent)
- [ ] `priority` field present for `cultural` category rules
- [ ] Content is additive (does not duplicate L0 PERSONA baseline)
- [ ] `authored_by: "sage_clinics"` on every rule
- [ ] At least one test in `tests/test_rules_integration.py` or `tests/test_cultural_output.py` that verifies the rule fires on its trigger condition
- [ ] At least one test that verifies the rule does NOT fire without the trigger
