#!/usr/bin/env python
"""Anti-overfit distinctness gate (A2.3) for the routing eval set.

Checks every in_scope case in an eval JSONL against the router's embedded target_presentations
and fails (exit 1) on near-verbatim overfit. Run inline during fan-out authoring and in CI.

Usage: PYTHONPATH=src python scripts/check_eval_distinctness.py [path.jsonl] [max_jaccard]
"""
import json
import sys
from collections import defaultdict

from sage_poc.routing_eval.distinctness import (
    check_distinct,
    intra_set_redundancy,
    load_all_target_presentations,
)


def main(path: str, max_jaccard: float = 0.7, intra_max_jaccard: float = 0.5) -> int:
    tps = load_all_target_presentations()
    violations = []
    by_route: dict[str, list[str]] = defaultdict(list)
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        # Intra-set redundancy applies to every cluster (in_scope skills AND the ABSTAIN OOS
        # strata) — keyed by (stratum, route) so far_oos and id_oos are checked within themselves.
        by_route[(r.get("stratum", "?"), r.get("expected_route", "?"))].append(r["utterance"])
        # Anchor overfit is an in_scope concern only (a skill case near-copying its presentations).
        if r.get("stratum") == "in_scope":
            ok, j, tp, sid = check_distinct(r["utterance"], tps, max_jaccard=max_jaccard)
            if not ok:
                violations.append((j, r["utterance"], tp, sid))
    for j, u, tp, sid in sorted(violations, reverse=True):
        print(f"OVERFIT j={j:.2f}  '{u[:60]}'  ~  '{tp}'  [{sid}]")
    print(f"{len(violations)} anchor distinctness violation(s) in {path}")

    # Intra-set pass: cases must be distinct from EACH OTHER, not only from anchors.
    intra = []
    for (stratum, route), us in by_route.items():
        for j, ua, ub in intra_set_redundancy(us, max_jaccard=intra_max_jaccard):
            intra.append((j, f"{stratum}/{route}", ua, ub))
    for j, route, ua, ub in sorted(intra, reverse=True):
        print(f"INTRA-DUP j={j:.2f}  [{route}]  '{ua[:45]}'  ~  '{ub[:45]}'")
    print(f"{len(intra)} intra-set near-duplicate pair(s) in {path}")
    return 1 if (violations or intra) else 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/routing_eval/dataset_seed.jsonl"
    mj = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
    sys.exit(main(path, mj))
