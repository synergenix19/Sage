import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLASSIFIER_MODEL = os.getenv("OPENROUTER_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
RESPONSE_MODEL = os.getenv("OPENROUTER_RESPONSE_MODEL", "anthropic/claude-3-5-sonnet")

