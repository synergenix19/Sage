"""Crisis-copy templating — resolve ``{{crisis_*}}`` placeholders to CRISIS_CONFIG values.

The crisis PHONE NUMBERS have exactly one source of truth: ``config.CRISIS_CONFIG``.
Crisis-copy source files (crisis_content rules, prompt_injection guidance, the L0 persona,
and the crisis skills) carry ``{{crisis_*}}`` placeholders instead of re-embedded literals,
so changing a number is a single-config edit. This module replaces those placeholders at
every load point so the RESOLVED text is what reaches the LLM / user.

Placeholders (all optional in any file; only the ones present are substituted):
  ``{{crisis_number}}``    -> CRISIS_CONFIG["number"]    (e.g. "800 46342")
  ``{{crisis_emergency}}`` -> CRISIS_CONFIG["emergency"] (e.g. "999")
  ``{{crisis_hours}}``     -> CRISIS_CONFIG["hours"]      (e.g. "24/7")
  ``{{crisis_label}}``     -> CRISIS_CONFIG["label"]      (e.g. "MoHAP Counselling Line")

Defense in depth (both required, neither sufficient alone):
  * BOOT GUARD  (assert_crisis_copy_resolves) — every crisis-copy source, in resolved form,
    must contain NO ``{{crisis_`` substring. A missed resolution point or a clinician typo
    (e.g. ``{{crisis_numbr}}``) fails the boot instead of shipping a raw placeholder into a
    crisis message.
  * CONFORMANCE (tests/test_crisis_helpline_conformance.py) — the resolved output actually
    carries CRISIS_CONFIG["number"].
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sage_poc.config import CRISIS_CONFIG

# Any placeholder that shares this prefix but is NOT in _PLACEHOLDERS survives resolution and
# is caught by the boot guard — that is the whole point (unknown/misspelled variable == boot fail).
_UNRESOLVED_MARKER = "{{crisis_"

# Placeholder -> resolved value. Built once from CRISIS_CONFIG at import.
_PLACEHOLDERS: dict[str, str] = {
    "{{crisis_number}}": CRISIS_CONFIG["number"],
    "{{crisis_emergency}}": CRISIS_CONFIG["emergency"],
    "{{crisis_hours}}": CRISIS_CONFIG["hours"],
    "{{crisis_label}}": CRISIS_CONFIG["label"],
}

# Roots scanned by the boot guard. Any crisis-copy JSON under these — present or future —
# is validated, so a new file carrying a broken variable also fails the boot.
_SRC_ROOT = Path(__file__).parent


def resolve_crisis_placeholders(text: str) -> str:
    """Replace every known ``{{crisis_*}}`` placeholder in *text* with its CRISIS_CONFIG value.

    Non-strings pass through unchanged. Unknown ``{{crisis_...}}`` variables are left intact so
    the boot guard can detect them; this function never invents a value for an unknown variable.
    """
    if not isinstance(text, str) or _UNRESOLVED_MARKER not in text:
        return text
    for placeholder, value in _PLACEHOLDERS.items():
        if placeholder in text:
            text = text.replace(placeholder, value)
    return text


def resolve_crisis_placeholders_deep(obj: Any) -> Any:
    """Recursively resolve placeholders in every string within a JSON-shaped structure.

    Dict/list containers are rebuilt; dict KEYS are structural and left untouched. Returns a
    new structure (does not mutate the input).
    """
    if isinstance(obj, str):
        return resolve_crisis_placeholders(obj)
    if isinstance(obj, list):
        return [resolve_crisis_placeholders_deep(item) for item in obj]
    if isinstance(obj, dict):
        return {key: resolve_crisis_placeholders_deep(value) for key, value in obj.items()}
    return obj


def crisis_copy_source_files() -> list[Path]:
    """Every JSON that may carry crisis copy: all rule data, all skills, all prompt templates.

    The boot guard scans this superset (not just the known crisis files) so a broken variable in
    any current or future file surfaces at boot rather than in a live crisis message.
    """
    paths: list[Path] = []
    paths += sorted((_SRC_ROOT / "rules" / "data").glob("**/*.json"))
    paths += sorted((_SRC_ROOT / "skills").glob("*.json"))
    paths += sorted((_SRC_ROOT / "prompts" / "templates").glob("**/*.json"))
    return paths


def crisis_copy_is_templated() -> bool:
    """DEPLOY-PROVENANCE probe: True iff the crisis-copy SOURCE on disk carries a ``{{crisis_``
    placeholder — i.e. the deployed tree is the TEMPLATED version, not the pre-templating literals.

    Exposed at /health/version because crisis templating is BYTE-IDENTICAL: the /health SHA can be
    a stale label and the crisis output looks the same either way, so neither distinguishes a real
    templated deploy from a stale literal one. This inspects the RAW (unresolved) source, which only
    the templated tree carries — a mechanism-level attestation that survives a lying SHA.
    """
    for path in crisis_copy_source_files():
        try:
            if _UNRESOLVED_MARKER in path.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def assert_crisis_copy_resolves(paths: list[Path] | None = None) -> None:
    """FAIL-CLOSED boot guard.

    Load every crisis-copy source in its RESOLVED form and assert NO ``{{crisis_`` substring
    remains anywhere. Raise RuntimeError (the app FAILS TO BOOT) if any does — the backstop for a
    missed resolution point or a clinician editing a variable by mistake. Never serve a raw
    placeholder in a crisis message.

    *paths* is injectable for testing; defaults to crisis_copy_source_files().
    """
    if paths is None:
        paths = crisis_copy_source_files()
    offenders: list[str] = []
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _UNRESOLVED_MARKER in resolve_crisis_placeholders(raw):
            try:
                rel = str(path.relative_to(_SRC_ROOT))
            except ValueError:
                rel = str(path)
            offenders.append(rel)
    if offenders:
        raise RuntimeError(
            "CRISIS COPY BOOT GUARD FAILED — unresolved '{{crisis_*}}' placeholder(s) remain "
            f"after resolution in: {offenders}. A crisis-copy file references a crisis variable "
            "that is not one of "
            f"{sorted(_PLACEHOLDERS)} (likely a typo or a new variable without a resolver mapping). "
            "Refusing to boot rather than serve a raw placeholder in a crisis message. "
            "Fix the variable name in the file, or add its mapping in crisis_copy._PLACEHOLDERS."
        )
