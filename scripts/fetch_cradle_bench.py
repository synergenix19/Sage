"""Download and normalise CRADLE Bench test split to our internal JSONL format.

Source: https://huggingface.co/datasets/SungJoo/Cradle-Bench
Paper:  arXiv 2510.23845 / EACL 2026 (emorynlp/CradleBench on GitHub)
License: Public dataset, cite the EACL 2026 paper.

Output: tests/fixtures/cradle_bench/eval.jsonl
Format: {"id": str, "text": str, "label": str, "labels": list[str], "split": "test"}

  label  = primary (most clinically severe) normalised category
  labels = all normalised categories for this post (multi-label)

Normalised category values:
    active_suicide_ideation, passive_suicide_ideation, self_harm,
    rape, domestic_violence, sexual_harassment, child_abuse_endangerment, safe
"""
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path

import requests

CRADLE_EVAL_URL = (
    "https://huggingface.co/datasets/SungJoo/Cradle-Bench/resolve/main/test/test.csv"
)
OUT_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "cradle_bench" / "eval.jsonl"

# Map actual CRADLE temporal label strings → our simplified category names.
# Temporal suffixes (_ongoing / _past) are stripped; we keep both since
# safety_check_node is trained to be conservative (flag historical disclosures too).
_TEMPORAL_TO_SIMPLE: dict[str, str] = {
    # Active SI
    "suicideideation_active_ongoing":    "active_suicide_ideation",
    "suicideideation_active_past":       "active_suicide_ideation",
    "suicideideation(active)_ongoing":   "active_suicide_ideation",
    "suicideideation(active)_past":      "active_suicide_ideation",
    # Passive SI
    "suicideideation_passive_ongoing":   "passive_suicide_ideation",
    "suicideideation_passive_past":      "passive_suicide_ideation",
    "suicideideation(passive)_ongoing":  "passive_suicide_ideation",
    "suicideideation(passive)_past":     "passive_suicide_ideation",
    # Self-harm
    "selfharm_ongoing":                  "self_harm",
    "selfharm_past":                     "self_harm",
    # Rape
    "rape_ongoing":                      "rape",
    "rape_past":                         "rape",
    # Domestic violence
    "domesticviolence_ongoing":          "domestic_violence",
    "domesticviolence_past":             "domestic_violence",
    # Sexual harassment
    "sexualharassment_ongoing":          "sexual_harassment",
    "sexualharassment_past":             "sexual_harassment",
    # Child abuse / endangerment
    "childabuse_endangerment_ongoing":   "child_abuse_endangerment",
    "childabuse_endangerment_past":      "child_abuse_endangerment",
    "childabuseendangerment_ongoing":    "child_abuse_endangerment",
    "childabuseendangerment_past":       "child_abuse_endangerment",
    # Safe / no crisis
    "no_crisis":                         "safe",
    # Fallback aliases (in case HuggingFace CSV differs from paper notation)
    "active_suicide_ideation":           "active_suicide_ideation",
    "passive_suicide_ideation":          "passive_suicide_ideation",
    "self_harm":                         "self_harm",
    "rape":                              "rape",
    "domestic_violence":                 "domestic_violence",
    "sexual_harassment":                 "sexual_harassment",
    "child_abuse_endangerment":          "child_abuse_endangerment",
    "safe":                              "safe",
    "no risk":                           "safe",
    "no_risk":                           "safe",
}

# Severity order for primary label derivation (most severe first).
# For multi-label posts the most clinically severe label is used as `label`
# so the post lands in the correct crisis/clinical/safe test bucket.
_SEVERITY = [
    "active_suicide_ideation",
    "passive_suicide_ideation",
    "self_harm",
    "rape",
    "domestic_violence",
    "sexual_harassment",
    "child_abuse_endangerment",
    "safe",
]
_SEVERITY_RANK = {cat: i for i, cat in enumerate(_SEVERITY)}


def normalise_label(raw: str) -> str:
    key = raw.strip().lower().replace(" ", "").replace("-", "")
    # Try exact match first
    if raw.strip().lower() in _TEMPORAL_TO_SIMPLE:
        return _TEMPORAL_TO_SIMPLE[raw.strip().lower()]
    if key in _TEMPORAL_TO_SIMPLE:
        return _TEMPORAL_TO_SIMPLE[key]
    raise ValueError(
        f"Unknown CRADLE label {raw!r}. "
        f"Add it to _TEMPORAL_TO_SIMPLE in scripts/fetch_cradle_bench.py."
    )


def primary_label(labels: list[str]) -> str:
    """Return the most clinically severe label from a multi-label list."""
    ranked = sorted(labels, key=lambda l: _SEVERITY_RANK.get(l, len(_SEVERITY)))
    return ranked[0]


def download_and_normalise(url: str) -> list[dict]:
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    print(f"  {len(rows)} rows read.")

    # Verify expected columns
    if rows:
        cols = list(rows[0].keys())
        if "question_text" not in cols or "final_labels" not in cols:
            print(f"  WARNING: unexpected columns {cols}. Attempting field inference.")

    normalised = []
    unknown_labels: set[str] = set()
    for idx, row in enumerate(rows):
        # Resolve text and id fields
        text = (
            row.get("question_text")
            or row.get("text")
            or row.get("message")
            or row.get("content")
            or ""
        ).strip()
        id_ = (
            row.get("question_id")
            or row.get("id")
            or row.get("example_id")
            or f"cradle_test_{idx:04d}"
        )
        raw_labels_str = (
            row.get("final_labels")
            or row.get("labels")
            or row.get("label")
            or ""
        ).strip()

        if not text or not raw_labels_str:
            print(f"  Skipping row {idx}: empty text or labels (id={id_!r})")
            continue

        # Parse comma-separated multi-label string
        raw_label_list = [l.strip() for l in raw_labels_str.split(",") if l.strip()]
        normalised_labels = []
        for rl in raw_label_list:
            try:
                normalised_labels.append(normalise_label(rl))
            except ValueError:
                unknown_labels.add(rl)
        if not normalised_labels:
            print(f"  Skipping row {idx}: no valid labels (raw={raw_labels_str!r})")
            continue

        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped = []
        for lb in normalised_labels:
            if lb not in seen:
                seen.add(lb)
                deduped.append(lb)

        normalised.append({
            "id": str(id_),
            "text": text,
            "label": primary_label(deduped),
            "labels": deduped,
            "split": "test",
        })

    if unknown_labels:
        print(f"\n  WARNING: {len(unknown_labels)} unknown label strings skipped:")
        for lb in sorted(unknown_labels):
            print(f"    {lb!r}")
        print("  Add these to _TEMPORAL_TO_SIMPLE if needed.")

    return normalised


def main() -> None:
    rows = download_and_normalise(CRADLE_EVAL_URL)
    if not rows:
        print("ERROR: No examples normalised. Check the URL and column names.")
        sys.exit(1)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = Counter(r["label"] for r in rows)
    multi_label_count = sum(1 for r in rows if len(r["labels"]) > 1)
    print(f"\nWrote {len(rows)} examples to {OUT_PATH}")
    print(f"Multi-label posts: {multi_label_count}/{len(rows)}")
    print("Primary label distribution:")
    for label, count in sorted(counts.items()):
        print(f"  {label:35s} {count:4d}")


if __name__ == "__main__":
    main()
