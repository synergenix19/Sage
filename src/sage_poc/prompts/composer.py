from __future__ import annotations
import re
import logging
from sage_poc.state import SageState
from sage_poc.skills.schema import SkillStep, load_skill
from sage_poc.rules import engine as rules_engine
from sage_poc.knowledge import lookup_knowledge
from .loader import get_template, get_intent_template
from .tokens import count_words, count_words_in_parts

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F9FF"
    r"\U00002600-\U000027BF"
    r"\U0001FA00-\U0001FAFF"
    r"\U0000FE00-\U0000FE0F"
    r"\U0000200D"
    r"]"
)

_log = logging.getLogger(__name__)


def _esc(s: str) -> str:
    return s.replace("{", "{{").replace("}", "}}")


def _sanitize_assistant_turn(text: str) -> str:
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)          # ***bold-italic*** -> text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)              # **bold** -> bold
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text) # *italic* -> italic
    text = text.replace("—", ", ")
    text = _EMOJI_RE.sub("", text)
    return text


def _is_arabic(text: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", text))


def _select_few_shot_examples(
    examples: list[str],
    language: str,
    intensity: int,
) -> list[str]:
    if not examples:
        return []
    if len(examples) == 1:
        return [examples[0]]
    if language == "ar":
        arabic = [e for e in examples if _is_arabic(e)]
        non_arabic = [e for e in examples if not _is_arabic(e)]
        if not arabic:
            _log.warning("_select_few_shot_examples: language=ar but no Arabic examples in skill step")
        if arabic:
            return [arabic[0], non_arabic[0]] if non_arabic else arabic[:2]
    return list(examples[:2])


def _build_l3_skill_block(
    skill_name: str,
    step: SkillStep,
    language: str,
    intensity: int,
) -> str:
    tmpl = get_template("L3_skill_wrapper")
    selected = _select_few_shot_examples(step.examples, language, intensity)
    few_shot_lines = "\n".join(f'- "{e}"' for e in selected)
    contraindication_block = (
        f"Important: {step.contraindications}\n\n"
        if step.contraindications
        else ""
    )
    technique_desc = (step.technique_description + " ") if step.technique_description else ""
    content = tmpl.content.format(
        skill_name=_esc(skill_name),
        step_goal=_esc(step.goal),
        technique_name=_esc(step.technique),
        technique_description=_esc(technique_desc),
        tone_instruction=_esc(step.tone),
        contraindication_block=_esc(contraindication_block),
        few_shot_block=_esc(few_shot_lines),
    )
    _log.debug("L3_skill_wrapper@%s loaded", tmpl.version)
    return content


_INTENSITY_GUIDANCE: dict[str, str] = {
    "low": "The user's distress is mild. A lighter touch is appropriate.",
    "mid": "The user is moderately engaged. Be present and attentive.",
    "high": "The user is significantly distressed. Prioritise validation. Hold space before offering any guidance.",
}


def _intensity_guidance(intensity: int) -> str:
    if intensity <= 3:
        return _INTENSITY_GUIDANCE["low"]
    if intensity <= 6:
        return _INTENSITY_GUIDANCE["mid"]
    return _INTENSITY_GUIDANCE["high"]


def _build_l2_intent_block(
    primary_intent: str | None,
    intensity: int,
    secondary_intent: str | None = None,
    variant: str | None = None,
) -> str:
    intent = primary_intent or "general_chat"
    tmpl = get_intent_template(intent, variant=variant)
    if tmpl is None:
        tmpl = get_intent_template("general_chat", variant=variant)
    if tmpl is None:
        raise ValueError(
            f"No L2 template found for intent '{intent}' and 'general_chat' fallback is also missing."
        )
    guidance = _intensity_guidance(intensity)
    variables: dict[str, str] = {
        "intensity": str(intensity),
        "intensity_guidance": guidance,
    }
    content = tmpl.content
    for var in tmpl.variables:
        content = content.replace("{" + var + "}", variables.get(var, ""))
    if secondary_intent:
        content += f" (blended with: {secondary_intent})"
    _log.debug("L2_%s@%s loaded (requested: %s)", tmpl.intent, tmpl.version, intent)
    return content


_FLAG_DESCRIPTIONS: dict[str, str] = {
    "substance_use": "This user has disclosed substance use. Use a motivational interviewing (MI) approach: non-judgmental, no lecturing.",
    "trauma_indicator": "This user has indicated trauma history. Be sensitive and do not probe for details.",
    "eating_concern": "This user has disclosed eating concerns. Do not comment on food, weight, or body image.",
    "medication_mention": "This user has mentioned medication. Do not advise on dosing or stopping medication.",
    "third_party_si": "This user has expressed concern about someone else's safety. Take this seriously.",
    "escalating_distress": "This user's distress has been elevated across multiple turns.",
}


def _build_l4_knowledge_block(snippet: str | None, variant: str | None = None) -> str | None:
    if not snippet:
        return None
    tmpl = get_template("L4_knowledge", variant=variant)
    passages = f"[1] {snippet}"
    content = tmpl.content.format(passages=_esc(passages))
    _log.debug("L4_knowledge@%s loaded", tmpl.version)
    return content


def _build_l5_user_context_block(
    clinical_flags: list[str],
    intensity: int,
    engagement: int,
    variant: str | None = None,
) -> str | None:
    relevant = [f for f in clinical_flags if f in _FLAG_DESCRIPTIONS]
    if not relevant:
        return None
    tmpl = get_template("L5_user_context", variant=variant)
    flags_summary = " ".join(_FLAG_DESCRIPTIONS[f] for f in relevant)
    distress_note = (
        " Distress has been elevated for multiple turns."
        if "escalating_distress" in relevant
        else ""
    )
    content = tmpl.content.format(
        flags_summary=_esc(flags_summary),
        intensity=str(intensity),
        engagement=str(engagement),
        distress_note=_esc(distress_note),
    )
    _log.debug("L5_user_context@%s loaded", tmpl.version)
    return content


def _build_l0_system_block(variant: str | None = None) -> str:
    tmpl = get_template("L0_persona", variant=variant)
    _log.debug("L0_persona@%s loaded", tmpl.version)
    return tmpl.content


def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
) -> str | None:
    if not conversation_history:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    word_budget = tmpl.word_budget or 300
    window = conversation_history[-window_size:]
    lines: list[str] = []
    word_total = 0
    for m in window:
        content = (
            _sanitize_assistant_turn(m["content"])
            if m["role"] == "assistant"
            else m["content"]
        )
        line = f"{m['role'].upper()}: {content}"
        word_total += count_words(line)
        if len(lines) > 0 and word_total > word_budget:
            _log.debug("L1 history truncated at word budget %d", word_budget)
            break
        lines.append(line)
    if not lines:
        return None
    history_text = _esc("\n".join(lines))
    content = tmpl.content.format(history_lines=history_text)
    _log.debug("L1_history@%s loaded", tmpl.version)
    return content


_CULTURAL_BUDGET_WORDS = 150
_TOTAL_WORD_BUDGET = 1100


def compose_prompt(state: SageState) -> tuple[str, str, list[str]]:
    """Return (system_str, user_str, prompt_layers) for role-separated LLM invocation.

    Implements v7 §5.6 6-layer progressive disclosure. Rules Service injections
    (cultural, clinical flags, post-crisis, secondary intent) are unchanged.
    """
    message_en = state.get("message_en", "")
    language = state.get("detected_language", "en")
    clinical_flags = state.get("clinical_flags", [])
    primary_intent = state.get("primary_intent")
    secondary_intent = state.get("secondary_intent")
    intensity = state.get("emotional_intensity", 5)
    engagement = state.get("engagement", 5)

    layers: list[str] = []

    # ---- System role -------------------------------------------------------
    # L0: Base persona (always included)
    system_parts = [_build_l0_system_block()]
    layers.append("persona")

    # Cultural injections from Rules Service (unchanged from original)
    code_switch = state.get("code_switching", False)
    cultural_result = rules_engine.evaluate("cultural", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "language": language,
        "code_switch": code_switch,
    })
    cultural_actions = sorted(
        [a for a in cultural_result.actions if a.get("target") == "system"],
        key=lambda a: a.get("priority", 5),
    )
    word_count = 0
    for action in cultural_actions:
        content = action["content"]
        words = count_words(content)
        if word_count + words <= _CULTURAL_BUDGET_WORDS or word_count == 0:
            if word_count == 0 and words > _CULTURAL_BUDGET_WORDS:
                _log.warning("Cultural action exceeds budget (%d > %d words)", words, _CULTURAL_BUDGET_WORDS)
            system_parts.append(content)
            word_count += words
        else:
            break
    if cultural_actions:
        layers.append("cultural")

    session_flags: list[str] = []
    if state.get("crisis_state") in ("active", "monitoring", "resolved"):
        session_flags.append("crisis_occurred")

    injection_result = rules_engine.evaluate("prompt_injection", {
        "text": message_en,
        "text_ar": state.get("raw_message") if language == "ar" else None,
        "clinical_flags": clinical_flags,
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "session_flags": session_flags,
    })
    system_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "system"
    ]
    if system_injections:
        system_parts.append(
            "\nCLINICAL ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )
        layers.append("clinical_adaptation")

    system_str = "\n\n".join(system_parts)

    # ---- User role ---------------------------------------------------------
    user_parts: list[str] = []

    # L1: Conversation history
    l1_block = _build_l1_history_block(state.get("conversation_history", []))
    if l1_block:
        user_parts.append(l1_block)
        layers.append("history")

    # L2: Intent framing (always included per v7 §5.6)
    l2_block = _build_l2_intent_block(primary_intent, intensity, secondary_intent)
    user_parts.append(l2_block)
    layers.append("intent")

    # L5: User context (before skill/knowledge so LLM has profile context first)
    l5_block = _build_l5_user_context_block(clinical_flags, intensity, engagement)
    if l5_block:
        user_parts.append(l5_block)
        layers.append("user_context")

    # Post-crisis context injection (text preserved from original)
    if state.get("crisis_state") == "monitoring":
        s7 = state.get("s7_result") or "UNCLEAR"
        user_parts.append(
            f"POST-CRISIS CONTEXT: The user was recently in crisis. "
            f"S7 recovery classifier result: {s7}. "
            f"Respond with extra warmth, patience, and safety-consciousness. "
            f"Do not probe for details of the crisis. Meet the user where they are."
        )
        layers.append("post_crisis_context")

    # User-targeted prompt_injection actions (Rules Service, unchanged)
    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    # L3: Skill context
    step_instruction = state.get("step_instruction")
    if step_instruction:
        if state.get("escalation_triggered"):
            user_parts.append(f"SKILL INSTRUCTION:\n{step_instruction}")
            layers.append("skill_instruction")
        elif state.get("active_skill_id") and state.get("executed_step_id"):
            try:
                skill = load_skill(state["active_skill_id"])
                step = next(
                    (s for s in skill.steps if s.step_id == state["executed_step_id"]),
                    None,
                )
                if step:
                    l3_block = _build_l3_skill_block(skill.skill_name, step, language, intensity)
                    user_parts.append(l3_block)
                    layers.append("L3_skill_wrapper")
                else:
                    user_parts.append(f"SKILL INSTRUCTION:\n{step_instruction}")
                    layers.append("skill_instruction")
            except Exception:
                user_parts.append(f"SKILL INSTRUCTION:\n{step_instruction}")
                layers.append("skill_instruction")
        else:
            user_parts.append(f"SKILL INSTRUCTION:\n{step_instruction}")
            layers.append("skill_instruction")

    # L4: Knowledge context (only for info_request intent)
    intent_set = {primary_intent, secondary_intent}
    if "info_request" in intent_set:
        snippet = lookup_knowledge(message_en)
        l4_block = _build_l4_knowledge_block(snippet)
        if l4_block:
            user_parts.append(l4_block)
            layers.append("knowledge")

    # User message always last
    user_parts.append(f"USER: {message_en}")

    # ---- Token budget enforcement (overflow: shrink L1 first) --------------
    total_words = count_words(system_str) + count_words_in_parts(user_parts)
    if total_words > _TOTAL_WORD_BUDGET and "history" in layers:
        history = state.get("conversation_history", [])
        l1_tmpl = get_template("L1_history")
        half_window = max(1, (l1_tmpl.window_size or 8) // 2)
        window = history[-half_window:]
        lines = [
            f"{m['role'].upper()}: {_sanitize_assistant_turn(m['content']) if m['role'] == 'assistant' else m['content']}"
            for m in window
        ]
        shrunk = l1_tmpl.content.format(history_lines=_esc("\n".join(lines)))
        user_parts[0] = shrunk  # history is always index 0 when present (appended first)
        _log.warning("Token budget overflow: L1 history shrunk to %d turns", half_window)

    user_str = "\n\n".join(user_parts)
    return system_str, user_str, layers
