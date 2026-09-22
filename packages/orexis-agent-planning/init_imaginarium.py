"""Filling an imaginarium: what a search over one scope is given, and the ground it stands on.

A FUNCTION OVER TWO STORES, which is the one thing in this package that cannot be a function
over a single one. `beliefs` is read and the empty store is written; both are the engine, a
`pyoxigraph.Store`, and the caller makes the empty one. Everything that happens to a possible
world afterwards happens to that store the ordinary way, so this is the seam and not a wrapper.

ITS OWN FILE because it is its own act. `imaginarium.py` holds the doors a rule is asked
through once a world exists; this decides what a world is made OF, which is a question about
the belief base rather than about the imaginarium — and the two shared a file only because the
fill used to be three lines inside a constructor.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from orexis_agent_execution.ontology import BELIEF, DESIRE, PREDICTION, PUBLIC, RECORD, STATE, WANT
from orexis_agent_execution.store import catalogue_of, graphs_of

from .ground import lay_ground


def init_imaginarium(beliefs: ox.Store, into: ox.Store, scope: str,
                     now: datetime) -> ox.Store:
    """Fill an empty store with what a search over one SCOPE needs, and hand it back.

    `beliefs` is read and `into` is written; both are the engine, a `pyoxigraph.Store`, and the
    caller makes the empty one. Everything that happens to a possible world afterwards happens
    to `into` the ordinary way, so this is the seam and not a wrapper.

    THREE THINGS CROSS, and then a fourth is BUILT:

    1. **Every public graph, asked rather than listed.** The record budgeted for four — world,
       derived, entailed, beliefs, 486 quads — on the reasoning that those are what the shipped
       rules read. Measured, that set makes the actuation and market CONSTRUCTs bind nothing:
       both walk `?term market:ofGood ?good`, and a valuation term is stated in a package's
       `ontology.ttl`, so it lands in the ontology graph along with the T-Box. Copying every
       public graph costs 10.4 ms and 2,646 quads on `world/loner` where the lean set is 0.6 ms
       and 165 — and the lean set is wrong in the way this function exists to prevent, since a
       pattern reaching a graph nobody copied returns an EMPTY RESULT rather than an error.
       **That measurement is also why nothing here is narrowed per scope**: fewer graphs is the
       same move under another name, and it fails the same silent way. The scope names this
       imaginarium; it does not yet cut it, and would need a slice a rule could be REFUSED
       against before it safely could.
    2. **The catalogue**, since every read inside asks it what the graphs are.
    3. **What the agent alone holds and a rule still names**: its readings, which are where the
       search starts; its picks, which a conversion comes out of; its predictions, which make
       the grounds; and its desires and wants, whose shapes the packages' shapes target. Whatever
       its period — a pass asks its rules at instants of its own, and a forecast holding then is
       a graph the present has not reached.
    4. **The GROUND WORLDS**, built here rather than copied: one graph per period the agent can
       see, classified `planning:GroundGraph` with the stretch it holds over, so which ground
       holds at an instant is the door's question. See `ground.timeline` for why a prediction
       has to be a diff for that to be possible at all.

    QUADS AND NOT TEXT, which is why this is not a `dump`-and-`load`: a serialise-and-reparse
    relabels blank nodes, so an observation node would come out the far side unequal to the one
    a retraction names.
    """
    private = [*graphs_of(beliefs, STATE), *graphs_of(beliefs, PREDICTION),
               *graphs_of(beliefs, DESIRE, WANT, RECORD), *graphs_of(beliefs, BELIEF)]
    for iri in dict.fromkeys([*graphs_of(beliefs, PUBLIC), catalogue_of(beliefs), *private]):
        if iri is None:
            continue                          # a store nobody has told anything to has no catalogue
        into.extend(beliefs.quads_for_pattern(None, None, None, ox.NamedNode(iri)))
    lay_ground(into, scope, now)
    return into
