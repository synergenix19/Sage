from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class PromptTemplate(BaseModel):
    template_id: str
    version: str
    authored_by: str = "sage_clinics"
    approved_by: Optional[str] = None
    effective_date: str
    layer: Literal["L0", "L1", "L2", "L3", "L4", "L5"]
    role: Literal["system", "user"]
    always_include: bool
    word_budget: int
    content: str
    variables: list[str] = []
    # Layer-specific config
    intent: Optional[str] = None           # L2: which intent type this template covers
    window_size: Optional[int] = None      # L1: verbatim turn count
    summary_trigger: Optional[int] = None  # L1: turn at which summarisation fires (Full Build)
    max_passages: Optional[int] = None     # L4: max knowledge passages
