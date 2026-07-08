"""Measure live V2 disposition over the Layer-1 trigger corpus.

Runs under flags-on (SKILL_ROUTING_V2=1 SKILL_RERANK_ENABLED=1 SKILL_RERANK_PRECISION=fp32).
For each utterance: replicate real_model_driver.routed_of AND capture WHICH path decided
(harm_intrusive veto / ocd veto / keyword / semantic_exclusion / tier2 / abstain), so the
observed disposition is fully attributable. Emits results.jsonl + per-category coverage log.
"""
import json, os, time, sys, pathlib

REPO = "/Users/knowledgebase/Documents/Sage/sage-poc-v2live"
CORPUS = f"{REPO}/tests/fixtures/bot_behaviour_audit/layer1_trigger_corpus.jsonl"
OUT = f"{REPO}/tests/fixtures/bot_behaviour_audit/layer1_results.jsonl"

t0 = time.time()
from sage_poc.routing_eval import real_model_driver as drv
from sage_poc.routing_eval.schema import EvalRecord, ABSTAIN
from sage_poc.skills.keyword_matcher import match_skill_keywords
from sage_poc.nodes.ocd_compulsion import is_ocd_compulsion
from sage_poc.nodes.harm_intrusive import is_harm_intrusive
import sage_poc.nodes.skill_select as ss

assert drv.MODE == "V2", f"expected V2, got {drv.MODE}"
pc = drv.positive_control()
if not (pc and pc.get("ok")):
    raise SystemExit(f"POSITIVE CONTROL FAILED sep={pc and pc.get('separation')}")
print(f"[{time.time()-t0:.1f}s] MODE={drv.MODE} PC={pc}", flush=True)

EXCLUDE = drv.DEFAULT_EXCLUDE_SKILLS  # mindfulness_meditation (spec §3 surface confound)
routed_of = drv.make_routed_of(EXCLUDE)  # builds V2 anchor surface
print(f"[{time.time()-t0:.1f}s] index built, exclude={sorted(EXCLUDE)}", flush=True)

def decide_with_path(utt):
    """Mirror routed_of but report the deciding path."""
    if is_harm_intrusive(utt):
        return ABSTAIN, "harm_intrusive_veto"
    if is_ocd_compulsion(utt):
        return ABSTAIN, "ocd_veto"
    kw = match_skill_keywords(utt, "", "en")
    kw = {sid: n for sid, n in kw.items() if sid not in EXCLUDE}
    if kw:
        ranked = sorted(kw.items(), key=lambda x: x[1], reverse=True)
        cands = [sid for sid,_ in ranked]
        if cands and cands[0] == "dbt_tipp" and {"grounding_5_4_3_2_1","dbt_tipp"} <= kw.keys():
            cands.remove("grounding_5_4_3_2_1"); cands.insert(0,"grounding_5_4_3_2_1")
        if ss._rerank_enabled() and ss._keyword_rerank_veto(cands, utt, "en"):
            return ABSTAIN, "keyword_rerank_veto"
        return cands[0], "keyword"
    if ss._SEMANTIC_EXCLUSION_RE.search(utt.lower()):
        return ABSTAIN, "semantic_exclusion"
    best, score = ss._semantic_match_sync(utt)
    if best is None:
        return ABSTAIN, "tier2_abstain"
    return best, "tier2"

REFERRAL_SKILLS = {"psychotic_referral"}

def observed_disposition(routed, path):
    if routed == ABSTAIN:
        if path in ("harm_intrusive_veto","ocd_veto"):
            return "abstain_veto"      # guard fired in skill_select (containment interim)
        return "abstain"               # plain hold-space / no route
    if routed in REFERRAL_SKILLS:
        return "professional_referral"
    return "self_help_skill"

rows = []
counts = {}
with open(CORPUS) as f:
    corpus = [json.loads(l) for l in f if l.strip()]

for i, r in enumerate(corpus):
    utt = r["utterance"]
    ts = time.time()
    routed, path = decide_with_path(utt)
    # sanity: cross-check against the canonical routed_of
    rec = EvalRecord(utterance=utt, lang="en", stratum="in_scope", expected_route=ABSTAIN)
    routed_canon = routed_of(rec)
    assert routed_canon == routed, f"path-mirror mismatch {utt!r}: {routed} vs {routed_canon}"
    obs = observed_disposition(routed, path)
    row = dict(r, routed_skill=routed, decision_path=path, observed_disposition=obs,
               elapsed=round(time.time()-ts,2))
    rows.append(row)
    counts[r["spec_id"]] = counts.get(r["spec_id"],0)+1
    if i % 20 == 0:
        print(f"[{time.time()-t0:.1f}s] {i}/{len(corpus)} {r['spec_id']} {utt[:40]!r} -> {routed} ({path})", flush=True)

with open(OUT,"w") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False)+"\n")

print(f"[{time.time()-t0:.1f}s] MEASURED {len(rows)} utterances across {len(counts)} categories", flush=True)
print("COVERAGE " + json.dumps(counts), flush=True)
print("ALLDONE", flush=True)
