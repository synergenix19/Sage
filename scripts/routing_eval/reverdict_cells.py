import json
from sage_poc.routing_eval import real_model_driver as drv
from sage_poc.routing_eval.gate_runner import compute_routing_metrics
pc = drv.positive_control()
if drv.MODE == "V2" and not (pc and pc.get("ok")):
    raise SystemExit(f"PC FAIL sep={pc and pc.get('separation')}")
routed_of = drv.make_routed_of()
records, _ = drv.load_en_bulk_records()
print("PC " + json.dumps(pc), flush=True)
for stratum in ("id_oos", "far_oos", "in_scope"):   # small→large so the decisive floor lands first
    rs = [r for r in records if r.stratum == stratum]
    m = compute_routing_metrics(rs, routed_of=routed_of)
    print(f"CELL en/{stratum} " + json.dumps({"recall": round(m.recall,4), "abstain": round(m.abstain_correctness,4),
          "mis": round(m.misroute_rate,4), "n": m.n, "ovr": m.override_misroute_count}), flush=True)
print("ALLDONE", flush=True)
