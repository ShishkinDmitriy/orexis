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

from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import NAMESPACES, rows

#  THE STAGES A WANT PASSES THROUGH (agent/ontology.ttl, "a want's life"). Spelled here as
#  terms, which rule 1 allows; what may never be spelled is an instance.
WANT_GRAPH = OREXIS + "WantGraph"
RECOGNIZED = OREXIS + "Recognized"
PLANNING = OREXIS + "Planning"
READY = OREXIS + "Ready"
PURSUED = OREXIS + "Pursued"
DONE = OREXIS + "Done"
FAILED = OREXIS + "Failed"
UNREACHABLE = OREXIS + "Unreachable"

#  WHERE A WANT IS: the graph of wants — or the record, for a debt — that holds this one, and
#  how many wants are in it, since that is what decides whether taking this one takes the graph.
_HOME_Q = """
SELECT ?g ?kind (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a orexis:Want . ?w a orexis:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:WantGraph orexis:RecordGraph } } }
GROUP BY ?g ?kind"""


def mark(engine, uri: str, state: str) -> None:
    """Move one want to a stage — the only way `orexis:state` is ever written.

    ONE VALUE AT A TIME, which is why this replaces rather than adds: a want in two stages is a
    want two readers disagree about, and the property says so in the T-Box. Whoever DECIDES a
    transition calls this; nothing infers a stage from anything else.

    SILENT FOR A WANT THAT IS NOT THERE. A pass may mark a want the derivation withdrew in the
    same breath, and an update that matches nothing is the right answer to that rather than an
    error — the want is gone, so there is no stage for it to be in.

    **`orexis:Done` IS TERMINAL and nothing moves a want out of it.** Stated as an invariant
    rather than left to call order, because the writers are meant to be independent: the
    deliberator marks a want already reached `Done` and answers with no plan, and the caller
    that asked then sees no plan and would have written `Unreachable` over it. Either of them
    knowing about the other is the coupling this design exists to avoid. What clears the stage
    is `forget_wants` taking the want away, and a desire still unmet mints a fresh one.
    """
    engine.update(f"""DELETE {{ GRAPH ?g {{ <{uri}> orexis:state ?was }} }}
WHERE  {{ GRAPH ?g {{ <{uri}> a orexis:Want ; orexis:state ?was .
          FILTER(?was != <{DONE}>) }} }} ;
INSERT {{ GRAPH ?g {{ <{uri}> orexis:state <{state}> }} }}
WHERE  {{ GRAPH ?g {{ <{uri}> a orexis:Want }}
          FILTER NOT EXISTS {{ GRAPH ?h {{ <{uri}> orexis:state <{DONE}> }} }} }}""",
                  prefixes=NAMESPACES)


#  EVERY WANT THAT IS FINISHED, for the collector below.
_DONE_Q = f"""
SELECT ?w WHERE {{
  GRAPH ?g {{ ?w a orexis:Want ; orexis:state <{DONE}> }}
  GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a ?kind .
                VALUES ?kind {{ orexis:WantGraph orexis:RecordGraph }} }} }}"""


def forget_wants(engine) -> list[str]:
    """GARBAGE COLLECTION: every want that is finished, taken away. Returns what went.

    A want is not deleted where it is finished. Deciding that something is done and clearing it
    away are two acts, and the one sweep is easier to reason about than a delete at each of the
    decision points — which is how the old code got here, with the sites that withdrew a want
    guarded on how it had been written and an authored want therefore never withdrawn at all.
    The keeper's own sweep works the same way: what ends by the clock is dropped on a tick
    rather than wherever it was noticed (#645).

    ON THE MIND'S PASS, because a want is deliberation's and this is deliberation's clock. The
    volume's other collector runs in progression, on the upkeep tick, and cannot call this one:
    progression is the lower layer and may not import upward.
    """
    gone = [r["w"] for r in rows(engine, _DONE_Q, ())]
    for uri in gone:
        forget_want(engine, uri)
    return gone


def forget_want(engine, uri: str) -> None:
    """Remove one want over the ENGINE, wherever it lives.

    `Wants.delete_by_uri` was a collection's door and announced itself; this announces nothing
    and whoever called it says what changed.
    """
    home = rows(engine, _HOME_Q, (), want=uri)
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
        engine.update(forget_graph(graph), prefixes=NAMESPACES)
        return
    #  OTHERWISE THE GRAPH STAYS and only the want goes: a world may ratify several into the
    #  graph it names, and a record is somebody else's house.
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
