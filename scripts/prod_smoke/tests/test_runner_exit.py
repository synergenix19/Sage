"""Unit tests for the prod smoke runner's exit-code logic.

No network access: tier functions are stubbed to return canned CheckResult
lists so this test can run anywhere (CI, laptop, no prod creds) and stays
fast. The live prod verification is a separate, manual step.
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROD_SMOKE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROD_SMOKE_DIR))

from result import CheckResult  # noqa: E402

# Load run.py under a module name distinct from the repo-root run.py — the
# repo has an unrelated top-level run.py, and a plain `import run` risks
# resolving to whichever one another test already cached in sys.modules.
_spec = importlib.util.spec_from_file_location(
    "prod_smoke_run", _PROD_SMOKE_DIR / "run.py"
)
runner = importlib.util.module_from_spec(_spec)
sys.modules["prod_smoke_run"] = runner
_spec.loader.exec_module(runner)


def _fake_tier(results):
    def _fn(base_url):
        return results
    return _fn


def test_exits_1_when_must_pass_check_fails():
    fail_results = [
        CheckResult(name="flag_x", tier="c", status="FAIL", detail="bad", must_pass=True),
    ]
    with patch.object(runner, "TIER_FUNCS", {"c": _fake_tier(fail_results)}):
        with pytest.raises(SystemExit) as exc:
            runner.main(["--tier", "c"])
    assert exc.value.code == 1


def test_exits_0_when_only_report_only_check_fails():
    results = [
        CheckResult(name="header_check", tier="c", status="FAIL", detail="report-only", must_pass=False),
    ]
    with patch.object(runner, "TIER_FUNCS", {"c": _fake_tier(results)}):
        with pytest.raises(SystemExit) as exc:
            runner.main(["--tier", "c"])
    assert exc.value.code == 0


def test_exits_0_when_must_pass_check_is_xfail():
    results = [
        CheckResult(name="flag_x", tier="c", status="XFAIL", detail="known gap", must_pass=True),
    ]
    with patch.object(runner, "TIER_FUNCS", {"c": _fake_tier(results)}):
        with pytest.raises(SystemExit) as exc:
            runner.main(["--tier", "c"])
    assert exc.value.code == 0


def test_exits_0_when_all_pass():
    results = [
        CheckResult(name="flag_x", tier="c", status="PASS", detail="ok", must_pass=True),
        CheckResult(name="header_check", tier="c", status="PASS", detail="ok", must_pass=False),
    ]
    with patch.object(runner, "TIER_FUNCS", {"c": _fake_tier(results)}):
        with pytest.raises(SystemExit) as exc:
            runner.main(["--tier", "c"])
    assert exc.value.code == 0


def test_tier_all_runs_a_b_c_with_a_b_noop():
    results = [
        CheckResult(name="flag_x", tier="c", status="PASS", detail="ok", must_pass=True),
    ]
    with patch.object(
        runner,
        "TIER_FUNCS",
        {"a": _fake_tier([]), "b": _fake_tier([]), "c": _fake_tier(results)},
    ):
        with pytest.raises(SystemExit) as exc:
            runner.main(["--tier", "all"])
    assert exc.value.code == 0
