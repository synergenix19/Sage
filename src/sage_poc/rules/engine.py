from __future__ import annotations
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    EvalResult, FiredRule,
)
from sage_poc.rules.loader import get_rules
from sage_poc.rules.normalize import normalize_text, normalize_arabic

_NEGATION_WORDS = frozenset([
    "don't", "dont", "do not", "not", "never", "no", "cannot", "can't", "cant",
    "لا", "ما", "مو", "مش", "مب", "ليس",
])
_NEGATION_WINDOW = 6


def _has_negation(text_lower: str, match_start: int) -> bool:
    """True if any negation word appears in the _NEGATION_WINDOW tokens before match_start."""
    prefix_tokens = text_lower[:match_start].split()
    window = prefix_tokens[-_NEGATION_WINDOW:]
    return any(neg in window for neg in _NEGATION_WORDS)


def _eval_safety(rules: list[SafetyRule], context: dict) -> EvalResult:
    """
    Evaluate safety rules. All matching rules fire (OR-semantics for crisis detection,
    accumulate-semantics for clinical flags — the calling node splits by action.type).

    context keys:
      text_en (str)         — English text (raw message if English; translated if Arabic)
      text_ar (str | None)  — Original Arabic text (None if message was English)
      language (str)        — "en" | "ar"
    """
    text_en = context.get("text_en", "")
    text_ar = context.get("text_ar") or ""
    language = context.get("language", "en")

    norm_en = normalize_text(text_en)
    norm_ar = normalize_arabic(text_ar) if text_ar else ""

    result = EvalResult()

    for rule in rules:
        lang = rule.language
        if lang == "ar":
            text_to_check = norm_ar
        elif lang == "en":
            text_to_check = norm_en
        else:  # "any" — check English path (already translated)
            text_to_check = norm_en

        if not text_to_check:
            continue

        for pattern in rule.patterns:
            pattern_norm = (normalize_arabic(pattern) if lang == "ar"
                            else normalize_text(pattern))
            idx = text_to_check.find(pattern_norm)
            if idx == -1:
                continue
            if "negation_check" in rule.modifiers and _has_negation(text_to_check, idx):
                continue
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))
            break  # one pattern match per rule is enough

    return result


def _eval_crisis_content(rules: list[CrisisContentRule], context: dict) -> EvalResult:
    """
    Select the crisis content rule matching locale + crisis_level.
    Returns at most one fired rule (locale-select strategy: first match wins).

    context keys:
      language (str)      — "en" | "ar"
      crisis_level (str)  — "acute" | "extended"
    """
    language = context.get("language", "en")
    crisis_level = context.get("crisis_level", "acute")
    locale = f"{language}_uae"

    result = EvalResult()
    for rule in rules:
        if rule.locale == locale and rule.crisis_level == crisis_level:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))
            break  # locale-select: first match wins

    return result


def _eval_cultural(rules: list[CulturalRule], context: dict) -> EvalResult:
    """
    Accumulate all cultural rules whose trigger_keywords appear in the message text.

    context keys:
      text (str)      — user message (English)
      language (str)  — "en" | "ar"
    """
    text_lower = normalize_text(context.get("text", ""))
    language = context.get("language", "en")

    result = EvalResult()
    for rule in rules:
        if rule.language not in ("any", language):
            continue
        if any(kw.lower() in text_lower for kw in rule.trigger_keywords):
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result


def _eval_prompt_injection(rules: list[PromptInjectionRule], context: dict) -> EvalResult:
    """
    Accumulate all prompt injection rules whose trigger condition matches.

    context keys:
      text (str)                      — user message (English)
      clinical_flags (list[str])      — e.g. ["substance_use"]
      primary_intent (str | None)
      secondary_intent (str | None)
    """
    text_lower = normalize_text(context.get("text", ""))
    clinical_flags: list[str] = context.get("clinical_flags", [])
    primary_intent: str | None = context.get("primary_intent")
    secondary_intent: str | None = context.get("secondary_intent")

    result = EvalResult()
    for rule in rules:
        fired = False
        if rule.trigger_type == "keyword_match":
            fired = any(kw.lower() in text_lower for kw in rule.trigger_keywords)
        elif rule.trigger_type == "flag_present":
            fired = rule.trigger_value in clinical_flags
        elif rule.trigger_type == "intent_match":
            fired = rule.trigger_value in (primary_intent, secondary_intent)
        elif rule.trigger_type == "secondary_intent_present":
            fired = secondary_intent is not None

        if fired:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result


_EVAL_DISPATCH = {
    "safety": _eval_safety,
    "crisis_content": _eval_crisis_content,
    "cultural": _eval_cultural,
    "prompt_injection": _eval_prompt_injection,
}


def evaluate(category: str, context: dict) -> EvalResult:
    """
    Evaluate all active rules in *category* against *context*.
    Returns EvalResult containing every fired rule and its action dict.

    The engine is stateless — it never reads or writes SageState.
    """
    rules = get_rules(category)
    eval_fn = _EVAL_DISPATCH.get(category)
    if eval_fn is None:
        raise ValueError(
            f"Unknown rule category: {category!r}. "
            f"Known categories: {list(_EVAL_DISPATCH)}"
        )
    return eval_fn(rules, context)
