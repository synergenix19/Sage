from __future__ import annotations
import re
import logging
import json as _json
from functools import lru_cache
from pathlib import Path
from sage_poc.state import SageState
from sage_poc.skills.schema import SkillStep, load_skill
from sage_poc.rules import engine as rules_engine
from sage_poc import config as _config
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

# D5 acuity guidance (GATED, default-off). Returned only when D5_ACUITY_GATE_ENABLED is True
# AND emotional_intensity >= D5_ACUITY_FLOOR (default 8). Replaces the high-intensity string
# at peak distress: validate by naming the specific thing said, stay purely supportive,
# do NOT challenge or question a distorted belief. No em dashes (rule content mirrors into LLM output).
_D5_ACUITY_GUIDANCE = (
    "The user is at peak distress. Validate the feeling by naming the specific thing they said, "
    "not a generic reflection. Stay purely supportive. Do not challenge or question a distorted "
    "belief here. Do NOT begin with 'It sounds like', 'That sounds', or any reflective opener. "
    "Do NOT offer guidance yet."
)

# P1(mid) response-shape floor (engineering, no clinical sign-off). Injected ONLY on
# pure-freeflow general_chat turns at the MID band (intensity 4-6), appended to the
# freeflow guardrail block at its existing discriminator (no step_instruction and no
# offer), so it cannot reach the skill_offer or skill_executor surfaces and never fires
# on the low band (light moments stay light) or the high/D5 acute band. Rationale: the
# 2026-06-25 band-attribution run showed the cold-reply defect is pure-freeflow + mid +
# no skill, and is a VARIANCE problem (5 samples of the same case ranged 19-38 words, all
# under the P-2 validation band) caused by the underspecified mid string giving no shape
# or length floor. This raises the floor and imposes R-7 shape (validation-first, one open
# question) bounded by the P-2 validation band (40-80 words). Deliberately EXCLUDES the
# P2 normalization sentence (parked for clinical sign-off) and the P3 menu/fork question
# (gated on Arabic + crisis eval): one plain open question only. No em dashes (mirrors into
# output). See docs/superpowers/audits 2026-06-25 band attribution.
#
# LOAD-BEARING COUPLING (do not remove without reading): this shape only clears the
# length floor because it INVOKES an existing, clinician-signed L0 exception rather than
# overriding L0's concision default. The plain "40-80 words" floor (v1) was overridden by
# L0's signed cap "Keep replies concise, two to four sentences" and produced no effect.
# The clause it rides, verbatim in L0_persona.json (template_id L0_persona), is:
#   "...two to four sentences unless the person needs more; a heavy disclosure deserves a
#    longer, more present reply even when it is brief..."
# That clause is CLINICIAN-OWNED (L0 is signed). If a future L0 edit tightens the concision
# cap or drops the "unless the person needs more / heavy disclosure deserves a longer reply"
# exception, this shape silently reverts to cold with no engineering signal. The coupling is
# guarded by tests/test_p1_mid_freeflow_shape.py::test_l0_longer_reply_exception_present,
# which fails loudly if that clause leaves L0. Arabic note: AR turns generate in English
# against this same L0 (see "ARABIC SESSION" below), so the exception is NOT language-split;
# the Arabic risk is translation survival of the floor, not a missing AR exception.
_MID_FREEFLOW_SHAPE = (
    "RESPONSE SHAPE: This is a turn that needs more than a brief reply, so give fuller presence "
    "rather than two short sentences. Begin by acknowledging the feeling the person named, in your "
    "own words. Then ask one open question that follows directly from what they said. Write three "
    "or four sentences, roughly forty to eighty words, enough to feel present and unhurried, never "
    "so long it becomes advice. Ask only a single question, not several, and do not offer "
    "suggestions or techniques here."
)

# Stall-guard recovery instruction (freeflow-only). Fires when the deterministic
# detector flags a stall. It must RE-GROUND in established context, not merely
# suppress the repeated question (which would degrade into a different generic
# opener). No em dashes: rule content mirrors into LLM output.
_STALL_RECOVERY_INSTRUCTION = (
    "RECOVERY: The user has repeated themselves or has not moved forward over the "
    "last few turns. Do not ask another open ended question and do not open with a "
    "new generic line. Use what they have ALREADY shared earlier in this "
    "conversation, name those specific details back to them, and offer one "
    "concrete next step grounded in those details."
)

_OFFER_DESCRIPTIONS_PATH = Path(__file__).parent / "offer_descriptions.json"
_DECLINED_INSTRUCTION_PATH = Path(__file__).parent / "declined_skills_instruction.json"


@lru_cache(maxsize=1)
def _offer_descriptions() -> dict:
    # Raises on load failure — the try/except lives in _build_offer_options_block
    # so a failed load is NOT cached. lru_cache still gives process-lifetime
    # caching on success, while the file appearing later allows recovery.
    return _json.loads(_OFFER_DESCRIPTIONS_PATH.read_text(encoding="utf-8"))["descriptions"]


@lru_cache(maxsize=1)
def _declined_instruction() -> dict:
    # Governed content (draft-pending-review). Same caching/recovery contract as
    # _offer_descriptions: raises on load failure so the try/except in the
    # caller decides fallback and a failed load is not cached.
    return _json.loads(_DECLINED_INSTRUCTION_PATH.read_text(encoding="utf-8"))["instruction"]


def _bilingual(entry_field: dict, language: str) -> str:
    """Bilingual envelope accessor: ar falls back to en when null/absent.

    A malformed entry (missing/null en) degrades to "" rather than raising —
    this runs on the hot path and must never abort the turn."""
    return entry_field.get(language) or entry_field.get("en") or ""


def _build_offer_options_block(offered_skill_ids: list[str], language: str) -> str:
    """One numbered line per offered skill: display name plus plain blurb.
    Falls back to registry skill_name when a blurb is missing (coverage test
    in test_engagement_templates.py should make that unreachable)."""
    try:
        descs = _offer_descriptions()
    except Exception as exc:
        _log.warning("offer_descriptions.json unavailable: %s", exc)
        descs = {}
    lines: list[str] = []
    for i, sid in enumerate(offered_skill_ids, 1):
        entry = descs.get(sid)
        if entry:
            name = _bilingual(entry["display_name"], language)
            desc = _bilingual(entry["description"], language)
            lines.append(f"{i}. {name}: {desc}")
        else:
            try:
                lines.append(f"{i}. {load_skill(sid).skill_name}")
            except Exception:
                _log.warning("offer options: unknown skill_id %s skipped", sid)
    return "\n".join(lines)


def _declined_skill_names(declined_skill_ids: list[str], language: str) -> list[str]:
    """Plain-language display names for declined skills (en/ar fallback).

    Reuses the offer_descriptions display names so the freeflow signal speaks the
    same plain language the user saw in the offer, never the raw skill_id. Unknown
    ids fall back to the registry skill_name, then to a de-underscored id, so the
    note never leaks an internal identifier."""
    try:
        descs = _offer_descriptions()
    except Exception as exc:
        _log.warning("offer_descriptions.json unavailable for declined note: %s", exc)
        descs = {}
    names: list[str] = []
    for sid in declined_skill_ids:
        entry = descs.get(sid)
        if entry:
            names.append(_bilingual(entry["display_name"], language))
            continue
        try:
            names.append(load_skill(sid).skill_name)
        except Exception:
            _log.warning("declined note: unknown skill_id %s; using de-underscored id", sid)
            names.append(sid.replace("_", " "))
    return [n for n in names if n]


def _build_declined_skills_note(declined_skill_ids: list[str], language: str) -> str:
    """S2-7 B2: short freeflow note listing skills the user declined this session
    so freeflow does not re-offer or re-deliver that specific content in prose.

    Fixed instruction wording lives in declined_skills_instruction.json
    (draft-pending-review). Returns "" if no display names resolve, so the caller
    can skip the layer rather than render an empty signal."""
    names = _declined_skill_names(declined_skill_ids, language)
    if not names:
        return ""
    try:
        instr = _declined_instruction()
        header = _bilingual(instr["header"], language)
        guidance = _bilingual(instr["guidance"], language)
    except Exception as exc:
        _log.warning("declined_skills_instruction.json unavailable: %s", exc)
        return ""
    names_str = ", ".join(names)
    return f"{header}: {guidance.format(names=names_str)}"


_L1_BASE_BUDGET = 450
_L1_FLEX_BUDGET = 600
_L1_MINIMUM_BUDGET = 150  # defensive floor — clinical minimum; unreachable after Task 0 cap reduction


def _intensity_guidance(intensity: int) -> str:
    if intensity <= 3:
        return _INTENSITY_GUIDANCE["low"]
    if intensity <= 6:
        return _INTENSITY_GUIDANCE["mid"]
    # High band (intensity >= 7). D5 acuity gate fires only when explicitly enabled AND
    # intensity reaches the acuity floor (default 8). Gate is OFF by default; when OFF the
    # return value is byte-identical to pre-D5 production. Floor/band gap is documented in
    # config.py: intensity == 7 is in the high band but below D5_ACUITY_FLOOR=8 by design.
    if _config.D5_ACUITY_GATE_ENABLED and intensity >= _config.D5_ACUITY_FLOOR:
        return _D5_ACUITY_GUIDANCE
    return _INTENSITY_GUIDANCE["high"]


def _compute_l1_budget(
    state: SageState,
    override_words: int = 0,
    guardrail_words: int = 0,
    offer_words: int = 0,
    declined_words: int = 0,
) -> int:
    """Return the L1 word budget for this turn.

    On freeflow turns (no skill step, no knowledge lookup), L3 and L4 layers
    are absent. Their unused budget headroom is loaned to L1 so that rich
    multi-turn disclosures don't get truncated.

    override_words: actual word count of the skill cultural_overrides block
        injected into the system prompt this turn. Subtracted from base so L1
        is proactively sized rather than shrunk reactively by the overflow guard.
        After Task 0 (cap=200w), max subtraction is 200, giving L1 ≥ 250w on
        skill turns — _L1_MINIMUM_BUDGET (150) is unreachable in practice.

    guardrail_words: actual word count of the freeflow guided-protocol guardrail
        block (S2-7 B1) injected into user_parts on freeflow turns. Subtracted
        alongside override_words so the L1 flex budget (600w) is proactively
        reduced before history is sized, preventing the overflow guard from
        firing and emergency-shrinking L1 history on long freeflow turns.
        On skill-execution turns and skill-offer turns this is 0 (guardrail
        not injected — see the freeflow-vs-offer discriminator at the call site).

    offer_words: actual word count of the L2 offer options block on a
        skill-offer turn, deducted the same way so the offer never triggers
        the reactive overflow guard. On a skill-offer turn guardrail_words is 0
        and vice versa, so the two never both apply on the same turn.

    declined_words: actual word count of the S2-7 B2 declined-skills note on a
        freeflow turn, deducted the same way so the consent-integrity signal
        never pushes a long-history freeflow turn into reactive overflow shrink.

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
    return max(
        _L1_MINIMUM_BUDGET,
        base - override_words - guardrail_words - offer_words - declined_words,
    )


def _build_l2_intent_block(
    primary_intent: str | None,
    intensity: int,
    secondary_intent: str | None = None,
    variant: str | None = None,
    extra_variables: dict[str, str] | None = None,
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
        **(extra_variables or {}),
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


def _allow_light_structure(state: SageState) -> bool:
    """Permit light list structure on a grounded info answer only.

    Gate (all three required): Node 6 populated knowledge_passages (info_request answer
    with evidence; the knowledge_lookup tool does not write this field), no active skill
    (mid-skill info detours stay prose), and not a crisis monitoring/resolved aftercare turn
    (active crisis never reaches here). See the 2026-06-19 spec for the routing rationale.
    """
    return bool(state.get("knowledge_passages")) \
        and not state.get("active_skill_id") \
        and state.get("crisis_state", "none") == "none"


def _build_l4_knowledge_block(
    passages: list[dict],
    abstain: bool,
    variant: str | None = None,
    allow_light_structure: bool = False,
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
    directive = ""
    if allow_light_structure and tmpl.light_structure_directive:
        directive = "\n\n" + tmpl.light_structure_directive
    content = tmpl.content.format(passages=_esc(passage_lines), format_directive=directive)
    _log.debug(
        "L4_knowledge@%s loaded (%d passages, light_structure=%s)",
        tmpl.version, len(passages), allow_light_structure,
    )
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

    Coverage boundary: this guardrail reaches only the compose_prompt freeflow
    path. low_confidence_respond_node now composes via compose_prompt (§5.6.3)
    but passes l2_intent_override="low_confidence", which suppresses this
    guardrail (and the MID shape) — low_confidence is its own short-clarifying
    contract, not a freeflow turn. This remains benign because that template
    caps output at 2 sentences, making free-prose protocol delivery practically
    impossible. If that 2-sentence cap is ever removed from the low_confidence
    template, drop the override-suppression so the guardrail reaches it.
    """
    tmpl = get_template("freeflow_guardrail", variant=variant)
    _log.debug("freeflow_guardrail@%s loaded", tmpl.version)
    return tmpl.content


def _build_l1_history_block(
    conversation_history: list[dict],
    variant: str | None = None,
    word_budget: int | None = None,
    conversation_summary: str | None = None,
    pin_turn: dict | None = None,
) -> str | None:
    if not conversation_history and not conversation_summary and pin_turn is None:
        return None
    tmpl = get_template("L1_history", variant=variant)
    window_size = tmpl.window_size or 8
    effective_budget = word_budget if word_budget is not None else (tmpl.word_budget or _L1_BASE_BUDGET)
    window = list(conversation_history[-window_size:])
    # self_reference eviction-exemption: guarantee the recalled disclosure turn is in the
    # window even if it falls outside it, so an overflow shrink cannot drop the very turn
    # the user is asking about. pin_turn is None for every non-recall caller, so the loop
    # below preserves its original behaviour byte-for-byte in that case.
    if pin_turn is not None and pin_turn not in window:
        window = [pin_turn] + window
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
        is_pinned = pin_turn is not None and m is pin_turn
        if lines and not is_pinned and word_total + words > effective_budget:
            _log.debug("L1 history truncated at word budget %d", effective_budget)
            if pin_turn is None:
                break          # original behaviour: stop at first over-budget turn
            continue           # recall turn: skip middle turns, keep scanning for the pinned disclosure
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


# --- self_reference eviction-exemption: find the disclosure turn the recall refers to ---
# Language split mirrors the detector: Arabic recall + Arabic history live in raw text, so an
# English-token anchor would silently miss every Arabic recall and fall back to most-recent —
# landing the weak path exactly where the diagnostic found eviction worst (Arabic/cultural turns).
_ANCHOR_STOP = {
    "what", "did", "just", "tell", "say", "said", "you", "your", "about", "the", "that", "this",
    "have", "with", "mention", "remember", "told", "and", "for", "was", "were", "dont", "don",
}


def _recall_text(state: SageState) -> str:
    return state.get("raw_message", "") if state.get("detected_language") == "ar" else state.get("message_en", "")


def _salient_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"\w+", (text or "").lower()) if len(t) >= 3 and t not in _ANCHOR_STOP}


def _anchor_turn(history: list[dict], recall_text: str) -> dict | None:
    """Most-recent user turn sharing a salient token with the recall; else most-recent user turn."""
    user_turns = [m for m in history if m.get("role") == "user"]
    if not user_turns:
        return None
    toks = _salient_tokens(recall_text)
    if toks:
        for m in reversed(user_turns):
            if toks & _salient_tokens(m.get("content", "")):
                return m
    return user_turns[-1]


# --- absent-side A4 fix: empty-retrieval sentinel for the MEMORY path ---
# Mirrors the knowledge path's "No relevant clinical evidence found" anchor. The original A4 fix
# shipped the L0 *instruction* to admit but not the *signal* to admit against, so empty retrieval
# was silence the model fabricates into (~15-25% of the time). This gives it the signal.
_MEMORY_ABSENT_SENTINEL = (
    "MEMORY CHECK: the person is asking you to recall something, but no earlier record of it was "
    "found, not in this conversation and not in any prior-session context above. Do not invent, "
    "infer, or guess what they said. Tell them you do not have a record of that and invite them to "
    "share it again."
)


def memory_absent_sentinel(state: SageState, prior_context_present: bool) -> str | None:
    """Return the sentinel ONLY when a recall is requested AND grounding is genuinely empty:
    no prior-session context, and no user turns in this conversation. Keys off emptiness
    (language-agnostic), NOT the keyword-anchor, so it carries no Arabic-parity dependency and
    cannot assert absence over real disclosure (which would re-introduce the false-denial vector).
    Returns None when any user history exists -> the back-door is closed by erring toward NOT firing."""
    if not state.get("self_reference") or prior_context_present:
        return None
    if any(m.get("role") == "user" for m in state.get("conversation_history", [])):
        return None
    return _MEMORY_ABSENT_SENTINEL


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


def compose_prompt(state: SageState, l2_intent_override: str | None = None, *, shadow_arabic: bool = False) -> tuple[str, str, list[str]]:
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
        if shadow_arabic:
            from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars  # noqa: PLC0415
            from sage_poc.gender_marker import detect_gender_marking  # noqa: PLC0415
            # Mirror-when-marked gender policy: detect grammatical self-marking from
            # the user's OWN raw Arabic text (never message_en — English carries no
            # equivalent marking), then select the matching few-shot rendering so the
            # shadow generation actually applies the policy the gender_marked
            # stratification column measures against.
            _gender = detect_gender_marking(state.get("raw_message") or "")
            _ex_version, _ex_block = load_khaleeji_shadow_exemplars(_gender)
            _mirror_directive = (
                "Address the user in the gender they grammatically self-mark; if "
                "unmarked, use gender-neutral constructions. Never infer gender from "
                "topic or name."
            )
            system_parts.append(
                "ARABIC SESSION (native generation): This user writes in Arabic. "
                "Generate your reply directly in warm, informal Gulf Arabic (Khaleeji "
                "dialect), not Modern Standard Arabic and not clinical or formal "
                "phrasing. Mirror the user's dialect and level of formality.\n"
                + _mirror_directive + "\n" + _ex_block
            )
            layers.append("arabic_native_shadow")
        else:
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

    # R1 (2026-06-12): a pending skill offer overrides intent-based L2 selection.
    # State-driven because the offer is created by skill_select, not intent_route.
    # Computed BEFORE the L1 budget so the offer block's words deduct proactively
    # from L1 instead of tripping the reactive overflow guard (C-1).
    _offer_ids = state.get("offered_skill_ids") or []
    _offer_block_str = ""
    _offer_words = 0
    if _offer_ids:
        _offer_block_str = _build_offer_options_block(_offer_ids, language)
        if not _offer_block_str.strip():
            # I-1: the skill_offer template must never render with a blank
            # options block — fall back to intent-based L2 for this turn.
            _log.warning(
                "offer options block is empty for ids %s; falling back to intent-based L2",
                _offer_ids,
            )
            _offer_ids = []
            _offer_block_str = ""
        else:
            _offer_words = count_words(_offer_block_str)

    # Freeflow guided-protocol guardrail (S2-7 B1) — pre-compute before _compute_l1_budget.
    # The block is built here (freeflow turns only) so its word count can be passed into
    # _compute_l1_budget as guardrail_words, proactively reducing L1 budget before history
    # is sized. Without this deduction the guardrail's ~90 words are appended AFTER the
    # budget calculation, pushing the total over _TOTAL_WORD_BUDGET and triggering the
    # overflow guard that emergency-shrinks L1 history — degrading exactly the
    # emotional-support turns that benefit most from rich history context.
    # The pre-built string is reused when appending below (not built twice).
    #
    # MERGE RESOLUTION (#4 ⊕ #8, 2026-06-13): a skill-offer turn also has no
    # step_instruction, so the freeflow discriminator alone would inject the
    # guardrail ON TOP OF the skill_offer L2 framing — two different response
    # contracts stacked in one prompt. The offer turn has its own framing
    # (present named options, await a choice), so the guardrail is suppressed
    # when an offer is live. This keeps guardrail_words and offer_words mutually
    # exclusive per turn, matching the budget docstring.
    _guardrail_block: str | None = None
    _guardrail_words: int = 0
    # l2_intent_override (e.g. low_confidence) is NOT a freeflow turn: it carries
    # its own response contract (a short clarifying question), so the freeflow-only
    # guardrail + MID shape must not fire here — the MID shape would contradict that
    # contract's brevity cap. Protocol-as-prose is impossible in a 2-sentence reply,
    # so suppressing the guardrail here is safe (same rationale as the pre-migration
    # bypass, now explicit).
    if not state.get("step_instruction") and not _offer_ids and not l2_intent_override:
        _guardrail_block = _build_freeflow_guardrail_block()
        # P1(mid): on pure-freeflow validation turns at the MID band only, append the
        # response-shape floor. Gated to 4 <= intensity <= 6 so the low band (light
        # moments) and the high/D5 acute band are untouched. This branch is already
        # inside the freeflow discriminator (no step_instruction, no offer), so the
        # shape can never reach the skill-offer or skill-execution surfaces. Appended
        # to the guardrail string so its words deduct from L1 in the same pass.
        if 4 <= intensity <= 6:
            _guardrail_block = _guardrail_block + "\n\n" + _MID_FREEFLOW_SHAPE
        _guardrail_words = count_words(_guardrail_block)

    # S2-7 B2: declined-skills signal (consent integrity). On freeflow turns
    # (no skill step), when the user has declined skills this session, tell
    # freeflow which ones so it does not re-offer or walk through that specific
    # content in prose. Built BEFORE the L1 budget so its words deduct
    # proactively from L1 (same pattern as the offer block). Depends on
    # declined_skills (feature-branch state).
    #
    # MERGE NOTE (#4 ⊕ #8 ⊕ B2, 2026-06-13): unlike the guardrail, this note is
    # NOT suppressed on offer turns. It is an exclusion constraint ("do not
    # re-deliver these declined items"), not a competing response contract, so it
    # is compatible with the skill_offer framing. The offer pool itself already
    # excludes declined skills in skill_select; this note only protects the
    # freeflow prose path, and declined_words simply adds to the same proactive
    # L1 deduction alongside offer_words when both apply.
    _is_freeflow = not state.get("step_instruction") and not l2_intent_override
    _declined_ids = state.get("declined_skills") or []
    _declined_note = ""
    _declined_words = 0
    if _is_freeflow and _declined_ids:
        _declined_note = _build_declined_skills_note(_declined_ids, language)
        if _declined_note:
            _declined_words = count_words(_declined_note)

    # L1: Conversation history
    l1_budget = _compute_l1_budget(
        state,
        override_words=_override_words,
        guardrail_words=_guardrail_words,
        offer_words=_offer_words,
        declined_words=_declined_words,
    )
    # self_reference eviction-exemption: pin the recalled disclosure from the INITIAL build, not
    # only inside the overflow branch. Otherwise the normal L1 budget can drop the disclosure here,
    # which keeps total under budget, so the overflow branch (and its pin) never runs.
    _pin_turn = (_anchor_turn(state.get("conversation_history", []), _recall_text(state))
                 if state.get("self_reference") else None)
    l1_block = _build_l1_history_block(
        state.get("conversation_history", []),
        word_budget=l1_budget,
        conversation_summary=state.get("conversation_summary"),
        pin_turn=_pin_turn,
    )
    if l1_block:
        user_parts.append(l1_block)
        layers.append("history")

    # L2: Intent framing (always included per v7 §5.6)
    # When new_skill intent reaches freeflow with no matched skill, use the
    # unmatched-disclosure template (structural constraints: name disclosed content,
    # do not re-probe named emotions, offer space not solutions). Selector pending
    # Rule 1 approval — template is draft-pending-review.
    # Offer override: _offer_ids / _offer_block_str were precomputed above the
    # L1 budget call so the block is built exactly once per turn.
    if l2_intent_override:
        # Explicit L2 selection (e.g. the low_confidence node, whose routing is a
        # confidence outcome, not a primary_intent). Bypasses intent/offer-based
        # selection. Every other caller passes None => byte-identical behaviour.
        _l2_intent = l2_intent_override
        _l2_extra = None
        _l2_variant = None
    elif _offer_ids:
        _l2_intent = "skill_offer"
        _l2_extra = {"offer_options_block": _offer_block_str}
        # Repeat-offer variant: on the 2nd+ consecutive render of the same offer
        # (offer_count tracked across turns), switch to the lighter re-ask template
        # so the consent prompt does not read as a repeated script. Falls back to
        # the base skill_offer template automatically if the variant file is absent.
        _l2_variant = "reoffer" if (state.get("offer_count") or 0) >= 2 else None
    else:
        _l2_intent = (
            "new_skill_unmatched"
            if primary_intent == "new_skill" and not state.get("active_skill_id")
            else primary_intent
        )
        _l2_extra = None
        # Directive posture (deterministic flag from intent_route): when set on a general_chat
        # turn, select the stronger directive variant (lead with specific suggestions, do not
        # re-probe, no closing question). Falls back to base general_chat automatically if the
        # variant file is missing (get_intent_template returns the base on unknown variant).
        _l2_variant = "directive" if (state.get("directive_posture") and _l2_intent == "general_chat") else None
        # Repeat-info_request dampening (D4 amendment 2026-07-07). A single-intent info_request
        # closes with one open clarifying QUESTION (base template, Abby-style triage). On an
        # IMMEDIATELY-CONSECUTIVE info_request (prev turn also info_request = "lookup mode"),
        # switch to the statement-bridge "repeat" variant so a user in lookup mode is not
        # re-triaged every turn. "repeat" is strictly immediately-consecutive: any intervening
        # non-info_request turn resets prev_primary_intent and restores the question-close.
        # Falls back to the base template automatically if the variant file is absent.
        if _l2_intent == "info_request" and state.get("prev_primary_intent") == "info_request":
            _l2_variant = "repeat"
    l2_block = _build_l2_intent_block(
        _l2_intent, intensity, secondary_intent, variant=_l2_variant, extra_variables=_l2_extra
    )
    user_parts.append(l2_block)
    layers.append("intent")

    # Freeflow guided-protocol guardrail (S2-7 B1) — FREEFLOW TURNS ONLY.
    # Mirrors the freeflow discriminator used by _compute_l1_budget: a turn with no
    # step_instruction is freeflow (no active skill / no L3 step). On skill-execution
    # turns the executor legitimately delivers the protocol via the L3 step instruction,
    # so the guardrail must NOT fire there (it would conflict with L3). This is why the
    # block lives in the composer conditioned on freeflow, not in L0_persona.
    # The block was pre-built above; reuse the string to avoid building it twice.
    if _guardrail_block is not None:
        user_parts.append(_guardrail_block)
        layers.append("freeflow_guardrail")

    # Stall-guard recovery (freeflow only). The deterministic detector set the
    # flag in intent_route; here we direct the model to re-ground in prior context
    # rather than ask yet another open question. On skill turns the executor owns
    # the protocol, so this must not fire there.
    if _is_freeflow and state.get("stall_detected"):
        user_parts.append(_STALL_RECOVERY_INSTRUCTION)
        layers.append("stall_recovery")

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

    # S2-7 B2: inject the precomputed declined-skills note (built above the L1
    # budget). Reuses the freeflow-only string captured earlier so the note is
    # built exactly once per turn and its word count matches the budget
    # deduction. Wording is governed (declined_skills_instruction.json,
    # draft-pending-review).
    if _declined_note:
        user_parts.append(_declined_note)
        layers.append("declined_skills_signal")

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
        l4_block = _build_l4_knowledge_block(
            knowledge_passages,
            knowledge_abstain,
            allow_light_structure=_allow_light_structure(state),
        )
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
    # v7 §5.6.3: shrink history first. The conversation_summary is the compact
    # carrier of all older context and is trimmed LAST — it survives every
    # overflow unconditionally. The raw recent window is the elastic budget: it
    # shrinks (down to zero turns if necessary) so the summary always fits.
    # (Previously the shrink rebuilt L1 from the last raw turns and dropped the
    # summary, silently erasing older context on long freeflow turns.)
    total_words = count_words(system_str) + count_words_in_parts(user_parts)
    if total_words > _TOTAL_WORD_BUDGET and "history" in layers:
        history = state.get("conversation_history", [])
        summary = state.get("conversation_summary")
        l1_tmpl = get_template("L1_history")
        half_window = max(1, (l1_tmpl.window_size or 8) // 2)
        non_l1_words = total_words - count_words(user_parts[0])
        # On a recall turn, pin the disclosure the user is asking about so the shrink below
        # cannot evict it (vector 1). Reuse the pin computed for the initial build above.
        pin_turn = _pin_turn
        for raw_turns in range(half_window, -1, -1):
            recent = history[-raw_turns:] if raw_turns else []
            shrunk = _build_l1_history_block(
                recent,
                word_budget=300,    # conservative for overflow case
                conversation_summary=summary,
                pin_turn=pin_turn,
            ) or ""
            if non_l1_words + count_words(shrunk) <= _TOTAL_WORD_BUDGET or raw_turns == 0:
                break
        user_parts[0] = shrunk  # history is always index 0 when present (appended first)
        _log.warning(
            "Token budget overflow: L1 raw window shrunk to %d turns (summary preserved)",
            raw_turns,
        )
        # Recall turn where even the pinned disclosure + static layers exceed budget: keep the
        # disclosure (never drop the thing being recalled), but make it OBSERVABLE rather than
        # silently shipping over budget. Status sentinel is "status:"-prefixed so it is not read
        # as a content layer. Deviation from v7 §5.6.3 shrink order is flagged in the sign-off.
        # Structural resolution (trim L0) is the broader-bloat ticket, not this one.
        if pin_turn is not None and non_l1_words + count_words(shrunk) > _TOTAL_WORD_BUDGET:
            layers.append("status:prompt_over_budget")
            _log.warning(
                "self_reference recall over budget after pinning disclosure; kept disclosure, "
                "prompt over budget (L0 bloat, broader-bloat ticket)"
            )

    user_str = "\n\n".join(user_parts)
    return system_str, user_str, layers
