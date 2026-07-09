"""#258 — build-side deploy-lock enforcement logic (scripts/verify_build_lock.sh).

Gates the enforcement LOGIC in CI (dormant-passes, in-log-passes, missing/unknown-blocks, prefix
match) so the check stays correct as it evolves. The script ships DEFAULT-OFF in the Dockerfile;
enabling it (ENFORCE_DEPLOY_LOCK=1) is a staged step (see 2026-07-08-prod-deploy-control.md #258).
"""
import subprocess
import pathlib

_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "verify_build_lock.sh"


def _run(sha, log, enforce):
    return subprocess.run(["bash", str(_SCRIPT), sha, log, enforce], capture_output=True, text=True).returncode


def test_self_test_passes():
    r = subprocess.run(["bash", str(_SCRIPT), "--self-test"], capture_output=True, text=True)
    assert r.returncode == 0, f"self-test must pass:\n{r.stdout}\n{r.stderr}"


def test_dormant_passes_regardless_of_log():
    assert _run("abc123def456", "", "0") == 0  # ENFORCE off -> always pass


def test_enforce_passes_when_sha_in_log():
    assert _run("abc123def456", "999,abc123def456,777", "1") == 0


def test_enforce_blocks_when_sha_absent():
    assert _run("abc123def456", "999,777", "1") == 1


def test_enforce_blocks_unknown_sha():
    assert _run("unknown", "999", "1") == 1
