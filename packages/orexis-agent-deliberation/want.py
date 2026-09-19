"""One want: a desire derived under another, carrying the temporals the parent has not.

The MODEL. `Wants` beside this file is the collection of them, and the split is the file naming
this package keeps — a singular file holds what a thing is, its plural holds where they are kept.

See knowledge/domain/desire.md for what separates a want from the desire it comes from, and
knowledge/decisions/a-repository-is-named-for-what-it-holds.md for why the two are separate files.
"""

from __future__ import annotations

from dataclasses import dataclass




@dataclass(frozen=True)
class Want:
    """One want, as the store holds it: what it was derived from, when it must hold, and what
    it points at.

    A SIBLING OF `Desire`, NOT A SUBCLASS. It was one, mirroring `orexis:Want rdfs:subClassOf
    orexis:Desire` — and that axis is gone, because it bought nothing where it was supposed to
    pay. The closure is materialised once at genesis and a want is minted long after, so no
    runtime want was ever entailed to be a desire and every writer hand-wrote both types to
    compensate; what the subclass actually did was make `?d a orexis:Desire` match both kinds,
    which is why a collection of desires had to filter on a binding to find its own contents
    (a-kind-is-a-type-not-a-binding). The two kinds are disjoint and each means itself.

    WHAT A WANT ADDS is the occasion: the period its graph holds during, which a desire has none
    of, the
    temporals, and — where it was derived rather than authored — the desire it came from. HOW it
    came to be is not the axis: three worlds ratify a want directly and it is a want all the same.

    STORED FACTS ONLY. How urgent it is and whether it is met are COMPUTED — a capability's
    answer about a world being judged — and belong to `Judgment`, which is what `pursuing()`
    hands out. A repository returns what is written down; the mind's view of it is not this
    object's business.
    """

    uri: str
    label: str = ""
    #  WHAT IT IS ABOUT, several where the desire is: a soil-and-air want is about both, and
    #  a want minted for the soil alone is about the soil alone. It was one string, which the
    #  greenhouse already contradicted (#566); the tuple is the properties in trouble.
    about: tuple = ()
    #  What it POINTS AT rather than restates: the desire's avoided state and estimate, one
    #  owner each — as `(predicate, object)` IRIs — and its OWN met-test, below.
    points: tuple = ()
    #  ITS MET-TEST, which is the desire's instantiated at the witness: the same shape, its
    #  target the one instance in trouble and its blocks the ones about what this want is
    #  about — a plant's moisture inside its range, where the desire said every property of
    #  everything. Carried as the triples of that shape, written into the want's own graph,
    #  so a want is judged on its own instance and a plan for one tank is not refused for
    #  another's. It pointed at the desire's whole shape for a while, and read unmet for
    #  every instance the desire was about.
    shape: tuple = ()
    #  WHO HOLDS IT — `<holder> orexis:holds <want>`, written into the want's own graph, so it
    #  is a stored fact of this want and not identity the collection carries. The agent is
    #  another aggregate root; what a want records ABOUT it is the want's.
    holder: str = ""
    desire: str = ""                    # what it was derived from — `prov:wasDerivedFrom`
    holds_at: str | None = None         # the instant it must hold at, where it binds At
    derived_at: str | None = None
    #  When it stops holding — the instant it must hold at plus the patience its plan is given
    #  after it, for a want bound `orexis:At`; open for one met at its plan's end.
    ends: str | None = None

    #  WHICH WAY IT BROKE when it was minted — `orexis:violationIs`, the side the met-test's
    #  own block declared: below, above, unmeasured, stale. It was a `deliberation:Judgment`'s
    #  to carry and there is no judgment now; a want says it, because it is what decides the
    #  repair — a look answers an unmeasured one and no lever does, water answers below and
    #  drowns on above. None where the block declared none, and where a cluster's witnesses
    #  disagree: two sides in one want is a want about two troubles.
    side: str | None = None
