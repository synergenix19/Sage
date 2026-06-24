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

# UAE crisis support line — MoHAP Mental Health Counselling Line (free, 24/7).
# This is the single authoritative source. Update here after clinical lead verification;
# the canonical-source test enforces all skill JSON occurrences match this value.
CRISIS_LINE_UAE = "800 46342"

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
