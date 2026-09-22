"""Taking a want away — the other half of a want's life, and its own module.

**A WANT IS ONE-SHOT.** It exists because something is wanted and it is gone when that is
settled: its plan finished, the search found it already reached, or the decomposition it came
from stopped producing it. A DESIRE lives forever and mints wants; a want is the occasion. So
this is not a tidy-up beside the derivation — it is the second of the two things that ever
happen to a want, and `derive_wants.py` holds the first.

**WHERE A WANT IS, ASKED RATHER THAN SPELLED.** This was `_forget(graph_of(agent_id, uri))`
inside the derivation, and the name it built was the derivation's own convention — so it
removed exactly the wants the derivation had named, and silently nothing else. A want a WORLD
ratified is in a graph the world named, so the update dropped a graph that does not exist and
reported success. Nothing ever withdrew an authored want, and that is why one had to be judged
a second time at read time to look met. A graph's name is for eyes and a reader asks its class
(AGENTS.md); this is a reader, and asking the catalogue is also what let the `agent_id`
parameter go.
"""

from __future__ import annotations

import logging

from orexis.agent.ontology import OREXIS
from datetime import datetime

from orexis.agent.store import NAMESPACES, forget_graph, rows

#  THE STAGES A WANT PASSES THROUGH (agent/ontology.ttl, "a want's life"). Spelled here as
#  terms, which rule 1 allows; what may never be spelled is an instance.
log = logging.getLogger("wants")

WANT_GRAPH = OREXIS + "WantGraph"
RECOGNIZED = OREXIS + "Recognized"
PLANNING = OREXIS + "Planning"
DONE = OREXIS + "Done"
#  TWO STATES, AND THE PREDECESSOR HAD SEVEN. A want is written RECOGNIZED when it is minted
#  and DONE when whoever decided it is finished says so, and `forget_wants` is garbage
#  collection over whatever is Done. The five between them — planning, ready, pursued, failed,
#  unreachable — were each written by a different decider, and this layer has none of those
#  deciders yet. A state nobody writes is a state no reader can trust.

#  WHERE A WANT IS: the graph of wants — or the record, for a debt — that holds this one, and
#  how many wants are in it, since that is what decides whether taking this one takes the graph.
_HOME_Q = """
SELECT ?g ?kind (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a orexis:Want . ?w a orexis:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:WantGraph orexis:RecordGraph } } }
GROUP BY ?g ?kind"""


#  EVERY WANT THAT IS FINISHED, for the collector below.
_DONE_Q = f"""
SELECT ?w WHERE {{
  GRAPH ?g {{ ?w a orexis:Want ; orexis:state <{DONE}> }}
  GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a ?kind .
                VALUES ?kind {{ orexis:WantGraph orexis:RecordGraph }} }} }}"""


#  WHAT A PLAN IS WALKING. An intention that has been adopted and not resolved pursues a want,
#  and that want is kept whatever its desire now reads: the world has not answered yet, and
#  taking the want away would leave a plan in flight with nothing it was for.
_PURSUED_Q = """
SELECT ?w WHERE {
  GRAPH ?g { ?i orexis:pursues ?w . FILTER NOT EXISTS { ?i orexis:resolvedAt ?done } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:IntentionGraph } }"""

#  EVERY WANT THE DERIVATION MINTED, ACROSS ALL TIME. Narrowed to what ARRIVED derived,
#  because a want a world ratified and a debt the ledger wrote are not this sweep's to judge:
#  no decomposition here implies them, so measured against one they would all read stale.
#
#  NOT AT AN INSTANT, and that is the same rule the derivation reads by. A want's period is the
#  stretch its TROUBLE occupies — a want foreseen from three is not handed to a reader standing
#  at two — and whether a want should still EXIST is not a question about an instant. Asked at
#  one, this would leave every foreseen want standing for ever, since it is invisible on every
#  pass until its trouble arrives and invisible again once it has lifted.
_DERIVED_Q = """
SELECT ?w WHERE {
  GRAPH ?g { ?w a orexis:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:WantGraph ; orexis:arrivedBy orexis:Derived } }"""


def withdraw(store, wanted, now: datetime) -> list[str]:
    """Drop every derived want standing at `now` that `wanted` does not name. Returns what went.

    `wanted` IS `derive_wants`' ANSWER, and that is the whole contract between them. A want
    exists because its desire read unmet, so a want the decomposition no longer produces is
    met — and the rows that say so are the ones the derivation has just read. Asking each
    standing want's own met-test again would be a second evaluation of what one pass had
    already concluded, which is what handing the conclusion on avoids.

    THE TWO ACTS ARE APART ON PURPOSE. This used to live inside the derivation, per desire, so
    "derive" and "withdraw" were one call and a caller could not have one without the other.
    They are different decisions: what is wanted is read off the desires, and what is taken
    away is read off what is wanted plus what is in flight. Being apart also makes the
    store-wide question askable — a want under a desire the world no longer states was never
    visited by a per-desire loop and stood for ever.

    A WANT A PLAN IS WALKING IS KEPT whatever its desire reads. A want IS its graph (#645), so
    withdrawing is `forget_want` and there is nothing left behind.
    """
    standing = {r["w"] for r in rows(store, _DERIVED_Q, ())}
    stale = standing - set(wanted)
    if not stale:
        return []
    pursued = {r["w"] for r in rows(store, _PURSUED_Q, ())}
    gone = []
    for uri in sorted(stale - pursued):
        forget_want(store, uri)
        log.info("%s withdrawn: its desire no longer reads it unmet", uri.rsplit("#", 1)[-1])
        gone.append(uri)
    return gone


def forget_want(store, uri: str) -> None:
    """Remove one want over the ENGINE, wherever it lives.

    `Wants.delete_by_uri` was a collection's door and announced itself; this announces nothing
    and whoever called it says what changed.
    """
    home = rows(store, _HOME_Q, (), want=uri)
    if not home:
        return
    #  A GRAPH OF WANTS holds wants and nothing else, so one want in one is the whole of it;
    #  a RECORD holds a package's own rows and a want is a guest there. `?kind` rather than
    #  `?wants` alone decides, because "one want in it" says nothing about what ELSE is in it:
    #  a record with a single want would have been dropped entire, taking the ledger's history.
    #  Several rows may come back where a graph is both; a graph of wants is the one to trust.
    home.sort(key=lambda r: r["kind"] != WANT_GRAPH)
    graph, kind, wants = home[0]["g"], home[0]["kind"], int(home[0]["wants"])
    if kind == WANT_GRAPH and wants == 1:
        #  A WANT IS ITS GRAPH where the derivation named it (#645), so the graph goes and the
        #  catalogue's account of it with it — one act, nothing left to tidy.
        forget_graph(store, graph)
        return
    #  OTHERWISE THE GRAPH STAYS and only the want goes: a world may ratify several into the
    #  graph it names, and a record is somebody else's house.
    store.update(_forget_one(graph, uri), prefixes=NAMESPACES)


def _forget_one(graph: str, uri: str) -> str:
    """Take one want out of a graph that holds others, leaving them untouched.

    EVERYTHING REACHABLE FROM IT, by a path of any predicate — `(<x>|!<x>)*`, the idiom for
    "any step, zero or more" — because a met-test is not one step away: a want points at its
    shape, the shape at a blank property node, the property node at the band. A pattern that
    took the want's own rows left the shape standing, which the snapshot caught.

    And the rows that point AT it, which is the holder's `orexis:holds`. Nothing else in this
    repo points at a want from inside its own graph.
    """
    any_step = "(<urn:x>|!<urn:x>)*"
    return f"""DELETE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}
WHERE  {{ GRAPH <{graph}> {{ <{uri}> {any_step} ?s . ?s ?p ?o }} }} ;
DELETE {{ GRAPH <{graph}> {{ ?s ?p <{uri}> }} }}
WHERE  {{ GRAPH <{graph}> {{ ?s ?p <{uri}> }} }}"""
