#!/usr/bin/env python
"""Anti-overfit distinctness gate (A2.3) for the routing eval set.

Checks every in_scope case in an eval JSONL against the router's embedded target_presentations
and fails (exit 1) on near-verbatim overfit. Run inline during fan-out authoring and in CI.

Usage: PYTHONPATH=src python scripts/check_eval_distinctness.py [path.jsonl] [max_jaccard]
"""
import json
import sys

from sage_poc.routing_eval.distinctness import check_distinct, load_all_target_presentations


def main(path: str, max_jaccard: float = 0.7) -> int:
    tps = load_all_target_presentations()
    violations = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("stratum") == "in_scope":
            ok, j, tp, sid = check_distinct(r["utterance"], tps, max_jaccard=max_jaccard)
            if not ok:
                violations.append((j, r["utterance"], tp, sid))
    for j, u, tp, sid in sorted(violations, reverse=True):
        print(f"OVERFIT j={j:.2f}  '{u[:60]}'  ~  '{tp}'  [{sid}]")
    print(f"{len(violations)} distinctness violation(s) in {path}")
    return 1 if violations else 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/routing_eval/dataset_seed.jsonl"
    mj = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
    sys.exit(main(path, mj))
