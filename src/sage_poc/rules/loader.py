# src/sage_poc/rules/loader.py
import json
from pathlib import Path
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
)

_RULE_MODELS: dict[str, type] = {
    "safety": SafetyRule,
    "crisis_content": CrisisContentRule,
    "cultural": CulturalRule,
    "prompt_injection": PromptInjectionRule,
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
                rules.append(rule)
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
