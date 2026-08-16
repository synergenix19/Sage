"""HR-1 Stage 1: single source of the "does an HR-class disclosure route
this turn" rule.

psychotic_disclosure ALWAYS routes: the psychosis path is already live in
prod and must never be gated off by HIGH_RISK_DETECTION_ENABLED.
mania_disclosure and dissociation_disclosure route only when the flag is
enabled (Task 2 scope; wiring into skill_select/graph is Task 3).
"""

from typing import Iterable, Optional

HR_DISCLOSURE_FLAGS = frozenset(
    {"psychotic_disclosure", "mania_disclosure", "dissociation_disclosure"}
)

_GATED_FLAGS = frozenset({"mania_disclosure", "dissociation_disclosure"})


def hr_disclosure_present(
    clinical_flags: Optional[Iterable[str]], *, flag_enabled: bool
) -> bool:
    flags = set(clinical_flags or [])
    if "psychotic_disclosure" in flags:
        return True
    return flag_enabled and bool(flags & _GATED_FLAGS)
