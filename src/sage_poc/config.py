import os
from dotenv import load_dotenv

load_dotenv()

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

# v7.1 crisis tiering (G1). Default OFF -> routing reads is_safe exactly as v7/master
# (Check B provable). ON -> _route_after_safety routes on crisis_tier (T2 crisis / T1 warm).
CRISIS_TIERING_ENABLED = os.getenv("SAGE_CRISIS_TIERING", "false").lower() == "true"

# Knowledge retrieval abstain floor. POC shipped 0.0 (never abstain), which surfaced weak
# RRF passages as authoritative (feedback #5 "Google is better"). Interim conservative default
# 0.015 (just above single-list rank-2+ RRF noise with k=60); finalize via
# scripts/calibrate_retrieval_threshold.py once a labeled query set exists.
KNOWLEDGE_ABSTAIN_THRESHOLD = float(os.getenv("SAGE_KNOWLEDGE_ABSTAIN_THRESHOLD", "0.015"))

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
