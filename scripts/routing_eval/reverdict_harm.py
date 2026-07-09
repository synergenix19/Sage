import json, os, sys
from sage_poc.routing_eval import real_model_driver as drv
from sage_poc.routing_eval.gate_runner import compute_metrics_by_stratum, harm_gate

pc = drv.positive_control()
if drv.MODE == "V2" and not (pc and pc.get("ok")):
    raise SystemExit(f"POSITIVE CONTROL FAILED separation={pc and pc.get('separation')}")
routed_of = drv.make_routed_of()   # loads model + candidate surface once

# HARM FIRST (fast, decisive) — print + flush immediately
harm_records = []
for hf in ("additive_safety_cases.jsonl", "harm_to_others_anger.jsonl", "redflag_somatic.jsonl"):
    p = drv._FIXTURE_DIR / hf
    if p.exists():
        harm_records += drv._load_jsonl(p)
hv = harm_gate(harm_records, routed_of=routed_of)
from sage_poc.routing_eval.gate_runner import _HARM_PRONE, _PATH_ASSERTION_KINDS
nonpath_fail = [r for r in hv.failures if getattr(r, "case_kind", None) not in _PATH_ASSERTION_KINDS]
print("HARM_JSON_START" + json.dumps({
    "mode": drv.MODE, "pc": pc,
    "harm_all": {"passed": hv.passed, "n_fail": len(hv.failures)},
    "harm_domain_leaks": [getattr(r, "utterance", "")[:55] for r in nonpath_fail],
}) + "HARM_JSON_END", flush=True)

# CELLS (slow) — print when done
cells = compute_metrics_by_stratum(*[drv.load_en_bulk_records()[0]], routed_of=routed_of)
print("CELLS_JSON_START" + json.dumps({
    f"{k[0]}/{k[1]}": {"recall": v.recall, "abstain": v.abstain_correctness,
                       "misroute_rate": v.misroute_rate, "n": v.n, "override_mis": v.override_misroute_count}
    for k, v in cells.items()}) + "CELLS_JSON_END", flush=True)
