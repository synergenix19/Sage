from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from .schemas import PromptTemplate

_DATA_DIR = Path(__file__).parent / "templates"
_cache: dict[str, PromptTemplate] = {}
_loaded: bool = False


def _load_all_templates() -> dict[str, PromptTemplate]:
    templates: dict[str, PromptTemplate] = {}
    for json_file in sorted(_DATA_DIR.glob("**/*.json")):
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        tmpl = PromptTemplate.model_validate(raw)
        templates[tmpl.template_id] = tmpl
    return templates


def get_template(template_id: str, variant: Optional[str] = None) -> PromptTemplate:
    """Return template by ID. KeyError if not found.
    If variant is set (e.g. 'v2'), tries '{template_id}_{variant}' first."""
    global _loaded
    if not _loaded:
        _cache.update(_load_all_templates())
        _loaded = True
    if variant:
        variant_id = f"{template_id}_{variant}"
        if variant_id in _cache:
            return _cache[variant_id]
    return _cache[template_id]


def get_intent_template(intent: str, variant: Optional[str] = None) -> Optional[PromptTemplate]:
    """Return the L2 template for a given intent string, or None if not found."""
    global _loaded
    if not _loaded:
        _cache.update(_load_all_templates())
        _loaded = True
    template_id = f"L2_{intent}"
    if variant:
        variant_id = f"{template_id}_{variant}"
        if variant_id in _cache:
            return _cache[variant_id]
    return _cache.get(template_id)


def reload_all() -> None:
    global _loaded
    _cache.clear()
    _loaded = False
    # Composer's offer-blurb cache is derived from template content; keep it
    # coherent with a template reload. Import inside the function to avoid a
    # cycle (composer imports from loader).
    try:
        from sage_poc.prompts.composer import _offer_descriptions, _declined_instruction
        _offer_descriptions.cache_clear()
        _declined_instruction.cache_clear()
    except Exception:
        pass
