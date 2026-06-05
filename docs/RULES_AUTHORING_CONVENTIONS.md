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

## Arabic regex patterns (safety rules)

**This section applies only to `safety` category rules with `"match_type": "regex"`.**

Arabic text is passed through `normalize_arabic()` before regex matching. This pipeline:

1. Strips invisible characters (ZWSP, ZWNJ, ZWJ, BOM)
2. Applies NFKC Unicode normalization
3. Removes Arabic diacritics (harakat: fatha, damma, kasra, sukun, shadda — U+064B–U+0670)
4. Normalizes alef variants to bare alef: `آ أ إ ٱ` → `ا`
5. Lowercases

**Consequence:** A regex pattern containing `أ` will never match the normalized text `ا`. The mismatch is silent — no error, no match, no crisis signal. This is a patient safety risk.

### Rule: Arabic regex patterns must use normalized forms

| Use | Instead of | Reason |
|-----|-----------|--------|
| `ا` (bare alef, U+0627) | `أ` `إ` `آ` `ٱ` | Alef variants are normalized away |
| No harakat | `مَات` | Diacritics are stripped |

```json
// WRONG — alef-hamza-above will never match normalized text
"patterns": ["أريد أن أموت"]

// RIGHT — normalized form matches normalized text
"patterns": ["اريد ان اموت"]
```

### Loader lint check

The rule loader automatically warns at startup when a loaded `safety` regex rule contains unnormalized Arabic characters:

```
SAFETY RULE LINT [rule-id]: regex pattern contains alef-hamza variant (آ أ إ ٱ)
which normalize_arabic() replaces with bare alef (ا). This pattern will NEVER
match Arabic text. Replace with bare alef. Pattern: '...'
```

If you see this warning, the rule is currently non-functional for Arabic text. Fix the pattern before deploying.

### Verifying normalization

```python
from sage_poc.rules.normalize import normalize_arabic
print(normalize_arabic("أريد أن أموت"))
# اريد ان اموت
```

Write your pattern against this output, not against the original text.

---

## S3 crisis phrase corpus authoring (`crisis_phrases.json`)

The S3 tier (BGE-M3 semantic) uses `src/sage_poc/safety/crisis_phrases.json` as its embedding anchor set. Mis-authored phrases here create false positives that cannot be suppressed by threshold adjustment — they propagate silently to every user session.

### Single-clause rule

**Every phrase must be single-clause, and the SI signal must dominate the whole phrase.**

Multi-clause phrases (two independent ideas joined by "but", "and", or temporal connectors) will cause false positives when the first clause matches therapeutic language and the SI signal is only in the second clause. BGE-M3 encodes the full phrase as a blend; acceptance-framed first clauses drag the embedding toward therapeutic acceptance space.

Examples of failures this rule prevents:
- `"I keep making room for these feelings but I do not see why I should keep going"` — the acceptance-framing in the first clause caused ACT defusion instructions to score 0.84 against the corpus. Removed Jun 2026.
- `"there is a quiet that comes with accepting nothing will change"` — acceptance language in first clause caused serenity-prayer form to score 0.92. Removed Jun 2026.

**The fix is NOT to delete the SI content.** Rewrite as a single clause centered on the SI signal:
```
# Wrong (multi-clause, acceptance + SI)
"there is a quiet that comes with accepting nothing will change"

# Right (single clause, SI signal dominates)
"accepting nothing will change feels like a reason to stop trying"
```

### FP regression check

After adding or editing any phrase in `crisis_phrases.json`, run `scripts/calibrate_s3_threshold.py` and verify:

1. All `GATE_SUPPRESS` phrases still score below the threshold — these include acceptance-framed therapeutic phrases. If a new corpus phrase pulls any suppress phrase above threshold, the phrase or threshold is wrong.
2. The gap (min_catch − max_suppress) remains ≥ 0.05. A narrower gap means the corpus is drifting toward therapeutic language space.

The suppress set includes acceptance-framed phrases specifically to guard against this class of authoring failure. Do not remove them from `GATE_SUPPRESS`.

### Authoring checklist for corpus entries

Before adding any phrase to `crisis_phrases.json`:

- [ ] Single clause (no "but", "and", or temporal connectors joining two ideas)
- [ ] SI signal present in the whole phrase, not just the end
- [ ] Not a paraphrase of an existing S1 keyword pattern (adds no new semantic territory)
- [ ] Re-run `scripts/calibrate_s3_threshold.py` and confirm gap ≥ 0.05 and all GATE_SUPPRESS pass
- [ ] Re-run `pytest -m "cradle and not slow"` — specificity ≥ 95% must be preserved
- [ ] Clinical reviewer sign-off

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
- [ ] **Arabic regex rules:** patterns use normalized Arabic (bare alef `ا`, no harakat)
