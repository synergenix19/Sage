"""§1c Part A: single source of the "does an anxiety-track derealization disclosure route
this turn" rule.

Separate from safety/hr_disclosure.py by design (Vee 1a/1b, 2026-07-21): CF-008 dissociation
(§HR-11 register) routes to the psychosis referral; the CF-010 `derealization` flag is the
softer §1c ANXIETY-TRACK register and routes to its own terminal. Precedence (safety_precedence
rank crisis > medical > hr > derealization) resolves any string overlap in the HR terminal's
favour, so a psychosis-context disclosure never lands on the anxiety terminal.

Gated by DEREALIZATION_DETECTION_ENABLED (unlike psychotic_disclosure, which is unconditional):
the terminal copy is not yet Vee-signed, so the route is inert until the flag is flipped.
"""
from typing import Iterable, Optional


def derealization_disclosure_present(
    clinical_flags: Optional[Iterable[str]], *, flag_enabled: bool
) -> bool:
    if not flag_enabled:
        return False
    return "derealization" in set(clinical_flags or [])
