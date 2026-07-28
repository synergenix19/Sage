"""Validators for psychoed content-as-code artifacts (spec §3, 2026-07-23 design).
Hand-rolled (no new deps). Each validate_* returns [] when valid, else error strings."""
from pathlib import Path
import json

# SKILL_REGISTRY lives in src/sage_poc — importable here because pytest's own
# pythonpath config (pyproject.toml [tool.pytest.ini_options] pythonpath = ["src", "."])
# puts "src" on sys.path for the whole test session before this module is ever imported
# (schemas.py is only ever reached via tests/test_psychoed_content_integrity.py today).
# No extra sys.path surgery needed here; if schemas.py is later invoked outside pytest,
# this import will need `sys.path.insert(0, "src")` first.
from sage_poc.skill_ids import SKILL_REGISTRY

EM_DASHES = ("—", "–")
SOURCE_FILE = "docs/superpowers/specs/bot-behaviour-oracle/bot_behaviour_full.md"
CATEGORIES = ("1f", "3c", "4b", "6d", "7c", "s2c")
DELIVERY_SHAPES = ("menu_first", "answer_first")
ROW_ROUTES = ("standard", "direct_diagnostic", "formal_diagnosis")
FRAMINGS = ("personal", "abstract")
ROW_PROVENANCES = ("doc_table", "inferred")

def _load(path: Path):
    return json.loads(Path(path).read_text())

def _req(d, keys, errs, prefix=""):
    for k in keys:
        if k not in d:
            errs.append(f"missing {prefix}{k}")

def validate_block(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("article_id", "language", "title", "content", "is_crisis_content", "psychoed"), errs)
    p = d.get("psychoed", {})
    _req(p, ("category", "article_family", "delivery_shape", "verbatim", "atomic",
             "menu_label", "source_citation"), errs, "psychoed.")
    if p.get("category") not in CATEGORIES:
        errs.append(f"bad category {p.get('category')}")
    if p.get("delivery_shape") not in DELIVERY_SHAPES:
        errs.append(f"bad delivery_shape {p.get('delivery_shape')}")
    if p.get("verbatim") is not True or p.get("atomic") is not True:
        errs.append("verbatim/atomic must be true")
    if p.get("source_citation", {}).get("file") != SOURCE_FILE:
        errs.append("source_citation.file must be the full extraction")
    if d.get("article_id") != Path(path).stem:
        errs.append("article_id != filename")
    if "<VERBATIM" in d.get("content", ""):
        errs.append("untranscribed placeholder")
    return errs

def validate_manifest(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("category", "delivery_shape", "safety_weave", "framing_statement",
             "menu_offer", "check_in", "blocks", "bridge_map", "source_citation"), errs)
    if d.get("delivery_shape") not in DELIVERY_SHAPES:
        errs.append("bad delivery_shape")
    if not isinstance(d.get("safety_weave"), bool):
        errs.append("safety_weave must be bool")
    for b in d.get("bridge_map", []):
        _req(b, ("block_id", "skill_id", "offer"), errs, "bridge_map.")
        if b.get("offer") != "optional":
            errs.append("bridge offers are optional-not-automatic (spec §3.2)")
        if b.get("skill_id") is not None:
            if b.get("skill_id") not in SKILL_REGISTRY:
                errs.append(f"bridge_map skill_id not in registry: {b.get('skill_id')}")
        else:
            _req(b, ("doc_target", "status"), errs, "bridge_map.")
    for field in ("framing_statement", "menu_offer", "check_in"):
        for ch in EM_DASHES:
            if ch in d.get(field, ""):
                errs.append(f"em/en dash in {field}")
    return errs

def validate_trigger_table(path) -> list[str]:
    errs: list[str] = []
    d = _load(path)
    _req(d, ("category", "language", "rows", "source_citation"), errs)
    seen: set[str] = set()
    for r in d.get("rows", []):
        _req(r, ("row_id", "type", "framing", "route", "phrases", "row_provenance"), errs, "row.")
        if r.get("framing") not in FRAMINGS:
            errs.append(f"{r.get('row_id')}: bad framing")
        if r.get("route") not in ROW_ROUTES:
            errs.append(f"{r.get('row_id')}: bad route")
        if r.get("row_provenance") not in ROW_PROVENANCES:
            errs.append(f"{r.get('row_id')}: bad row_provenance")
        for ph in r.get("phrases", []):
            if ph.lower() in seen:
                errs.append(f"duplicate phrase within table: {ph}")
            seen.add(ph.lower())
    return errs

def iter_psychoed_files(kind: str) -> list[Path]:
    roots = {"block": "data/psychoed/blocks/en",
             "manifest": "data/psychoed/manifests",
             "trigger_table": "data/psychoed/trigger_tables/en"}
    return sorted(Path(roots[kind]).rglob("*.json"))
