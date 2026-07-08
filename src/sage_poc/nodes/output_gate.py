import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from sage_poc.state import SageState
from sage_poc.language import async_translate_to_arabic
from sage_poc.config import AUDIT_LOG_ENABLED, CRISIS_LINE_UAE, CRISIS_CONFIG, CLASSIFIER_MODEL
from sage_poc.llm import get_classifier
from sage_poc.rules import engine as rules_engine
from sage_poc.prompts.summarizer import summarise_history
from sage_poc.audit import write_session_audit, write_identity_substitution_audit

_log = logging.getLogger(__name__)

_FLAG_CONFIG_PATH = Path(__file__).parent.parent / "rules" / "data" / "flag_lifecycle_config.json"
with _FLAG_CONFIG_PATH.open() as _f:
    _FLAG_LIFECYCLE_CONFIG: dict = json.load(_f)
_CROSS_SESSION_FLAGS: dict[str, bool] = _FLAG_LIFECYCLE_CONFIG.get("cross_session_persistence", {})

# #58 / #65 INTERIM: clinical-flag detection is keyword-only and fails open on naturalistic phrasing
# (issue #65). Per clinical-lead sign-off 2026-06-25, the opener rewrite must NOT rely on the flag
# firing: suppress (pass through) on a broader sensitive-topic lexicon OR on elevated distress. This is
# mitigation, not resolution — the real fix is the semantic tier (#65). Lexicon contents are a DRAFT
# pending clinical-lead confirmation; over-matching is acceptable (it only costs a soft opener, the
# direction Decision 2 endorsed). This gate touches the rewrite ONLY — it does not set clinical_flags
# or drive the 24h escalation.
_SENSITIVE_LEXICON_PATH = Path(__file__).parent.parent / "rules" / "data" / "safety" / "sensitive_topic_suppression_lexicon.json"
with _SENSITIVE_LEXICON_PATH.open() as _f:
    _SENSITIVE_LEXICON_RAW: dict = json.load(_f)
_SENSITIVE_LEXICON_CATS: dict = _SENSITIVE_LEXICON_RAW.get("categories", {})
# English phrases matched against the user message (English) + the candidate reply; Arabic phrases
# matched against the original raw message (the bilingual gap lives in MT fidelity, so match AR directly).
_SENSITIVE_TOPIC_PHRASES_EN: tuple[str, ...] = tuple(
    p.lower() for _cat in _SENSITIVE_LEXICON_CATS.values() for p in _cat.get("en", [])
)
_SENSITIVE_TOPIC_PHRASES_AR: tuple[str, ...] = tuple(
    p for _cat in _SENSITIVE_LEXICON_CATS.values() for p in _cat.get("ar", [])
)

# W4 — pinned AR mood-rating anchor. The numeric-anchor clause (واحد يعني صعب جدا وعشرة يعني ممتاز)
# is emitted VERBATIM from mood_check_in.json, never through the translate step — that step is where
# it corrupted into identical anchors ("1 means very good, 10 means very good"). This is the fallback
# template for the deterministic score_mood guard below. One instrument; generalise when a second exists.
_MOOD_SKILL_PATH = Path(__file__).parent.parent / "skills" / "mood_check_in.json"
try:
    with _MOOD_SKILL_PATH.open(encoding="utf-8") as _mf:
        _MOOD_SKILL_RAW: dict = json.load(_mf)
    _MOOD_STEPS = _MOOD_SKILL_RAW.get("steps") or next(
        (v for v in _MOOD_SKILL_RAW.values() if isinstance(v, list)
         and any(isinstance(x, dict) and x.get("step_id") == "score_mood" for x in v)), [])
    _MOOD_PINNED_TEMPLATE_AR: str = next(
        s["pinned_template_ar"] for s in _MOOD_STEPS if s.get("step_id") == "score_mood")
    _MOOD_PINNED_ANCHOR_AR: str = next(
        s["pinned_anchor_ar"] for s in _MOOD_STEPS if s.get("step_id") == "score_mood")
    _MOOD_PINNED_SCALE_AR: str = next(
        s["pinned_scale_ar"] for s in _MOOD_STEPS if s.get("step_id") == "score_mood")
except Exception:  # pragma: no cover — config error surfaces at import
    _MOOD_PINNED_TEMPLATE_AR = ""
    _MOOD_PINNED_ANCHOR_AR = ""
    _MOOD_PINNED_SCALE_AR = ""

# Each scale endpoint's descriptor: the phrase after يعني ("means"), up to " و <digit>" / punctuation.
_MOOD_ANCHOR_RX = re.compile(r"يعني\s+(.+?)(?=\s+و\s+[\d٠-٩]|\s*[،,.؟?]|$)")
# A 1-10 scale is being presented when the high endpoint (10 / ١٠) appears as a standalone number.
_MOOD_SCALE_RX = re.compile(r"(?<![\d٠-٩])(?:10|١٠)(?![\d٠-٩])")


def _has_identical_rating_anchors(text: str) -> bool:
    """True when two scale endpoints "mean" the same phrase — the translate-step corruption."""
    descs = [re.sub(r"\s+", " ", m.group(1)).strip() for m in _MOOD_ANCHOR_RX.finditer(text)]
    return len(descs) >= 2 and len(descs) != len(set(descs))


def _pin_mood_anchor(text: str, executed_step_id: str | None, lang: str) -> str:
    """Node-8 post-check (W4, signed §K + G5-b Option C). On an AR score_mood turn the canonical
    anchored 1-10 scale is ALWAYS present — the instrument is administered by the step, not at the
    LLM's discretion (Cardinal Rule 3; B8/AlHadi: a scale is valid only as administered). The LLM
    renders the warm Khaleeji invitation; the scale clause is verbatim, never reworded/paraphrased:
      1. corrupt/non-monotonic anchors (translate corruption) -> full pinned template  [defense].
      2. canonical anchors already present verbatim                 -> unchanged.
      3. some other numeric scale present (LLM paraphrased it)      -> full pinned template.
      4. warm wrapper with no scale (the common prod case)          -> append the canonical clause.
    No-op for other steps and other languages."""
    if executed_step_id != "score_mood" or lang != "ar" or not _MOOD_PINNED_TEMPLATE_AR:
        return text
    if _has_identical_rating_anchors(text):        # 1. defense: corruption -> pinned template
        return _MOOD_PINNED_TEMPLATE_AR
    if _MOOD_PINNED_ANCHOR_AR in text:             # 2. already carries the verbatim anchors
        return text
    if _MOOD_SCALE_RX.search(text):                # 3. LLM presented a non-canonical scale -> canonical
        return _MOOD_PINNED_TEMPLATE_AR
    return text.rstrip() + " " + _MOOD_PINNED_SCALE_AR  # 4. warm wrapper only -> append canonical scale
_OPENER_REWRITE_DISTRESS_CEILING = 9  # severe distress (9-10/10) -> suppress rewrite (pass through);
# the lexicon is the primary sensitive-content gate, this is a wording-independent backstop for the top of the scale


def _rewrite_suppressed_reason(message_en: str, response_en: str, emotional_intensity,
                               raw_message: str = "") -> str | None:
    """Interim sensitive-content guard for the opener rewrite (#65). Returns a suppression reason
    ('sensitive_topic' | 'high_distress') or None. Independent of, and in addition to, the
    clinical_flags / crisis_flags guards — it catches naturally-worded disclosures the keyword
    flags miss, in English (via message_en/response_en) and Khaleeji Arabic (via the raw message).
    Errs toward suppression by design."""
    try:
        intensity = int(emotional_intensity)
    except (TypeError, ValueError):
        intensity = 0
    if intensity >= _OPENER_REWRITE_DISTRESS_CEILING:
        return "high_distress"
    haystack_en = f"{message_en or ''} {response_en or ''}".lower()
    if any(phrase in haystack_en for phrase in _SENSITIVE_TOPIC_PHRASES_EN):
        return "sensitive_topic"
    if raw_message and any(phrase in raw_message for phrase in _SENSITIVE_TOPIC_PHRASES_AR):
        return "sensitive_topic"
    return None

SCOPE_REFUSAL_RESPONSE = (
    "That's a question better answered by a medical professional or licensed therapist. "
    "I want to make sure you get accurate information. I can help you think through "
    "how you're feeling about it, or find some general information. Would either of those help?"
)

_FORMAT_VIOLATIONS = re.compile(
    r"—"                            # em dash
    r"|\*\*"                        # bold markdown
    r"|["
    r"\U0001F300-\U0001F9FF"        # misc symbols, emoticons, transport, flags
    r"\U00002600-\U000027BF"        # misc symbols (weather, chess, etc.)
    r"\U0001FA00-\U0001FAFF"        # extended symbols and pictographs
    r"]"
)

# T6 (DEV-2026-06-19-C) — deterministic output-format strip. Load-bearing since the
# GPT-primary decision (DEV-B, 2026-06-20): the model prior is fixed and not retrainable
# in-house, so this Node 8 gate is the PRIMARY style guarantee, not a backstop. It enforces
# the L0 "plain prose, no markdown/emoji/dashes" rule deterministically on the live turn
# (which was previously log-only — see _FORMAT_VIOLATIONS above), while preserving the L4
# light-structure permission (newlines + numbered/hyphen lists).
_TRIPLE_EMPHASIS_RE = re.compile(r"\*\*\*(.+?)\*\*\*")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# Italic: a * only opens/closes emphasis at a word boundary (not attached to a word char).
# Unicode \w covers Arabic, so lone citation markers ("note*", "المصدر*") never open emphasis,
# even when several appear on one line. Emphasis edges must be non-space (CommonMark-ish).
_ITALIC_RE = re.compile(r"(?<![\w*])\*(\S(?:[^*\n]*?\S)?)\*(?![\w*])")
_EMOJI_STRIP_RE = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF]"
)
_EMDASH_SPACED_RE = re.compile(r"\s*—\s*")
_QUOTED_SPAN_RE = re.compile(r"[\"“][^\"”]*[\"”]")


def _strip_output_format(text: str) -> str:
    """Deterministically remove banned style tokens from an outgoing turn.

    Removes paired ***/**/* emphasis and emoji. Replaces em-dash with ", " OUTSIDE quoted
    spans only, so a cited passage that legitimately contains an em-dash is not corrupted
    (T6 false-positive guard). Lone "*" (citation/footnote markers) and newlines + numbered/
    hyphen lists are preserved.

    DESIGN DECISION flagged for the T6 owner / clinical confirm (see the L4 spec, T6):
      - em-dash quote-awareness is the chosen policy for the false-positive guard.
    The *italic* rule is word-boundary anchored (Unicode \\w), so lone citation markers in
    either language and any number of them on a line are preserved; only true *emphasis* at
    word boundaries is stripped (pinned by tests).
    """
    if not text:
        return text
    text = _TRIPLE_EMPHASIS_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _EMOJI_STRIP_RE.sub("", text)
    out: list[str] = []
    last = 0
    for m in _QUOTED_SPAN_RE.finditer(text):
        out.append(_EMDASH_SPACED_RE.sub(", ", text[last:m.start()]))
        out.append(m.group(0))  # quoted span preserved verbatim (cited content)
        last = m.end()
    out.append(_EMDASH_SPACED_RE.sub(", ", text[last:]))
    return "".join(out)

# Question-discipline (Node 8, deterministic). MIND-SAFE: one question at a time, never
# stack. Cannot be a cultural_output rule (that schema is blocklist/allowlist substitute
# only — see rules/schemas.py), so it lives here as structural logic.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?؟])\s+")
# Anchor-safe: the leading \s* was redundant (\s ⊂ [^.!?]) and its overlap with [^.!?]*
# inside the repeated group caused catastrophic backtracking (ReDoS) on replies with many
# '?' clauses and a non-question tail — a synchronous freeze of the single-replica event
# loop. Groups are uniquely delimited by '?', so this form is linear and behaviourally identical.
# Updated to include Arabic question mark (؟) for language-aware discipline.
_TRAILING_QUESTION_RE = re.compile(r"(?:[^.!?؟]*[?؟])+\s*$")


def _limit_to_one_question(text: str) -> str:
    """Keep at most one question sentence (the first); drop later question sentences.
    Statements are preserved in order. No-op when 0 or 1 question. Never returns empty."""
    if not text or (text.count("?") + text.count("؟")) <= 1:
        return text
    out, seen_q = [], False
    for sent in _SENT_SPLIT_RE.split(text.strip()):
        if sent.rstrip().endswith(("?", "؟")):
            if seen_q:
                continue
            seen_q = True
        out.append(sent)
    result = " ".join(out).strip()
    return result if result else text


def _strip_trailing_question(text: str) -> str:
    """Drop trailing question sentence(s) so an advice turn ends on substance. Returns the
    original unchanged if stripping would empty the turn (whole turn was a question)."""
    if not text or ("?" not in text and "؟" not in text):
        return text
    stripped = _TRAILING_QUESTION_RE.sub("", text).rstrip()
    return stripped if stripped else text


_BANNED_OPENER_PATTERNS: list[str] = [
    r"it sounds like\b",
    r"that sounds (really |very |incredibly |quite )?(tough|hard|difficult|painful|overwhelming|exhausting|challenging|frustrating|lonely|scary|frightening)\b",
    r"it seems like\b",
    r"i can hear (that|how|the)\b",
    r"i can see (that|how)\b",
    r"it looks like\b",
    # Sycophantic praise-openers. Moved here from the L0 prompt in L0 v2.0.0 (2026-06-14):
    # the persona switched to positive framing (prompt best practice + clinical sign-off), so the
    # hard guarantee against these must live at the gate, alongside the reflective-filler patterns
    # above. These were previously prompt-only and NOT gate-enforced; this closes that gap.
    r"that's (really |so |very |genuinely )?(great|good|wonderful|lovely|nice|amazing) to hear\b",
    r"it's (really |so )?(great|good|wonderful) to hear\b",
    r"i'm (really |so )?(glad|happy|pleased) to hear\b",
    # Sympathy-opener family. Added 2026-06-14 after the stock-opener RCA: the prior
    # list caught reflective fillers and praise but NOT "I'm sorry to hear ...", the most
    # common distress-response default. These are high-precision openers (anchored at ^),
    # so a mid-reply "I'm sorry, could you say more" is unaffected. See
    # docs/superpowers/audits/2026-06-14-stock-opener-rca.md
    r"i'm sorry to hear\b",
    r"i'm sorry you\b",
    r"i'm sorry that\b",
    r"i'm so sorry\b",
    r"sorry to hear\b",
]
_BANNED_OPENER_RE = re.compile(
    r"(?i)^(" + "|".join(_BANNED_OPENER_PATTERNS) + r")"
)
_HAS_ARABIC_RE = re.compile(r"[؀-ۿ]")
# Arabic-output English-bleed guard (feedback #4). Latin alphabetic runs of length >= 3 that
# are not known acronyms/brands indicate an untranslated English word in an Arabic reply.
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")
_LATIN_ALLOWLIST = {"cbt", "act", "dbt", "tipp", "sage", "youtube"}


def _has_english_bleed(text: str) -> bool:
    return any(w.lower() not in _LATIN_ALLOWLIST for w in _LATIN_WORD_RE.findall(text))


_BANNED_OPENER_CORRECTION = (
    "Your previous response began with a banned opener. "
    "Respond again without beginning with 'It sounds like', 'That sounds', or any "
    "reflective paraphrase. Name the specific thing the user said and ask one direct question."
)

# PLACEHOLDER — pending clinical review before Gitex.
# Constraints: (1) must NOT begin with a banned or near-banned opener (regex or structural),
# (2) Khaleeji wellness-companion register — warm, open-ended, never "I cannot respond to that",
# (3) safe to emit on any turn including after heavy disclosure (not dismissive),
# (4) must work in EN and AR turns (translation pipeline still runs on this string),
# (5) treat as user-facing copy with measurable frequency, not a rare error message.
# Review doc: docs/superpowers/reviews/FALLBACK_RESPONSE_REVIEW.md
_VETTED_FALLBACK_RESPONSE = "I'm here with you, and what you've shared matters. Take a moment, I'm listening whenever you're ready."

# #58 — opener rewrite (register-preserving fix). DRAFT copy pending clinical sign-off
# (docs/superpowers/reviews/2026-06-24-banned-opener-rewrite-signoff.md). No em dashes.
_OPENER_REWRITE_TIMEOUT = 4.0  # fail fast -> pass-through; never block the turn on a non-critical edit
_OPENER_REWRITE_SYSTEM = (
    "You are lightly editing one wellness-companion reply that you wrote. It began with a "
    "reflective or sympathy cliche we avoid. Rewrite ONLY the opening so it names the specific "
    "thing the person said, warm and present, one to one. "
    # Register guardrails folded into the OPERATIVE instruction (clinical advisory 2026-06-24):
    # the register standard is only enforced if it is in the prompt the model actually receives.
    "Reflect only what the person actually expressed. Do not name or assign a strong emotion they "
    "did not state, and keep any inference tentative. Do not restate distressing or graphic detail. "
    "Keep the emotional intensity the same as the original, neither heavier nor lighter. "
    "Keep every following sentence exactly as written. Do not add advice, do not add a question, "
    "do not change the length or the meaning. Use plain prose, commas not dashes, no emojis. "
    "Return only the full revised reply."
)


def _opener_rewrite_user(user_message_en: str, response_en: str, opener: str) -> str:
    return (
        f"The person said: {user_message_en}\n\n"
        f"Your reply (revise only the opening, keep the rest verbatim): {response_en}\n\n"
        f"The banned opener you used and must replace: {opener}"
    )


async def _rewrite_opener(response_en: str, opener: str, user_message_en: str) -> str:
    """Rewrite only the banned opening of an existing reply via the classifier model,
    preserving the rest. Returns "" on timeout/failure (caller passes the original through).

    Deliberately NOT wrapped in resilient_invoke: its fixed 30s x 2 timeout under the 55s graph
    ceiling is a SERVER_ERROR vector on the ~27% of turns that fire. A slow rewrite must degrade
    to pass-through, so this uses a short asyncio.wait_for with no retries -- pass-through is the
    safe fallback. asyncio.TimeoutError is an Exception subclass; CancelledError is NOT and is
    correctly not swallowed."""
    if not response_en:
        return ""
    try:
        msg = await asyncio.wait_for(
            get_classifier().ainvoke([
                {"role": "system", "content": _OPENER_REWRITE_SYSTEM},
                {"role": "user", "content": _opener_rewrite_user(user_message_en, response_en, opener)},
            ]),
            timeout=_OPENER_REWRITE_TIMEOUT,
        )
        return msg if isinstance(msg, str) else (getattr(msg, "content", None) or "")
    except Exception:
        return ""

# Re-surface resources if a MONITORING (post-crisis) turn would otherwise return blank.
# A silent turn during crisis monitoring is the worst failure mode; commas only (no em dash).
_EMPTY_MONITORING_FALLBACK = (
    "I'm still here with you. If things get harder, please reach out right now, "
    f"the UAE MoHAP support line on {CRISIS_LINE_UAE}, or {CRISIS_CONFIG['emergency']} for an emergency."
)

JAILBREAK_RESPONSE = (
    "I'm Sage, a wellness companion here to offer emotional support and evidence-based coping "
    "techniques. That's my role. What's been on your mind today?"
)


async def _log_clinical_review(
    session_id: str,
    user_id: str,
    crisis_flags: list[str],
    clinical_flags: list[str],
    *,
    severity_override: str | None = None,
    reason_override: str | None = None,
) -> None:
    """Deterministic clinician review log: fires when Layer 1 safety rules detected flags.
    source='layer1_safety' distinguishes this from the LLM tool path.
    severity='high' for crisis, 'medium' for clinical-only (DB constraint: low/medium/high).
    severity_override/reason_override support the v7.1 G1b path (a T1 warm turn writes ONE
    'low' cumulative-distress flag, never a 'high' crisis review).
    """
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if not pool:
            return
        severity = severity_override or ("high" if crisis_flags else "medium")
        reason_parts = []
        if crisis_flags:
            reason_parts.append(f"crisis flags: {', '.join(crisis_flags)}")
        if clinical_flags:
            reason_parts.append(f"clinical flags: {', '.join(clinical_flags)}")
        notifier = PostgresNotifier(pool)
        await notifier.notify_review_required(
            user_id=user_id,
            session_id=session_id,
            reason=reason_override or "; ".join(reason_parts),
            source="layer1_safety",
            payload={"flags": crisis_flags + clinical_flags},
            severity=severity,
        )
    except Exception as exc:
        _log.warning("[output_gate] _log_clinical_review failed: %s", exc)


async def _write_persisted_clinical_flags(
    user_id: str,
    clinical_flags: list[str],
) -> None:
    """Write cross-session-eligible flags to user_therapeutic_profiles.
    Gated by flag_lifecycle_config.json cross_session_persistence values.
    Non-fatal — errors are logged only.
    """
    flags_to_persist = [f for f in clinical_flags if _CROSS_SESSION_FLAGS.get(f, False)]
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if pool is None:
            return
        repo = PostgresMemoryRepository(pool)
        await repo.write_persisted_clinical_flags(user_id, flags_to_persist)
    except Exception as exc:
        _log.warning("[output_gate] write_persisted_clinical_flags failed: %s", exc)


async def _persist_session_summary(
    session_id: str,
    user_id: str,
    summary_text: str,
    crisis_flags: list[str],
    clinical_flags: list[str],
    skills_used: list[str] | None = None,
    mood_score: float | None = None,
) -> None:
    """Persist session summary to database. Non-fatal — errors are logged only."""
    try:
        from server import app  # noqa: PLC0415
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
        from sage_poc.memory.embedding import get_embedding_async  # noqa: PLC0415
        pool = getattr(app.state, "_db_pool", None)
        if pool is None:
            return
        embedding = await get_embedding_async(summary_text)
        safety_level = (
            "crisis" if crisis_flags
            else "clinical" if clinical_flags
            else "normal"
        )
        repo = PostgresMemoryRepository(pool)
        await repo.save_session_summary(
            session_id, user_id, summary_text, embedding, safety_level,
            skills_used=skills_used,
            mood_score=mood_score,
        )
    except Exception:
        _log.warning("Failed to persist session summary for session %s", session_id)
    # Flag persistence is intentionally decoupled from session summary persistence.
    # A summary write failure must not block flag persistence: persisted_clinical_flags
    # feeds safety_check at the start of the next session (Cardinal Rule 4 path) and
    # must be written regardless of whether the summary write succeeded.
    try:
        await _write_persisted_clinical_flags(user_id, clinical_flags)
    except Exception as exc:
        _log.warning("[output_gate] write_persisted_clinical_flags failed: %s", exc)


async def output_gate_node(state: SageState) -> dict:
    gate_path = state.get("gate_path")
    # Per-turn latency for session_audit. turn_started_at is stamped before ainvoke (server.py);
    # output_gate is the last node, so now - turn_started_at captures ~the full graph turn. Folded
    # into state here so every write_session_audit({**state, ...}) below picks it up. None-safe:
    # unit tests and any path without the stamp simply leave latency_ms unset (NULL in audit).
    _turn_started_at = state.get("turn_started_at")
    if _turn_started_at is not None:
        state = {**state, "latency_ms": int((time.monotonic() - _turn_started_at) * 1000)}
    lang = state["detected_language"]

    # v7.1 tiering disposition (reader table): a T1 (warm) turn carries crisis_flags=["s3_semantic"]
    # but is NOT a crisis review — because T2 bypasses output_gate, these branches are dead flag-OFF,
    # so excluding T1 here is what stops a T1 turn filing a HIGH-severity crisis review every turn.
    # T1 is governed instead by G1b (one 'low' cumulative-distress flag on the 2nd T1 of a session).
    import sage_poc.config as _cfg  # noqa: PLC0415
    _is_t1_turn = bool(_cfg.CRISIS_TIERING_ENABLED and state.get("crisis_tier") == "T1")
    _review_crisis_flags = [] if _is_t1_turn else (state.get("crisis_flags") or [])
    path = (state.get("path") or []) + ["output_gate"]
    session_id = state.get("session_id")
    user_id = state.get("user_id")

    if gate_path == "scope_refusal":
        response_en = SCOPE_REFUSAL_RESPONSE
    elif gate_path == "jailbreak":
        response_en = JAILBREAK_RESPONSE
    else:
        response_en = state["response_en"] or ""

    # Empty-reply fail-safe (RC-6 / feedback #2). Fires on the FIRST attempt too (the existing
    # retry-only substitution below only covers banned_opener_retry_count >= 1). A monitoring
    # turn re-surfaces resources rather than a generic line; never return silence.
    if not response_en and gate_path not in ("scope_refusal", "jailbreak"):
        if state.get("crisis_state") == "monitoring":
            response_en = _EMPTY_MONITORING_FALLBACK
        else:
            response_en = _VETTED_FALLBACK_RESPONSE
        path = path + ["output_gate_empty_fallback"]
        _log.warning(
            "[output_gate] empty response substituted (crisis_state=%s, session=%s)",
            state.get("crisis_state"), session_id,
        )

    _arabic_chars = len(_HAS_ARABIC_RE.findall(response_en))
    _total_chars = len(response_en.strip())
    _response_en_is_arabic = (
        lang == "ar"
        and gate_path not in ("scope_refusal", "jailbreak")
        and _total_chars > 0
        and (_arabic_chars / _total_chars) > 0.4
    )
    if _response_en_is_arabic:
        _log.warning(
            "[output_gate] response_en is predominantly Arabic "
            "(ratio=%.2f, session=%s, gate=%s) -- "
            "skipping EN validators and translation; audit for CU-DM-001 regression",
            _arabic_chars / _total_chars, session_id, gate_path,
        )

    if gate_path not in ("scope_refusal", "jailbreak"):
        cultural_violations = rules_engine.evaluate("cultural_output", {
            "response_text": response_en,
            "message_en": state.get("message_en", ""),
            "clinical_flags": state.get("clinical_flags", []),
        })
        _identity_sub_rule_id: str | None = None
        _original_response_hash: str | None = None
        _original_response_text: str | None = None
        for rule in cultural_violations.fired:
            _log.warning(
                "[output_gate] cultural violation %s v%s: %s",
                rule.rule_id, rule.version,
                rule.action.get('message', rule.action.get('type', '')),
            )
            if rule.action.get("type") == "substitute" and _identity_sub_rule_id is None:
                _original_response_text = response_en
                _original_response_hash = hashlib.sha256(response_en.encode()).hexdigest()[:16]
                _identity_sub_rule_id = rule.rule_id
                response_en = rule.action["substitute_with"]
                _log.warning(
                    "[output_gate] Rule %s substituted response (hash: %s)",
                    rule.rule_id, _original_response_hash,
                )
                # Write full original text to restricted PDPL audit table (non-fatal).
                # The main audit log records only the hash; the original text lives here
                # under RLS policies permitting DPO and clinician_admin access only.
                if session_id:
                    asyncio.create_task(
                        write_identity_substitution_audit(
                            session_id=session_id,
                            turn_number=state.get("turn_number", 0),
                            rule_id=rule.rule_id,
                            original_response_hash=_original_response_hash,
                            original_response_text=_original_response_text,
                            substitute_with=rule.action["substitute_with"],
                            user_id=user_id,
                        )
                    )
        cultural_output_violations = [r.rule_id for r in cultural_violations.fired]
    else:
        _identity_sub_rule_id = None
        _original_response_hash = None
        _original_response_text = None
        cultural_output_violations = []

    banned_opener_violation = False
    banned_opener_fallback_used = False
    # Substitute fallback on empty retry response — the second LLM call can return "" due to
    # rate limiting, token-budget overflow, or other transient failures. Empty is not valid
    # wellness-companion copy; treat it the same as an exhausted-retry banned opener.
    _retry_count = state.get("banned_opener_retry_count", 0)
    if (
        not response_en
        and _retry_count >= 1
        and gate_path not in ("scope_refusal", "jailbreak")
    ):
        response_en = _VETTED_FALLBACK_RESPONSE
        banned_opener_fallback_used = True
        path = path + ["output_gate_fallback_substituted"]
        _log.warning("[output_gate] empty response on retry — substituting vetted fallback")
        if session_id:
            _empty_audit = asyncio.create_task(
                write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"})
            )
            _empty_audit.add_done_callback(
                lambda t: _log.warning("[output_gate] empty-retry audit error: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )
    # #58: register-preserving opener fix. ALLOWLIST (not blocklist) so the rewrite only ever touches
    # ordinary freeflow replies. scope_refusal/jailbreak keep their clinician-authored copy; crisis
    # never reaches output_gate (crisis route => END) -- the crisis_flags check is belt-and-suspenders.
    # SUPPRESS on clinical_flags (trauma_indicator, domestic_situation, substance_use, eating_concern,
    # psychotic_disclosure, ...) -- clinical advisory 2026-06-24, Decision 1b (conservative default).
    # The external model must not re-word the most delicate openers; flagged replies pass through
    # unchanged (a soft opener is the lesser harm than an unsupervised rewrite that could mislabel
    # affect or re-state trauma, which the deterministic re-check cannot catch). Revisitable per-flag
    # once an LLM register evaluator + stratified human review over the flagged subset are live.
    opener_rewrite_audit = None
    if (
        gate_path in (None, "standard")
        and not state.get("crisis_flags")
        and not state.get("clinical_flags")
        and response_en and not _response_en_is_arabic
    ):
        banned_match = _BANNED_OPENER_RE.match(response_en.lstrip())
        if banned_match:
            opener = banned_match.group(0)
            # INTERIM #65 guard (clinical-lead sign-off 2026-06-25): the clinical_flags check above
            # is keyword-only and fails open on naturalistic phrasing. Do not rely on it — also suppress
            # the rewrite on a broader sensitive-topic lexicon or elevated distress, passing the real
            # reply through unchanged. Mitigation, not resolution (#65 semantic tier is the real fix).
            suppress_reason = _rewrite_suppressed_reason(
                state.get("message_en", ""), response_en, state.get("emotional_intensity"),
                raw_message=state.get("raw_message", ""),
            )
            if suppress_reason:
                path = path + ["output_gate_opener_suppressed_sensitive"]
                opener_rewrite_audit = {"applied": False, "model": CLASSIFIER_MODEL, "opener": opener,
                                        "latency_ms": 0, "suppressed": suppress_reason}
                banned_opener_violation = True  # reply ships with the soft opener intact (audit accuracy)
                _log.info("[output_gate] opener rewrite suppressed (%s); passing original reply through", suppress_reason)
                banned_match = None  # fall through without rewrite
        if banned_match:
            _t0 = time.monotonic()
            rewritten = await _rewrite_opener(response_en, opener, state.get("message_en", ""))
            _rw_ms = int((time.monotonic() - _t0) * 1000)
            # LOAD-BEARING deterministic re-check (ABSOLUTE RULE 1): the LLM proposes, _BANNED_OPENER_RE
            # disposes, failure falls back to deterministic pass-through. Do NOT remove this re-check.
            if rewritten and not _BANNED_OPENER_RE.match(rewritten.lstrip()):
                response_en = rewritten
                path = path + ["output_gate_opener_rewritten"]
                opener_rewrite_audit = {"applied": True, "model": CLASSIFIER_MODEL, "opener": opener, "latency_ms": _rw_ms}
            else:
                # Pass the model's REAL reply through (a soft opener is the lesser evil) rather than a
                # content-free placeholder. The canned fallback is reserved for empty generations.
                path = path + ["output_gate_opener_passthrough"]
                banned_opener_violation = True
                opener_rewrite_audit = {"applied": False, "model": CLASSIFIER_MODEL, "opener": opener, "latency_ms": _rw_ms}
                _log.warning("[output_gate] opener rewrite unavailable; passing original reply through")

    # Question discipline (deterministic). Global on freeflow turns: collapse stacked
    # questions to one (MIND-SAFE: one question at a time). Directive turns additionally end
    # on substance, not a question. Runs on English text before translation so the Arabic
    # render inherits the cleaned text.
    # SAFETY CARVE-OUT: NEVER run on a crisis/monitoring turn — a monitoring turn can carry
    # a safety question ("Are you safe right now?") as the 2nd question, which collapse would
    # strip. crisis_response already bypasses output_gate (graph.py END edge); this guards the
    # monitoring path that DOES transit here. D1: also skip skill-execution turns
    # (step_instruction set) so clinician-authored L3 step questions are never overridden.
    if (
        gate_path not in ("scope_refusal", "jailbreak")
        and state.get("crisis_state") in (None, "none")
        and not state.get("step_instruction")
        and response_en
    ):
        _disciplined = _limit_to_one_question(response_en)
        if state.get("directive_posture") and not (state.get("offered_skill_ids")):
            _disciplined = _strip_trailing_question(_disciplined)
        if _disciplined != response_en:
            response_en = _disciplined
            path = path + ["question_discipline_applied"]

    # Invariant: user-visible offer ⇔ promotable state (S1-1a). If the vetted
    # fallback replaced an offer created THIS turn ("skill_offer_made" is in this
    # turn's path; state["path"] is per-turn, reset by _build_state), the user never
    # saw the offer options, so the offer must not stay promotable in the checkpoint.
    # An offer from an EARLIER turn (already seen by the user) is left alone;
    # re-rendering it next turn is correct there.
    _offer_voided = False
    # #58: the invariant fires whenever a fallback hid an offer the user never saw. Pre-#58 the
    # only such path was the retry-exhausted banned-opener substitution (banned_opener_fallback_used);
    # that path was removed (banned openers are now rewritten / passed through, which PRESERVE the
    # offer text). The surviving displacing path is the empty fail-safe, so the trigger is re-homed
    # to it (banned_opener_fallback_used kept for any residual/legacy path; now ~always False).
    if (
        ("output_gate_empty_fallback" in path or banned_opener_fallback_used)
        and state.get("offered_skill_ids")
        and "skill_offer_made" in state.get("path", [])
    ):
        _offer_voided = True
        path = path + ["offer_voided_fallback"]
        _log.warning(
            "[output_gate] fallback replaced an offer-creating turn; voiding unseen offer %s",
            state.get("offered_skill_ids"),
        )

    response_en = _strip_output_format(response_en)
    violations = _FORMAT_VIOLATIONS.findall(response_en)
    if violations:
        # Now telemetry only: anything surviving the deterministic strip (e.g. a stray
        # em-dash preserved inside a quoted span) — not a leak to act on.
        _log.warning("[output_gate] format tokens after strip: %s", violations)

    if lang == "ar" and not _response_en_is_arabic:
        # §5 served-arm latency timer: brackets ONLY the translate-out operation (plus its
        # strict-retry, when it fires) -- not the surrounding gate work (cultural check,
        # format strip, audit build). Same time.monotonic() idiom as latency_ms.
        _translate_t0 = time.monotonic()
        final_response = await async_translate_to_arabic(response_en)
        if _has_english_bleed(final_response):
            _log.warning("[output_gate] English bleed in Arabic output; re-translating strict")
            final_response = await async_translate_to_arabic(response_en, strict=True)
            path = path + ["arabic_token_guard_retranslate"]
            if _has_english_bleed(final_response):
                _log.warning("[output_gate] English bleed persists after strict re-translate (telemetry only)")
        state = {**state, "translate_out_ms": int((time.monotonic() - _translate_t0) * 1000)}
    else:
        final_response = response_en
    final_response = _strip_output_format(final_response)

    # W4 (signed §K): pin the AR mood-rating anchor. Primary — a presented scale without anchors gets
    # the verbatim clause concatenated (never un-anchored). Defense — identical anchors (translate
    # corruption) fall back to the pinned template. AR score_mood turns only.
    final_response = _pin_mood_anchor(final_response, state.get("executed_step_id"), lang)

    if AUDIT_LOG_ENABLED:
        audit = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": state.get("turn_count", 0),
            "path": path,
            "gate_path": gate_path or "standard",
            "detected_language": lang,
            "primary_intent": state.get("primary_intent"),
            "active_skill": state.get("active_skill_id") or state.get("completed_skill_id"),
            "skill_match_method": state.get("skill_match_method"),
            "prepass_rule_id": state.get("prepass_rule_id"),  # v7.2 Node-2 keyword pre-pass provenance
            "semantic_score": state.get("semantic_score"),
            "executed_step": state.get("executed_step_id"),
            "next_step": state.get("active_step_id"),
            "emotional_intensity": state.get("emotional_intensity"),
            "engagement": state.get("engagement"),
            "is_safe": state.get("is_safe"),
            "crisis_state": state.get("crisis_state", "none"),
            "s7_result": state.get("s7_result"),
            "s7_method": state.get("s7_method"),
            "clinical_flags": state.get("clinical_flags", []),
            "third_party_crisis": state.get("third_party_crisis", False),
            "escalation": state.get("escalation_triggered"),
            "knowledge_source": state.get("knowledge_source", ""),
            "knowledge_passage_ids": [
                p.get("source_id") for p in (state.get("knowledge_passages") or [])
            ],
            "knowledge_abstain": state.get("knowledge_abstain", False),
            "knowledge_query_raw": state.get("knowledge_query_raw", ""),
            "knowledge_query_searched": state.get("knowledge_query_searched", ""),
            "knowledge_top_similarity": state.get("knowledge_top_similarity"),
            "identity_substitution": (
                {"rule_id": _identity_sub_rule_id, "original_response_hash": _original_response_hash}
                if _identity_sub_rule_id else None
            ),
            "banned_opener_violation": banned_opener_violation,
        }
        _log.info("[output_gate] AUDIT %s", json.dumps(audit))

        if state.get("clinical_flags"):
            _log.info("[output_gate] clinical flags: %s", ', '.join(state['clinical_flags']))
        if state.get("escalation_triggered"):
            esc = state["escalation_triggered"]
            _log.warning("[output_gate] escalation L%s: %s", esc['level'], esc['reason'])

    new_history = state.get("conversation_history", []) + [
        {"role": "user", "content": state["message_en"]},
        {"role": "assistant", "content": response_en},
    ]

    next_turn = state.get("turn_count", 0) + 1
    new_summary = state.get("conversation_summary")
    if next_turn % 10 == 0:
        try:
            new_summary = await summarise_history(new_history)
            _log.info("Conversation summary generated at turn %d", next_turn)
        except Exception:
            _log.warning("Summarisation failed at turn %d; keeping prior summary", next_turn)
        if new_summary and session_id and user_id:
            _task = asyncio.create_task(
                _persist_session_summary(
                    session_id, user_id, new_summary,
                    _review_crisis_flags,  # T1 excluded: a warm turn is not a 'crisis' session
                    state.get("clinical_flags", []),
                    skills_used=(
                        [state["active_skill_id"]] if state.get("active_skill_id")
                        else [state["completed_skill_id"]] if state.get("completed_skill_id")
                        else []
                    ),
                    mood_score=float(state.get("emotional_intensity", 5)),
                )
            )
            _task.add_done_callback(
                lambda t: _log.warning("[output_gate] summary persist error: %s", t.exception())
                if not t.cancelled() and t.exception() else None
            )

    _clinical_flags = state.get("clinical_flags") or []
    # T1 is excluded from crisis review via _review_crisis_flags (disposition table).
    if (_review_crisis_flags or _clinical_flags) and session_id and user_id:
        _review_task = asyncio.create_task(
            _log_clinical_review(session_id, user_id, _review_crisis_flags, _clinical_flags)
        )
        _review_task.add_done_callback(
            lambda t: _log.warning("[output_gate] clinical review error: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    # G1b (v7.1): exactly ONE low-severity cumulative-distress flag on the 2nd T1 turn of a
    # session — not the 1st, not the 3rd, never high-severity. t1_count is set in safety_check.
    if _is_t1_turn and state.get("t1_count") == 2 and session_id and user_id:
        _g1b_task = asyncio.create_task(
            _log_clinical_review(
                session_id, user_id, [], [],
                severity_override="low",
                reason_override="cumulative warm-tier (T1) distress: 2nd of session",
            )
        )
        _g1b_task.add_done_callback(
            lambda t: _log.warning("[output_gate] G1b review error: %s", t.exception())
            if not t.cancelled() and t.exception() else None
        )

    _audit_task = asyncio.create_task(write_session_audit({**state, "path": path, "gate_path": gate_path or "standard"}))
    _audit_task.add_done_callback(
        lambda t: _log.warning("[output_gate] session audit error: %s", t.exception())
        if not t.cancelled() and t.exception() else None
    )

    result = {
        "response": final_response,
        "response_en": response_en,
        "gate_path": gate_path or "standard",
        "path": path,
        "turn_count": next_turn,
        # Persist THIS turn's intent as next turn's prev, for consecutive-info_request
        # ("lookup mode") detection in the composer. Mirrors prev_step_id: lives in
        # SageState, absent from _build_state, so it survives via the checkpoint.
        "prev_primary_intent": state.get("primary_intent"),
        "conversation_history": new_history,
        "conversation_summary": new_summary,
        "cultural_output_violations": cultural_output_violations,
        "identity_substitution_rule_id": _identity_sub_rule_id,
        "original_response_hash": _original_response_hash,
        "original_response_text": _original_response_text,
        "last_turn_at": datetime.now(timezone.utc).isoformat(),
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
        "banned_opener_violation": banned_opener_violation,
        "banned_opener_fallback_used": banned_opener_fallback_used,
        "opener_rewrite": opener_rewrite_audit,  # #58 traceability; persisted via Step 3b migration
    }
    if _offer_voided:
        # Key included only when voiding so a normal turn's channel merge never
        # clobbers an offer set by skill_select this turn or pending from earlier.
        result["offered_skill_ids"] = None
    return result
