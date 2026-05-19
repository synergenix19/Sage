import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

CLASSIFIER_MODEL = os.getenv("OPENROUTER_CLASSIFIER_MODEL", "openai/gpt-4o-mini")
RESPONSE_MODEL = os.getenv("OPENROUTER_RESPONSE_MODEL", "anthropic/claude-3-5-sonnet")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
TRANSLATION_MODEL = os.getenv("OLLAMA_TRANSLATION_MODEL", "qwen2.5:7b")
