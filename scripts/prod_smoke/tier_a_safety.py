"""Tier A — safety regression checks (crisis recall/precision spot-checks).

Not built yet. `run.py` calls run_all() unconditionally for `--tier a` and
`--tier all`; it must no-op gracefully until Tier A lands so the runner stays
green end-to-end today.
"""
from result import CheckResult


def run_all(base_url: str) -> list[CheckResult]:
    """Placeholder — Tier A checks are not implemented yet. Returns no results."""
    return []
