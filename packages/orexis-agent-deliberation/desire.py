"""The desires this agent holds, as they are WRITTEN DOWN — and the modality they live in.

A **desire** here is a declaration: a node a package's `desires.ru` writes into the agent's roots
graph at genesis, saying what this agent stands for its whole life. It carries a binding, a label
and a met-test, it is never pursued itself, and what IS pursued is a `Want` derived under it
(`wants.py`, whose `Want` subclasses the `Desire` below exactly as `orexis:Want rdfs:subClassOf
orexis:Desire` says). Stored facts only: how urgent one is and what it currently reads are
`Want`\'s, made every pass by whichever capability holds the stake.

See knowledge/decisions/a-desire-is-declared-and-a-judgment-is-made.md and
knowledge/domain/desire.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Desire:
    """One desire as the store holds it — the DECLARED kind, standing and underived.

    IT HOLDS AT EVERY INSTANT, which its type says and its graph says again by having no period
    (a-desire-is-universal-and-a-want-is-existential). There was an `orexis:bindsWhen` carrying
    that as a fourth statement, and it is gone (#681).

    STORED FACTS ONLY. What a capability judges ABOUT one — urgency, the reading, the window
    left — is `Want`\'s and is never written down.
    """

    uri: str
    label: str = ""
    about: str | None = None
    #  What it POINTS AT rather than restates: the met-test, the avoided state, the estimate —
    #  one owner each, as `(predicate, object)` IRIs.
    points: tuple = ()
