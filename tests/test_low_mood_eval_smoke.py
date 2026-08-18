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


def test_oracle_version_selection():
    # Owner directive 7: oracle versioned, never mutated in place. Default = v1
    # (the signed oracle of record); SAGE_3A_ORACLE_VERSION=2 selects the v2
    # draft, which the harness hard-aborts on unless the unsigned override is
    # explicitly set (proven live 2026-08-18; module-level selection pinned here).
    #
    # SUBPROCESS-ISOLATED (rebase lesson 2026-08-18): the harness's module top
    # level setdefaults SKILL_ROUTING_V2 / SKILL_RERANK_ENABLED into the live
    # environment and mutates config.LOW_MOOD_SCREEN_ENABLED — loading it
    # in-process leaked V2+rerank into every later test in the session and
    # broke master's routing suite. Never exec_module this script in-process.
    import os

    def load(env_version):
        env = {k: v for k, v in os.environ.items()
               if k not in ("SAGE_3A_ORACLE_VERSION", "SKILL_ROUTING_V2", "SKILL_RERANK_ENABLED")}
        if env_version is not None:
            env["SAGE_3A_ORACLE_VERSION"] = env_version
        code = (
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('lm3a_ver_smoke', {str(SCRIPT)!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "print('TRIGGERS=' + mod.TRIGGERS.name)\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        return proc.stdout.strip().split("TRIGGERS=")[-1]

    assert load(None) == "low_mood_3a_triggers.json"
    assert load("2") == "low_mood_3a_triggers_v2.json"
    assert (REPO / "src/sage_poc/rules/data/safety/low_mood_3a_triggers_v2.json").is_file()
