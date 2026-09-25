"""Preparing the ground: what a search over one scope is given, and the world it stands in.

BOTH HALVES ARE IN THE NAME. What crosses from the belief base is copied in, and what the
agent can SEE — the present, and what each prediction makes of it — is laid out as one graph
per period. The second is the reason the first is worth doing: a store with the beliefs in it
and no grounds is a store where a desire asked at a future instant sees the reading AND the
prediction of it, which is the failure `lay_ground` exists to close. It was called
`init_imaginarium`, which named the store rather than the work.

WHY THERE IS A SECOND STORE AT ALL. A plan is `(beliefs − retracts) + adds`, applied step
after step, and every step's rule is a SPARQL query. A query reads ONE store, so the question
"what would be true here" is answerable only if there is a store in which *here* is what is
true. There was not: the predecessor computed each step honestly and asked the BELIEF BASE for
the next one, so the first step was right and every step after it was predicted from the
reading on disk. Depth beyond 1 was nominal for any desire about a measured value, which is
most of them. So the rules are run against a second `pyoxigraph.Store`, in memory for the life
of one plan — the **imaginarium**, in the sovereign's word, and the word says the thing that
matters: what is in it never happened. See
knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.

**IT IS A STORE**, and was a class twice over — a subclass of the store's wrapper, then a
holder forwarding twenty-two methods of which a search called five. The graphs a rule may read
are copied in, so an ordinary query means the same thing here as it does in the belief base:
`graphs_of(PUBLIC)` discovers the same names off the same ontology graph, and `effects.apply`
cannot tell the two apart. What differs is that this one was constructed with no path, so it
is memory and there is nothing to clean up — the whole store is dropped when the plan ends,
and a crash mid-plan leaves nothing behind to find. That is most of why it is a store of its
own rather than a graph in the agent's: a graph can be forgotten to be dropped, and a store
that was never on disk cannot be.

**AND IT IS THE CHEAP HALF**, measured on this bench, alternated within one session because
the Pi drifts about twofold between invocations. A whole pass over the plans case costs
13.9 ms with this store in memory and 32.6 ms with it on disk — 2.3x, filling included. Per
operation, medians of five rounds against a 5,000-quad store: forking a two-quad graph 0.12 ms
against 0.25, forking the 5,000 22.4 ms against 92.0, a SELECT 2.6 ms against 3.3, a DELETE
0.13 ms against 0.21. So a READ pays about a third more and a WRITE pays two to four times,
which is the shape RocksDB has: the engine answers questions at nearly the same speed either
way and pays for durability when something changes. A pass writes a graph per fork, so the
argument from cleanup and the argument from cost point the same way.

**AND IT DOES NOT EVEN SAVE MEMORY, which is the reason somebody would reach for a file.** An
imaginarium after a pass over the plans case is 97 quads in 11 named graphs, filled from an
86-quad belief base — a fork copies the READINGS, not the world, so the shared thousands cross
once and each node adds its own handful. Held on disk instead, peak RSS went UP: 50 MB against
57, because RocksDB's memtables, block cache and file handles cost more than 97 quads ever
could, and the directory was 270 KB. If what is wanted is to SEE a pass after it ends, dumping
the whole imaginarium as n-quads costs 0.09 ms and 17.6 KB and hands back a text anything can
read, where a store on disk is a directory one process at a time may open.

A FUNCTION OVER TWO STORES, which is the one thing in this package that cannot be a function
over a single one. `beliefs` is read and the empty store is written; both are the engine, a
`pyoxigraph.Store`, and the caller makes the empty one. Everything that happens to a possible
world afterwards happens to that store the ordinary way, so this is the seam and not a wrapper.

ITS OWN FILE because it is its own act. `imaginarium.py` holds the doors a rule is asked
through once a world exists; this decides what a world is made OF, which is a question about
the belief base rather than about the imaginarium — and the two shared a file only because the
fill used to be three lines inside a constructor.

THE GROUND WORLDS are the second half of filling one, and `lay_ground` lays them — called by the
Planner after this, since an act calls no other act: this copies, that builds.

**AND A SECOND FILLING IS A REFRESH.** The imaginarium outlives the pass — it is the Planner's,
and what the last pass imagined is what `reroot` identifies the present in — so this is called
on a store that already holds a copy, and what it does then is take back everything the
previous filling brought across and bring it across again: a reading replaced, a forecast
swept, a claim lapsed, a round closed since are not left standing beside their successors,
and a graph the beliefs no longer hold is not left standing at all. What the store MADE for
itself — its grounds, its possible worlds, its plans, and the wants its derivation minted, which
are kept and withdrawn by their own rule — is not the copy's and stays.
"""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.ontology import BELIEF, DESIRE, PREDICTION, PUBLIC, RECORD, STATE, WANT
from agent.store import catalogue_of, forget_graph, graphs_of, rows

from .ontology import SCOPE_GRAPH

log = logging.getLogger("prepare_ground")


def prepare_ground(beliefs: ox.Store, into: ox.Store) -> ox.Store:
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
       same move under another name, and it fails the same silent way. One imaginarium is one
       scope's; the scope does not cut it, and would need a slice a rule could be REFUSED
       against before it safely could.
    2. **The catalogue**, since every read inside asks it what the graphs are.
    3. **What the agent alone holds and a rule still names**: its readings, which are where the
       search starts; its predictions, which make the grounds; and its desires and wants,
       whose shapes the packages' shapes target. Whatever
       its period — a pass asks its rules at instants of its own, and a forecast holding then is
       a graph the present has not reached. AND THE SCOPES, because the derivation runs in
       here and clusters what it reads unmet by them: without the scope graph it found none,
       and a desire broken in two scopes minted one want about both — which the plans case's
       diff showed as a `DROPPED` graph, and no case of the derivation's could, since those
       run on a store the scopes were never taken from.
    4. **The GROUND WORLDS** are `lay_ground`'s, called next: one graph per period the agent can
       see, classified `planning:GroundGraph` with the stretch it holds over.

    QUADS AND NOT TEXT, which is why this is not a `dump`-and-`load`: a serialise-and-reparse
    relabels blank nodes, so an observation node would come out the far side unequal to the one
    a retraction names.
    """
    #  ONE QUESTION, NOT FIVE. `graphs_of` takes as many kinds as a reader means and answers
    #  with the graphs of ANY of them, so asking kind by kind was four extra round trips to the
    #  catalogue for a set that is unioned anyway. Measured at 107 µs a call on the plans case,
    #  which is why the list is spelled out here rather than built in pieces.
    made = {r["g"] for r in rows(into, _MADE_Q, ())}
    for iri in graphs_of(into, *CROSSING):
        if iri not in made:
            forget_graph(into, iri)           # what the last filling brought across
    #  A READING'S REVISIONS CROSS BY KIND: what the rules concluded of it is a belief, in a graph
    #  derived from the reading's, and a met-test asks the side it holds.
    for iri in dict.fromkeys([*graphs_of(beliefs, *CROSSING), catalogue_of(beliefs)]):
        if iri is None:
            continue                          # a store nobody has told anything to has no catalogue
        into.extend(beliefs.quads_for_pattern(None, None, None, ox.NamedNode(iri)))
    return into


#  THE KINDS THAT CROSS, spelled once for the filling and the refresh.
CROSSING = (PUBLIC, STATE, PREDICTION, DESIRE, WANT, RECORD, BELIEF, SCOPE_GRAPH)

#  WHAT THE STORE MADE FOR ITSELF, which a refresh keeps: the grounds, the possible worlds and
#  the plans, which are planning's kinds, and the wants the derivation minted, which are a
#  kind that also crosses and are told apart by how they arrived — the derivation writes
#  `orexis:Derived`, and no want crosses from the beliefs that way, since the derivation runs
#  here and nowhere else.
_MADE_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    { ?g a ?kind . VALUES ?kind { planning:GroundGraph planning:PossibleGraph planning:PlanGraph } }
    UNION { ?g a orexis:WantGraph ; orexis:arrivedBy orexis:Derived } } }"""
