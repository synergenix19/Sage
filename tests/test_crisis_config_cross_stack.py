"""Cross-stack crisis-number equality: backend CRISIS_CONFIG == frontend crisis-config.ts.

The one silent-divergence seam between the two stacks is that the backend
(sage_poc.config.CRISIS_CONFIG) and the frontend (cdai/apps/web/lib/crisis-config.ts) each hold
their own copy of the crisis number. This test parses the frontend `number:` literal and asserts it
equals the backend value, so a change to one stack that is not mirrored to the other fails CI.

CONSISTENCY only: asserts the two stacks AGREE, nothing about which number is correct.
"""
import re
from pathlib import Path

import pytest

from sage_poc.config import CRISIS_CONFIG

# Backend repo root is .../sage-poc; the frontend lives in the sibling cdai/ checkout.
_FRONTEND_CONFIG = (
    Path(__file__).resolve().parents[2] / "cdai" / "apps" / "web" / "lib" / "crisis-config.ts"
)

# number: '800 46342'  |  number: "800 46342"
_NUMBER_RE = re.compile(r"""\bnumber\s*:\s*(['"])(?P<num>[^'"]+)\1""")


def _parse_frontend_number(text: str) -> str:
    m = _NUMBER_RE.search(text)
    assert m, "could not find a `number: '...'` line in crisis-config.ts"
    return m.group("num")


def test_backend_and_frontend_crisis_number_agree():
    if not _FRONTEND_CONFIG.exists():
        pytest.skip(f"frontend crisis-config.ts not present at {_FRONTEND_CONFIG}")
    frontend_number = _parse_frontend_number(_FRONTEND_CONFIG.read_text(encoding="utf-8"))
    assert frontend_number == CRISIS_CONFIG["number"], (
        f"Cross-stack divergence: frontend crisis number {frontend_number!r} != backend "
        f"CRISIS_CONFIG['number'] {CRISIS_CONFIG['number']!r}. Update BOTH stacks together "
        "(cdai/apps/web/lib/crisis-config.ts and sage_poc/config.py)."
    )
