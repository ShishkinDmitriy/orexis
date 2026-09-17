"""One want: a desire derived under another, carrying the temporals the parent has not.

The MODEL. `Wants` beside this file is the collection of them, and the split is the file naming
this package keeps — a singular file holds what a thing is, its plural holds where they are kept.

See knowledge/domain/desire.md for what separates a want from the desire it comes from, and
knowledge/decisions/a-repository-is-named-for-what-it-holds.md for why the two are separate files.
"""

from __future__ import annotations

from dataclasses import dataclass

from .desire import Desire



@dataclass(frozen=True)
class Want(Desire):
    """One want, as the store holds it: what it was derived from, when it must hold, and what
    it points at.

    A SUBCLASS, because `orexis:Want rdfs:subClassOf orexis:Desire` and the stored shapes may as
    well say what the vocabulary says. What a want ADDS to a declared desire is exactly what the
    word means: the desire it was derived from, and the temporals — a declared desire binds
    `orexis:Always` and has no instant to hold at, a want binds to one.

    STORED FACTS ONLY. How urgent it is and whether it is met are COMPUTED — a capability's
    answer about a world being judged — and belong to `Judgment`, which is what `pursuing()`
    hands out. A repository returns what is written down; the mind's view of it is not this
    object's business.
    """

    desire: str = ""                    # what it was derived from — `prov:wasDerivedFrom`
    holds_at: str | None = None         # the instant it must hold at, where it binds At
    derived_at: str | None = None
    #  When it stops holding — the instant it must hold at plus the patience its plan is given
    #  after it, for a want bound `orexis:At`; open for one met at its plan's end.
    ends: str | None = None
