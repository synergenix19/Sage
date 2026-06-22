"""§1.5 harness orchestrator.

Runs the four blocking checks + the per-stratum AUGRC table over an eval set and
produces the baseline result. Exit is non-zero if any blocking check fails (BC1, BC2,
BC3 — hard gates). BC4 is reporting only (6b-i / 6b-ii are emitted, never fused into a
pass/fail token; the threshold comparison against the G6-signed floors is the deferred
full-gate runner, §5). Gate config carries no silent defaults: an unset value hard-errors
at baseline time (§2.4).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from sage_poc.routing_eval.augrc import CellAUGRC, LossWeights, per_cell_augrc
from sage_poc.routing_eval.blocking_checks import (
    BC3Result,
    CheckResult,
    SixBReport,
    bc1_crisis_path_invariance,
    bc2_referral_exclusion,
    bc3_per_stratum_parity,
    bc4_split_report,
)
from sage_poc.routing_eval.schema import EvalRecord


@dataclass(frozen=True)
class HarnessConfig:
    """Gate config. Every value is G6/Track-A signed; none has a default (§2.4)."""
    loss: LossWeights
    delta: float
    n_floor: int
    tau: float

    def validate(self) -> None:
        for field_name in ("loss", "delta", "n_floor", "tau"):
            if getattr(self, field_name) is None:
                raise ValueError(
                    f"unset gate config: {field_name!r} has no value. "
                    "Gate-6 values are G6-signed (no silent defaults, §2.4)."
                )


@dataclass(frozen=True)
class BaselineResult:
    passed: bool
    exit_code: int
    bc1: CheckResult
    bc2: CheckResult
    bc3: BC3Result
    bc4: SixBReport
    augrc_table: dict[tuple[str, str], CellAUGRC]


def run_baseline(records: list[EvalRecord], config: HarnessConfig) -> BaselineResult:
    config.validate()

    bc1 = bc1_crisis_path_invariance(records)
    bc2 = bc2_referral_exclusion(records)

    augrc_table = per_cell_augrc(records, config.loss)
    bc3 = bc3_per_stratum_parity(augrc_table, delta=config.delta, n_floor=config.n_floor)

    ar_idoos = [r for r in records if r.lang == "ar" and r.stratum == "id_oos" and r.held_out]
    bc4 = bc4_split_report(ar_idoos, tau=config.tau)

    passed = bc1.passed and bc2.passed and bc3.passed
    return BaselineResult(
        passed=passed,
        exit_code=0 if passed else 1,
        bc1=bc1, bc2=bc2, bc3=bc3, bc4=bc4,
        augrc_table=augrc_table,
    )


def main(records: list[EvalRecord], config: HarnessConfig) -> None:  # pragma: no cover
    """Thin entry point: run and exit with the baseline's exit code."""
    sys.exit(run_baseline(records, config).exit_code)
