# approved_by / active CI Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CI-enforced pytest assertion that fails the build whenever any safety rule or prompt template is active/live but lacks a clinical sign-off (`approved_by: null`). This converts 17 ungoverned live rules from an invisible state into a red build that forces the sign-off conversation before any future rule ships.

**Architecture:** A single new test file `tests/test_clinical_governance.py` that walks all rule JSON files in `rules/data/` and all template JSON files in `prompts/templates/` and asserts the approved_by invariant. No application code changes. No migrations. Runs in the default (non-slow, non-integration) CI tier. Fails loudly with a table showing every violating rule_id / template_id.

**Tech Stack:** Python 3.12, pytest, json, pathlib. No external services.

**Why this comes before individual fixes:** Fixing CRITICAL-1's "dead serious" FP without this guard means the next rogue pattern will ship green. The CI guard is what makes "we'll fix the governance gap" real rather than aspirational. **46** active rules (not 17 — that was safety/ only; full scope includes crisis_content, cultural, cultural_output, prompt_injection) plus **14** prompt templates all have `approved_by: null`. Each one becomes a red build entry as soon as this lands; each forces a sign-off conversation to clear the build.

---

## Files changed

| File | Change |
|---|---|
| `tests/test_clinical_governance.py` | Create — contains all three assertions below |

---

## Task 1 — CI guard: no active rule may have approved_by null

**What counts as "active":** In rule JSON files, a rule object has `"active": true`. In prompt template JSON files, a template is "live" when `"status"` is NOT `"draft-pending-review"` AND `"approved_by"` is null. (Templates with `status: "draft-pending-review"` are already supposed to be inert — but as the audit found, `new_skill_unmatched` is actually live despite this status. That second check is Task 2.)

**Files:**
- Create: `tests/test_clinical_governance.py`

- [ ] **Step 1.1: Create the test file with the rules governance assertion**

Create `tests/test_clinical_governance.py`:

```python
"""CI governance assertions for clinical content.

These tests fail the build when safety rules or prompt templates are live
without clinical sign-off. They exist to prevent the 2026-06-04 audit
finding from recurring: 46 active rules and 14 prompt templates all had
approved_by=null (full scope: safety/, crisis_content/, cultural/,
cultural_output/, prompt_injection/ — not just safety/).

To clear a failing assertion: get clinical sign-off, then set approved_by
in the relevant JSON file. Do NOT add exceptions to this file.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RULES_DATA = REPO_ROOT / "src" / "sage_poc" / "rules" / "data"
TEMPLATES_DIR = REPO_ROOT / "src" / "sage_poc" / "prompts" / "templates"

# Rules that are explicitly approved_by: null but KNOWN-INACTIVE (pending sign-off).
# These are allowed to stay null — they cannot be set active=true until approved.
# When a rule is activated, remove it from this set (the build will then fail until
# approved_by is populated).
_KNOWN_INACTIVE_NULL = {
    "CF-006",        # psychotic_disclosure — inactive pending clinician sign-off
    "FPE-AR-002",    # Gulf frustration idioms — inactive pending native-speaker review
    "FPE-EN-002",    # Work/burnout hyperbole — inactive pending clinician review
    "FPE-EN-003",    # Digital disconnection — inactive pending clinician review
}


def _load_all_rules() -> list[dict]:
    """Walk all JSON rule files and return (rule_id, active, approved_by) triples."""
    records = []
    for json_file in RULES_DATA.rglob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rules = data.get("rules", [])
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            records.append({
                "rule_id":    rule.get("rule_id", "<no-id>"),
                "active":     rule.get("active", False),
                "approved_by": rule.get("approved_by"),
                "file":       str(json_file.relative_to(REPO_ROOT)),
            })
    return records


def _load_all_templates() -> list[dict]:
    """Walk all JSON template files and return (template_id, status, approved_by) triples."""
    records = []
    for json_file in TEMPLATES_DIR.rglob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        records.append({
            "template_id": data.get("template_id", json_file.stem),
            "status":      data.get("status", ""),
            "approved_by": data.get("approved_by"),
            "file":        str(json_file.relative_to(REPO_ROOT)),
        })
    return records


def test_no_active_rule_without_approved_by():
    """Every rule with active=true must have a non-null approved_by.

    To fix: get clinical sign-off and set approved_by in the rule JSON.
    Do NOT add rule_ids to _KNOWN_INACTIVE_NULL — that list is for inactive rules only.
    """
    violations = []
    for r in _load_all_rules():
        if r["active"] and r["approved_by"] is None and r["rule_id"] not in _KNOWN_INACTIVE_NULL:
            violations.append(f"  {r['rule_id']:20s}  active=true, approved_by=null  [{r['file']}]")

    if violations:
        table = "\n".join(violations)
        raise AssertionError(
            f"\n{len(violations)} active rule(s) missing clinical sign-off:\n\n"
            f"{'RULE_ID':20s}  STATUS\n"
            f"{'-'*70}\n"
            f"{table}\n\n"
            "To clear: obtain sign-off from the clinical lead and set approved_by "
            "in the rule JSON. Do NOT add to _KNOWN_INACTIVE_NULL."
        )


def test_no_live_template_without_approved_by():
    """Every prompt template that is not explicitly draft-pending-review must have approved_by.

    'draft-pending-review' status is meant to mark templates as inert,
    but as of 2026-06-04 audit, new_skill_unmatched is active in the production
    code path despite this status. This test catches templates that are
    actually loaded by the production composer without clinical sign-off.

    NOTE: This assertion will currently fail for ALL templates (approved_by=null
    on all 16 template files as of 2026-06-04 audit). That is correct — it should
    fail. Each one needs a clinical sign-off to clear the build.
    """
    violations = []
    for t in _load_all_templates():
        if t["status"] != "draft-pending-review" and t["approved_by"] is None:
            violations.append(f"  {t['template_id']:30s}  approved_by=null  [{t['file']}]")

    if violations:
        table = "\n".join(violations)
        raise AssertionError(
            f"\n{len(violations)} live prompt template(s) missing clinical sign-off:\n\n"
            f"{'TEMPLATE_ID':30s}  STATUS\n"
            f"{'-'*70}\n"
            f"{table}\n\n"
            "To clear: obtain sign-off and set approved_by in the template JSON. "
            "Do NOT change status to 'draft-pending-review' to hide the violation."
        )


def test_draft_templates_are_actually_inert():
    """Templates marked draft-pending-review must NOT be in the composer's active routing.

    This is a canary test for the new_skill_unmatched incident: a template was
    marked 'draft-pending-review' but was actively routed by composer.py.
    This test checks the known-live templates list against the draft list.

    Add to KNOWN_LIVE_TEMPLATES only when a template is explicitly wired into
    composer.py AND has obtained approved_by sign-off (after which it should also
    have its status changed from 'draft-pending-review' to a non-draft value).
    """
    # Templates confirmed wired into composer.py production paths.
    # ADD a template here when it is actively routed by composer.py but still
    # has status="draft-pending-review" or approved_by=null — adding it makes
    # this test FAIL, which is the forcing function for the sign-off.
    # REMOVE a template only when: (a) it is removed from composer.py routing,
    # OR (b) approved_by is set AND status is changed from "draft-pending-review".
    # The new_skill_unmatched template is the canonical example of this scenario:
    # it is marked draft-pending-review but is actively routed by composer.py
    # lines 443-448 when primary_intent=="new_skill" and active_skill_id is None.
    KNOWN_LIVE_TEMPLATES = {
        "L2_new_skill_unmatched",   # draft-pending-review but wired into production — audit finding 2026-06-04
    }

    for t in _load_all_templates():
        if (
            t["template_id"] in KNOWN_LIVE_TEMPLATES
            and t["status"] == "draft-pending-review"
            and t["approved_by"] is None
        ):
            raise AssertionError(
                f"Template {t['template_id']!r} is in KNOWN_LIVE_TEMPLATES "
                f"(wired into production routing) but still marked draft-pending-review "
                f"with approved_by=null. This is the new_skill_unmatched incident pattern.\n"
                f"File: {t['file']}\n"
                f"Either obtain sign-off (set approved_by + update status) or remove "
                f"the template from composer.py routing."
            )
```

- [ ] **Step 1.2: Run the new test to confirm it fails with the expected violations**

```bash
cd /Users/knowledgebase/Documents/Sage/sage-poc
uv run pytest tests/test_clinical_governance.py -v 2>&1 | tail -40
```

Expected output shape:
- `test_no_active_rule_without_approved_by` FAILS with **46 violations** (verified 2026-06-04 by direct scan: covers safety/, crisis_content/, cultural/, cultural_output/, prompt_injection/ — all rule categories, not just safety)
- `test_no_live_template_without_approved_by` FAILS with **14 violations** (L0, L1, L2×10, L3, L4, L5 — all non-draft templates unsigned)
- `test_draft_templates_are_actually_inert` FAILS with **1 violation** — `L2_new_skill_unmatched` (wired into composer.py but still marked draft-pending-review with approved_by=null)

Total: 3 tests failing, 61 violations to clear via clinical sign-off. These numbers are the verified baseline as of 2026-06-04; recount if new rules or templates were added.

- [ ] **Step 1.3: Verify the _KNOWN_INACTIVE_NULL set is correct**

For each rule_id in `_KNOWN_INACTIVE_NULL`, verify `"active": false` in the JSON:

```bash
grep -r '"CF-006"\|"FPE-AR-002"\|"FPE-EN-002"\|"FPE-EN-003"' src/sage_poc/rules/data/safety/ | grep '"active"'
```

Expected: Each shows `"active": false`. If any shows `"active": true`, remove it from `_KNOWN_INACTIVE_NULL` — an active rule must have `approved_by` set.

- [ ] **Step 1.4: Commit the CI guard — leave it red**

```bash
git add tests/test_clinical_governance.py
git commit -m "$(cat <<'EOF'
test(governance): CI guard for approved_by on all active rules and live templates

Adds tests/test_clinical_governance.py with three assertions:
  1. No active rule may have approved_by=null (46 violations on first run — covers
     safety/, crisis_content/, cultural/, cultural_output/, prompt_injection/)
  2. No non-draft prompt template may have approved_by=null (14 violations)
  3. No template in KNOWN_LIVE_TEMPLATES may be draft-pending-review + unsigned
     (1 violation: L2_new_skill_unmatched, wired into composer.py)

61 total violations. Each cleared by clinical sign-off + setting approved_by in JSON.
Build stays red until the clinical sign-off process clears each one.
Do NOT add exceptions to this file to get green.

Baseline verified 2026-06-04 by direct walker scan against all rule categories.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

The build is intentionally red after this commit. This is correct. The violations are real. Clearing them is the clinical team's job.

---

## Task 2 — How to clear the build: sign-off ceremony per rule/template

This section documents the process for clearing the build after Task 1 lands. It is not engineering work — it is a governance checklist for the clinical lead.

**For each active safety rule with approved_by=null:**

1. Clinical lead reviews the `patterns` array in the rule JSON
2. Clinical lead runs (or reviews results of): `uv run pytest tests/test_rules_safety.py -v`
3. Clinical lead signs off by setting `"approved_by": "<name>_<YYYY-MM-DD>"` in the JSON
4. Engineer commits the sign-off: `git add <file> && git commit -m "sign-off: <rule_id> approved by <name>"`
5. Build goes green for that rule

**For each prompt template with approved_by=null:**

1. Clinical lead reviews the `content` field in the template JSON
2. Clinical lead sets `"approved_by": "<name>_<YYYY-MM-DD>"`
3. Engineer commits

**Recommended sign-off order (highest clinical risk first):**

Tier 1 — Crisis and SI detection (any miss here is a patient safety failure):
1. SK-EN-002 (passive SI English — the `approved_by` sign-off IS the resolution of the 2 clinical_decision_pending FP tests. They are the same clinical conversation, not sequential steps. The clinician reads the FP boundary tests, makes the Option A/B decision, and sets `approved_by` in that same commit. Do not treat "resolve FP tests" and "set approved_by" as separate prerequisites — the first IS the second.)
2. SK-EN-001, SK-AR-001, SK-AZ-001 (primary SI + Arabic SI — these have no `approved_by` field at all, not just null; add the field when signing)
3. SK-AZ-001, SK-AZ-002 (Arabizi transliteration SI)
4. SK-EN-003, SK-EN-004, SK-EN-005 (self-harm method, third-party crisis, additional passive SI)
5. SK-AR-002, SK-AR-003 (Gulf Arabic passive SI, emotional exhaustion idioms)
6. CK-CH-001, CK-CH-002 (command hallucination)

Tier 2 — Clinical flags (these gate referral and monitoring pathways):
7. CF-001 through CF-005 (clinical flag adaptations — these inject into prompts when flags are set)

Tier 3 — Crisis content (response library for crisis path):
8. CC-EN-001, CC-EN-002, CC-AR-001

Tier 4 — Prompt injection and cultural rules (affect every user interaction):
9. L0_persona.json (persona — highest frequency, every turn)
10. L2_intents/crisis.json
11. Remaining L2 intent templates (10 files)
12. L3_skill_wrapper, L4_knowledge, L5_user_context, L1_history
13. PI-* rules (prompt injection adaptations — 9 rules)
14. CU-* rules (cultural injection — 8 rules)
15. CUO-* rules (cultural output gate — 5 rules)
16. L2_new_skill_unmatched (resolve: either sign off + change status from draft-pending-review, or remove from composer routing)
