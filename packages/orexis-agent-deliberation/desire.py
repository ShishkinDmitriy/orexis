"""The desires this agent holds, as they are WRITTEN DOWN — and the modality they live in.

A **desire** here is a declaration: a node a package's `desires.ru` writes into the agent's roots
graph at genesis, saying what this agent stands for its whole life. It carries a binding, a label
and a met-test, it is never pursued itself, and what IS pursued is a `Want` derived under it
(`wants.py`, whose `Want` subclasses the `Desire` below exactly as `orexis:Want rdfs:subClassOf
orexis:Desire` says). Stored facts only: how urgent one is and what it currently reads are
`Judgment`\'s, made every pass by whichever capability holds the stake.

See knowledge/decisions/a-desire-is-declared-and-a-judgment-is-made.md and
knowledge/domain/desire.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Desire:
    """One desire as the store holds it — the DECLARED kind, standing and underived.

    IT STATES NO BINDING. A desire holds at every instant, so a triple saying so said nothing
    its type did not — and while it said it, the binding was doing a type's job and a node could
    be a desire by type and a want by binding at once. `orexis:bindsWhen` is a `Want`\'s alone
    (a-kind-is-a-type-not-a-binding).

    STORED FACTS ONLY. What a capability judges ABOUT one — urgency, the reading, the window
    left — is `Judgment`\'s and is never written down.
    """

    uri: str
    label: str = ""
    about: str | None = None
    #  What it POINTS AT rather than restates: the met-test, the avoided state, the estimate —
    #  one owner each, as `(predicate, object)` IRIs.
    points: tuple = ()
