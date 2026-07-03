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

# UAE crisis helpline — the SINGLE authoritative source for every crisis-copy site
# (graph, output_gate, crisis_content rules, L0). Nothing may re-embed these literals.
# ⚠️ VALUES PENDING G8: `number` is a likely transcription error (→ "800 4673" / 800-HOPE,
# "Mental Support Line", hours "8am-8pm daily") and `hours` "24/7" is FALSE for that line.
# The value/label/hours correction + rules-JSON + L0 edits ride the gated commit-2 (dial-test
# + L0 fast-track re-sign). Commit-1 keeps CURRENT values so behaviour is unchanged.
CRISIS_CONFIG = {
    "number": "800 46342",
    "label": "MoHAP Counselling Line",
    "hours": "24/7",
    "emergency": "999",
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
