"""What a rule is answered over in one world, once the ground is laid.

ONE READER FOR THE SEARCH AND THE DERIVATION, because a list built for the wrong instant
returns an EMPTY RESULT rather than an error (#666). The search built this for its nodes and
the derivation built its own for its boundaries, and the derivation's read the state graph
beside the prediction holding then — so a tank low now with a forecast refilling it read
unmet for ever, the exact failure the grounds were laid to close. Measured before it was
believed: the grounds were right and the want was open-ended.

WHAT IS LEFT OUT IS EVERYTHING THE GROUND SPEAKS FOR: the agent's own readings, every
prediction, and every ground and possible world but the one meant. A ground IS the readings
as they stand over a period with each prediction applied, so handing the raw state graph
beside it puts the present's value in the world next to the one that superseded it, and a
shape holding over every value sees both.

THE INSTANT IS THE WORLD'S OWN, read off its row: a possible world's `planning:atInstant`, a
ground's period start. A reader names a world and nothing else.
"""

from __future__ import annotations

from datetime import datetime

from agent.ontology import PREDICTION, STATE

from .ontology import FORESEEN
from agent.store import Raw, catalogue_of, graphs_of, remember, revisions_of, rows

from .ontology import GROUND_GRAPH, POSSIBLE_GRAPH

_WHEN_Q = """
SELECT ?at WHERE {
  GRAPH $cat { OPTIONAL { $world planning:atInstant ?a } OPTIONAL { $world dcterms:temporal/orexis:start ?start } }
  BIND(COALESCE(?a, ?start) AS ?at) }"""


def world_at(store, world: str, *, holder: str | None = None, now: datetime | None = None,
             memo=None) -> list[str]:
    """The graphs a rule reads in `world`: public knowledge, the records, the desires and the
    wants holding at the world's own instant, and the world itself in the state's place.

    `holder` narrows the agent's own graphs to one holder's where a store holds several
    agents' (a test world); `now` is the present, at which a record is read whatever instant
    is asked about (#645). `memo` is the pass's: the graphs the grounds speak for are asked
    once per store, and the list per instant once per instant, because a fork used to spend
    more of itself asking which graphs to read than reading them.
    """
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    when = remember(memo, ("when", world), lambda: next(
        (r.get("at") for r in rows(store, _WHEN_Q, (), world=world, cat=cat)), None))
    if when is None:
        raise LookupError(f"{world} says no instant — is it a ground or a possible world?")
    at = datetime.fromisoformat(when)
    #  WHAT A WORLD SPEAKS FOR: the readings, the predictions, the grounds and the possible
    #  worlds — and what the rules concluded of a reading or a prediction, since a ground is laid
    #  with those revisions and a step's effect rewrites them there. Read beside the world, a
    #  reading's old side would outlive the dose that answered it.
    def spoken():
        readings = graphs_of(store, STATE, PREDICTION)
        return frozenset([*graphs_of(store, STATE, PREDICTION, GROUND_GRAPH, POSSIBLE_GRAPH),
                          *revisions_of(store, *readings)])
    spoken_for = remember(memo, ("spoken_for",), spoken)
    known = remember(memo, ("knowable", at, holder, now), lambda: tuple(
        g for g in graphs_of(store, *FORESEEN, at=at, holder=holder, now=now)
        if g not in spoken_for))
    return [*known, world]
