from __future__ import annotations
import re
import logging
from sage_poc.state import SageState
from sage_poc.skills.schema import SkillStep, load_skill
from sage_poc.rules import engine as rules_engine
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
    "high": "The user is significantly distressed. Name the specific thing they said, directly. Ask one focused question about it. Do NOT paraphrase or reflect back what they said. Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener. Do NOT offer guidance yet.",
}

_L1_BASE_BUDGET = 450
_L1_FLEX_BUDGET = 600
_L1_MINIMUM_BUDGET = 150  # defensive floor — clinical minimum; unreachable after Task 0 cap reduction


def _intensity_guidance(intensity: int) -> str:
    if intensity <= 3:
        return _INTENSITY_GUIDANCE["low"]
    if intensity <= 6:
        return _INTENSITY_GUIDANCE["mid"]
    return _INTENSITY_GUIDANCE["high"]


def _compute_l1_budget(state: SageState, override_words: int = 0) -> int:
    """Return the L1 word budget for this turn.

    On freeflow turns (no skill step, no knowledge lookup), L3 and L4 layers
    are absent. Their unused budget headroom is loaned to L1 so that rich
    multi-turn disclosures don't get truncated.

    override_words: actual word count of the skill cultural_overrides block
        injected into the system prompt this turn. Subtracted from base so L1
        is proactively sized rather than shrunk reactively by the overflow guard.
        After Task 0 (cap=200w), max subtraction is 200, giving L1 ≥ 250w on
        skill turns — _L1_MINIMUM_BUDGET (150) is unreachable in practice.

    SPEC DIVERGENCE (§5.6.1): v7 §5.6.1 specifies ~300w for L1. The 450/600
    values are a pre-existing architectural deviation pending review. Do not
    adjust these constants here — raise via the §5.6.1 architectural review.

    POC NOTE (§6.5.2): The info_request proxy misses tool-invoked knowledge.
    knowledge_lookup (§6.5.2) can add ~300w of evidence on a turn classified
    as emotional support — that turn is treated as freeflow (L1=600) with no
    knowledge-budget deduction. This is a pre-existing gap; fixing it requires
    routing information not yet available at budget calculation time.
    """
    has_skill = bool(state.get("step_instruction"))
    has_knowledge = state.get("primary_intent") == "info_request" or \
                    state.get("secondary_intent") == "info_request"
    base = _L1_BASE_BUDGET if (has_skill or has_knowledge) else _L1_FLEX_BUDGET
    return max(_L1_MINIMUM_BUDGET, base - override_words)


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
    "domestic_situation": "This user has disclosed a domestic safety concern. Prioritise safety. Do NOT advise leaving without safety planning. Do NOT minimise their account.",
    "escalating_distress": "This user's distress has been elevated across multiple turns.",
}


def _build_l4_knowledge_block(
    passages: list[dict],
    abstain: bool,
    variant: str | None = None,
) -> str | None:
    if abstain and not passages:
        return (
            "KNOWLEDGE: No relevant clinical evidence found for this query. "
            "Do not fabricate clinical facts. If asked, tell the user you do not have "
            "specific information on that topic and offer to help them find a professional resource."
        )
    if not passages:
        return None
    tmpl = get_template("L4_knowledge", variant=variant)
    passage_lines = "\n".join(
        f"[{i+1}] {p['text']} (Source: {p.get('citation', p.get('source_id', ''))})"
        for i, p in enumerate(passages[:5])
    )
    content = tmpl.content.format(passages=_esc(passage_lines))
    _log.debug("L4_knowledge@%s loaded (%d passages)", tmpl.version, len(passages))
    return content


def _build_cross_session_block(profile: dict | None) -> str:
    if not profile:
        return ""
    parts = []
    techs = profile.get("effective_techniques", [])
    if techs:
        parts.append(f"Techniques that have helped: {', '.join(techs)}.")
    bad = profile.get("ineffective_techniques", [])
    if bad:
        parts.append(f"Approaches to avoid: {', '.join(bad)}.")
    patterns = profile.get("distortion_patterns", [])
    if patterns:
        parts.append(f"Common thought patterns: {', '.join(patterns)}.")
    concerns = profile.get("disclosed_concerns", [])
    if concerns:
        parts.append(f"Life areas shared: {', '.join(concerns)}.")
    style = profile.get("communication_style")
    if style:
        parts.append(f"Communication note: {style}")
    prefs = profile.get("cultural_preferences", {})
    if prefs.get("religious_framing"):
        parts.append("This user is comfortable with religious framing.")
    if prefs.get("family_context"):
        parts.append("This user often references family context.")
    if not parts:
        return ""
    n = profile.get("session_count", 1)
    return f" From {n} previous session{'s' if n != 1 else ''}: " + " ".join(parts)


def _build_l5_user_context_block(
    clinical_flags: list[str],
    intensity: int,
    engagement: int,
    therapeutic_profile: dict | None = None,
    variant: str | None = None,
) -> str | None:
    relevant = [f for f in clinical_flags if f in _FLAG_DESCRIPTIONS]
    cross_session = _build_cross_session_block(therapeutic_profile)
    if not relevant and not cross_session:
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
        cross_session_profile=_esc(cross_session),
    )
    _log.debug("L5_user_context@%s loaded", tmpl.version)
    return content


def _build_l0_system_block(variant: str | None = None) -> str:
    tmpl = get_template("L0_persona", variant=variant)
    _log.debug("L0_persona@%s loaded", tmpl.version)
    return tmpl.content


def _build_freeflow_guardrail_block(variant: str | None = None) -> str:
    """Guided-protocol guardrail for FREEFLOW turns only (S2-7 B1).

    Forbids leading a structured therapeutic protocol (guided breathing,
    grounding, PMR, body scan, safe-place visualization, TIPP-style reset) as
    free prose, which would route around the contraindication screening those
    protocols carry. Permits suggesting + offering the guided version. Must NOT
    be injected on skill-execution turns, where the executor delivers the
    protocol via the L3 step instruction. Draft-pending clinical review.
    """
    tmpl = get_template("freeflow_guardrail", variant=variant)
    _log.debug("freeflow_guardrail@%s loaded", tmpl.version)
    return tmpl.content


def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
    word_budget: int | None = None,
    conversation_summary: str | None = None,
) -> str | None:
    if not conversation_history and not conversation_summary:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    effective_budget = word_budget if word_budget is not None else (tmpl.word_budget or _L1_BASE_BUDGET)
    window = conversation_history[-window_size:]
    lines: list[str] = []
    word_total = 0
    for m in reversed(window):            # newest → oldest
        content = (
            _sanitize_assistant_turn(m["content"])
            if m["role"] == "assistant"
            else m["content"]
        )
        line = f"{m['role'].upper()}: {content}"
        words = count_words(line)
        if lines and word_total + words > effective_budget:
            _log.debug("L1 history truncated at word budget %d", effective_budget)
            break
        lines.append(line)
        word_total += words
    lines.reverse()                       # restore chronological order for prompt

    if conversation_summary:
        summary_block = f"SUMMARY (earlier context):\n{_esc(conversation_summary)}"
        if lines:
            history_text = summary_block + "\n\nRECENT TURNS:\n" + _esc("\n".join(lines))
        else:
            history_text = summary_block
    else:
        if not lines:
            return None
        history_text = _esc("\n".join(lines))

    content = tmpl.content.format(history_lines=history_text)
    _log.debug("L1_history@%s loaded", tmpl.version)
    return content


_CULTURAL_BUDGET_WORDS = 250
_CULTURAL_OVERRIDE_BUDGET_WORDS = 200  # clinician-signed cap; forces concise complete overrides
_TOTAL_WORD_BUDGET = 1100


def build_cultural_override_block(skill) -> str | None:
    """Build the override block string exactly as compose_prompt injects it.

    Returns the block string if the skill has cultural_overrides and the block
    fits within _CULTURAL_OVERRIDE_BUDGET_WORDS; returns None otherwise.

    Call this from the audit and CI tests instead of reconstructing the format
    — any divergence between a hand-rolled reconstruction and this function is
    the silent-drop bug wearing a test as a disguise.
    """
    if not skill.cultural_overrides:
        return None
    lines = "\n".join(f"- {v}" for v in skill.cultural_overrides.values())
    block = f"SKILL-SPECIFIC CULTURAL CONTEXT:\n{lines}"
    if count_words(block) <= _CULTURAL_OVERRIDE_BUDGET_WORDS:
        return block
    return None


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

    # L0 extension: Arabic session generation contract.
    # Sole authoritative location for the EN-first directive. Fires before cultural
    # rules so the LLM sees the translation architecture before register calibration.
    # CU-DM-001 v1.2 must not restate this (register calibration only after this fix).
    if language == "ar":
        system_parts.append(
            "ARABIC SESSION: This user writes in Arabic. Your response will be "
            "translated to Khaleeji Arabic by the delivery layer. Generate in English "
            "with warmth and conversational rhythm that translates naturally to Gulf "
            "Arabic, not clinical or formal phrasing. Do not write in Arabic."
        )
        layers.append("arabic_register")

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

    # Skill-specific cultural overrides — more specific than global rules; injected after them.
    # _override_words is captured here so _compute_l1_budget can proactively reduce L1 budget,
    # eliminating the need for reactive overflow shrinking on normal skill turns.
    _override_words = 0
    _active_for_overrides = state.get("active_skill_id")
    if _active_for_overrides:
        try:
            _override_skill = load_skill(_active_for_overrides)
            _override_block = build_cultural_override_block(_override_skill)
            if _override_block is not None:
                _override_words = count_words(_override_block)
                system_parts.append(_override_block)
                layers.append("cultural_skill_overrides")  # only when actually injected
            elif _override_skill.cultural_overrides:
                _log.warning(
                    "cultural_overrides exceeds budget for %s", _active_for_overrides
                )
                # Block not injected; no layer tag — audit trail must reflect reality
        except Exception as exc:
            _log.warning("cultural_overrides load failed for %s: %s", _active_for_overrides, exc)

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
        # Label is "SUPPORT ADAPTATIONS" to avoid clinical framing in the LLM context.
        # The safety and clinical rules themselves are unchanged — only the header label differs.
        system_parts.append(
            "\nSUPPORT ADAPTATIONS (follow these strictly):\n"
            + "\n".join(f"- {c}" for c in system_injections)
        )
        layers.append("clinical_adaptation")

    system_str = "\n\n".join(system_parts)

    # ---- User role ---------------------------------------------------------
    user_parts: list[str] = []

    # L1: Conversation history
    l1_budget = _compute_l1_budget(state, override_words=_override_words)
    l1_block = _build_l1_history_block(
        state.get("conversation_history", []),
        word_budget=l1_budget,
        conversation_summary=state.get("conversation_summary"),
    )
    if l1_block:
        user_parts.append(l1_block)
        layers.append("history")

    # L2: Intent framing (always included per v7 §5.6)
    # When new_skill intent reaches freeflow with no matched skill, use the
    # unmatched-disclosure template (structural constraints: name disclosed content,
    # do not re-probe named emotions, offer space not solutions). Selector pending
    # Rule 1 approval — template is draft-pending-review.
    _l2_intent = (
        "new_skill_unmatched"
        if primary_intent == "new_skill" and not state.get("active_skill_id")
        else primary_intent
    )
    l2_block = _build_l2_intent_block(_l2_intent, intensity, secondary_intent)
    user_parts.append(l2_block)
    layers.append("intent")

    # Freeflow guided-protocol guardrail (S2-7 B1) — FREEFLOW TURNS ONLY.
    # Mirrors the freeflow discriminator used by _compute_l1_budget: a turn with no
    # step_instruction is freeflow (no active skill / no L3 step). On skill-execution
    # turns the executor legitimately delivers the protocol via the L3 step instruction,
    # so the guardrail must NOT fire there (it would conflict with L3). This is why the
    # block lives in the composer conditioned on freeflow, not in L0_persona.
    if not state.get("step_instruction"):
        user_parts.append(_build_freeflow_guardrail_block())
        layers.append("freeflow_guardrail")

    # L5: User context (before skill/knowledge so LLM has profile context first)
    l5_block = _build_l5_user_context_block(
        clinical_flags, intensity, engagement,
        therapeutic_profile=state.get("therapeutic_profile"),
    )
    if l5_block:
        user_parts.append(l5_block)
        layers.append("user_context")

    # Third-party crisis: user is worried about someone else, not disclosing their own crisis.
    # Provide guidance on supporting the friend; do not apply crisis protocol to the user.
    if state.get("third_party_crisis"):
        user_parts.append(
            "THIRD-PARTY CONCERN: The user is concerned about someone else's safety, not their own. "
            "Provide compassionate guidance on how they can support that person. "
            "Suggest crisis resources they can share with them. "
            "Do not treat the current user as being in crisis."
        )
        layers.append("third_party_crisis")

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

    # Stale skill re-entry: prior skill was parked (session gap > 4h); active_skill_id is now None.
    # Prompt the LLM to acknowledge the prior work naturally — let the user guide direction.
    stale_skill_id = state.get("stale_skill_id")
    if stale_skill_id:
        try:
            skill = load_skill(stale_skill_id)
            skill_display = skill.skill_name
        except Exception:
            skill_display = stale_skill_id.replace("_", " ")
        user_parts.append(
            f"PARKED SKILL CONTEXT: The user was previously working through '{skill_display}' "
            f"but is returning after an extended break. "
            f"If their current message suggests they want to continue that work, gently acknowledge it "
            f"and offer to pick up where they left off or explore what is on their mind today. "
            f"If their message is about something unrelated or more urgent, focus on that first."
        )
        layers.append("stale_skill_context")

    # User-targeted prompt_injection actions (Rules Service, unchanged)
    user_injections = [
        a["content"] for a in injection_result.actions if a.get("target") == "user"
    ]
    for content in user_injections:
        user_parts.append(content)

    # L3: Skill context
    # escalation_triggered is NOT handled as a special early-exit here.
    # L1 escalation (active_skill_id=None) naturally falls to the else branch below.
    # L2 escalation (active_skill_id still set) falls to the _build_l3_skill_block branch,
    # which applies language-aware example selection via _select_few_shot_examples.
    # The previous L2 early-exit caused Arabic users to receive examples[:2] (English-ordered)
    # precisely on the high-stakes turns when register quality matters most.
    step_instruction = state.get("step_instruction")
    if step_instruction:
        if state.get("rule_fired"):
            # A step_policy rule overrode the default step instruction. Use it directly —
            # rebuilding L3 from the skill step would discard the clinical override.
            user_parts.append(f"SKILL INSTRUCTION:\n{step_instruction}")
            layers.append("skill_instruction_override")
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

    # L4: Knowledge context — from Node 6 retrieval or knowledge_lookup tool result in state
    knowledge_passages = state.get("knowledge_passages") or []
    knowledge_abstain = state.get("knowledge_abstain", False)
    if knowledge_passages or knowledge_abstain:
        l4_block = _build_l4_knowledge_block(knowledge_passages, knowledge_abstain)
        if l4_block:
            user_parts.append(l4_block)
            layers.append("knowledge")

    # User message always last
    user_parts.append(f"USER: {message_en}")

    correction = state.get("banned_opener_correction")
    if correction:
        user_parts.append(f"[CORRECTION]: {correction}")
        layers.append("banned_opener_correction")

    # ---- Token budget enforcement (overflow: shrink L1 first) --------------
    total_words = count_words(system_str) + count_words_in_parts(user_parts)
    if total_words > _TOTAL_WORD_BUDGET and "history" in layers:
        history = state.get("conversation_history", [])
        l1_tmpl = get_template("L1_history")
        half_window = max(1, (l1_tmpl.window_size or 8) // 2)
        shrunk = _build_l1_history_block(
            history[-half_window:],
            word_budget=300,    # conservative for overflow case
        ) or ""
        user_parts[0] = shrunk  # history is always index 0 when present (appended first)
        _log.warning("Token budget overflow: L1 history shrunk to %d turns", half_window)

    user_str = "\n\n".join(user_parts)
    return system_str, user_str, layers
