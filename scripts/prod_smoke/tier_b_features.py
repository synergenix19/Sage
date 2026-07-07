"""Tier B — Playwright-driven feature checks (frontend flows against prod).

Not built yet. `run.py` calls run_all() unconditionally for `--tier b` and
`--tier all`; it must no-op gracefully until Tier B lands so the runner stays
green end-to-end today.
"""
from result import CheckResult


def run_all(base_url: str) -> list[CheckResult]:
    """Placeholder — Tier B checks are not implemented yet. Returns no results."""
    return []
