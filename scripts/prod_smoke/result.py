"""Shared result type for the prod smoke suite.

CheckResult is the common currency between tier modules (tier_a_safety,
tier_b_features, tier_c_regression) and the runner (run.py). Tier functions
return list[CheckResult]; the runner aggregates and decides the process exit
code from `status` + `must_pass` alone — it never re-inspects tier internals.
"""
from dataclasses import dataclass
from typing import Literal

Status = Literal["PASS", "FAIL", "XFAIL"]


@dataclass
class CheckResult:
    name: str
    tier: str
    status: Status
    detail: str
    must_pass: bool
