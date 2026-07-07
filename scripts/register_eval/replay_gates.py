"""Offline: estimate which English deterministic gates WOULD fire on native Khaleeji
shadow output. Runs over shadow_register_eval rows (NOT the live turn). Uses the REAL
message_en + clinical_flags per row so message-conditioned mirroring rules fire correctly
(Blocking #3). Back-translation is an approximation; rater spot-check adjudicates borderline.

Gate-fire estimates MIRROR the live gate semantics in nodes/output_gate.py, not a
looser approximation of them:
  - banned_opener: the live gate matches `_BANNED_OPENER_RE.match(response_en.lstrip())`
    (anchored at the start of the lstripped text). We replay the same `.match(...lstrip())`
    call. `_BANNED_OPENER_RE` itself is `^(...)` with no re.MULTILINE, so `.search` and
    `.match` are equivalent on the same input; the divergence that mattered was the missing
    `.lstrip()`, which under-fires (and so under-counts, not over-counts) on back-translated
    text with leading whitespace/newlines.
  - format_tokens: the live gate strips banned style tokens via `_strip_output_format`
    FIRST and then runs `_FORMAT_VIOLATIONS.findall` on the stripped text (residual
    telemetry post-strip, not raw density). We replay the same strip-then-findall order."""
from __future__ import annotations


async def replay_gates_on_row(row: dict) -> dict:
    from sage_poc.language import async_translate_to_english  # noqa: PLC0415
    from sage_poc.rules import engine as rules_engine  # noqa: PLC0415
    from sage_poc.nodes.output_gate import (  # noqa: PLC0415
        _BANNED_OPENER_RE,
        _FORMAT_VIOLATIONS,
        _strip_output_format,
    )

    text = row.get("shadow_arabic_text") or ""
    back_en = await async_translate_to_english(text) if text else ""
    cultural = rules_engine.evaluate("cultural_output", {
        "response_text": back_en,
        "message_en": row.get("message_en") or "",        # REAL user message, per Blocking #3
        "clinical_flags": row.get("clinical_flags") or [],
    })
    stripped = _strip_output_format(back_en)
    return {"back_en": back_en,
            "cultural_fired": [r.rule_id for r in cultural.fired],
            "banned_opener": bool(_BANNED_OPENER_RE.match(back_en.lstrip())),
            "format_tokens": _FORMAT_VIOLATIONS.findall(stripped)}


def gate_fire_summary(rows: list[dict]) -> dict:
    n = len(rows) or 1
    any_fire = sum(1 for r in rows if r["cultural_fired"] or r["banned_opener"] or r["format_tokens"])
    return {"n": len(rows),
            "cultural_fires": sum(1 for r in rows if r["cultural_fired"]),
            "banned_opener_fires": sum(1 for r in rows if r["banned_opener"]),
            "format_fires": sum(1 for r in rows if r["format_tokens"]),
            "any_gate_fire_rate": round(any_fire / n, 4)}
