"""What a rule is answered over in one world, once the ground is laid.

ONE READER FOR THE SEARCH AND THE DERIVATION, because a list built for the wrong instant
returns an EMPTY RESULT rather than an error (#666). The search built this for its nodes and
the derivation built its own for its boundaries, and the derivation's read the state graph
beside the prediction holding then — so a tank low now with a prediction refilling it read
unmet for ever, the exact failure the grounds were laid to close. Measured before it was
believed: the grounds were right and the want was open-ended.

WHAT IS LEFT OUT IS EVERYTHING THE GROUND SPEAKS FOR: the agent's own state, every
prediction, and every ground and possible world but the one meant. A ground IS the state
as it stands over a period with each prediction applied, so handing the raw state graph
beside it puts the present's value in the world next to the one that superseded it, and a
shape holding over every value sees both. A PERCEPT IS NEVER IN IT, nor anything concluded of one:
what a sensor said is of no kind read here (#944), and the state a transition made of it is.

THE PERIOD IS THE WORLD'S OWN, read off its row. A ground is read at its start, the instant the
search stands at; a possible world at its start — the earliest the landings on its path reach it,
in whose ground it was forked (`take`) — and over its whole period for what else it reads: a want,
a record or a round that ends inside the period is not one a step landing anywhere in it may count
on (#596). A reader names a world and nothing else.

AND THE PRESENT IS A WORLD A STORE HOLDS WITHOUT A GROUND. Named as none, at an instant, the world is
the state as it stands and what was concluded of it — what the present ground is laid FROM
(`lay_ground`), with no prediction applied, since the present is where none has applied yet. It is
what a head is checked against as it is taken (`Planner.check`, #916): the belief base, between two
passes, after a fictive step before it wrote its effect into the readings, has no ground that says
so, and laying one per step taken would be a second pass. A world named that says no period is
still refused.
"""

from __future__ import annotations

from datetime import datetime

from agent.ontology import PREDICTION, STATE

from .ontology import FORESEEN
from agent.store import Raw, catalogue_of, graphs_of, remember, revisions_of, rows

from .ontology import GROUND_GRAPH, POSSIBLE_GRAPH

_WHEN_Q = """
SELECT ?at ?until WHERE {
  GRAPH $cat { $world dcterms:temporal ?p . ?p orexis:start ?at .
               OPTIONAL { $world a planning:PossibleGraph . ?p orexis:end ?until } } }"""


def world_at(store, world: str | None, *, holder: str | None = None, now: datetime | None = None,
             memo=None) -> list[str]:
    """The graphs a rule reads in `world`: public knowledge, the records, the desires and the
    wants holding at the world's own instant, and the world itself in the state's place — or,
    where `world` is None, the PRESENT the store holds at `now`: the state graphs and their revisions
    in the place a ground would stand.

    `holder` narrows the agent's own graphs to one holder's where a store holds several
    agents' (a test world); `now` is the present, at which a record is read whatever instant
    is asked about (#645). `memo` is the pass's: the graphs the grounds speak for are asked
    once per store, and the list per instant once per instant, because a fork used to spend
    more of itself asking which graphs to read than reading them.
    """
    if world is None:
        if now is None:
            raise ValueError("the present is read at an instant, and a reader meaning now says so")
        at = until = now
    else:
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        when = remember(memo, ("when", world), lambda: next(
            ((r.get("at"), r.get("until")) for r in rows(store, _WHEN_Q, (), world=world, cat=cat)), None))
        if when is None:
            raise LookupError(f"{world} says no period — is it a ground or a possible world?")
        at = datetime.fromisoformat(when[0])
        until = datetime.fromisoformat(when[1]) if when[1] else at
    #  WHAT A WORLD SPEAKS FOR: the readings, the predictions, the grounds and the possible
    #  worlds — and what the rules concluded of a reading or a prediction, since a ground is laid
    #  with those revisions and a step's effect rewrites them there. Read beside the world, a
    #  reading's old side would outlive the dose that answered it.
    def spoken():
        readings = graphs_of(store, STATE, PREDICTION)
        return frozenset([*graphs_of(store, STATE, PREDICTION, GROUND_GRAPH, POSSIBLE_GRAPH),
                          *revisions_of(store, *readings)])
    spoken_for = remember(memo, ("spoken_for",), spoken)
    known = remember(memo, ("knowable", at, until, holder, now), lambda: tuple(
        g for g in graphs_of(store, *FORESEEN, at=at, until=until, holder=holder, now=now)
        if g not in spoken_for))
    if world is None:
        #  THE PRESENT GROUND'S OWN FILLING, read where it lies: every state graph and what the rules
        #  concluded of it, as `lay_ground` copies them into the ground it lays at the present.
        states = graphs_of(store, STATE)
        return [*known, *states, *revisions_of(store, *states)]
    return [*known, world]
