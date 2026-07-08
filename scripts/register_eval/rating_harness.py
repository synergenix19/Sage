"""Offline blinded dual-arm register rating harness (Task 9).

Standalone offline analysis: pure functions only, no production/serving
imports, no DB writes, no network. Scores the two arms of the native-Arabic
shadow-measure experiment:
  - shadow arm:  rows from the `shadow_register_eval` table
  - shipped arm: served Arabic text, joined from the messages store
                 (or session_audit) by (session_id, turn_number)

`fetch_pairs()` below is a docstring-only stub describing the live DB read;
the logic that matters (blinding, IRR, delta, join) lives in the pure
functions, which are unit-tested in tests/test_rating_harness.py.
"""

from __future__ import annotations

import random

REGISTER_KPI = 4.0  # v7 §16.1


def build_blinded_sheet(pairs: list[dict], seed: int) -> list[dict]:
    """Build a rater-facing blinded A/B sheet from shipped/shadow pairs.

    Deterministic (seeded) per-pair coin flip decides which arm is "A" and
    which is "B". The rater-facing row never exposes `shipped`/`shadow` keys
    or values under those names — only `arms: {"A": ..., "B": ...}`. The
    A/B -> arm-identity mapping is kept separately in `_map`, which callers
    must withhold from raters and only consult when unblinding scores.
    """
    rng = random.Random(seed)
    sheet = []
    for p in pairs:
        flip = rng.random() < 0.5
        a, b = (p["shipped"], p["shadow"]) if flip else (p["shadow"], p["shipped"])
        sheet.append({
            "turn_id": p["turn_id"],
            "arms": {"A": a, "B": b},
            "_map": {"A": "shipped" if flip else "shadow", "B": "shadow" if flip else "shipped"},
        })
    return sheet


def compute_irr(scores_by_rater: dict[str, list[int]]) -> float:
    """Simplified ordinal inter-rater agreement for exactly two raters.

    agreement = 1 - mean(|r1_i - r2_i|) / 4, on a 1-5 rating scale (max
    possible absolute difference = 4). Returns NaN if fewer than two raters
    are present or their score lists are empty/misaligned in length.

    NOTE: this is a simplified proxy, not Krippendorff's alpha. The
    production upgrade path is a full Krippendorff-alpha implementation
    (e.g. `krippendorff` lib) once more than two raters or missing-data
    handling is needed.
    """
    rs = list(scores_by_rater.values())
    if len(rs) < 2 or len(rs[0]) != len(rs[1]) or not rs[0]:
        return float("nan")
    dis = sum(abs(x - y) for x, y in zip(rs[0], rs[1])) / len(rs[0])
    return round(1.0 - dis / 4.0, 4)


def register_delta(unblinded: list[dict]) -> dict:
    """Compute per-arm means, delta, and KPI pass/fail on unblinded scores.

    `unblinded` rows must carry `shipped_score` and `shadow_score` (arm
    identity already resolved via the `_map` from build_blinded_sheet).
    """
    n = len(unblinded)
    sh = sum(r["shadow_score"] for r in unblinded) / n
    sp = sum(r["shipped_score"] for r in unblinded) / n
    return {
        "n": n,
        "shadow_mean": round(sh, 4),
        "shipped_mean": round(sp, 4),
        "delta": round(sh - sp, 4),
        "shadow_meets_kpi": sh >= REGISTER_KPI,
    }


def pair_by_turn(shadow_rows: list[dict], shipped_rows: list[dict]) -> list[dict]:
    """Verification #2: join the two-table split explicitly on (session_id, turn_number).

    shadow_rows come from `shadow_register_eval`; shipped_rows are the served
    Arabic text joined from the messages store (or session_audit). Turns
    without both arms present are dropped (the caller is responsible for
    logging/reporting the drop count).
    """
    shipped_by_key = {(r["session_id"], r["turn_number"]): r["arabic_text"] for r in shipped_rows}
    pairs = []
    for s in shadow_rows:
        key = (s["session_id"], s["turn_number"])
        if key in shipped_by_key and s.get("shadow_arabic_text"):
            pairs.append({
                "turn_id": f"{key[0]}:{key[1]}",
                "shadow": s["shadow_arabic_text"],
                "shipped": shipped_by_key[key],
            })
    return pairs


def fetch_pairs():
    """Live DB read (NOT implemented here — docstring stub only).

    In production this would:
      1. Query `shadow_register_eval` for shadow-arm rows, filtered to the
         primary evaluation set with `tool_loop_iterations == 0` (excludes
         turns where the shadow generation looped tools, which is out of
         scope for the primary register-quality comparison).
      2. Query the messages store (or session_audit) for the shipped
         (served) Arabic text on the same (session_id, turn_number) keys.
      3. Call `pair_by_turn(shadow_rows, shipped_rows)` to join the two
         result sets into rater-ready pairs.

    This function intentionally performs no DB access, no network calls,
    and imports no production/serving modules — it exists only to document
    where the live read plugs into the pure functions above.
    """
    raise NotImplementedError(
        "fetch_pairs is a docstring stub; the live DB read is out of scope "
        "for this offline harness. Use pair_by_turn() with rows fetched by "
        "the caller (e.g. shadow_register_eval + messages-store queries)."
    )
