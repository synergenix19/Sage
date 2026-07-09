"""Proof 1 harness — capture the DETERMINISTIC crisis-routing surface for a fixed corpus.

Surfaces (all deterministic; generation + S3 stubbed): per-case routing decision, gate_path,
is_safe, crisis_flags, the canned crisis copy, and whether tier fields are present. Run on the
MASTER tree and on the branch (flag OFF); the two JSON outputs must be identical (Check B).

Deterministic by construction: check_s3 -> 0.0 (no model), no LLM generation is invoked (safe
turns capture only the routing decision; crisis turns capture the deterministic canned copy).
Timestamps are never captured. Same script runs on both trees.

Run: cd <tree> && .venv/bin/python scripts/gen_deterministic_surface.py > surface.json
"""
import sys, json, asyncio
from unittest.mock import patch

sys.path.insert(0, "src")

CORPUS = [
    "hello, how are you",
    "i had a really good day today",
    "i want to kill myself",
    "i want to end my life tonight",
    "i have a plan to hurt myself",
    "i feel hopeless",
    "it feels like a burden and it is making me feel so low",
    "i've been so stressed about work",
    "أنا أريد أن أموت",
    "أنا i just want to die",
]


def _state(text):
    return {
        "raw_message": text, "path": [], "turn_number": 0, "turn_count": 0,
        "crisis_state": "none", "clinical_flags": [], "crisis_flags": [],
        "distress_trajectory": [], "engagement_trajectory": [], "engagement": 5,
        "emotional_intensity": 5, "therapeutic_profile": {},
    }


async def _surface_for(text):
    from sage_poc.nodes.safety_check import safety_check_node
    from sage_poc.graph import _route_after_safety, _crisis_response_node
    out = await safety_check_node(_state(text))
    merged = {**_state(text), **out}
    route = _route_after_safety(merged)
    rec = {
        "route": route,
        "is_safe": out.get("is_safe"),
        "crisis_flags": sorted(out.get("crisis_flags") or []),
        "detected_language": out.get("detected_language"),
        # tier fields MUST be absent when the flag is OFF (schema decision / Check B)
        "tier_fields_present": sorted(k for k in ("crisis_tier", "tier_rule_id", "supportive_posture", "t1_count") if k in out),
    }
    if route == "crisis":
        cr = await _crisis_response_node(merged)
        rec["gate_path"] = cr.get("gate_path")
        rec["canned_copy"] = cr.get("response")  # deterministic crisis text (rules_engine)
    return rec


async def main():
    # Stub S3 to 0.0 everywhere it is called from safety_check (no BGE-M3, fully deterministic).
    with patch("sage_poc.nodes.safety_check.check_s3", return_value=0.0), \
         patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        surface = {}
        for text in CORPUS:
            surface[text] = await _surface_for(text)
    print(json.dumps(surface, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
