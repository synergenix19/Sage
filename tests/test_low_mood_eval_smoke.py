# tests/test_low_mood_eval_smoke.py
#
# F13 (code_review.md 2026-08-17): the §3a eval harness previously could not run
# under its own documented invocation (ModuleNotFoundError importing from tests/;
# cwd-relative oracle path). This smoke test loads the script's module top level
# — the exact surface that failed — via subprocess from a NEUTRAL cwd with no
# PYTHONPATH help, so a regression to either defect fails CI, without paying for
# the full eval run (main() stays behind the __main__ guard).

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "low_mood_3a_semantic_eval.py"

_LOADER = """
import importlib.util
spec = importlib.util.spec_from_file_location("lm3a_eval_smoke", {script!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.TRIGGERS.is_file(), f"oracle not found at {{mod.TRIGGERS}}"
state = mod._mk(message_en="smoke")
assert state["message_en"] == "smoke" and state["detected_language"] == "en"
print("SMOKE-OK")
"""


def test_harness_module_loads_from_any_cwd():
    with tempfile.TemporaryDirectory() as neutral_cwd:
        proc = subprocess.run(
            [sys.executable, "-c", _LOADER.format(script=str(SCRIPT))],
            cwd=neutral_cwd, capture_output=True, text=True, timeout=120,
        )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SMOKE-OK" in proc.stdout
