# src/sage_poc/rules/loader.py
import json
import logging
import re as _re
from pathlib import Path
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    CulturalOutputRule, SkillMatchingRule,
)

_log = logging.getLogger(__name__)

# Characters that normalize_arabic() strips before regex matching.
# A regex pattern containing these will silently match nothing against Arabic text.
_UNNORM_ALEF_RE  = _re.compile(r'[آأإٱ]')        # → bare alef (ا)
_ARABIC_DIACRITIC_RE = _re.compile(r'[ً-ٰ]')  # harakat stripped by strip_arabic_diacritics()
_HAS_ARABIC_RE   = _re.compile(r'[؀-ۿ]')


def _lint_arabic_regex_rule(rule: SafetyRule) -> None:
    """Emit a WARNING if an Arabic regex pattern contains characters that
    normalize_arabic() strips before matching. Silent misses in crisis rules
    are a patient safety risk — they must surface at load time, not at runtime.
    See docs/RULES_AUTHORING_CONVENTIONS.md § Arabic regex patterns.
    """
    for pattern in rule.patterns:
        if not _HAS_ARABIC_RE.search(pattern):
            continue
        if _UNNORM_ALEF_RE.search(pattern):
            _log.warning(
                "SAFETY RULE LINT [%s]: regex pattern contains alef-hamza variant "
                "(آ أ إ ٱ) which normalize_arabic() replaces with bare alef (ا). "
                "This pattern will NEVER match Arabic text. "
                "Replace with bare alef. Pattern: %r",
                rule.rule_id, pattern,
            )
        if _ARABIC_DIACRITIC_RE.search(pattern):
            _log.warning(
                "SAFETY RULE LINT [%s]: regex pattern contains Arabic diacritics (harakat, "
                "U+064B–U+0670) which normalize_arabic() strips before matching. "
                "This pattern will NEVER match Arabic text. "
                "Remove diacritics from the pattern. Pattern: %r",
                rule.rule_id, pattern,
            )

_RULE_MODELS: dict[str, type] = {
    "safety": SafetyRule,
    "crisis_content": CrisisContentRule,
    "cultural": CulturalRule,
    "prompt_injection": PromptInjectionRule,
    "cultural_output": CulturalOutputRule,
    "skill_matching": SkillMatchingRule,
}

_DATA_DIR = Path(__file__).parent / "data"

# Module-level cache — populated on first get_rules() call per category.
# Clear with reload_all() in tests or after hot-editing JSON files.
_cache: dict[str, list] = {}


def load_rules(category: str) -> list:
    """Read all active rules for *category* from JSON files in data/{category}/.
    Files are loaded in alphabetical order. Within each file, rules are appended
    in the order they appear in the "rules" array.
    """
    category_dir = _DATA_DIR / category
    if not category_dir.exists():
        return []

    model_cls = _RULE_MODELS.get(category)
    if model_cls is None:
        raise ValueError(f"Unknown rule category: {category!r}. "
                         f"Known categories: {list(_RULE_MODELS)}")

    rules = []
    for json_file in sorted(category_dir.glob("*.json")):
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        for rule_data in raw.get("rules", []):
            rule = model_cls.model_validate(rule_data)
            if rule.active:
                if isinstance(rule, SafetyRule) and rule.match_type == "regex":
                    _lint_arabic_regex_rule(rule)
                if isinstance(rule, (SafetyRule, SkillMatchingRule)) and rule.approved_by is None:
                    _log.warning(
                        "[rules/loader] UNAPPROVED ACTIVE %s RULE: %s "
                        "(authored_by=%s) — clinical sign-off required before production",
                        rule.category.upper(), rule.rule_id, rule.authored_by,
                    )
                rules.append(rule)
    if category == "skill_matching":
        seen_priorities: dict[int, str] = {}
        for rule in rules:
            if rule.priority in seen_priorities:
                # Stable sort below preserves file order on ties, so first-match-wins
                # still resolves duplicates by file order — fragile for clinician-
                # authored rules, hence the warning.
                _log.warning(
                    "[rules/loader] skill_matching rules %s and %s share priority %d; "
                    "first-match-wins resolves by file order, which is fragile for "
                    "clinician-authored rules — assign distinct priorities",
                    seen_priorities[rule.priority], rule.rule_id, rule.priority,
                )
            else:
                seen_priorities[rule.priority] = rule.rule_id
        # Pre-sort by ascending priority once at load time; the evaluator iterates
        # in list order on every call (hot path) and relies on this ordering.
        rules.sort(key=lambda r: r.priority)
    return rules


def get_rules(category: str) -> list:
    """Return cached rules for *category*, loading from disk on first access."""
    if category not in _cache:
        _cache[category] = load_rules(category)
    return _cache[category]


def reload_all() -> None:
    """Invalidate the rule cache. Use in tests after writing fixture files,
    or after hot-editing JSON rule documents in development."""
    _cache.clear()
