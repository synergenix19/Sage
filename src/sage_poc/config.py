import logging
import os
from dotenv import load_dotenv

load_dotenv()

_log = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLASSIFIER_MODEL = os.getenv("SAGE_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
RESPONDER_MODEL = os.getenv("SAGE_RESPONDER_MODEL", "openai/gpt-4o")
TRANSLATOR_MODEL = os.getenv("SAGE_TRANSLATOR_MODEL", "openai/gpt-4o-mini")
FALLBACK_RESPONDER_MODEL = os.getenv("SAGE_FALLBACK_RESPONDER_MODEL", "openai/gpt-4o")
FALLBACK_CLASSIFIER_MODEL = os.getenv("SAGE_FALLBACK_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
# Resistance scoring requires a sovereign/calibrated model separate from the general classifier.
# Set SAGE_RESISTANCE_MODEL to a local Falcon-3B endpoint before production.
# Defaults to CLASSIFIER_MODEL so the existing .env value acts as interim fallback.
RESISTANCE_MODEL = os.getenv("SAGE_RESISTANCE_MODEL", CLASSIFIER_MODEL)

# Default ON — crisis activations must leave an audit trail unless explicitly disabled.
AUDIT_LOG_ENABLED = os.getenv("SAGE_AUDIT_LOG", "true").lower() == "true"

# UAE crisis helpline — the SINGLE source for every crisis-copy site. Crisis-copy files carry
# {{crisis_*}} placeholders (not literals), resolved from this dict at load (crisis_copy.py); the
# graph/output_gate Python fail-safes read it directly. Change a value HERE and every surface
# follows — a true single-config edit. Defense in depth: the boot guard (server.py lifespan) fails
# the app if any {{crisis_*}} stays unresolved, and the conformance test asserts the resolved output
# carries this value. Frontend mirror: cdai apps/web/lib/crisis-config.ts (cross-stack test).
# CRISIS_RESOURCES — structured resource directory (H4). CRISIS_CONFIG below is DERIVED from this
# list (primary national + emergency entries), so every existing consumer keeps working unchanged.
# ✅ VALUES ADOPTED 2026-07-10 (ALL GATES CLEARED): the doc's verified composition is now LIVE.
#   - Dial-test confirmed all 5 numbers 2026-07-10; GL-1 reversal confirmed; crisis-freeze lifted;
#     clinical sign-off (Vee). The prior "800 46342 / 24/7" verified-final set is SUPERSEDED — the
#     dial-test is the primary record and it resolved the 46342-vs-4673 question in favour of the
#     National Mental Support Line (800-HOPE / 800-4673, 8am-8pm daily).
#   - CRISIS_CONFIG.number is therefore now the NATIONAL line (8am-8pm), NOT a 24/7 number. This is
#     SAFE ONLY because the frontend multi-resource crisis card (coupled PR) always renders a 24/7
#     line (999 + SAKINA + DHA) alongside it; select_crisis_resources() below guarantees a 24/7
#     option is present in the top set at every hour (property-tested). Do not surface the single
#     derived number alone on any always-open surface.
#   - If a value ever changes, change this ONE list; every surface follows.
# select_crisis_resources() implements the doc lead-logic + always-pair-24/7 (never leads with a
# closed line, always includes a dialable 24/7 option regardless of the clock).
CRISIS_RESOURCES = [
    {"name": "National Mental Support Line", "number": "800-HOPE (800-4673)", "hours": "8am–8pm daily", "scope": "national"},
    {"name": "Emergency Services", "number": "999", "hours": "24/7", "scope": "emergency"},
    {"name": "Abu Dhabi 24/7 crisis line", "number": "800-SAKINA (800-725462)", "hours": "24/7", "scope": "regional"},
    {"name": "Dubai Health Authority helpline", "number": "800 111", "hours": "24/7", "scope": "regional"},
    {"name": "Sharjah Child & Youth Mental Health Helpline", "number": "800 51115", "hours": "9am–5pm Mon–Fri", "scope": "youth"},
    {"name": "Nearest hospital emergency department", "number": "999 / nearest ER", "hours": "immediate danger or outside helpline hours", "scope": "emergency"},
]


def _hours_window(hours: str):
    """(start, end) 24h ints for a 'Nam-Mpm' daily window; None for 24/7 or unparseable (both
    treated as always-available so a parse failure never hides a resource)."""
    import re  # noqa: PLC0415
    if not hours or "24/7" in hours:
        return None
    m = re.search(r"(\d{1,2})\s*(am|pm)\s*[-–]\s*(\d{1,2})\s*(am|pm)", hours.lower())
    if not m:
        return None

    def _to24(h, ap):
        return int(h) % 12 + (12 if ap == "pm" else 0)

    return (_to24(m.group(1), m.group(2)), _to24(m.group(3), m.group(4)))


def _is_out_of_hours(hours: str, now) -> bool:
    win = _hours_window(hours)
    if win is None:
        return False
    start, end = win
    return not (start <= now.hour < end)


def select_crisis_resources(resources=None, *, immediate_danger: bool = False, now=None) -> list[dict]:
    """Ordered crisis-card resources (BOT BEHAVIOUR lead-logic L2146 + hours-awareness).

    immediate_danger -> emergency (999) leads. Otherwise the national line leads IF open, else a
    24/7 alternative leads (never lead with a closed line). The result ALWAYS contains a 24/7 option
    (999 is 24/7), so the card is never left with only an out-of-hours number regardless of the
    clock. `now` defaults to Asia/Dubai wall-clock; injectable for deterministic tests.
    """
    from datetime import datetime  # noqa: PLC0415
    from zoneinfo import ZoneInfo  # noqa: PLC0415
    resources = list(resources if resources is not None else CRISIS_RESOURCES)
    if now is None:
        now = datetime.now(ZoneInfo("Asia/Dubai"))

    def _is_247(r):
        return _hours_window(r.get("hours", "")) is None

    def _open(r):
        return not _is_out_of_hours(r.get("hours", ""), now)

    emergency = [r for r in resources if r.get("scope") == "emergency"]
    national = [r for r in resources if r.get("scope") == "national"]
    others = [r for r in resources if r.get("scope") not in ("emergency", "national")]

    ordered: list[dict] = []
    if immediate_danger:
        ordered += emergency
    open_national = [r for r in national if _open(r)]
    if open_national:
        ordered += open_national
    else:  # national closed -> lead with a 24/7 alternative, not the closed line
        ordered += [r for r in (others + national) if _is_247(r)]
    for r in national + others + emergency:
        if r not in ordered:
            ordered.append(r)
    # always-pair guarantee: at least one 24/7 line must be present (999 is 24/7).
    if emergency and not any(_is_247(r) or r.get("scope") == "emergency" for r in ordered):
        ordered += emergency
    return ordered


def _primary_resource() -> dict:
    return next((r for r in CRISIS_RESOURCES if r.get("scope") == "national"), CRISIS_RESOURCES[0])


def _emergency_resource() -> dict:
    return next((r for r in CRISIS_RESOURCES if r.get("scope") == "emergency"), CRISIS_RESOURCES[-1])


# Back-compat shim: CRISIS_CONFIG stays the four-key dict every consumer expects, DERIVED from the
# primary national + emergency entries. Byte-identical to the prior literal while the values are the
# current verified set (so crisis_copy placeholders, the graph/output_gate fail-safes, and the
# byte-identical/conformance/cross-stack tests are all unchanged).
CRISIS_CONFIG = {
    "number": _primary_resource()["number"],
    "label": _primary_resource()["name"],
    "hours": _primary_resource()["hours"],
    "emergency": _emergency_resource()["number"],
}
# Back-compat alias for existing importers during the migration.
CRISIS_LINE_UAE = CRISIS_CONFIG["number"]

# v7.1 crisis tiering (G1). Default ON as of 2026-07-03 (product-owner directive executing signed
# item A; migration 006 must be applied in every target env first). ON -> _route_after_safety routes
# on crisis_tier (T2 crisis / T1 warm). The env var is now a KILL-SWITCH: set SAGE_CRISIS_TIERING=false
# to instantly revert to v7/master byte-identical behaviour (no redeploy/revert-PR on the crisis path).
# Default flipped to bypass a Railway env-injection bug (configured var not reaching containers);
# see docs/superpowers/governance/2026-07-03-clinician-signoff-packet.md.
# STRICT FAIL-SAFE kill-switch parse (2026-07-03): only a LITERAL "false" disables tiering. Unset /
# empty / whitespace / garbage -> the signed default (ON). A Railway env-injection bug delivered an
# EMPTY string to the container, which under a `== "true"` parse silently flipped the crisis path OFF
# to a state nobody signed. This inverts that: disabling the crisis-tier routing now requires INTENT.
_tiering_raw = os.getenv("SAGE_CRISIS_TIERING")
CRISIS_TIERING_ENABLED = not (_tiering_raw is not None and _tiering_raw.strip().lower() == "false")
if _tiering_raw is not None and _tiering_raw.strip().lower() not in ("true", "false"):
    _log.warning(
        "SAGE_CRISIS_TIERING unexpected value %r — applying signed default (tiering ON); "
        "only 'false' disables.", _tiering_raw,
    )
# Boot-observable log of the resolved state lives in server.py lifespan (guaranteed-visible after
# logging is configured): "[sage/startup] CRISIS_TIERING_ENABLED=... raw_env=...".

# B0 — BOT BEHAVIOUR §4.5 deterministic safety-route precedence (crisis>medical>hr>ipv).
# KILL-SWITCH, DEFAULT OFF. Unlike CRISIS_TIERING (signed, defaults ON), this is a NEW,
# not-yet-ratified mechanism: OFF must be byte-identical v7/master. So the strict parse INVERTS
# — only a LITERAL "true" enables; unset / empty / whitespace / garbage -> OFF (safe default).
# That default also survives the Railway empty-string env-injection bug (empty -> OFF -> current
# routing), the same class of failure that motivated the tiering strict parse above. Flipping ON
# is the governed step gated on the §4.5 clinical-lead signature + each route's ≥95% recall gate;
# the resolver and its wiring may land (OFF) before those clear.
_precedence_raw = os.getenv("SAGE_ROUTE_PRECEDENCE")
ROUTE_PRECEDENCE_ENABLED = (
    _precedence_raw is not None and _precedence_raw.strip().lower() == "true"
)
if _precedence_raw is not None and _precedence_raw.strip().lower() not in ("true", "false"):
    _log.warning(
        "SAGE_ROUTE_PRECEDENCE unexpected value %r — applying safe default (precedence OFF); "
        "only 'true' enables.", _precedence_raw,
    )

# E7 — BOT BEHAVIOUR §6a coercive-control / relationship-safety pre-emption. KILL-SWITCH, DEFAULT
# OFF, same inverted strict parse as ROUTE_PRECEDENCE: only a LITERAL "true" enables; unset / empty /
# whitespace / garbage -> OFF. OFF is byte-identical v7 — only the approved CF-005 domestic_situation
# lexicon fires (passive referral). ON -> the 19 §6a-guard expansion phrases also fire domestic_situation
# and drive the active §6 (coaching_confrontation) pre-emption. Flip is governed: E7 recall >=95% on the
# fixture set + clinician CMS approval (Rohan's CF-005 workflow is the precedent) before permanent ON,
# at which point the expansion folds into CF-005 vNext and this flag-gated side-path retires.
_ipv_preempt_raw = os.getenv("SAGE_IPV_PREEMPTION")
IPV_PREEMPTION_ENABLED = (
    _ipv_preempt_raw is not None and _ipv_preempt_raw.strip().lower() == "true"
)
if _ipv_preempt_raw is not None and _ipv_preempt_raw.strip().lower() not in ("true", "false"):
    _log.warning(
        "SAGE_IPV_PREEMPTION unexpected value %r — applying safe default (pre-emption OFF); "
        "only 'true' enables.", _ipv_preempt_raw,
    )

# Knowledge abstain gates. RRF is pure RANK fusion: its minimum meaningful score is
# 1/(k+1) = 1/61 = 0.0164 (k=60), and the whole top-5 single-list range (1/61..1/65 =
# 0.0164..0.0154) sits ABOVE 0.015, so KNOWLEDGE_ABSTAIN_THRESHOLD at 0.015 can NEVER
# abstain (verified 2026-07-03: 0/12 off-domain queries abstained). It is retained as a
# SECONDARY per-passage guard only; the AUTHORITATIVE abstain decision is the cosine gate
# below. Proper fix = reranker (#45) + calibration at the corpus >100 gate.
KNOWLEDGE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD", "0.015"))

# Authoritative abstain gate: cosine SIMILARITY (1 - pgvector distance) of the best passage
# in the returned evidence pack. Abstain when best similarity < threshold. Default 0.0 is
# FAIL-OPEN (never abstains = pre-fix behaviour); deploy sets SAGE_COSINE_ABSTAIN_THRESHOLD
# to the calibrated value (spec 2026-07-03 Appendix A). Set to 0.0 to roll back instantly.
COSINE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_COSINE_ABSTAIN_THRESHOLD", "0.0"))

# Skill-routing precision (feedback #6). A runner-up (second offer) must be strong AND close
# to the primary, else only the primary is offered. Defaults conservative; confirm with clinical.
SKILL_RUNNER_UP_MIN = float(os.getenv("SAGE_SKILL_RUNNER_UP_MIN", "0.50"))
SKILL_RUNNER_UP_MARGIN = float(os.getenv("SAGE_SKILL_RUNNER_UP_MARGIN", "0.05"))

# Offer cooldown: suppress a fresh skill offer for N turns after one was made (D3 4a).
# Value is the fallback when the skill_matching default_offer rule omits cooldown_turns.
SKILL_OFFER_COOLDOWN_TURNS = int(os.getenv("SAGE_SKILL_OFFER_COOLDOWN_TURNS", "2"))

# Offer-cooldown enable gate (GATED — default OFF). The cooldown is clinical-facing
# behaviour (it changes when/whether Sage re-offers a coping skill), so it ships inert
# and merging it does NOT make it live. Flipping SAGE_SKILL_OFFER_COOLDOWN_ENABLED=true
# is an explicit, logged, signed decision gated on clinical sign-off C3 (cooldown N), the
# same control the merge would have been — not an auto-flip. Decouples merge timing from
# C3 timing without bypassing C3.
SKILL_OFFER_COOLDOWN_ENABLED: bool = os.getenv("SAGE_SKILL_OFFER_COOLDOWN_ENABLED", "false").lower() == "true"

# D5 deterministic acuity gate (GATED — default OFF, pending standalone clinical sign-off).
# When enabled, _intensity_guidance() returns a validate-only string at/above the floor:
# name the specific thing said, stay purely supportive, do NOT challenge a distorted belief.
# Floor default 8 matches the executor validate_only floor (emotional_intensity > 7, v7 §9.2 rule 1).
# Floor/band gap (clinical decision): intensity == 7 is in the high band but below floor=8,
# so it gets standard high guidance, NOT the D5 challenge-suppress. Set SAGE_D5_ACUITY_FLOOR=7
# to cover the full high band; pin the value at the standalone clinical sign-off.
D5_ACUITY_GATE_ENABLED: bool = os.getenv("SAGE_D5_ACUITY_GATE", "false").lower() == "true"
D5_ACUITY_FLOOR: int = int(os.getenv("SAGE_D5_ACUITY_FLOOR", "8"))

# Tier 0 native-Arabic register measurement. Ships INERT: when on, generates a
# second native-Khaleeji response written ONLY to shadow_register_eval and NEVER
# served or placed in SageState. See docs/superpowers/plans/2026-07-07-native-arabic-shadow-measure.md
NATIVE_ARABIC_SHADOW_ENABLED: bool = os.getenv("SAGE_NATIVE_ARABIC_SHADOW", "false").lower() == "true"

# Connection-pool ceilings (feedback #9). POC ran asyncpg max_size=5 and httpx keepalive=5,
# which throttled under the 58-user load behind the p95 latency. Raise + make env-configurable.
DB_POOL_MAX_SIZE = int(os.getenv("SAGE_DB_POOL_MAX_SIZE", "20"))
HTTP_MAX_CONNECTIONS = int(os.getenv("SAGE_HTTP_MAX_CONNECTIONS", "100"))
HTTP_MAX_KEEPALIVE = int(os.getenv("SAGE_HTTP_MAX_KEEPALIVE", "20"))

# Checkpointer (saver_pool) ceiling — SEPARATE from DB_POOL_MAX_SIZE above. The de3caab
# "raise pools" change lifted the asyncpg memory pool but left the LangGraph checkpointer
# pool at psycopg's default (min=max=4). That pool is touched on EVERY turn (checkpoint read
# at server.py + LangGraph's per-turn write), so 4 is the real per-turn concurrency ceiling.
# Raise to match the asyncpg pool. NOTE (Supabase/Supavisor): safe at 20 when the checkpointer
# runs through the TRANSACTION-mode pooler (port 6543) via CHECKPOINT_DATABASE_URL — 20 client
# slots then multiplex over Supavisor's smaller server pool (prepare_threshold=None in server.py
# is already set for exactly this). In SESSION mode (port 5432) each slot holds a persistent
# server connection, so total = (checkpoint + asyncpg) x replicas; size against the Supabase
# tier's pool_size / connection cap and the Railway replica count before raising.
CHECKPOINT_POOL_MAX_SIZE = int(os.getenv("SAGE_CHECKPOINT_POOL_MAX_SIZE", "20"))

# EMBED-CACHE (arch §20.2): dedupe the BGE-M3 query encode of message_en shared by S3
# (Layer 1 crisis) and skill_select Tier 2. The cache PRIMITIVE always exists (the
# equivalence gate tests it directly); this flag gates only the WIRING into check_s3 /
# skill_select, so EMBED-CACHE before/after is one build with a flag flip (same discipline
# as the ① pool measurement). Default on — shipped only because the equivalence gate
# (test_embed_cache_equivalence.py) asserts crisis output is byte-identical with the cache.
EMBED_CACHE_ENABLED: bool = os.getenv("SAGE_EMBED_CACHE_ENABLED", "true").lower() == "true"

# B1 interim medical red-flag guard. Default OFF; flip only when the must-NOT-fire
# controls are green (see plan Task 6). Not frozen; touches no signed field.
MEDICAL_REDFLAG_GUARD_ENABLED: bool = os.getenv("SAGE_MEDICAL_REDFLAG_GUARD", "false").lower() == "true"

# HR-1 Stage 1: gates mania_disclosure / dissociation_disclosure HR-class
# routing (psychotic_disclosure routing is unconditional and unaffected by
# this flag; see safety/hr_disclosure.py). Default OFF.
HIGH_RISK_DETECTION_ENABLED: bool = os.getenv("SAGE_HIGH_RISK_DETECTION", "false").lower() == "true"

# Q1-terminal default: the MEDICAL guard wording (doc lines 62/81/131 / Section 6):
# "prompt to seek in-person/medical/emergency evaluation; treat as a possible medical
# emergency." NOT doc L1477 (that is the psychiatric-crisis line rule, a different guard).
# NUMBER: lead with 998 = UAE AMBULANCE. 999 is UAE POLICE and must NOT lead a medical/cardiac
# emergency (the earlier "999" default was inherited from the psychiatric-crisis Resources
# table, where police co-response is appropriate). The crisis pathway's 999 is unchanged;
# this is the MEDICAL terminal only. Regression-guarded by test_medical_referral_uses_998.
# PROVENANCE (do not overclaim): 998=ambulance / 999=police are the standard published UAE
# emergency numbers (PO-sourced + flagged 2026-07-15). A documented verification record —
# dial-test or cited authority, per the GL-1 crisis-number precedent — is a PRE-FLIP gate,
# tracked in the crisis/medical numbers verification ticket. Do not flip on the comment alone.
# Single blocking parameter, pending clinician ratification of wording.
MEDICAL_REFERRAL_TEXT: str = os.getenv(
    "SAGE_MEDICAL_REFERRAL_TEXT",
    "The symptoms you're describing can be signs of a medical emergency. "
    "Please seek in-person medical evaluation now. Call 998 (ambulance) in the UAE, "
    "or go to the nearest emergency department. I'm not able to assess "
    "physical symptoms, and this needs a medical professional right away.",
)
# F6 venting-suppression authority. Default OFF; changes live routing (Routing-SF-2).
VENTING_SUPPRESSION_ENABLED: bool = os.getenv("SAGE_VENTING_SUPPRESSION", "false").lower() == "true"
D1_SCREEN_ENABLED: bool = os.getenv("SAGE_D1_SCREEN", "false").lower() == "true"  # #338 medical screen; default-OFF (flag-off == identity routing)

# HR-1 Stage 2 (docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md):
# migrates HR delivery out of the LLM-rendered psychotic_referral skill into a
# dedicated deterministic two-turn node (high_risk_response). KILL-SWITCH, DEFAULT
# OFF, same inverted strict parse as ROUTE_PRECEDENCE_ENABLED above: only a LITERAL
# "true" enables; unset / empty / whitespace / garbage -> OFF. Distinct from
# HIGH_RISK_DETECTION_ENABLED (Stage 1, gates which HR classes route here at all) so
# the Stage-2 delivery upgrade can flip independently of Stage-1 detection. OFF =
# Stage-1 behavior (byte-identical). Flip is governed: clinician sign-off on the
# §HR fixed copy below + the two-turn state-machine design.
_hr_terminal_raw = os.getenv("SAGE_HIGH_RISK_TERMINAL")
HIGH_RISK_TERMINAL_ENABLED = (
    _hr_terminal_raw is not None and _hr_terminal_raw.strip().lower() == "true"
)
if _hr_terminal_raw is not None and _hr_terminal_raw.strip().lower() not in ("true", "false"):
    _log.warning(
        "SAGE_HIGH_RISK_TERMINAL unexpected value %r — applying safe default (terminal OFF); "
        "only 'true' enables.", _hr_terminal_raw,
    )

# §HR fixed copy (verbatim from the design doc's "Fixed copy" section) has moved to
# src/sage_poc/safety/hr_copy.py: each single string below is now a POOL of
# clinician-ratifiable variants (HR_DISTRESS_QUESTION_POOL, HR_SUPPORTIVE_MESSAGE_POOL,
# HR_REDIRECT_HIGHER_POOL, HR_REDIRECT_LOWER_POOL, HR_REASK_POOL), picked
# deterministically per (session_id, slot_key) by hr_copy.pick_hr_variant -- still
# SINGLE-SOURCED, still never LLM-rendered, no runtime randomness. The pools are marked
# DRAFT pending clinician ratification (mirrors CF-007/008/009's active:false/unsigned
# convention); SAGE_HIGH_RISK_TERMINAL stays default-OFF until sign-off. The
# high_risk_response node reads from hr_copy, not from literals here.

# Psychoed Mechanism-A (docs/superpowers/specs/2026-07-17-psychoed-mechanism-a-design.md):
# gates skill_select.py's info_request-branch consult (keyword+semantic matching against
# INFO_REQUEST_SKILL_CONSULT_SET before the KB short-circuit). KILL-SWITCH, DEFAULT OFF,
# same inverted strict parse as ROUTE_PRECEDENCE_ENABLED above: only a LITERAL "true"
# enables; unset / empty / whitespace / garbage -> OFF (survives the Railway empty-string
# env-injection bug). OFF must be byte-identical to today's info_request -> knowledge_retrieve
# path: the consult matching never runs, no skill is ever selected via
# "info_request_skill_consult", so graph.py's _route_after_skill_select diversion to
# skill_executor is unreachable. Flip is governed: clinician sign-off on the consult set's
# disposition scoping (INFO_REQUEST_SKILL_CONSULT_SET) per the design doc.
_info_request_consult_raw = os.getenv("SAGE_INFO_REQUEST_CONSULT")
INFO_REQUEST_CONSULT_ENABLED = (
    _info_request_consult_raw is not None and _info_request_consult_raw.strip().lower() == "true"
)
if _info_request_consult_raw is not None and _info_request_consult_raw.strip().lower() not in ("true", "false"):
    _log.warning(
        "SAGE_INFO_REQUEST_CONSULT unexpected value %r — applying safe default (consult OFF); "
        "only 'true' enables.", _info_request_consult_raw,
    )
