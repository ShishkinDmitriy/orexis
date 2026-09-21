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

from orexis_agent_progression.store import NAMESPACES, rows

#  WHERE A WANT IS: the graph of wants — or the record, for a debt — that holds this one, and
#  how many wants are in it, since that is what decides whether taking this one takes the graph.
_HOME_Q = """
SELECT ?g (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a orexis:Want . ?w a orexis:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:WantGraph orexis:RecordGraph } } }
GROUP BY ?g"""


def forget_want(engine, uri: str) -> None:
    """Remove one want over the ENGINE, wherever it lives.

    `Wants.delete_by_uri` was a collection's door and announced itself; this announces nothing
    and whoever called it says what changed.
    """
    home = rows(engine, _HOME_Q, (), want=uri)
    if not home:
        return
    graph, wants = home[0]["g"], int(home[0]["wants"])
    if wants == 1:
        #  A WANT IS ITS GRAPH where the derivation named it (#645), so the graph goes and the
        #  catalogue's account of it with it — one act, nothing left to tidy.
        engine.update(forget_graph(graph), prefixes=NAMESPACES)
        return
    #  SEVERAL IN ONE GRAPH: a world may ratify more than one into the graph it names, and
    #  dropping it for one of them would take its siblings. The graph stays; the want goes.
    engine.update(_forget_one(graph, uri), prefixes=NAMESPACES)


def forget_graph(graph: str) -> str:
    """The update that removes a want's whole graph, and everything the catalogue says of it.

    Shared, because there are two ways a want goes and they must leave the same nothing:
    `save_want` replaces one whole and puts it back, and `forget_want` does not. A want IS its
    graph (#645), so there is no second place to tidy — but the catalogue's account of that
    graph is not in it, and a row left pointing at an empty graph is litter every reader asking
    by class would still be handed.
    """
    return f"""DROP SILENT GRAPH <{graph}> ;
DELETE {{ GRAPH ?cat {{ <{graph}> ?p ?o . ?period ?pp ?po }} }}
WHERE  {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{graph}> ?p ?o .
          OPTIONAL {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }} }}"""


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
