"""Download and normalise CRADLE Bench eval split to our internal JSONL format.

Find the dataset URL from arXiv 2510.23845 / ACL Anthology 2026.eacl-long.73,
then set CRADLE_EVAL_URL below before running.

Output: tests/fixtures/cradle_bench/eval.jsonl
One line per example: {"id": str, "text": str, "label": str, "split": "eval"}

Labels (normalised to snake_case):
    active_suicide_ideation, passive_suicide_ideation, self_harm,
    rape, domestic_violence, sexual_harassment, child_abuse_endangerment, safe
"""
import json
import csv
import io
import sys
from collections import Counter
from pathlib import Path
import requests

# ── Set this to the actual download URL found from the paper ──────────────
CRADLE_EVAL_URL = ""  # e.g. "https://raw.githubusercontent.com/.../eval.jsonl"
# ──────────────────────────────────────────────────────────────────────────

OUT_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "cradle_bench" / "eval.jsonl"

_LABEL_ALIASES: dict[str, str] = {
    "active_suicide_ideation": "active_suicide_ideation",
    "active_suicidal_ideation": "active_suicide_ideation",
    "active suicidal ideation": "active_suicide_ideation",
    "asi": "active_suicide_ideation",
    "suicidal ideation (active)": "active_suicide_ideation",
    "passive_suicide_ideation": "passive_suicide_ideation",
    "passive_suicidal_ideation": "passive_suicide_ideation",
    "passive suicidal ideation": "passive_suicide_ideation",
    "psi": "passive_suicide_ideation",
    "suicidal ideation (passive)": "passive_suicide_ideation",
    "self_harm": "self_harm",
    "self-harm": "self_harm",
    "self harm": "self_harm",
    "sh": "self_harm",
    "rape": "rape",
    "sexual assault": "rape",
    "domestic_violence": "domestic_violence",
    "domestic violence": "domestic_violence",
    "dv": "domestic_violence",
    "sexual_harassment": "sexual_harassment",
    "sexual harassment": "sexual_harassment",
    "child_abuse_endangerment": "child_abuse_endangerment",
    "child abuse": "child_abuse_endangerment",
    "child abuse/endangerment": "child_abuse_endangerment",
    "cae": "child_abuse_endangerment",
    "safe": "safe",
    "none": "safe",
    "no_risk": "safe",
    "no risk": "safe",
    "0": "safe",
}


def normalise_label(raw: str) -> str:
    key = raw.strip().lower()
    if key not in _LABEL_ALIASES:
        raise ValueError(f"Unknown CRADLE label {raw!r}. Add it to _LABEL_ALIASES.")
    return _LABEL_ALIASES[key]


def _parse_jsonl(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _parse_json(text: str) -> list[dict]:
    data = json.loads(text)
    return data if isinstance(data, list) else data.get("data", data.get("examples", []))


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _infer_text_field(row: dict) -> str:
    for key in ("text", "message", "input", "sentence", "utterance", "content"):
        if key in row:
            return row[key]
    raise KeyError(f"Cannot find text field in row keys: {list(row.keys())}")


def _infer_label_field(row: dict) -> str:
    for key in ("label", "category", "class", "crisis_type", "type", "annotation"):
        if key in row:
            return row[key]
    raise KeyError(f"Cannot find label field in row keys: {list(row.keys())}")


def _infer_id_field(row: dict, idx: int) -> str:
    for key in ("id", "example_id", "idx", "index"):
        if key in row:
            return str(row[key])
    return f"cradle_eval_{idx:04d}"


def _infer_split(row: dict) -> str:
    for key in ("split", "partition", "set"):
        if key in row and str(row[key]).lower() in ("eval", "dev", "test", "train"):
            return str(row[key]).lower()
    return "eval"


def download_and_normalise(url: str) -> list[dict]:
    print(f"Downloading from {url} ...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text

    text_stripped = text.strip()
    if text_stripped.startswith("[") or text_stripped.startswith('{"data'):
        rows = _parse_json(text)
    elif text_stripped.startswith("{"):
        # Try JSONL first (each line is a JSON object); fall back to JSON object
        try:
            rows = _parse_jsonl(text)
        except json.JSONDecodeError:
            try:
                rows = _parse_json(text)
            except (json.JSONDecodeError, AttributeError):
                print("ERROR: Could not parse response as JSONL, JSON array, or JSON object.")
                print(f"First 200 chars: {text[:200]!r}")
                sys.exit(1)
    else:
        try:
            rows = _parse_csv(text)
        except Exception:
            try:
                rows = _parse_jsonl(text)
            except json.JSONDecodeError:
                print("ERROR: Could not parse response as CSV or JSONL.")
                print(f"First 200 chars: {text[:200]!r}")
                sys.exit(1)

    normalised = []
    for idx, row in enumerate(rows):
        try:
            normalised.append({
                "id": _infer_id_field(row, idx),
                "text": _infer_text_field(row),
                "label": normalise_label(_infer_label_field(row)),
                "split": _infer_split(row),
            })
        except (KeyError, ValueError) as exc:
            print(f"  Skipping row {idx}: {exc}")
    return normalised


def main() -> None:
    if not CRADLE_EVAL_URL:
        print("ERROR: Set CRADLE_EVAL_URL in this script before running.")
        print("Find the dataset URL at: https://arxiv.org/abs/2510.23845")
        sys.exit(1)

    rows = download_and_normalise(CRADLE_EVAL_URL)
    eval_rows = [r for r in rows if r["split"] in ("eval", "test")]
    if not eval_rows:
        print("WARNING: No eval/test split found -- using all rows.")
        eval_rows = rows

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fh:
        for row in eval_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    counts = Counter(r["label"] for r in eval_rows)
    print(f"\nWrote {len(eval_rows)} examples to {OUT_PATH}")
    print("Label distribution:")
    for label, count in sorted(counts.items()):
        print(f"  {label:35s} {count:4d}")


if __name__ == "__main__":
    main()
