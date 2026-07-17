"""D1 — medical screening question (#338), deterministic core.

Spec L58/L101 discriminating quality-check for the AMBIGUOUS middle: a physical-symptom mention WITHOUT
an already-firing red-flag keyword. Architecture (V-signed 2026-07-17): conversational question (rendered
in flow, LLM), DETERMINISTIC consequence (this module). Language-contract: the trigger reads RAW input.

The question asks BOTH halves: the L101 acute symptom-QUALITY differentiation (panic vs emergency → 998) AND
the L194 CONTRAINDICATION disclosure (chronic heart condition / pregnancy → grounding, a routing fact not an
emergency). A clear_no on quality is NOT a clear on contraindications — a disclosed condition wins over it.

FAIL-SAFE INVARIANT: the screen routes AWAY, never CLEARS. Only `clear_no` proceeds; only a red-flag-quality
answer escalates to the guard; a disclosed contraindication and EVERY other class (and any unrecognised
class) default to the contraindication-free skill (grounding).
See docs/superpowers/governance/2026-07-17-d1-screening-question-build-spec.md.
"""
from __future__ import annotations

from sage_poc.safety.medical_redflag import detect_medical_redflag


# ── trigger (layered, recall-biased): physical symptom mentioned WITHOUT a red-flag keyword ──
# Recall-biased keyword net for the core; a BGE-M3 physical-symptom anchor tier is the integration
# addition (cast wider still — a false trigger only asks one gentle question). Reads RAW input.
_PHYS_TERMS = (
    "chest", "breath", "breathe", "breathing", "heart", "dizzy", "dizz", "faint", "numb", "tingl",
    "pain", "pressure", "tight", "palpitation", "pound", "racing", "weak", "in my body", "my body",
    "صدر", "تنفّس", "تنفس", "قلب", "دوخ", "خدر", "تنميل", "ألم", "ضغط", "نبض", "جسمي",
)


def is_physical_symptom_ambiguous(*texts: str) -> bool:
    """True when a physical symptom is mentioned but NO red-flag keyword already fired. That is the
    ambiguous middle the screen exists for; an explicit red-flag goes straight to the medical guard."""
    hay = " ".join(t for t in texts if t).lower()
    if not hay.strip():
        return False
    if detect_medical_redflag(hay):
        return False  # explicit red-flag → guard, not the screen
    return any(term in hay for term in _PHYS_TERMS)


# ── deterministic answer classifier ──
_RED_FLAG_ANSWER_MARKERS = (
    "spreading to my arm", "spreading to my jaw", "spreading to my back", "to my arm", "to my jaw",
    "one side", "one-sided", "numbness", "real trouble breathing", "can't breathe at all",
    "sharp", "crushing", "stabbing", "searing", "passed out",
)
# L194 contraindications: a disclosed CHRONIC/STABLE condition (heart / pregnancy). A routing fact, not an
# emergency, so it routes to grounding, NOT the 998 guard. Specific CONDITION phrases only (never bare
# "heart", which is a symptom word in the trigger) so a symptom mention like "my heart is racing" does not
# over-match. Reads RAW input (the answer is the user's own words).
_CONTRAINDICATION_MARKERS = (
    "heart condition", "heart problem", "heart disease", "cardiac", "pacemaker", "angina", "arrhythmia",
    "pregnant", "pregnancy",
    "مرض في القلب", "مرض القلب", "مشكلة في القلب", "مشكلة بالقلب", "مشاكل القلب", "حامل", "الحمل",
)
_CLEAR_NO_MARKERS = (
    "same as always", "nothing different", "not different", "feels the same", "just my usual",
    "just anxiety", "like usual", "the usual",
)
_UNCLEAR_MARKERS = ("both", "not sure", "don't know", "dont know", "idk", "hard to say", "no idea")
_YES_MARKERS = ("yes", "yeah", "yep", "kind of", "kinda", "a bit different", "little different",
                "seems different", "feels different", "bit off", "maybe")


def classify_screen_answer(text: str) -> str:
    """Map a user's answer to the screen into exactly one class:
    clear_no | red_flag | contraindication_disclosed | yes | unclear | no_answer. Order matters:
    red-flag ACUTE quality wins over everything (emergency); a disclosed chronic condition
    (heart/pregnancy) is next and MUST win over any surface 'no' (else "same as always, but I have a heart
    condition" collapses to clear_no and proceeds to TIPP); then plain negation-of-difference is clear_no;
    hedge/both/unknown is unclear. Reads the user's raw answer."""
    t = (text or "").strip().lower()
    if not t:
        return "no_answer"
    if detect_medical_redflag(t) or any(m in t for m in _RED_FLAG_ANSWER_MARKERS):
        return "red_flag"
    if any(m in t for m in _CONTRAINDICATION_MARKERS):
        return "contraindication_disclosed"     # L194: routes AWAY (grounding), never proceeds — beats clear_no
    if any(m in t for m in _CLEAR_NO_MARKERS) or t in ("no", "nope", "nah") or t.startswith(("no,", "no ", "nope")):
        return "clear_no"
    if any(m in t for m in _UNCLEAR_MARKERS):
        return "unclear"
    if any(m in t for m in _YES_MARKERS):
        return "yes"
    return "no_answer"  # topic-change / non-answer


# ── branch table + FAIL-SAFE default ──
_ROUTES = {"clear_no": "proceed", "red_flag": "medical_guard"}


def route_screen_answer(answer_class: str) -> str:
    """clear_no → proceed with the offered skill; red_flag → medical guard (998); contraindication_disclosed
    (L194 chronic heart/pregnancy) → grounding, a routing fact not an emergency; EVERYTHING ELSE → grounding.
    The `.get(..., 'grounding')` default IS the fail-safe: an unmapped/unknown class can never reach
    'proceed'. contraindication_disclosed rides that default BY DESIGN — it is deliberately absent from
    _ROUTES so it can never acquire a 'proceed' path by edit. The screen routes away, never clears."""
    return _ROUTES.get(answer_class, "grounding")


# ── placeholder guard: the QUESTION text is unservable until Vee's signed bytes land ──
class UnsignedScreenError(RuntimeError):
    """Raised when the screen question is requested before its wording is clinician-signed. The mechanism
    is inert (routes to grounding fail-safe by default) until this lifts — a half-built screen must never
    serve an unsigned question."""


# Populated ONLY from signed_clinical_fields.json on Vee's tick (per-language). Empty = unsigned = unservable.
# Per-language fail-safe: until an entry exists for a language, that language gets grounding-only for
# acute-overwhelm (no screen in a language whose answers/question aren't signed).
_SIGNED_QUESTIONS: dict[str, str] = {}


def is_screen_ready(lang: str) -> bool:
    """True iff the screen question for `lang` is signed and servable."""
    return lang in _SIGNED_QUESTIONS


def screen_question(lang: str) -> str:
    if lang not in _SIGNED_QUESTIONS:
        raise UnsignedScreenError(
            f"D1 screen question for lang={lang!r} is unsigned — unservable until Vee ticks the signed "
            f"bytes (#338, signed_clinical_fields.json). AR holds grounding-only until its own tick."
        )
    return _SIGNED_QUESTIONS[lang]


# ── wiring: the injection decision (skill_select calls this) ──────────────────────────────
# Acute skills with physical contraindications (spec L194). Extend as future skills are flagged.
CONTRAINDICATED_SKILLS = frozenset({"dbt_tipp"})

_ACTION_FOR_ROUTE = {"proceed": "proceed", "medical_guard": "to_medical_guard", "grounding": "reroute_grounding"}


class ScreenAuditError(RuntimeError):
    """Raised when the screen audit row cannot be written. #160 alert-or-fail: a swallowed screen_asked
    write is a contraindication decision with NO record — the PDPL exposure the D-item exists to close.
    Never swallow it."""


def decide_screen(routed_skill: str, state: dict) -> dict:
    """Session-persistent injection decision. Returns {action, [session_screen_answer], [audit]}.

    action ∈ ask_screen | proceed | reroute_grounding | to_medical_guard | abandon_crisis.

    (2) CRISIS SUPREMACY (defense-in-depth): crisis this turn abandons the screen — the answer is never
        classified as unclear→grounding; the crisis path owns it, abandonment is audited.
    (1) SESSION-PERSISTENT: `session_screen_answer` persists across turns (per-session). clear_no once →
        proceed on every later contraindicated routing without re-asking; any not-cleared prior → grounding.
    """
    crisis = (not state.get("is_safe", True)) or bool(state.get("crisis_flags"))
    pending = bool(state.get("screen_pending"))
    contraindicated = routed_skill in CONTRAINDICATED_SKILLS

    if crisis and (pending or contraindicated):
        return {"action": "abandon_crisis",
                "audit": {"screen_asked": False, "screen_answer_class": None, "screen_branch_taken": "abandoned_crisis"}}

    # answering a pending screen (this turn's raw text is the answer)
    if pending:
        cls = classify_screen_answer(state.get("raw_message", ""))
        route = route_screen_answer(cls)
        return {"action": _ACTION_FOR_ROUTE[route], "session_screen_answer": cls,
                "audit": {"screen_asked": False, "screen_answer_class": cls, "screen_branch_taken": route}}

    # non-contraindicated skill never screens
    if not contraindicated:
        return {"action": "proceed"}

    # fresh routing to a contraindicated skill — honour the session-persistent prior answer
    prior = state.get("session_screen_answer")
    if prior == "clear_no":
        return {"action": "proceed"}                 # cleared this session; no re-ask
    if prior is not None:
        return {"action": "reroute_grounding"}        # screened, not cleared → grounding (fail-safe); no re-ask
    return {"action": "ask_screen",                    # never screened this session → ask
            "audit": {"screen_asked": True, "screen_answer_class": None, "screen_branch_taken": None}}


def write_screen_audit(row: dict, writer) -> None:
    """Write the screen audit row (screen_asked / screen_answer_class / screen_branch_taken) via `writer`.
    #160 alert-or-fail: on any failure, raise ScreenAuditError — never swallow. A contraindication decision
    that isn't recorded cannot be defended under the PDPL right-to-object."""
    try:
        writer(row)
    except Exception as exc:  # noqa: BLE001 — deliberately loud
        raise ScreenAuditError(
            f"D1 screen audit write FAILED — contraindication decision with no record (PDPL exposure): {exc}"
        ) from exc


# ── call-site: skill_select post-processor (FLAG-GATED, byte-identical when off) ──────────────
def apply_screen_at_route(state: dict, result: dict) -> dict:
    """Post-process a skill_select routing result. THE FLAG BOUNDARY: when SAGE_D1_SCREEN is off this is
    IDENTITY — decide_screen is never called, no channel is touched, `result` is returned unchanged.

    Positioned AFTER the safety vetoes in skill_select, so it respects the supremacy chain by construction:
    crisis > vetoes > containment > screen > routing. A veto result (active_skill_id=None) is never a
    contraindicated-skill situation, so no screen is asked and no screen state is written.
    """
    from sage_poc import config  # read at call time so the flag is honoured/monkeypatchable
    if not config.D1_SCREEN_ENABLED:
        return result  # ── identity: the off-path writes nothing ──

    pending = bool(state.get("screen_pending"))
    resolved = result.get("active_skill_id") or (result.get("offered_skill_ids") or [None])[0]
    if not pending and resolved not in CONTRAINDICATED_SKILLS:
        return result  # not a screen situation (covers every veto result: resolved is None)

    lang = (state.get("detected_language") or "en").lower()
    d = decide_screen(resolved or "", state)
    action = d["action"]
    audit = d.get("audit", {})
    out = dict(result)
    for k in ("screen_asked", "screen_answer_class", "screen_branch_taken"):
        if audit.get(k) is not None:
            out[k] = audit[k]
    if "session_screen_answer" in d:
        out["session_screen_answer"] = d["session_screen_answer"]

    if action == "ask_screen":
        try:
            out["screen_question_text"] = screen_question(lang)   # signed → serve it
            out.update({"active_skill_id": None, "offered_skill_ids": None, "screen_pending": True})
            return out
        except UnsignedScreenError:
            action = "reroute_grounding"  # unsigned → per-language fail-safe default

    if action == "proceed":
        out["screen_pending"] = False
        return out
    if action == "to_medical_guard":
        out.update({"active_skill_id": None, "offered_skill_ids": None, "screen_pending": False,
                    "medical_flags": list(state.get("medical_flags") or []) + ["screen_red_flag"]})
        return out
    # reroute_grounding / abandon_crisis → fail-safe (grounding, or nothing for crisis; crisis path owns it)
    out.update({"active_skill_id": None if action == "abandon_crisis" else "grounding_5_4_3_2_1",
                "offered_skill_ids": None, "screen_pending": False})
    return out
