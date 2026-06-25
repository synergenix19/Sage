"""Cross-encoder reranker model — bge-reranker-v2-m3, precision-configurable.

The §4.3 selector (Falcon-3B in the spec) substituted by bge-reranker-v2-m3 (cost/fit, justified by
the probe: +7.23 control gap, clean per-stratum win). Quality is settled and IDENTICAL across
precisions (same m3 weights): int8 holds the win (62/90/100), promotion + confidence gap preserved.
The ONLY axis distinguishing int8 from fp32 is latency-on-x86, which is structurally unmeasurable on
the Apple-Silicon dev proxy (qnnpack int8 reads slower than Accelerate fp32 — an artifact). So
precision is a CONFIGURABLE parameter (SKILL_RERANK_PRECISION=int8 default | fp32 fallback) and the
choice is deferred to the Railway x86 latency measurement — not decided offline.

INVOCATION DISCIPLINE: AutoModelForSequenceClassification ONLY. sentence_transformers.CrossEncoder
silently does NOT load the reranker head → ~0 logits → confident-wrong. Pinned by head_loaded_ok().
"""
from __future__ import annotations

import os
import platform

_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
_REVISION = None  # pin once the deploy revision is recorded

_state: dict = {}  # lazy singletons: tokenizer, model


def active_precision() -> str:
    """int8 (default) | fp32. Read dynamically so Railway can flip it without a rebuild."""
    p = os.environ.get("SKILL_RERANK_PRECISION", "int8").lower()
    return p if p in ("int8", "fp32") else "int8"


def _quant_engine() -> str | None:
    """The int8 backend for this host: fbgemm on x86 (Railway), qnnpack on ARM (Apple Silicon dev).
    Returns None if neither is available (int8 then falls back to fp32 rather than erroring)."""
    import torch
    supported = set(getattr(torch.backends.quantized, "supported_engines", []))
    prefer = "fbgemm" if not platform.machine().lower().startswith(("arm", "aarch")) else "qnnpack"
    for eng in (prefer, "fbgemm", "qnnpack"):
        if eng in supported:
            return eng
    return None


def _load():
    if "model" in _state:
        return _state["tokenizer"], _state["model"]
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(_RERANK_MODEL, revision=_REVISION)
    mdl = AutoModelForSequenceClassification.from_pretrained(_RERANK_MODEL, revision=_REVISION).eval()
    if active_precision() == "int8":
        eng = _quant_engine()
        if eng is not None:
            torch.backends.quantized.engine = eng
            mdl = torch.quantization.quantize_dynamic(mdl, {torch.nn.Linear}, dtype=torch.qint8)
        # else: no int8 backend on this host -> stay fp32 (quality identical; latency the only cost)
    _state.update(tokenizer=tok, model=mdl)
    return tok, mdl


def score_pairs(pairs: list[tuple[str, str]]) -> list[float]:
    """Cross-encoder relevance logits for (query, candidate_description) pairs. HIGHER = more
    relevant. The active-precision m3, canonical head. Empty -> []."""
    if not pairs:
        return []
    import torch
    tok, mdl = _load()
    # BATCH-SIZE-1 / no cross-candidate padding -> each pair's logit is INDEPENDENT of what else is
    # scored with it (batch-INVARIANT, deterministic). Batched scoring made int8 logits batch-DEPENDENT
    # (the quantization×padding interaction: a pair scored -6.04 / -6.25 / -6.54 across batch contexts),
    # which means routing depended on batch composition — unauditable for a clinical router. Per-pair
    # scoring removes the padding entirely. Cost: k forward passes instead of 1 (latency, measured on
    # Railway as the deterministic-batch-1 number, not an optimistic batched estimate).
    out: list[float] = []
    with torch.no_grad():
        for q, d in pairs:
            inp = tok([q], [d], truncation=True, max_length=512, return_tensors="pt")
            out.append(float(mdl(**inp).logits.view(-1)[0]))
    return out


def head_loaded_ok() -> bool:
    """Positive control: the reranker head is loaded and produces real logit separation (>3) for the
    active precision — not the ~0 logits a headless CrossEncoder load yields."""
    rel, off = score_pairs([
        ("I want to write down and challenge my negative thoughts",
         "Guided practice for writing down an automatic negative thought and examining the evidence."),
        ("what time does the grocery store close today",
         "Guided practice for writing down an automatic negative thought and examining the evidence."),
    ])
    return (rel - off) > 3.0
