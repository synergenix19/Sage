"""Loads the normalised CRADLE Bench JSONL into CradleCase named-tuples."""
import json
from pathlib import Path
from typing import NamedTuple

from tests.fixtures.cradle_bench.label_map import LABEL_MAP


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
            if row["label"] not in LABEL_MAP:
                raise ValueError(
                    f"Unknown CRADLE label {row['label']!r} in {path.name} "
                    f"at id={row.get('id', '?')!r}. Known labels: {sorted(LABEL_MAP)}"
                )
            cases.append(CradleCase(
                id=row["id"],
                text=row["text"],
                label=row["label"],
                split=row.get("split", "eval"),
            ))
    return cases
