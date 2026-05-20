import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLASSIFIER_MODEL = os.getenv("SAGE_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
RESPONDER_MODEL = os.getenv("SAGE_RESPONDER_MODEL", "anthropic/claude-sonnet-4-6")
TRANSLATOR_MODEL = os.getenv("SAGE_TRANSLATOR_MODEL", "openai/gpt-4o-mini")

# Default ON — crisis activations must leave an audit trail unless explicitly disabled.
AUDIT_LOG_ENABLED = os.getenv("SAGE_AUDIT_LOG", "true").lower() == "true"

