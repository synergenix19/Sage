"""Loads the normalised CRADLE Bench JSONL into CradleCase named-tuples."""
import json
from pathlib import Path
from typing import NamedTuple

from tests.fixtures.cradle_bench.label_map import LABEL_MAP


class CradleCase(NamedTuple):
    id: str
    text: str
    label: str         # primary (most severe) normalised label from LABEL_MAP
    split: str         # "test", "dev", or "train"
    labels: tuple[str, ...]  # all normalised labels for this post (multi-label)


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
            # labels list present in new format; fall back to single label for older files
            raw_labels = row.get("labels", [row["label"]])
            labels = tuple(lb for lb in raw_labels if lb in LABEL_MAP)
            if not labels:
                labels = (row["label"],)
            cases.append(CradleCase(
                id=row["id"],
                text=row["text"],
                label=row["label"],
                split=row.get("split", "test"),
                labels=labels,
            ))
    return cases
