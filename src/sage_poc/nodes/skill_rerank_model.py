"""Cross-encoder reranker model — bge-reranker-v2-m3, precision-configurable.

The §4.3 selector (Falcon-3B in the spec) substituted by bge-reranker-v2-m3 (cost/fit, justified by
the probe: +7.23 control gap, clean per-stratum win).

PRECISION = fp32 (DEFAULT, REQUIRED for prod). int8 is SAFETY-DISQUALIFIED. The earlier claim that
quality was "IDENTICAL across precisions, latency the only axis" was FALSIFIED on 2026-06-25: the
safety-relevance check on the 29 deterministic (batch-1) cross-precision flips found 6/6 id_oos flips
in the disqualifying direction — int8 ROUTES clinician-territory disclosures (disposition=ABSTAIN)
that fp32 correctly ABSTAINS. Confirmed at the production node, global τ=-6.0843: fp32 6/6 ABSTAIN vs
int8 6/6 ROUTE (incl. dbt_tipp on an irritability disclosure, mindfulness_body_scan on body-image
distress) — the exact over-route class the reranker exists to close, re-admitted by quantization
noise. int8's "slightly higher" aggregate id_oos was that over-routing, not better routing. So the
precision fork was NEVER purely latency: fp32 is the accurate reference, int8 deviates on 29/324 (9%)
incl. 6 safety-cell over-routes. int8 stays SELECTABLE (SKILL_RERANK_PRECISION=int8) for latency
probing ONLY — never the prod default. Railway measures fp32 batch-1 latency (the deployable number).

INVOCATION DISCIPLINE: AutoModelForSequenceClassification ONLY. sentence_transformers.CrossEncoder
silently does NOT load the reranker head → ~0 logits → confident-wrong. Pinned by head_loaded_ok().
"""
from __future__ import annotations

import os
import platform

_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
# PINNED 2026-06-25 to the exact snapshot every V2 gate result (60/86/100, the int8 safety
# disqualification) was measured on — so the deploy ships the weights the gate validated, and the
# Dockerfile bake of this revision lets prod load offline (local_files_only) with no runtime download.
_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"

_state: dict = {}  # lazy singletons: tokenizer, model


def active_precision() -> str:
    """fp32 (DEFAULT, required for prod) | int8 (safety-disqualified, selectable for latency probing
    only). Read dynamically so Railway can flip it without a rebuild. See module docstring: int8
    over-routes 6/6 id_oos safety-cell cases that fp32 ABSTAINS (2026-06-25 safety check)."""
    p = os.environ.get("SKILL_RERANK_PRECISION", "fp32").lower()
    return p if p in ("int8", "fp32") else "fp32"


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
    # Prefer the baked/cached pinned revision offline (prod: no runtime download, deterministic);
    # fall back to download if absent (dev/first-run). Mirrors the BGE-M3 load pattern.
    try:
        tok = AutoTokenizer.from_pretrained(_RERANK_MODEL, revision=_REVISION, local_files_only=True)
        mdl = AutoModelForSequenceClassification.from_pretrained(
            _RERANK_MODEL, revision=_REVISION, local_files_only=True).eval()
    except (OSError, EnvironmentError):
        tok = AutoTokenizer.from_pretrained(_RERANK_MODEL, revision=_REVISION)
        mdl = AutoModelForSequenceClassification.from_pretrained(_RERANK_MODEL, revision=_REVISION).eval()
    if active_precision() == "int8":
        eng = _quant_engine()
        if eng is not None:
            torch.backends.quantized.engine = eng
            mdl = torch.quantization.quantize_dynamic(mdl, {torch.nn.Linear}, dtype=torch.qint8)
        # else: no int8 backend on this host -> stay fp32 (the safe + accurate default; see docstring)
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
