from .composer import compose_prompt
from .loader import get_template as _get_template

# Evaluated at import time; will NOT reflect reload_all() calls. For backward compat only.
PERSONA: str = _get_template("L0_persona").content

__all__ = ["compose_prompt", "PERSONA"]
