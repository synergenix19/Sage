"""#233 — continuation-context crisis-recall harness (STRUCTURE; labels arrive from the #231 session).

Consumes the #231 deck format VERBATIM — the interface contract, so the session's output drops in
without transformation: the five schema fields (crisis, tier, flag, set, context) plus the clinician
disposition columns (clinician_tier, dialect_ok). Reports THREE lines, exactly as signed (D5 + the
R2→D3 qualifier on #232/#233):

  1. Node-1 recall  — STANDALONE (context-free) positives ONLY. A single-utterance classifier is
     accountable only for meaning it can see. This is the Node-1 sub-target's scope.
  2. System recall  — ALL positives, target >= 0.95. Context-required positives are credited to the
     D3 sticky-state layer (guaranteed scrutiny within a stickied session), NOT to Node 1.
  3. Cross-session residual — context-required positives arriving in a NEW session: caught by NEITHER
     MARBERT (no markers) NOR session-sticky D3. EXPECTED-MISS under the signed design
     (D3 reset=session-end). Measured, not hidden — so D3's duration is later revisited with data.

Plus precision on the negative set. Detection is a pluggable callable, so this structure runs today
against a stub and against the real Node-1 classifier when it lands. Nothing here labels or fine-tunes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SYSTEM_RECALL_TARGET = 0.95  # D5, clinician-set — same guarantee as first disclosure

STANDALONE = "standalone"
CONTEXT_REQUIRED = "context-required"
POS = "POS"
NEG = "NEG"


@dataclass
class DeckItem:
    """One row of the #231 labeling deck. Extra columns are preserved in `raw` (forward-compatible)."""
    id: str
    text: str
    lang: str
    crisis: bool
    set: str                 # POS / NEG
    context: str             # standalone / context-required (field 5 — the routing field)
    tier: str | None = None
    flag: str | None = None
    clinician_tier: str | None = None
    dialect_ok: bool | None = None
    raw: dict = field(default_factory=dict)

    @property
    def is_pos(self) -> bool:
        return self.set == POS

    @property
    def is_standalone(self) -> bool:
        return self.context == STANDALONE


# Detector contract: given an item and whether the session is crisis-stickied (D3), return True iff
# the system flags the turn as crisis. `session_stickied=True` models the D3 monitoring guarantee.
Detector = Callable[[DeckItem, bool], bool]


def _validate_deck(deck: list[DeckItem]) -> None:
    """FAIL LOUD on set/crisis inconsistency. `set` and `crisis` are independent columns in the #231
    schema, but a POS item MUST be crisis=True and a NEG item crisis=False. A mismatch is a labeling
    error (e.g. `crisis` corrected in triage but `set` not) that would otherwise silently shrink a
    denominator on a >=95% gate, or penalise precision for a correct detection — so we raise rather
    than drop. No silent caps on a clinical-recall metric."""
    bad = [i.id for i in deck if i.is_pos != i.crisis]
    if bad:
        raise ValueError(
            "deck set/crisis inconsistency (POS must be crisis=True, NEG crisis=False): "
            + ", ".join(bad)
        )


def load_deck(path: str | Path) -> list[DeckItem]:
    """Load a JSONL deck in the #231 schema. Unknown columns are kept in `raw` (no transformation)."""
    items: list[DeckItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        items.append(DeckItem(
            id=d["id"], text=d["text"], lang=d.get("lang", ""),
            crisis=bool(d["crisis"]), set=d["set"], context=d["context"],
            tier=d.get("tier"), flag=d.get("flag"),
            clinician_tier=d.get("clinician_tier"), dialect_ok=d.get("dialect_ok"),
            raw=d,
        ))
    _validate_deck(items)
    return items


@dataclass
class HarnessReport:
    node1_recall: float | None            # standalone positives only
    node1_n: int
    system_recall: float | None           # all positives; context-required credited to D3
    system_n: int
    system_pass: bool
    cross_session_residual_rate: float | None   # context-required missed under fresh-session
    cross_session_n: int
    precision: float | None               # negatives that did NOT fire / all negatives
    neg_n: int

    def format(self) -> str:
        def pct(x): return "n/a" if x is None else f"{x*100:.1f}%"
        return (
            "continuation-recall harness\n"
            f"  1. Node-1 recall (standalone POS, n={self.node1_n}):        {pct(self.node1_recall)}\n"
            f"  2. System recall (all POS, n={self.system_n}, target {SYSTEM_RECALL_TARGET*100:.0f}%): "
            f"{pct(self.system_recall)}  [{'PASS' if self.system_pass else 'FAIL'}]\n"
            f"  3. Cross-session residual (context-req, n={self.cross_session_n}, EXPECTED-MISS): "
            f"{pct(self.cross_session_residual_rate)}\n"
            f"  precision (NEG, n={self.neg_n}):                    {pct(self.precision)}"
        )


def score(deck: list[DeckItem], detect: Detector) -> HarnessReport:
    """Score a labeled deck against a detector. Pure — no I/O, no model loading. Raises on a
    set/crisis-inconsistent deck (fail-loud; see _validate_deck), so a directly-built deck is held
    to the same invariant as a loaded one."""
    _validate_deck(deck)
    pos = [i for i in deck if i.is_pos]      # crisis==True guaranteed by _validate_deck
    neg = [i for i in deck if not i.is_pos]  # crisis==False guaranteed by _validate_deck
    standalone_pos = [i for i in pos if i.is_standalone]
    context_pos = [i for i in pos if not i.is_standalone]

    # 1. Node-1: standalone positives, detector on the utterance alone (no sticky).
    node1_hits = sum(1 for i in standalone_pos if detect(i, False))
    node1_recall = (node1_hits / len(standalone_pos)) if standalone_pos else None

    # 2. System: standalone covered iff Node-1 fires; context-required covered by D3 (in-session).
    system_covered = node1_hits + len(context_pos)   # D3 guarantees scrutiny within a stickied session
    system_recall = (system_covered / len(pos)) if pos else None
    system_pass = bool(system_recall is not None and system_recall >= SYSTEM_RECALL_TARGET)

    # 3. Cross-session residual: context-required in a FRESH session (no sticky) — expected miss.
    cross_hits = sum(1 for i in context_pos if detect(i, False))
    cross_residual = ((len(context_pos) - cross_hits) / len(context_pos)) if context_pos else None

    # Precision: negatives must NOT fire (standalone; the worst case is fresh-session no-sticky).
    neg_fired = sum(1 for i in neg if detect(i, False))
    precision = (1 - neg_fired / len(neg)) if neg else None

    return HarnessReport(
        node1_recall=node1_recall, node1_n=len(standalone_pos),
        system_recall=system_recall, system_n=len(pos), system_pass=system_pass,
        cross_session_residual_rate=cross_residual, cross_session_n=len(context_pos),
        precision=precision, neg_n=len(neg),
    )
