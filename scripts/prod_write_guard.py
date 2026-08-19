"""Mechanical source-ref assertion for any script that WRITES to prod.

Why this exists (2026-08-19 incident, fourth occurrence of the class):
a targeted repair of two corpus articles was run from a checkout parked on a stale
feature branch. It read `data/knowledge_corpus/ar/*.json` from that branch and wrote
PRE-REFRESH content into production, silently reverting two clinician-approved citation
upgrades. The damage was caught only because the repair carried a mandatory post-write
integrity comparison; nothing prevented the write itself.

Every prior occurrence of this class was a stale READ that produced a wrong claim. This
one was a stale WRITE that produced wrong prod data. The standing rule -- assert the ref
before quoting a repo read -- was documentation, and documentation did not fire. This
module is the same invariant enforced in code, on the write side.

Usage, before touching prod:

    from scripts.prod_write_guard import assert_source_ref
    assert_source_ref(["data/knowledge_corpus"])   # raises unless identical to origin/master

The check is content-based, not branch-name-based: a branch name proves nothing, whereas
"the files I am about to ship are byte-identical to the reviewed ref" is the actual
property that matters. Working-tree edits count as divergence.

No network: compares against whatever `origin/master` your local git already knows. Fetch
first if freshness matters -- staleness of the REF is a separate question from divergence
FROM it, and this guard deliberately answers only the second.
"""
from __future__ import annotations

import logging
import os
import pathlib
import subprocess

_log = logging.getLogger(__name__)

DEFAULT_REF = "origin/master"
ESCAPE_ENV = "SAGE_ALLOW_UNVERIFIED_SOURCE_REF"


class SourceRefMismatch(RuntimeError):
    """The working tree's content for the guarded paths is not the reviewed ref."""


def _git(args: list[str], repo_root: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(repo_root), capture_output=True, text=True, check=False,
    )


def repo_root(start: str | pathlib.Path | None = None) -> pathlib.Path:
    start = pathlib.Path(start or pathlib.Path(__file__).resolve().parent)
    out = _git(["rev-parse", "--show-toplevel"], start)
    if out.returncode != 0:
        raise SourceRefMismatch(f"not a git repository: {start}")
    return pathlib.Path(out.stdout.strip())


def diverging_paths(paths: list[str], ref: str = DEFAULT_REF,
                    root: pathlib.Path | None = None) -> list[str]:
    """Files under `paths` whose working-tree content differs from `ref`."""
    root = root or repo_root()
    out = _git(["diff", "--name-only", ref, "--", *paths], root)
    if out.returncode != 0:
        raise SourceRefMismatch(
            f"cannot compare against {ref}: {out.stderr.strip() or 'unknown git error'}. "
            f"If {ref} is unknown locally, fetch it before running a prod write."
        )
    return [line for line in out.stdout.splitlines() if line.strip()]


def describe_head(root: pathlib.Path | None = None) -> str:
    root = root or repo_root()
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    sha = _git(["rev-parse", "--short", "HEAD"], root).stdout.strip()
    return f"{branch}@{sha} in {root}"


def assert_source_ref(paths: list[str], ref: str = DEFAULT_REF,
                      root: pathlib.Path | None = None) -> None:
    """Refuse to continue unless `paths` are byte-identical to `ref`.

    Raises SourceRefMismatch naming the diverging files and the checkout in use, so the
    operator sees WHICH checkout they are standing in -- the thing that was wrong in the
    incident this guard exists to prevent.
    """
    root = root or repo_root()
    if os.getenv(ESCAPE_ENV) == "1":
        _log.error(
            "[prod-write-guard] BYPASSED via %s=1. Writing to prod from %s WITHOUT verifying "
            "that %s match %s. If this write reaches clinical content, it is unreviewed.",
            ESCAPE_ENV, describe_head(root), paths, ref,
        )
        return

    diverged = diverging_paths(paths, ref, root)
    if diverged:
        raise SourceRefMismatch(
            f"REFUSING TO WRITE TO PROD: {len(diverged)} file(s) under {paths} differ from "
            f"{ref}.\n  checkout: {describe_head(root)}\n  diverging: "
            + ", ".join(diverged[:10])
            + ("" if len(diverged) <= 10 else f", ... (+{len(diverged) - 10} more)")
            + f"\nRun from a checkout whose content matches {ref}, or set {ESCAPE_ENV}=1 to "
              f"override deliberately (logged at ERROR)."
        )
    _log.info("[prod-write-guard] source ref verified: %s match %s (%s)",
              paths, ref, describe_head(root))
