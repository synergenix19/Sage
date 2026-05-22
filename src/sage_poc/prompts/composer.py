from __future__ import annotations
import re
import logging
from sage_poc.state import SageState
from sage_poc.skills.schema import SkillStep, load_skill
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
