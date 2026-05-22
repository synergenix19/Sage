from .composer import compose_prompt
from .loader import get_template as _get_template

PERSONA: str = _get_template("L0_persona").content

__all__ = ["compose_prompt", "PERSONA"]
