"""
Pre-submission SI-boundary check for semantic_anchors candidates.

Run before submitting any anchor sentence for clinical sign-off. Reports which
SI probe phrases bleed above SEMANTIC_THRESHOLD so re-authoring happens before
the two-round-trip cycle (submit → automated gate fails → re-author → resubmit).

Three result tiers per candidate:
  PASS   — max SI score < TARGET (0.40): submit for clinical sign-off
  WARN   — max SI score >= TARGET but < THRESHOLD: clearance is thin; revise if possible
  BLEED  — max SI score >= THRESHOLD (0.4593): do not submit; will fail automated gate

The target (0.40) is a deliberate 0.033 buffer below the frozen baseline's highest
off-topic miss (interpersonal_effectiveness 0.4330 against the general corpus).
It is not the same number as SEMANTIC_THRESHOLD — passing THRESHOLD is not enough.

Usage:
  # Check one or more sentences on the command line:
  uv run python scripts/check_anchor_si_boundary.py "My sentence one" "My sentence two"

  # Pipe sentences from a file (one per line):
  cat candidate_anchors.txt | uv run python scripts/check_anchor_si_boundary.py --stdin

  # Interactive mode (no args, no --stdin):
  uv run python scripts/check_anchor_si_boundary.py

Exit codes:
  0 — all candidates PASS (max SI score < TARGET for every candidate)
  1 — at least one candidate BLEEDS or WARNS (max SI score >= TARGET)
"""
from __future__ import annotations
import json, pathlib, sys, textwrap
import numpy as np

sys.path.insert(0, "src")

THRESHOLD = 0.4593  # automated gate — anchors above this fail validate_grief_sf1_boundary.py
TARGET = 0.40       # submission bar — anchors must stay below this before sign-off

CRISIS_PHRASES_PATH = pathlib.Path("src/sage_poc/safety/crisis_phrases.json")

_PASSIVE_SI_SOURCES = {"SF-1"}


def _load_si_phrases() -> list[str]:
    data = json.loads(CRISIS_PHRASES_PATH.read_text())
    return [p["text"] for p in data["phrases"] if p.get("source") in _PASSIVE_SI_SOURCES]


def _score_against_si(sentences: list[str], si_phrases: list[str], embed_fn) -> list[dict]:
    all_embeddings = embed_fn(sentences + si_phrases, normalize_embeddings=True)
    anchor_embs = all_embeddings[: len(sentences)]
    si_embs = all_embeddings[len(sentences):]

    results = []
    for i, sentence in enumerate(sentences):
        sims = np.dot(si_embs, anchor_embs[i])
        bleed_entries = []
        for j, phrase in enumerate(si_phrases):
            score = float(sims[j])
            if score >= TARGET:
                bleed_entries.append({"phrase": phrase, "score": score, "over_target": score - TARGET})
        bleed_entries.sort(key=lambda x: x["score"], reverse=True)
        max_score = float(np.max(sims))

        if max_score >= THRESHOLD:
            tier = "BLEED"
        elif max_score >= TARGET:
            tier = "WARN"
        else:
            tier = "PASS"

        results.append({
            "sentence": sentence,
            "max_si_score": max_score,
            "tier": tier,
            "entries_above_target": bleed_entries,
        })
    return results


def _print_report(results: list[dict]) -> bool:
    any_not_pass = False
    for r in results:
        tier = r["tier"]
        bar = "=" * 80
        print(f"\n{bar}")
        print(f"  {tier}  max_si_score={r['max_si_score']:.4f}  target={TARGET}  threshold={THRESHOLD}")
        print(f"  {textwrap.fill(repr(r['sentence']), width=76, initial_indent='  ', subsequent_indent='         ')}")
        print(bar)
        if r["entries_above_target"]:
            any_not_pass = True
            label = "BLEED (above threshold — will fail automated gate)" if tier == "BLEED" else "WARN (above target — revise if possible)"
            print(f"  {label}")
            print(f"  {'score':>8}  {'over target':>11}  phrase")
            print(f"  {'-'*8}  {'-'*11}  {'-'*60}")
            for b in r["entries_above_target"]:
                over_threshold = b["score"] - THRESHOLD
                threshold_flag = f"  *** +{over_threshold:.4f} over gate" if b["score"] >= THRESHOLD else ""
                print(f"  {b['score']:8.4f}  {b['over_target']:+11.4f}  {repr(b['phrase'][:60])}{threshold_flag}")
            print()
            if tier == "BLEED":
                print("  ACTION: this anchor bleeds above the automated gate. Common causes:")
                print("  (a) void/absence framing: re-frame around active experience or sensory memory")
                print("  (b) 'I keep [verb]ing' construction: matches SI repetitive-thought patterns")
                print("  (c) intense emotional-impact language: grief + SI share concept space in BGE-M3")
                print("  If no lower-bleed framing exists, this presentation routes via freeflow instead.")
                print("  See docs/SKILL_AUTHORING_CONVENTIONS.md §semantic_anchors.")
            else:
                print("  ACTION: clearance is thin (0.40-0.4593 zone). Revise if possible.")
                print("  If no better framing exists, this anchor may route to freeflow instead.")
        else:
            print(f"  max_si_score={r['max_si_score']:.4f} < target={TARGET} — safe to submit.")
    return any_not_pass


def main() -> int:
    import time
    from sage_poc.nodes import skill_select as ss

    # Collect candidate sentences
    candidates: list[str] = []

    if "--stdin" in sys.argv:
        for line in sys.stdin:
            line = line.strip()
            if line:
                candidates.append(line)
    else:
        args = [a for a in sys.argv[1:] if not a.startswith("-")]
        candidates.extend(args)

    if not candidates:
        print("check_anchor_si_boundary.py — pre-submission SI-boundary check")
        print()
        print("Usage:")
        print('  uv run python scripts/check_anchor_si_boundary.py "sentence one" "sentence two"')
        print("  cat file.txt | uv run python scripts/check_anchor_si_boundary.py --stdin")
        print()
        print("Target: max SI score must be below 0.40 before submission for clinical sign-off.")
        print("(Threshold 0.4593 is the automated gate; 0.40 is the submission bar.)")
        print()
        print("Enter candidate anchor sentences interactively (empty line to finish):")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                break
            candidates.append(line)

    if not candidates:
        print("No candidates provided. Exiting.")
        return 0

    print(f"\nLoading BGE-M3 model...", end="", flush=True)
    t0 = time.time()
    ss._ensure_semantic_ready()
    print(f" done ({time.time() - t0:.1f}s)")

    si_phrases = _load_si_phrases()
    print(f"Scoring {len(candidates)} candidate(s) against {len(si_phrases)} SF-1 passive-SI probes")
    print(f"Target: < {TARGET}  |  Gate threshold: {THRESHOLD}")

    results = _score_against_si(candidates, si_phrases, ss._embed_model.encode)

    _print_report(results)

    pass_count = sum(1 for r in results if r["tier"] == "PASS")
    warn_count = sum(1 for r in results if r["tier"] == "WARN")
    bleed_count = sum(1 for r in results if r["tier"] == "BLEED")

    print(f"\nSUMMARY: {pass_count} PASS  {warn_count} WARN  {bleed_count} BLEED")
    if bleed_count:
        print(f"  {bleed_count} candidate(s) above gate threshold ({THRESHOLD}). Do not submit.")
        return 1
    if warn_count:
        print(f"  {warn_count} candidate(s) above target ({TARGET}) but below gate threshold.")
        print("  Revise if possible. If no better framing exists, consider freeflow path.")
        return 1
    print(f"  All candidates below target ({TARGET}). Safe to submit for clinical sign-off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
