"""
Pre-submission SI-boundary check for semantic_anchors candidates.

Run before submitting any anchor sentence for clinical sign-off. Reports which
SI probe phrases bleed above SEMANTIC_THRESHOLD so re-authoring happens before
the two-round-trip cycle (submit → automated gate fails → re-author → resubmit).

Usage:
  # Check one or more sentences on the command line:
  uv run python scripts/check_anchor_si_boundary.py "My sentence one" "My sentence two"

  # Pipe sentences from a file (one per line):
  cat candidate_anchors.txt | uv run python scripts/check_anchor_si_boundary.py --stdin

  # Interactive mode (no args, no --stdin):
  uv run python scripts/check_anchor_si_boundary.py

Exit codes:
  0 — all candidates CLEAR (no bleed above threshold)
  1 — at least one candidate BLEEDS on at least one SI phrase
"""
from __future__ import annotations
import json, pathlib, sys, textwrap
import numpy as np

sys.path.insert(0, "src")

THRESHOLD = 0.4593
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
            margin = THRESHOLD - score
            if score >= THRESHOLD:
                bleed_entries.append({"phrase": phrase, "score": score, "over": -margin})
        bleed_entries.sort(key=lambda x: x["score"], reverse=True)
        max_score = float(np.max(sims))
        results.append({
            "sentence": sentence,
            "max_si_score": max_score,
            "bleeds": bleed_entries,
            "clear": len(bleed_entries) == 0,
        })
    return results


def _print_report(results: list[dict]) -> bool:
    any_bleed = False
    for r in results:
        status = "CLEAR" if r["clear"] else "BLEED"
        bar = "=" * 80
        print(f"\n{bar}")
        print(f"  {status}  max_si_score={r['max_si_score']:.4f}  threshold={THRESHOLD}")
        print(f"  {textwrap.fill(repr(r['sentence']), width=76, initial_indent='  ', subsequent_indent='         ')}")
        print(bar)
        if r["bleeds"]:
            any_bleed = True
            print(f"  {'score':>8}  {'over':>6}  phrase")
            print(f"  {'-'*8}  {'-'*6}  {'-'*60}")
            for b in r["bleeds"]:
                print(f"  {b['score']:8.4f}  {b['over']:+6.4f}  {repr(b['phrase'][:70])}")
            print()
            print("  ADVICE: dominant semantic load is the void/absence. Re-frame around")
            print("  the bereaved person's active experience, sensory memory, or ongoing")
            print("  relationship with the deceased. See docs/SKILL_AUTHORING_CONVENTIONS.md")
            print("  §semantic_anchors for the void-framing rule and safe anchor examples.")
        else:
            print(f"  All {len(results)} SI probes below threshold — safe to submit for clinical sign-off.")
    return any_bleed


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
    print(f"Threshold: {THRESHOLD}")

    results = _score_against_si(candidates, si_phrases, ss._embed_model.encode)

    any_bleed = _print_report(results)

    clear_count = sum(1 for r in results if r["clear"])
    bleed_count = sum(1 for r in results if not r["clear"])
    print(f"\nSUMMARY: {clear_count} CLEAR, {bleed_count} BLEED")
    if bleed_count:
        print("One or more candidates bleed. Do not submit for clinical sign-off until revised.")
        return 1
    print("All candidates clear. Safe to include in clinical sign-off submission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
