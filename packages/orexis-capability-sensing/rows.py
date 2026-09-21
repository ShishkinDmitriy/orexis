"""The Want-shaped rows sensing mints — split from `regions.py` by #455.

A base class is an import: `ObservedWant` subclasses the mind's `Want`, so the file
defining it loads the deliberation layer the moment it is imported. The queries, the
`Region`/`Gap` arithmetic and the derivation live in `regions.py`, which a sensing-only
assembly may import freely; what lives here is exactly what only a RUNNING mind constructs,
and `regions.__getattr__` forwards the names so no caller moved.
"""

from __future__ import annotations

from dataclasses import dataclass

from orexis_agent_deliberation.want import Want

from .regions import _desired, _known, _measured_urgency, regions_of, _subjects_of


@dataclass(frozen=True)
class ObservedWant(Want):
    """A desire ABOUT AN OBSERVED PROPERTY — the kernel's `Want`, plus the one thing this
    package knows about it that the kernel does not. A stake and a freshness want are both
    of this kind; an obligation and a call are not. The kernel ranks, plans for and commits to the
    base type by its node; whoever needs the property asks this package, which is where the
    property was ever meaningful (the-stake-is-sensings-want).

    Named for the KIND, as every type is: a desire is the kind and a want is one of them
    (knowledge/domain/desire.md)."""
    observed_property: str | None = None


def desires_of(desires, beliefs, agent_uri: str, measure=None) -> list[Want]:
    """Sensing's wants, hottest first: every stake, and every freshness want.

    Was the kernel's `desires_of`, and it read the DUTIES too — the ledger reads its own now
    (`agent/ower.py`), and what is left here is exactly the two kinds of want whose premise is
    an observation: a region a reading should sit inside, and an instrument that should have
    spoken recently. Two handles since the dataset split (#298): `desires` answers what is
    WANTED (`desires.rq`, this package's), `beliefs` what IS (the sensed graph), and the join
    is here. The MAGNITUDE is nobody's arithmetic here: `measure` is the choir's own
    (`_measured_urgency`), so the ranking and the gap cannot disagree.

    A want whose reading is missing is maximally urgent: not knowing whether the pot is dying
    outranks knowing it is uncomfortable, which is why the first intention is always to look.
    """
    subjects = _subjects_of(beliefs, agent_uri)
    known, by_instrument = _known(beliefs)
    regions = regions_of(beliefs, agent_uri)     # the bands' edges, off the belief base (#579)
    out = []
    for row in _desired(desires, agent_uri):
        if row["kind"] == "freshness":
            subject = None
            item = by_instrument.get((row.get("instrument"), row["property"]))
        else:
            subject = next((s for s in subjects if (s, row["property"]) in known), None)
            item = known.get((subject, row["property"])) if subject else None
        value = item.value if item else None
        if row["kind"] == "freshness":
            #  MEASURED like everything else since the want moved into sensing, where the
            #  reading and the horizon both live. The number it comes back with is the one
            #  this branch used to compute — maximal while nothing current is known, zero
            #  otherwise — and the difference is that the planner can now ask the same
            #  question of a world nobody is in yet, which is what lets a look be preferred
            #  to standing still instead of being recognised by a special case.
            #
            #  The STATE stays here, because it is a different question and one this side
            #  holds the clock for: which of the two ways of not knowing this is. The measure
            #  reads the same published horizon, so the two cannot disagree about whether a
            #  reading is current — one fact, two readers, rather than two definitions.
            #  STILL ASKED, and no longer carried: the number does not ride out on the want
            #  any more, but WHICH kind of not-current this is is read off it, so the label and
            #  the measure cannot part company. It goes when the measure does.
            current = _measured_urgency(measure, row, value)
            #  READ OFF THE MEASURE, so the label and the number cannot part company. It used
            #  to come off `_is_stale`, which declines to judge at all where no horizon has
            #  been published — so a want the measure scored maximal reported `met`, which is
            #  the disagreement the reification was supposed to have ended. Anything the
            #  measure does not call current is not current; WHICH kind of not-current it is
            #  is the reading's to say, and that distinction is worth keeping because the two
            #  are different faults (never looked, against looked and let it go cold).
            state = "met" if current < 1.0 else \
                ("unmeasured" if value is None else "stale")
        else:
            region = regions.get(row["property"])
            if region is None:
                continue
            if value is None:
                state = "unmeasured"
            else:
                #  A STAKE JUDGES THE NUMBER IT HAS. It used to go maximal when the reading was
                #  past sensing's horizon, which meant the kernel judging staleness with a word
                #  that is sensing's; not knowing is the freshness want's business now — hot,
                #  and answered first by `want_about` — and the stake says how the last
                #  number sits, which is what it knows.
                #  Whichever capability MEASURES such wants, asked through the choir's own the
                #  caller handed in — the same question the planner asks of a candidate
                #  world, which is the whole point of one measure. The STATE stays the
                #  region's: met is the shape's verdict, urgency is the measure's, and since
                #  the measure is anchored at the aim the two genuinely differ —
                #  met-and-urgent is an agent inside its region and off its pick, a true
                #  situation, not a contradiction.
                #  THE STATE IS THE REGION'S, and the measure is not asked here at all now:
                #  met is the shape's verdict, and how far off the reading sits was the number
                #  that rode out on the want.
                state = "unmet" if value < region.low or value > region.high else "met"
        out.append(ObservedWant(uri=row["desire"], state=state,
                        observed_property=row["property"], value=value,
                        read_at=item.at if item else None,
                        #  Only a freshness row binds one, which is what makes it the
                        #  discriminator rather than a decoration.
                        instrument=row.get("instrument")))
    #  NO ORDER OF MY OWN. These came back hottest first, and nothing chose by it: every want
    #  handed up is planned for, so the sort decided which was planned first and nothing else.
    return out
