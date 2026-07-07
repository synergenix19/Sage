"""Systemic guard: every L2 intent template must declare an engagement posture.

The 2026-06-14 engagement rewrite (PR #4) enriched general_chat but silently
left info_request / exit_skill / new_skill / low_confidence on the
pre-engagement template — because nothing forced an editor to classify each
surface. This manifest converts that silent-omission failure into a FORCED
classification: a new or re-versioned L2 template that is not (re)classified
turns the build red. That is the systemic control PR #4 never had.
"""
import json
from pathlib import Path

_PROMPTS = Path(__file__).resolve().parents[1] / "src" / "sage_poc" / "prompts"
_L2_DIR = _PROMPTS / "templates" / "L2_intents"
_MANIFEST = _PROMPTS / "l2_engagement_manifest.json"

# Closed enum. `l3_owned` covers surfaces whose engagement is delivered by the
# L3 skill step, not the L2 frame (skill_continuation). Extend deliberately, in
# lockstep with a reviewed rationale — never to make a red build pass.
_ALLOWED_POSTURES = {
    "engagement_bridge",
    "terse_by_design",
    "clarifying_contract",
    "l3_owned",
}


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


def _l2_files() -> dict:
    # Key by filename stem — unique per file (the `intent` field collides across
    # variants, e.g. general_chat / general_chat_directive both intent=general_chat).
    return {p.stem: p for p in _L2_DIR.glob("*.json")}


def test_manifest_posture_enum_matches():
    assert set(_manifest()["postures"]) == _ALLOWED_POSTURES


def test_every_l2_template_has_a_manifest_entry():
    missing = set(_l2_files()) - set(_manifest()["templates"])
    assert not missing, (
        "L2 templates with no engagement-posture classification (add a manifest "
        f"entry with posture + rationale + classified_against_version): {sorted(missing)}"
    )


def test_no_orphan_manifest_entries():
    orphans = set(_manifest()["templates"]) - set(_l2_files())
    assert not orphans, f"Manifest entries with no template file: {sorted(orphans)}"


def test_every_entry_has_posture_from_enum_and_a_rationale():
    for name, e in _manifest()["templates"].items():
        assert e.get("posture") in _ALLOWED_POSTURES, f"{name}: invalid posture {e.get('posture')!r}"
        assert (e.get("rationale") or "").strip(), f"{name}: missing rationale"


def test_classified_against_matches_live_template_version():
    """Version-drift guard: content rewritten without posture re-review. If a
    template's version changed since classification, re-confirm the posture and
    bump classified_against_version to the live version."""
    files = _l2_files()
    drift = []
    for name, e in _manifest()["templates"].items():
        if name in files:
            live = json.loads(files[name].read_text())["version"]
            if e.get("classified_against_version") != live:
                drift.append(
                    f"{name}: classified against {e.get('classified_against_version')!r}, live is {live!r}"
                )
    assert not drift, "Re-confirm posture and bump classified_against_version:\n" + "\n".join(drift)
