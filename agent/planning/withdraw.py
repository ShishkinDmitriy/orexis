"""Withdrawing what the derivation no longer implies — the pass-level sweep, and the second
of the two things that ever happen to a want.

**A WANT IS ONE-SHOT.** It exists because something is wanted and it is gone when that is
settled: its plan finished, the search found it already reached, or the decomposition it came
from stopped producing it. A DESIRE lives forever and mints wants; a want is the occasion. So
this is not a tidy-up beside the derivation — it is the other half of a want's life, and
`derive_wants.py` holds the first. Taking ONE want away is the private act beneath, wherever
the want lives: a graph of wants holds wants and nothing else, so one want in one is the whole
of it and the graph goes; a record is somebody else's house and only the want goes.
"""

from __future__ import annotations

import logging
from datetime import datetime

from agent.ontology import OREXIS
from agent.store import NAMESPACES, Raw, bind, forget_graph, rows, update

log = logging.getLogger("withdraw")

WANT_GRAPH = OREXIS + "WantGraph"

#  WHERE A WANT IS: the graph of wants — or the record, for a debt — that holds this one, and
#  how many wants are in it, since that is what decides whether taking this one takes the graph.
_HOME_Q = """
SELECT ?g ?kind (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a orexis:Want . ?w a orexis:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:WantGraph orexis:RecordGraph } } }
GROUP BY ?g ?kind"""


#  TAKE ONE WANT OUT OF A GRAPH THAT HOLDS OTHERS, leaving them untouched — the text
#  `forget_want` runs, and the one the derivation runs before it puts a want back, since
#  replacing a want whole is removing it and putting it back.
#
#  EVERYTHING REACHABLE FROM IT, by a path of any predicate — `(<x>|!<x>)*`, the idiom for
#  "any step, zero or more" — because a met-test is not one step away: a want points at its
#  shape, the shape at a blank property node, the property node at the band. A pattern that
#  took the want's own rows left the shape standing, which the snapshot caught.
#
#  And the rows that point AT it, which is the holder's `orexis:holds`. Nothing else in this
#  repo points at a want from inside its own graph.
FORGET_ONE_U = """DELETE { GRAPH $graph { ?s ?p ?o } }
WHERE  { GRAPH $graph { $want (<urn:x>|!<urn:x>)* ?s . ?s ?p ?o } } ;
DELETE { GRAPH $graph { ?s ?p $want } }
WHERE  { GRAPH $graph { ?s ?p $want } }"""



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

    A WANT A PLAN IS WALKING IS KEPT whatever its desire reads, and that is the CALLER'S to
    say: the ledger is another store, so the Planner hands this the derivation's answer with
    what `execution.plans.pursued` names beside it. This used to ask the store it was handed
    for an intention graph, in a vocabulary the keeper never wrote, and in production found
    none.

    NOTHING IS LEFT BEHIND. A want IS its graph (#645), so withdrawing is `forget_want` — and
    what the search wrote ABOUT the want, its weighings over every world and its plan, goes
    with it, since the imaginarium outlives the pass and a weighing for a want that no longer
    exists is a row the frontier would still be handed.
    """
    standing = {r["w"] for r in rows(store, _DERIVED_Q, ())}
    stale = standing - set(wanted)
    if not stale:
        return []
    gone = []
    for uri in sorted(stale):
        _forget_want(store, uri)
        _forget_search(store, uri)
        log.info("%s withdrawn: its desire no longer reads it unmet", uri.rsplit("#", 1)[-1])
        gone.append(uri)
    return gone


#  THE SEARCH'S OWN ROWS ABOUT A WANT: its weighings, with the violation rows hanging off each,
#  and the plan graph it was extracted into, found by class and by the want its row names.
_WEIGHINGS_U = """
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x a planning:Weighing ; planning:for $want ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"""

_PLAN_Q = """
SELECT ?plan WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?plan a planning:PlanGraph }
  GRAPH ?plan { ?plan planning:for $want } }"""


def _forget_search(store, uri: str) -> None:
    """Drop what a search wrote about one want: every weighing for it and its plan."""
    update(store, bind(_WEIGHINGS_U, want=uri))
    for row in rows(store, _PLAN_Q, (), want=uri):
        forget_graph(store, row["plan"])


def _forget_want(store, uri: str) -> None:
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
    store.update(bind(FORGET_ONE_U, graph=Raw(f"<{graph}>"), want=Raw(f"<{uri}>")),
                 prefixes=NAMESPACES)
