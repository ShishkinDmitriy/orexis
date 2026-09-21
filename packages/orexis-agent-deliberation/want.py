"""One want: a desire derived under another, carrying the temporals the parent has not.

The MODEL. `wants.py` beside this file holds the reads over them, and the split is the file
naming this package keeps — a singular file holds what a thing is, its plural holds where they
are kept and how they are asked for.

See knowledge/domain/desire.md for what separates a want from the desire it comes from, and
knowledge/decisions/a-repository-is-named-for-what-it-holds.md for why the two are separate files.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime




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
    answer about a world being judged — and belong to `Want`, which is what `pursuing()`
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
    #  WHAT IT WAS DERIVED FROM — `prov:wasDerivedFrom`, and None where nothing derived it:
    #  a want a world ratifies directly, or one a package speaks for. `None` and not `""`,
    #  because whether a want stands under a desire is the question `pursuit.handed` asks to
    #  decide whether a pass must derive one first, and an empty string answers it wrongly.
    desire: str | None = None
    holds_at: datetime | None = None    # the instant it must hold at, where it binds At
    derived_at: datetime | None = None
    #  When it stops holding — the instant it must hold at plus the patience its plan is given
    #  after it, for a want bound `orexis:At`; open for one met at its plan's end.
    ends: datetime | None = None

    #  WHICH WAY IT BROKE when it was minted — `orexis:violationIs`, the side the met-test's
    #  own block declared: below, above, unmeasured, stale. It was a `deliberation:Judgment`'s
    #  to carry and there is no judgment now; a want says it, because it is what decides the
    #  repair — a look answers an unmeasured one and no lever does, water answers below and
    #  drowns on above. None where the block declared none, and where a cluster's witnesses
    #  disagree: two sides in one want is a want about two troubles.
    side: str | None = None


    #  --- and what a JUDGMENT carried, made fresh on every pass -------------------------------
    #
    #  A want was two types for a while: this one, stored, and a `Want` built per pass to
    #  say how badly it was wanted. The sovereign struck the second — all Want had, now has
    #  Want — and these are its fields. They are not stored and not read back: whoever holds
    #  the stake fills them when the choir is asked, and a want read from the store carries
    #  their defaults. Urgency is a function of a situation and a situation moves, which is why
    #  asking twice gives two answers and neither is written down.

    urgency: float = 0.0  # 0 = content, 1 = at the edge of what it can bear or of its deadline

    # What it currently reads, where whoever contributed the want has a number for it — a
    # stake's reading, filled by sensing. None when nothing has been observed, which is a gap
    # and not a zero. WHAT the want is about is not on this type: a want is its node, and a
    # package that needs the property of one it holds walks to it in its own words
    # (the-stake-is-sensings-want; sensing's `ObservedDesire` carries `observed_property`).
    value: float | None = None

    #  A PACKAGE'S WORDS ARE NOT HERE. A debt's claim and whom it is owed to were two fields
    #  of this type, and `is_obligation` read them — every kernel branch on it has gone, one
    #  slice at a time (#697, #698, #700), and the market's own judgment carries the two
    #  words now (`orexis_capability_market.ower.OwedWant`, a subclass). What the kernel does
    #  with a judgment it does with every judgment: rank it, ask whether it may be acted on,
    #  hand it to the search.

    #  When the want stops being satisfiable, carried here so the planner can
    #  hold a candidate plan's landing time to the room left (#472). A BY, not an AT: a plan
    #  for a want at an instant (`holds_at`) is placed to land there; a plan for a want that
    #  expires is refused where it would land late. A debt's deadline, set by the ledger that
    #  speaks for it; None for a stake, and None for a debt whose market stated no window.
    expires: datetime | None = None

    # An EPISTEMIC want's one: the instrument whose reading is wanted current. Present exactly
    # where the want is about knowing rather than about a number, which is what `is_epistemic`
    # reads — not a flag saying what kind this is, because a flag that can disagree with the
    # data beside it is a flag that eventually does: it is the premise, and a want derived from
    # an instrument is a want about that instrument by construction.
    #
    # It is here because two wants can now be about ONE property — fern holds a region in its
    # moisture AND wants its probe to have spoken recently — and everything that used to ask
    # "the want about this property" had exactly one answer and now has two. Whose the
    # instrument IS stays out of the kernel: this is an IRI handed over, and the capability
    # that derived the want is the one that knows what to do with it.
    instrument: str | None = None

    # Whether anything is being asked of this agent YET. A obligation nobody has presented stands and
    # may be hot, and still must not be acted on: the holder is waiting for its own watch to be
    # live, and a host that doses early spends the water where nothing is looking. Always true
    # for a stake — a plant does not ask.
    pursuable: bool = True

    #  What state the desire is in, in its own kind's vocabulary: `met`, `unmet` or `unmeasured`
    #  for a stake, `met`, `stale` or `unmeasured` for an epistemic want — where it is read off
    #  the MEASURE, so a want scored maximal can never report as met, which it did while the
    #  label came from a staleness test that declines to judge at all without a published
    #  horizon — and `standing` or `demanded` for an obligation. Carried rather than inferred from
    #  urgency, and that distinction is not academic — urgency is 0 only exactly at the point
    #  being steered for, so "urgency > 0" counts a barrel sitting comfortably inside 1-5 as
    #  unmet. It read that way on the bench for about ten minutes and made a calm society look
    #  stuck. The split is now structural: the met-SHAPE governs the state and the MEASURE
    #  governs the urgency, and they are different questions on the desire's own node.
    state: str | None = None

    #  THE ROOT THIS WANT IS DERIVED UNDER (#618), or None for a root and for anything not
    #  derived from a want. An `orexis:Desire` is never pursued itself: the row the
    #  container presents in its place carries the root's own measure and names the root
    #  here, so a mark or a lookup by either name meets the same want.


    #  THE INSTANT AN `orexis:At` WANT HOLDS AT (#619), or None. A want derived under a root
    #  from a predicted crossing: judged as the world will be THEN, late past it, and its
    #  room is the stretch to it — which the container computes into `urgency` when it
    #  presents the want, since a time room is the kernel's arithmetic as a debt's is.
    holds_at: datetime | None = None

    #  WHEN THE READING THIS ROW JUDGES WAS TAKEN, or None where nothing was read — filled by
    #  whoever holds the reading (sensing). A pass for a want met at an instant drifts the
    #  reading's AGE at its root (#619, #625): the present is the world as it was OBSERVED, a
    #  drift that counted from the pass's clock would leave those seconds undrifted, and this
    #  engine cannot turn the stretch between two instants into a number (AGENTS, the traps).
    read_at: datetime | None = None

    #  NO measure field, deliberately, and one briefly existed: a desire does not carry how
    #  its badness is scored, because that is a capability's answer and not the mind's
    #  structure (a-desire-states-its-own-measure). Whoever needs the number asks the choir —
    #  `Agent.desire_urgency(desire, query, sensed)` — of whichever world is being judged,
    #  and sensing answers for observation-backed wants from its own declaration. A obligation's
    #  fraction-of-window stays kernel Python behind a pinned engine limit (this store binds
    #  nothing for duration division — tests/test_desires.py), with the market's own
    #  declaration as its recorded future home.

    @property
    def is_met(self) -> bool:
        """Nothing is wanted here right now. A debt's judgment never says so — a debt is
        discharged, and a discharged debt is history rather than a want."""
        return self.state == "met"

    @property
    def is_epistemic(self) -> bool:
        """Is this a want about my KNOWLEDGE of something rather than about the thing?

        The two are repaired by different means — no lever moves a number you cannot see —
        and, since a property may carry one of each, whoever asks "what should I do about
        this property" has to say which of the two it means. An actuator means the number.
        """
        return self.instrument is not None

