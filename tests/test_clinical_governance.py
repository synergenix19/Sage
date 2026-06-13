"""CI governance assertions for clinical content.

These tests fail the build when safety rules or prompt templates are live
without clinical sign-off. They exist to prevent the 2026-06-04 audit
finding from recurring: 46 active rules and 14 prompt templates all had
approved_by=null (full scope: safety/, crisis_content/, cultural/,
cultural_output/, prompt_injection/ — not just safety/).

To clear a failing assertion: get clinical sign-off, then set approved_by
in the relevant JSON file. Do NOT add exceptions to this file.

ENFORCEMENT STATUS (2026-06-05): Convention-based, not automated. Running
`make test-governance` is a team discipline, not a gate. These tests are
excluded from the default `make test` run so a functional regression still
shows as a distinct red. Standing up minimal CI that runs this lane on every
push and blocks merges is the step that converts the guard from "reveals"
to "enforces." Until that exists, the 61 violations are a tracked burn-down,
not a hard gate. Record accordingly — do not write "CI enforces sign-off"
until automated enforcement exists.
"""
import pytest
import json
from pathlib import Path

# All tests in this file run only under `make test-governance` (or -m governance).
# Excluded from the default `make test` run so governance-red and regression-red
# remain distinguishable signals.
pytestmark = pytest.mark.governance

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
    """Walk all JSON rule files and return rule records."""
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
    """Walk all JSON template files and return template records."""
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
            violations.append(f"  {r['rule_id']:22s}  active=true, approved_by=null  [{r['file']}]")

    if violations:
        table = "\n".join(sorted(violations))
        raise AssertionError(
            f"\n{len(violations)} active rule(s) missing clinical sign-off:\n\n"
            f"{'RULE_ID':22s}  STATUS\n"
            f"{'-'*72}\n"
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

    NOTE: This assertion will currently fail for all non-draft templates
    (14 files as of 2026-06-04 audit). That is correct — it should fail.
    Each one needs a clinical sign-off to clear the build.
    """
    violations = []
    for t in _load_all_templates():
        if t["status"] != "draft-pending-review" and t["approved_by"] is None:
            violations.append(f"  {t['template_id']:35s}  [{t['file']}]")

    if violations:
        table = "\n".join(sorted(violations))
        raise AssertionError(
            f"\n{len(violations)} live prompt template(s) missing clinical sign-off:\n\n"
            f"{'TEMPLATE_ID':35s}  FILE\n"
            f"{'-'*72}\n"
            f"{table}\n\n"
            "To clear: obtain sign-off and set approved_by in the template JSON. "
            "Do NOT change status to 'draft-pending-review' to hide the violation."
        )


def test_draft_templates_are_actually_inert():
    """Templates marked draft-pending-review must NOT be in the composer's active routing.

    This is a canary test for the new_skill_unmatched incident (2026-06-04 audit):
    a template was marked 'draft-pending-review' but was actively routed by
    composer.py lines 443-448 when primary_intent=='new_skill' and active_skill_id
    is None. Adding a template to KNOWN_LIVE_TEMPLATES makes this test fail until
    the template is either signed off (approved_by set + status changed from
    'draft-pending-review') or removed from composer routing.
    """
    # Add a template here when it is confirmed wired into composer.py production paths
    # but still has status="draft-pending-review" or approved_by=null.
    # The test FAILS while a template is in this set AND unsigned AND draft — that is
    # the forcing function. Remove from this set ONLY when the template is either
    # signed off (approved_by set + status no longer 'draft-pending-review') or
    # removed from composer routing entirely.
    KNOWN_LIVE_TEMPLATES = {
        "L2_new_skill_unmatched",   # draft-pending-review but wired into production — audit 2026-06-04
        # L2_skill_offer and L2_general_chat removed 2026-06-13: both signed off by the
        # clinical lead (status=approved + approved_by set), so the forcing function is
        # discharged. They are now covered by test_no_live_template_without_approved_by.
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
                f"To clear: either obtain sign-off (set approved_by + change status from "
                f"'draft-pending-review') or remove the template from composer.py routing."
            )
