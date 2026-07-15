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
NODES_DIR = REPO / "src" / "sage_poc" / "nodes"


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


def scan_nodes() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    writes: dict[str, set[str]] = {}
    reads: dict[str, set[str]] = {}
    for f in sorted(NODES_DIR.rglob("*.py")):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            # WRITES: string keys of any dict literal that is returned, or assigned to a var
            # (nodes commonly build `upd = {...}` then `return {**base, **upd}` or `return upd`).
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                for k in _dict_string_keys(node.value):
                    writes.setdefault(k, set()).add(f.name)
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
                for k in _dict_string_keys(node.value):
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
