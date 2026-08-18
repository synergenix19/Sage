"""§3a semantic-routing eval harness (calibration-gated, config-stamped, joint-path).

R7 governance tool: every §3a routing change re-runs through THIS harness against the SIGNED
oracle (low_mood_3a_triggers.json). Preserved from the design-confirmation runs.

=== REQUIRED ADDITIONS BEFORE THE STEP-2 ENRICHMENT RUN (Vee, 2026-07-10) — not yet wired ===
1. CD3/R4 HARD ABORT: if ANY of the 3 signed edge markers ("I feel numb", "I feel stuck",
   "I don't feel like myself") is BA-offerable POST-enrichment, raise SystemExit(MEASUREMENT VOID).
   Treat it exactly like the calibration anchor — a boundary the code cannot cross silently, because
   BA-offering a grief-adjacent marker routes grieving people into behavioral activation (signed
   clinical error). NOT a checklist item; a hard abort.
2. FLATNESS-CLUSTER as its own STAMPED pass/fail criterion (separate threshold), reported apart from
   aggregate recall. Guards the failure mode where aggregate clears CD4 ~80-90% while the terse
   affective-flatness markers ("I feel flat/numb/disconnected") remain the residual — a passing
   headline over a hole in the highest-signal sub-band. Pre-register FLATNESS_RECALL_MIN.
3. NON-§3a CONTROL SET for BA GLOBAL false-positive: List B is the §3a look-alike set and will NOT
   catch BA regressing onto ordinary low-energy/non-§3a chatter (2 of 3 current FPs were the semantic
   tier over-firing). Add a non-§3a control set and the assertion "BA offer-rate on the control set
   does NOT rise vs pre-enrichment baseline." Enriching BA anchors widens its boundary; measure it.
Sequence unchanged; flag OFF throughout; Task-3 hold decoupled.
"""

#!/usr/bin/env python
"""§3a semantic-routing eval harness — calibration-gated, end-to-end, config-stamped.

REVIEW BEFORE RUNNING. This measures whether the REAL prod routing path makes
`behavioral_activation` offerable for the signed List A (fire) and does NOT for
List B (look-alikes). It is built to make the measurement itself reviewable, per
the four requirements that turned a real signal into a flat-band artifact last time:

  (1) CALIBRATION IS A HARD ABORT. Known-good anchors must land where they must, or
      the run raises SystemExit and emits NO recall/precision numbers. A cold or
      misconfigured model cannot silently produce a plausible table.
  (2) CONFIG IS STAMPED INTO THE OUTPUT, bound to the numbers (routing tier, reranker
      on/off, exemplars loaded, threshold, embedding-timeout, model revision, anchor
      index shape, and the pre-registered pass criteria). A number without its config
      next to it is not a result.
  (3) MEASURED THROUGH THE REAL ROUTING PATH, end to end: it calls skill_select_node
      and reads the offerable set that routing actually produces (offered_skill_ids /
      active_skill_id) — NOT a matcher similarity score interpreted as offerable. Any
      embedding_timeout on any input aborts (it would mean a keyword-only fallback,
      i.e. the wrong function again).
  (4) PASS CRITERIA ARE PRE-REGISTERED below, before any numbers are seen, with the
      precision direction strict (err-toward-not-asking: a spurious §3a fires an SI
      question at a benign user near the still-broken GL-1 card).

Run (from any directory; flags are setdefault'd to the prod arm, an operator export wins):
    uv run python scripts/low_mood_3a_semantic_eval.py
"""
import os, json, asyncio, hashlib, subprocess
from pathlib import Path

# ---- prod-parity config, set BEFORE import (F12/F13, code_review.md 2026-08-17) ----
# SKILL_ROUTING_V2 must be set in the ENVIRONMENT: every runtime V2 behavior (per-route
# thresholds, argmax tau condition, anchor debias feeding the reranker) gates on
# _v2_enabled(), which re-reads os.environ — assigning the module constant
# (ss.SKILL_ROUTING_V2 = True, the previous approach) widened the warmup anchors only and
# measured a hybrid config matching neither prod arm while stamping "V2".
os.environ.setdefault("SKILL_ROUTING_V2", "1")
os.environ.setdefault("SKILL_RERANK_ENABLED", "1")
os.environ.setdefault("SKILL_RERANK_PRECISION", "fp32")

import sage_poc.config as config
config.LOW_MOOD_SCREEN_ENABLED = False          # measure RAW BA-offerability, upstream of the §3a interception
import sage_poc.nodes.skill_select as ss
import numpy as np


def _mk(**overrides):
    # Mirror of tests/test_skill_select._ss_state, inlined (F13): the editable install
    # exposes only src/, so `from tests...` raised ModuleNotFoundError under the script's
    # own documented invocation (pyproject's pythonpath is pytest-only). Keep in sync.
    base = {
        "raw_message": "", "detected_language": "en", "message_en": "",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [], "crisis_state": "none",
        "s7_result": None, "s7_method": None,
        "primary_intent": None, "secondary_intent": None, "intent_confidence": 1.0,
        "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None, "path": [], "turn_count": 0,
        "conversation_history": [], "skill_match_method": None, "semantic_score": None,
        "distress_trajectory": [], "code_switching": False,
    }
    base.update(overrides)
    return base

# ---- (4) PRE-REGISTERED PASS CRITERIA (clinician-adjustable; frozen before the run) ----
RECALL_MIN = 0.90      # List A: semantic routing must make BA offerable for >= 90% of the signed fire set
FP_MAX     = 0.00      # List B: err-toward-not-asking -> ZERO spurious BA-offers; any FP is tier-attributed

# F13: root-anchored (was cwd-relative — launching from any other directory failed to find
# the oracle and silently stamped "uncommitted-or-untracked" provenance).
REPO = Path(__file__).resolve().parents[1]
TRIGGERS = REPO / "src/sage_poc/rules/data/safety/low_mood_3a_triggers.json"

def ba_offerable(msg: str):
    """End-to-end (requirement 3): run the real routing node, read the offerable set it produces."""
    out = asyncio.run(ss.skill_select_node(_mk(message_en=msg, detected_language="en")))
    if out.get("embedding_timeout"):
        raise SystemExit(f"ABORT: embedding_timeout on {msg!r} -> keyword-only fallback, measurement VOID.")
    offered = out.get("offered_skill_ids") or []
    active = out.get("active_skill_id")
    is_ba = ("behavioral_activation" in offered) or (active == "behavioral_activation")
    return is_ba, out.get("skill_match_method"), out.get("semantic_score")

def calibrate():
    """(1) HARD ABORT. Canonical §3a must be BA-offerable; clearly-unrelated and anxiety must not be BA."""
    anchors = [
        ("canonical_3a_must_be_BA", "I have lost interest in everything and I cannot get myself to do anything anymore", True),
        ("unrelated_must_not_be_BA", "what time does the grocery store close today", False),
        ("anxiety_must_not_be_BA", "my heart is racing and I feel panicky and cannot breathe", False),
    ]
    for name, msg, want in anchors:
        is_ba, method, score = ba_offerable(msg)
        if is_ba != want:
            raise SystemExit(f"CALIBRATION FAILED [{name}]: BA-offerable={is_ba} want={want} "
                             f"(method={method}, score={score}). MEASUREMENT VOID — model cold/misconfigured.")
    print("CALIBRATION PASSED (3 anchors)")

def main():
    # warm + prove the index is actually built with exemplars
    ss._ensure_semantic_ready()
    idx = None if ss._anchor_embeddings is None else np.asarray(ss._anchor_embeddings).shape
    if idx is None:
        raise SystemExit("ABORT: anchor index not built.")

    # ---- oracle provenance + signing state (amendment c): which List A/B produced these numbers ----
    _ob = TRIGGERS.read_bytes()
    _oracle = json.loads(_ob)  # single read; List A/B below reuse this object
    _ostatus = _oracle.get("_meta", {}).get("status", "unknown")
    try:
        _ogit = subprocess.check_output(
            ["git", "rev-parse", "--short", f"HEAD:{TRIGGERS.relative_to(REPO)}"],
            cwd=REPO, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        _ogit = "uncommitted-or-untracked"

    # (2) config stamped, bound to the numbers below — EFFECTIVE values only (F12): every
    # entry reflects what the runtime readers compute, never an import-time module constant.
    cfg = {
        "routing": "V2" if ss._v2_enabled() else "V1", "reranker_enabled": ss._rerank_enabled(),
        "exemplars_in_anchors": ss.SKILL_ROUTING_V2, "semantic_threshold": ss.SEMANTIC_THRESHOLD,
        "embedding_timeout_s": ss.EMBEDDING_TIMEOUT_SECONDS, "bge_revision": ss._BGE_M3_REVISION,
        "anchor_index_shape": idx, "low_mood_screen_flag": config.LOW_MOOD_SCREEN_ENABLED,
        "pre_registered": {"recall_min_listA": RECALL_MIN, "fp_max_listB": FP_MAX},
        "oracle_file": str(TRIGGERS), "oracle_content_sha256_12": hashlib.sha256(_ob).hexdigest()[:12],
        # F14: _meta.status VERBATIM — the previous hardcoded "PROPOSED, NOT Vee-signed"
        # suffix contradicted the JSON's updated SIGNED status in every stamp.
        "oracle_git_blob": _ogit, "oracle_status": _ostatus,
    }
    print("CONFIG:", json.dumps(cfg, default=str))

    calibrate()   # aborts here if the path is not the real, warm, discriminating one

    fire  = [p for fam in _oracle["fire_families"].values() for p in fam]         # List A (39)
    looks = [p for cat in _oracle["lookalike_categories"].values() for p in cat]  # List B (15)

    def measure(items):
        rows = []
        for p in items:
            is_ba, method, score = ba_offerable(p)
            rows.append({"text": p, "ba_offerable": is_ba, "tier": method, "score": score})
        return rows

    fire_rows, look_rows = measure(fire), measure(looks)
    recall = sum(r["ba_offerable"] for r in fire_rows) / len(fire_rows)
    fp     = sum(r["ba_offerable"] for r in look_rows) / len(look_rows)

    # PROVE the joint path ran (not semantic-in-isolation): tier distribution across all List A.
    from collections import Counter
    def dist(rows): return dict(Counter((r["tier"] or "no_match") for r in rows))
    ba_hits = [r for r in fire_rows if r["ba_offerable"]]
    print("\nJOINT-PATH PROOF (skill_select_node = keyword Tier 1 + semantic Tier 2):")
    print("  List A tier distribution (all 39):", dist(fire_rows))
    print("  List A BA-offerable hits by tier :", dist(ba_hits),
          "  <- if any 'keyword_offer' here, Tier 1 was live")

    print(f"\nLIST A (fire, n={len(fire_rows)}): JOINT recall={recall:.3f}  [pre-registered >= {RECALL_MIN}]")
    print("  RESIDUAL — §3a markers that survive BOTH tiers (this is the real gap, for Vee's read):")
    for r in fire_rows:
        if not r["ba_offerable"]:
            print(f"   MISS  (tier={r['tier']}, score={r['score']}) :: {r['text']}")
    print(f"LIST B (look-alike, n={len(look_rows)}): FP={fp:.3f}  [pre-registered <= {FP_MAX}]")
    for r in look_rows:
        if r["ba_offerable"]:
            print(f"   SPURIOUS-BA  via tier={r['tier']} (score={r['score']}) :: {r['text']}")

    recall_ok, fp_ok = recall >= RECALL_MIN, fp <= FP_MAX
    print(f"\nRESULT: recall_ok={recall_ok} fp_ok={fp_ok} -> "
          f"{'PASS' if (recall_ok and fp_ok) else 'FAIL'} (vs pre-registered criteria)")
    # tier-attribute any FP so a keyword-tier leak scopes the target_presentations fix (not a classifier)
    kw_fps = [r for r in look_rows if r["ba_offerable"] and (r["tier"] or "").startswith("keyword")]
    if kw_fps:
        print(f"NOTE: {len(kw_fps)} FP(s) attributable to the KEYWORD tier (target_presentations) -> "
              f"targeted fix, not a classifier: {[r['text'] for r in kw_fps]}")

if __name__ == "__main__":
    main()
