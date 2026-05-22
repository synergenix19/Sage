from __future__ import annotations
from sage_poc.rules.schemas import (
    SafetyRule, CrisisContentRule, CulturalRule, PromptInjectionRule,
    CulturalOutputRule,
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


def _apply_suppressions(result: EvalResult) -> EvalResult:
    """Post-filter: mark crisis_flag actions suppressed when a crisis_suppress rule fired
    on the same or overlapping text span.

    Suppression is span-scoped: a FPE rule that fires on "killing it" at position 4
    must not suppress a genuine SI rule that fired on "no reason to live" at position 44.
    Both must be present in the same result for message-level analysis, but only the
    overlapping SI match is suppressed.

    If span info is unavailable (matched_span is None on either side), falls back to
    message-level suppression as a conservative default.
    """
    suppress_rules = [r for r in result.fired if r.action.get("type") == "crisis_suppress"]
    if not suppress_rules:
        return result

    for si_rule in result.fired:
        if si_rule.action.get("type") != "crisis_flag":
            continue
        flag_id = si_rule.action.get("flag_id")
        si_span = si_rule.matched_span

        for fpe_rule in suppress_rules:
            if flag_id not in fpe_rule.action.get("suppresses", []):
                continue
            fpe_span = fpe_rule.matched_span
            if si_span is None or fpe_span is None:
                # Span unknown on either side: cannot determine overlap.
                # Do NOT suppress — missing position data is not grounds for hiding a
                # crisis signal. The safe default is to let the flag through.
                continue
            # Suppress only if the spans overlap
            if max(fpe_span[0], si_span[0]) < min(fpe_span[1], si_span[1]):
                si_rule.suppressed = True
                break

    return result


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

        matched = False
        for pattern in rule.patterns:
            if matched:
                break
            # For "any" rules: route Arabic-script patterns to norm_ar, others to norm_en
            is_arabic_pattern = lang == "ar" or (
                lang == "any" and any('؀' <= ch <= 'ۿ' for ch in pattern)
            )
            text_to_check = norm_ar if is_arabic_pattern else norm_en

            if not text_to_check:
                continue

            pattern_norm = (normalize_arabic(pattern) if is_arabic_pattern
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
                matched_span=(idx, idx + len(pattern_norm)),
            ))
            matched = True

    return _apply_suppressions(result)


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
    Accumulate all cultural rules whose trigger condition matches.

    context keys:
      text (str)            -- user message (English)
      text_ar (str | None)  -- original Arabic text (if language == "ar")
      language (str)        -- "en" | "ar"
      code_switch (bool)    -- True when raw_message contains both Arabic and Latin characters
    """
    text_lower = normalize_text(context.get("text", ""))
    text_ar = context.get("text_ar") or ""
    norm_ar = normalize_arabic(text_ar) if text_ar else ""
    language = context.get("language", "en")
    code_switch: bool = context.get("code_switch", False)

    result = EvalResult()
    for rule in rules:
        if rule.language not in ("any", language):
            continue

        if rule.trigger_type == "code_switch":
            if code_switch:
                result.fired.append(FiredRule(
                    rule_id=rule.rule_id,
                    version=rule.version,
                    action=rule.action,
                ))
            continue

        # Empty trigger_keywords = language-only trigger: fire for every message in
        # the rule's target language without inspecting content. This lets cultural
        # baseline rules (e.g. "always respond in Arabic") fire unconditionally.
        if not rule.trigger_keywords:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))
            continue

        # trigger_type == "keyword_match" (default)
        matched = False
        for kw in rule.trigger_keywords:
            is_arabic_kw = any('؀' <= ch <= 'ۿ' for ch in kw)
            if is_arabic_kw:
                if norm_ar and normalize_arabic(kw) in norm_ar:
                    matched = True
                    break
            else:
                if kw.lower() in text_lower:
                    matched = True
                    break
        if matched:
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
      text (str)                      — user message (English translation)
      text_ar (str | None)            — original Arabic text (None if message was English)
      clinical_flags (list[str])      — e.g. ["substance_use"]
      primary_intent (str | None)
      secondary_intent (str | None)
    """
    text_lower = normalize_text(context.get("text", ""))
    text_ar_raw = context.get("text_ar") or ""
    norm_ar = normalize_arabic(text_ar_raw) if text_ar_raw else ""
    clinical_flags: list[str] = context.get("clinical_flags", [])
    primary_intent: str | None = context.get("primary_intent")
    secondary_intent: str | None = context.get("secondary_intent")
    session_flags: list[str] = context.get("session_flags", [])

    result = EvalResult()
    for rule in rules:
        fired = False
        if rule.trigger_type == "keyword_match":
            # English keywords matched against English text
            en_fired = any(
                kw.lower() in text_lower
                for kw in rule.trigger_keywords
                if not any('؀' <= c <= 'ۿ' for c in kw)
            )
            # Arabic keywords matched against original Arabic text
            ar_fired = bool(norm_ar) and any(
                normalize_arabic(kw) in norm_ar
                for kw in rule.trigger_keywords
                if any('؀' <= c <= 'ۿ' for c in kw)
            )
            fired = en_fired or ar_fired
        elif rule.trigger_type == "flag_present":
            fired = rule.trigger_value in clinical_flags
        elif rule.trigger_type == "intent_match":
            fired = rule.trigger_value in (primary_intent, secondary_intent)
        elif rule.trigger_type == "secondary_intent_present":
            fired = secondary_intent is not None
        elif rule.trigger_type == "session_flag_present":
            fired = rule.trigger_value in session_flags

        if fired:
            result.fired.append(FiredRule(
                rule_id=rule.rule_id,
                version=rule.version,
                action=rule.action,
            ))

    return result


def _eval_cultural_output(rules: list[CulturalOutputRule], context: dict) -> EvalResult:
    """
    Evaluate post-generation cultural output rules.

    Fires when a rule's condition is met AND the response violates the check type:
      blocklist          -- any pattern found in response -> violation
      allowlist_required -- no pattern found in response -> violation

    context keys:
      response_text (str)         -- generated English response text
      message_en (str)            -- original user message in English
      clinical_flags (list[str])  -- active clinical flags from state
    """
    response_text = normalize_text(context.get("response_text", ""))
    if not response_text:
        return EvalResult()
    message_en = normalize_text(context.get("message_en", ""))
    clinical_flags: list[str] = context.get("clinical_flags", [])

    result = EvalResult()
    for rule in rules:
        condition_met = False
        if rule.condition_type == "always":
            condition_met = True
        elif rule.condition_type == "keyword_in_message":
            condition_met = any(kw.lower() in message_en for kw in rule.condition_keywords)
        elif rule.condition_type == "flag_present":
            condition_met = rule.condition_value in clinical_flags

        if not condition_met:
            continue

        violated = False
        if rule.check_type == "blocklist":
            violated = any(p.lower() in response_text for p in rule.patterns)
        elif rule.check_type == "allowlist_required":
            violated = not any(p.lower() in response_text for p in rule.patterns)

        if violated:
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
    "cultural_output": _eval_cultural_output,
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
