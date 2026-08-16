#!/usr/bin/env python3
"""Static enforcement of the SageState channel contract.

Incident class (4th instance: #191 render seam, #205 affordance seam, SG-2 JSON->prompt
seam, SG-2 node->node channel seam): a value is WRITTEN by one graph node and READ by
another, but the key is not a declared SageState channel. LangGraph merges only declared
keys into shared state, so the undeclared key is silently DROPPED between nodes and the
reader gets None — every component green, the seam broken, no test failing.

This check makes that failure class structurally impossible: any key returned by a node
(a state write) AND read via state.get(...)/state[...] MUST be declared in the SageState
TypedDict, or the build fails. Run in CI (unit-gate) and by hand as the sibling audit.

Exit 1 (with the offending channels) on any violation; exit 0 otherwise.
"""
import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
STATE_FILE = REPO / "src" / "sage_poc" / "state.py"
# Scan the WHOLE package, not just nodes/. The 2026-07-20 D1 enforce-flip incident proved the blind spot:
# `screen_question_text` was written in a HELPER module (safety/medical_screen.py) via a SUBSCRIPT assignment
# (`out["screen_question_text"] = ...`) and read in graph.py's router — neither in nodes/, neither a dict
# literal — so the seam was invisible and shipped to prod. A channel's transport crosses node boundaries
# regardless of which module physically writes the value, so the scan must cover every module that builds a
# state-update, not just the node functions.
SCAN_ROOT = REPO / "src" / "sage_poc"
_SKIP = {"state.py"}  # the TypedDict declaration source itself


def declared_channels() -> set[str]:
    keys: set[str] = set()
    tree = ast.parse(STATE_FILE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SageState":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    keys.add(stmt.target.id)
    return keys


def _dict_string_keys(d: ast.Dict) -> list[str]:
    return [k.value for k in d.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]


# Variable names that conventionally accumulate a STATE UPDATE (a dict returned/merged into graph state),
# as opposed to a DB row or other local dict. A subscript / .update() / dict-assign write counts as a
# state-write only for these — so an audit-ROW build (`row = {...}`, `row["k"] = state.get("k")`) is not
# mistaken for a state channel, while the D1-incident shape (`out["screen_question_text"] = ...`) is caught.
_STATE_UPDATE_VARS = {"out", "result", "upd", "updates", "update", "state_update",
                      "patch", "delta", "ret", "obs", "acc", "merged", "new_state"}


def _is_state_update_target(t: ast.expr) -> bool:
    # `out` (Name) or `out["k"]` (Subscript on a Name) whose base name is a state-update accumulator.
    if isinstance(t, ast.Name):
        return t.id in _STATE_UPDATE_VARS
    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
        return t.value.id in _STATE_UPDATE_VARS
    return False


def scan_nodes() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    writes: dict[str, set[str]] = {}
    reads: dict[str, set[str]] = {}
    for f in sorted(SCAN_ROOT.rglob("*.py")):
        if f.name in _SKIP:
            continue
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            # WRITES: a returned dict literal (a node function's state update) — any module.
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                for k in _dict_string_keys(node.value):
                    writes.setdefault(k, set()).add(f.name)
            # WRITES: `<acc> = {...}` — a dict literal assigned to a STATE-UPDATE accumulator var only (so an
            # audit-row build `row = {...}` is NOT counted as state; see _STATE_UPDATE_VARS).
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                if any(_is_state_update_target(t) for t in node.targets):
                    for k in _dict_string_keys(node.value):
                        writes.setdefault(k, set()).add(f.name)
            # WRITES (subscript form): `out["k"] = v` — the D1 incident shape. Counted only for a state-update
            # accumulator var, so `row["k"] = state.get("k")` (audit row) is not a false positive.
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if (isinstance(tgt, ast.Subscript) and isinstance(tgt.slice, ast.Constant)
                            and isinstance(tgt.slice.value, str) and _is_state_update_target(tgt)):
                        writes.setdefault(tgt.slice.value, set()).add(f.name)
            # WRITES (dict.update form): `out.update({"k": v})` — state-update accumulator var only.
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "update" and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in _STATE_UPDATE_VARS
                    and node.args and isinstance(node.args[0], ast.Dict)):
                for k in _dict_string_keys(node.args[0]):
                    writes.setdefault(k, set()).add(f.name)
            # READS: state.get("k") and state["k"]
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "state"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                reads.setdefault(node.args[0].value, set()).add(f.name)
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "state"
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                reads.setdefault(node.slice.value, set()).add(f.name)
    return writes, reads


def main() -> int:
    declared = declared_channels()
    writes, reads = scan_nodes()
    channels = set(writes) & set(reads)  # keys both written and read = cross-node channels
    violations = sorted(k for k in channels if k not in declared)
    if violations:
        print("FAIL: undeclared SageState channels (written by a node, read by a node, "
              "absent from SageState — LangGraph DROPS these; the reader gets None):")
        for k in violations:
            print(f"  - {k}: written in {sorted(writes[k])}; read in {sorted(reads[k])}")
        print(f"\nDeclare each in {STATE_FILE.relative_to(REPO)} (SageState TypedDict).")
        return 1
    print(f"OK: all {len(channels)} written+read state keys are declared SageState channels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
