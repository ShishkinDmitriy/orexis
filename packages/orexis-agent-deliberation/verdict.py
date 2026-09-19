"""One stored judgment as a row: what one desire's met-test read at one instant.

THE ROW IS CALLED A VERDICT, and the node it reads is a `deliberation:Judgment`. The word
`Judgment` in this package already names what the choir assembles on every pass — the
urgency, the current reading, the deadline (`judgment.py`) — and a stored judgment is the
other half of the same thing: met or unmet, and the results where unmet. The two fold when
the choir's half is written down beside this one; until then the store's row carries the
judge's own word for what it says.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Result:
    """One `sh:ValidationResult`: the focus node in trouble, what it is about where the
    met-test's block says, which block refused it, and the offending value as a term."""

    focus: str
    about: str | None
    constraint: int
    value: str | None      # rendered as a SPARQL term — an IRI in brackets, or a typed literal


@dataclass(frozen=True)
class Verdict:
    """What one desire read at one instant: met or unmet, and the results where unmet.
    `holds_at` is the instant judged about, None for the present — as a want's is."""

    desire: str
    holds_at: datetime | None
    met: bool
    results: tuple[Result, ...] = ()
