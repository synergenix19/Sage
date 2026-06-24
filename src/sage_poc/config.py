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
