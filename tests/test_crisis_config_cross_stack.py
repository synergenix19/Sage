"""Cross-stack crisis-resource parity: backend CRISIS_RESOURCES == frontend crisis-config.ts array.

The one silent-divergence seam between the two stacks is that the backend (sage_poc.config) and the
frontend (cdai/apps/web/lib/crisis-config.ts) each hold their own copy of the crisis-resource
directory. This test parses the frontend `CRISIS_RESOURCES` array and asserts it matches the backend
ENTRY-FOR-ENTRY, in order (label/name, number, hours, scope), so a change to one stack that is not
mirrored to the other fails CI. This is the MERGE-BLOCKING gate the coupled value flip (both stacks
-> the doc's multi-entry composition) must pass together — it is what keeps the card from ever
showing one stack's numbers while the other holds different ones.

Backend source of truth: the structured CRISIS_RESOURCES list (H4). On a backend that predates it,
the 2-entry pair is DERIVED from CRISIS_CONFIG so this gate is green regardless of the order in which
the two stacks' changes merge.

CONSISTENCY only: asserts the two stacks AGREE, nothing about which values are correct.
"""
import re
from pathlib import Path

import pytest

try:  # H4 structured directory (PR #288+).
    from sage_poc.config import CRISIS_RESOURCES as _BACKEND_RESOURCES  # type: ignore
except ImportError:  # pre-H4 backend: derive the 2-entry pair from the flat CRISIS_CONFIG.
    from sage_poc.config import CRISIS_CONFIG as _CC

    _BACKEND_RESOURCES = [
        {"name": _CC["label"], "number": _CC["number"], "hours": _CC["hours"], "scope": "national"},
        {"name": "Emergency Services", "number": _CC["emergency"], "hours": "24/7", "scope": "emergency"},
    ]

# Backend repo root is .../sage-poc; the frontend lives in the sibling cdai/ checkout.
_FRONTEND_CONFIG = (
    Path(__file__).resolve().parents[2] / "cdai" / "apps" / "web" / "lib" / "crisis-config.ts"
)

# The `export const CRISIS_RESOURCES: readonly CrisisResource[] = [ ... ] as const` block.
_ARRAY_RE = re.compile(r"CRISIS_RESOURCES\s*:[^=]*=\s*\[(?P<body>.*?)\]\s*as const", re.DOTALL)
_OBJ_RE = re.compile(r"\{(?P<obj>[^{}]*)\}", re.DOTALL)


def _field(obj: str, key: str) -> str:
    m = re.search(rf"""\b{key}\s*:\s*(['"])(?P<v>[^'"]*)\1""", obj)
    assert m, f"frontend resource entry missing `{key}`: {obj!r}"
    return m.group("v")


def _parse_frontend_resources(text: str):
    block = _ARRAY_RE.search(text)
    assert block, "could not find `CRISIS_RESOURCES = [ ... ] as const` in crisis-config.ts"
    resources = []
    for m in _OBJ_RE.finditer(block.group("body")):
        obj = m.group("obj")
        resources.append(
            {
                "labelEn": _field(obj, "labelEn"),
                "number": _field(obj, "number"),
                "hours": _field(obj, "hours"),
                "scope": _field(obj, "scope"),
            }
        )
    return resources


def test_backend_and_frontend_crisis_resources_agree():
    if not _FRONTEND_CONFIG.exists():
        pytest.skip(f"frontend crisis-config.ts not present at {_FRONTEND_CONFIG}")
    frontend = _parse_frontend_resources(_FRONTEND_CONFIG.read_text(encoding="utf-8"))
    backend = list(_BACKEND_RESOURCES)

    assert len(frontend) == len(backend), (
        f"Cross-stack divergence: frontend has {len(frontend)} crisis resources, backend has "
        f"{len(backend)}. Update BOTH stacks together (cdai/apps/web/lib/crisis-config.ts and "
        "sage_poc/config.py CRISIS_RESOURCES)."
    )
    for i, (fe, be) in enumerate(zip(frontend, backend)):
        assert fe["labelEn"] == be["name"], (
            f"entry {i}: frontend labelEn {fe['labelEn']!r} != backend name {be['name']!r}"
        )
        assert fe["number"] == be["number"], (
            f"entry {i}: frontend number {fe['number']!r} != backend number {be['number']!r}"
        )
        assert fe["hours"] == be["hours"], (
            f"entry {i}: frontend hours {fe['hours']!r} != backend hours {be['hours']!r}"
        )
        assert fe["scope"] == be["scope"], (
            f"entry {i}: frontend scope {fe['scope']!r} != backend scope {be['scope']!r}"
        )
