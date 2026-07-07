"""Tier 0 native-Khaleeji shadow generation — MEASUREMENT ONLY.
Output is NEVER served and NEVER enters SageState. Fail-open: any error → None."""
from __future__ import annotations
import hashlib, logging, time
from sage_poc.prompts.composer import compose_prompt
from sage_poc.prompts.loader import load_khaleeji_shadow_exemplars

_log = logging.getLogger(__name__)

async def generate_shadow_arabic(state: dict, llm=None) -> dict | None:
    if state.get("detected_language") != "ar":
        return None
    try:
        if llm is None:
            from sage_poc.llm import get_responder  # noqa: PLC0415
            llm = get_responder()
        system_str, user_str, _ = compose_prompt(state, shadow_arabic=True)
        messages = [{"role": "system", "content": system_str}, {"role": "user", "content": user_str}]
        prompt_hash = hashlib.sha256(system_str.encode("utf-8")).hexdigest()[:16]
        exemplar_version, _blk = load_khaleeji_shadow_exemplars()
        t0 = time.monotonic()
        resp = await llm.ainvoke(messages)
        gen_latency_ms = int((time.monotonic() - t0) * 1000)
        text = getattr(resp, "content", None)
        if not text or not text.strip():
            _log.warning("[shadow_arabic] empty/absent generation content; treating as failed (None)")
            return None
        return {
            "text": text,
            "prompt_hash": prompt_hash,
            "exemplar_version": exemplar_version,
            "generation_language": "ar_native",
            "gen_latency_ms": gen_latency_ms,
        }
    except Exception as exc:
        _log.warning("[shadow_arabic] generation failed (fail-open): %s", exc)
        return None
