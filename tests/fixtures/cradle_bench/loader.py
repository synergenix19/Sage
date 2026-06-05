"""Loads the normalised CRADLE Bench JSONL into CradleCase named-tuples."""
import json
from pathlib import Path
from typing import NamedTuple


class CradleCase(NamedTuple):
    id: str
    text: str
    label: str    # normalised snake_case label from LABEL_MAP
    split: str    # "eval", "dev", or "train"


def load_cradle_split(path: Path) -> list[CradleCase]:
    """Load all examples from the given JSONL path."""
    cases = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cases.append(CradleCase(
                id=row["id"],
                text=row["text"],
                label=row["label"],
                split=row.get("split", "eval"),
            ))
    return cases
