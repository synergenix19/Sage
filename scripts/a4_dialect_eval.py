"""A4 §20.1 Dialect-QA eval harness — Khaleeji translation.

Runs a fixed set of synthetic English support utterances through the new few-shot
Khaleeji translator (async_translate_to_arabic) N times each, then writes a
markdown scoring sheet for a NATIVE EMIRATI rater to fill. This is the evidence
that clears the A4 §20.1 Dialect-QA deployment gate and lets the clinical lead /
linguist fill the `_signed_off` fields on:
  - src/sage_poc/data/khaleeji_translation_exemplars.json
  - src/sage_poc/prompts/templates/L2_intents/skill_offer.json (v0.2.0)
  - src/sage_poc/prompts/templates/L2_intents/skill_offer_reoffer.json

Input is synthetic — NO user data. The translator already calls the external LLM
in normal production operation, so this introduces no new data path.

Multiple runs per utterance are intentional: the Syrian<->Emirati drift is
INTERMITTENT, so a single snapshot cannot show consistency. N runs let the rater
see whether the register holds across repetitions.

Usage:
  .venv/bin/python scripts/a4_dialect_eval.py [--runs 3] [--out PATH]
"""
from __future__ import annotations

import argparse
import asyncio

# (category, english utterance) — 5 categories x 3 = 15
UTTERANCES: list[tuple[str, str]] = [
    ("warm reflection", "That sounds really exhausting, and it makes complete sense that you're worn out."),
    ("warm reflection", "It takes a lot to keep going through something this heavy."),
    ("warm reflection", "I can hear how much this has been weighing on you."),
    ("gentle question", "When did you first start noticing these feelings?"),
    ("gentle question", "What feels like the heaviest part of this for you right now?"),
    ("gentle question", "Is there anything that's helped, even a little, on the harder days?"),
    ("crisis-adjacent reassurance", "You don't have to face this alone, and reaching out was a brave step."),
    ("crisis-adjacent reassurance", "Your safety matters, and there are people ready to support you right now."),
    ("crisis-adjacent reassurance", "Whatever you're feeling is valid, and you deserve care and support."),
    ("skill hand-off", "We could try a short breathing exercise together, or we can just keep talking, whichever feels right."),
    ("skill hand-off", "Would it help to walk through a quick grounding exercise, or would you rather keep talking it through?"),
    ("skill hand-off", "There's a short exercise some people find calming. Want to give it a try, or keep talking?"),
    ("post-crisis recovery", "I'm really glad you're still here talking with me. How are you feeling now compared to earlier?"),
    ("post-crisis recovery", "You've gotten through the hardest part of today. Let's take the next bit slowly."),
    ("post-crisis recovery", "It's okay to feel drained after all that. We can go at whatever pace you need."),
]


async def _translate(text: str) -> str:
    from sage_poc.language import async_translate_to_arabic
    return await async_translate_to_arabic(text)


async def _gather(runs: int) -> list[dict]:
    rows: list[dict] = []
    for category, en in UTTERANCES:
        outputs: list[str] = []
        for _ in range(runs):
            ar = await _translate(en)
            outputs.append(ar)
        fallback = any(o.strip() == en.strip() for o in outputs)
        rows.append({"category": category, "en": en, "outputs": outputs, "fallback": fallback})
    return rows


def _render(rows: list[dict], runs: int) -> str:
    lines: list[str] = []
    lines.append("# A4 §20.1 Dialect-QA Scoring Sheet — Khaleeji Translation")
    lines.append("")
    lines.append("> **Rater: native Emirati speaker.** For each utterance, the translator was run "
                 f"{runs}× (drift is intermittent, so repetition reveals consistency). Score each row, "
                 "then sign at the bottom. Synthetic input — no user data.")
    lines.append("")
    lines.append("**Scoring key**")
    lines.append("- **Dialect (1-5):** 5 = natural Emirati Gulf, 1 = Levantine/MSA/wrong Gulf sub-dialect")
    lines.append("- **Consistent? (Y/N):** do all runs stay in the same Emirati register?")
    lines.append("- **Warmth (1-5):** 5 = warmth/meaning fully preserved, 1 = clinical/flat/altered meaning")
    lines.append("- **Correction:** the phrasing you would ship instead, if any")
    lines.append("")
    lines.append("**Gate criteria (proposed):** every row Dialect ≥ 4, Consistent = Y, Warmth ≥ 4, "
                 "no meaning-altering corrections. Any FALLBACK row (translator returned English) is an "
                 "automatic fail to investigate before re-running.")
    lines.append("")
    for i, r in enumerate(rows, 1):
        lines.append(f"## {i}. [{r['category']}]")
        lines.append("")
        lines.append(f"**EN:** {r['en']}")
        if r["fallback"]:
            lines.append("")
            lines.append("> ⚠️ FALLBACK DETECTED: at least one run returned the original English "
                         "(translator/API failure). Investigate before scoring.")
        lines.append("")
        lines.append("| Run | Output |")
        lines.append("|-----|--------|")
        for n, o in enumerate(r["outputs"], 1):
            lines.append(f"| {n} | {o} |")
        lines.append("")
        lines.append("| Dialect (1-5) | Consistent? (Y/N) | Warmth (1-5) | Correction |")
        lines.append("|---------------|-------------------|--------------|------------|")
        lines.append("|               |                   |              |            |")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Sign-off")
    lines.append("")
    lines.append("- Rater name: ____________________  Date: ____________")
    lines.append("- Overall verdict: PASS / FAIL (circle)")
    lines.append("- If PASS: fill `_signed_off` on the three draft artifacts and clear A4 §20.1.")
    lines.append("- If FAIL: list corrections above; fold into "
                 "`khaleeji_translation_exemplars.json`, bump version, re-run this harness.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", default="docs/superpowers/governance/2026-06-16-khaleeji-a4-dialect-eval.md")
    args = parser.parse_args()

    rows = asyncio.run(_gather(args.runs))
    sheet = _render(rows, args.runs)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(sheet)

    n_fallback = sum(1 for r in rows if r["fallback"])
    print(f"Wrote {args.out}: {len(rows)} utterances x {args.runs} runs.")
    if n_fallback:
        print(f"WARNING: {n_fallback} utterance(s) had a fallback (English) output — check API/key.")
    else:
        print("No fallbacks — all utterances translated. Ready for native Emirati rating.")


if __name__ == "__main__":
    main()
