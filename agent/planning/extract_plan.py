"""Reading a plan out of the worlds that were walked to find it.

A search leaves a tree of possible worlds in the imaginarium, each saying which CANDIDATE
reached it and the candidate saying which world it was taken in — candidates connect possible
worlds. When one of them meets the want, the plan is that world's ancestry: walk
`planning:by/planning:from` back to the ground the pass started in, and mint one
`execution:Step` per candidate on the way, in order.

**THE CHAIN IS IN THE STORE, WHICH IS WHY THIS IS A FUNCTION OVER ONE.** It was a tuple each
search node carried — the candidates taken to reach it — so how a world had been reached was
known only to whatever Python object still held it, and only while the pass ran. Now the
worlds say it. A reader can ask the imaginarium how any world was reached, whether or not it
was the one a plan came from.

**A STEP IS MINTED HERE AND NOWHERE ELSE**, which is the whole difference between the two
words: a search walks candidates, and a candidate the search PICKED becomes a step. Each step
names the candidate it came from (`planning:of`), so the plan says not just what to do but
which of the moves considered at that world it was.

**A STEP IS WRITTEN IN THE WORDS OF WHOEVER READS IT.** `execution:Step`, `execution:partOf`
and `execution:then` are the ledger's, because the ledger reads them — what a plan holds, and
in what order. It reads nothing else of a step, so everything else is the SEARCH's and says
so: `planning:fills` for the action, `planning:of` for the candidate it was picked from, and
one triple per parameter under the parameter's own IRI. `plans.copy_plan` is then a copy, and
what a lower layer does not read it also does not drop.

**THE PLAN ITSELF IS THIS LAYER'S**, and so is which want it is for and how the pass ended: a
plan is what a SEARCH found, and a ledger keeps commitments rather than the reasoning that
produced them. So the root is `planning:Plan` and the ledger reads past it to the steps.
"""

from __future__ import annotations

from urllib.parse import quote

import pyoxigraph as ox

from agent.ontology import GRAPH_PREFIX, local_of
from agent.store import Raw, bind, clear_graph, rows, update

from .ontology import EXHAUSTED, NO_CANDIDATE, SATISFIED

#  ONE UPDATE, FIVE OPERATIONS, and nothing read out. It was a clear, four updates and a
#  classification of three questions each — eight round trips per plan — and every part of
#  that is something the engine does over its own graphs in one text.
#
#  1. THE ROOT, written whatever the pass concluded: a plan with no steps is an ANSWER and
#     `planning:outcome` says which of the three it is.
#  2. A STEP PER CANDIDATE ON THE ANCESTRY. `(planning:by/planning:from)*` walks the worlds
#     back from the one that met the want — the zero-length case is that world itself — and
#     the ground ends the walk by carrying no `planning:by`. A step is named for its world
#     under the plan, so two wants planning through one world mint two steps, and nothing
#     counts. What each is FILLED with rides on the
#     same row — one triple per parameter under the parameter's own IRI, the type and
#     `planning:fills` left out because a step states both in the LEDGER's words — and a
#     candidate filled with nothing still mints its step, because a template triple whose
#     variable is unbound is simply not written.
#  3. THE CHAIN, OFF THE SAME ANCESTRY: a step follows the step of the world its world was
#     taken in, so the order is the worlds' and nothing counts. This is the whole reason the
#     walk could stop being Python — ORDER was the one thing a list seemed to be needed for.
#  4. WHAT THE GRAPH IS, on its catalogue row, the catalogue found by its own row.
#  5. EVERY KIND THE VOCABULARY PUTS A PLAN GRAPH BENEATH, from one `rdfs:subClassOf` step —
#     the closure is materialised at genesis, so one step is every step. Its own operation,
#     because a vocabulary that says nothing of plan graphs must not take the row with it.
#  A STEP SAYS WHEN IT MAY BE TAKEN AND WHEN IT LANDS, in the ledger's words: `execution:notBefore` is
#  the instant of the world the step is taken in and `execution:landsAt` the instant of the world it
#  reaches, so a plan placed at the instant of its root carries that placing across, and the executor
#  keeps time by the first and holds the world to the step by the second.
#  A STEP IS NAMED FOR ITS WORLD UNDER THE PLAN — `<plan>.<world's tail>` — so two wants
#  planning through one world mint two steps, and nothing counts: a depth-numbered name needed
#  a subselect walking the ancestry per world, measured at twice this update's cost, and a
#  name is for eyes. The chain is read off the ancestry: a step follows the step of the world
#  its world was taken in.
_PLAN_U = """
INSERT { GRAPH $plan { $plan a planning:Plan ; planning:for $want ; planning:outcome $outcome $costs } }
WHERE  {} ;
INSERT { GRAPH $plan { ?step a execution:Step ; execution:partOf $plan ;
                       planning:fills ?action ; planning:of ?by ;
                       execution:notBefore ?since ; execution:landsAt ?lands . ?step ?p ?v } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                      ?by planning:fills ?action ; planning:from ?in .
                      OPTIONAL { ?in planning:atInstant ?a0 } OPTIONAL { ?in dcterms:temporal/orexis:start ?s0 }
                      OPTIONAL { ?w planning:atInstant ?lands }
                      OPTIONAL { ?by ?p ?v . FILTER(?p NOT IN (planning:fills, planning:from, rdf:type)) } }
         BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""))) AS ?step)
         BIND(COALESCE(?a0, ?s0) AS ?since) } ;
INSERT { GRAPH $plan { ?prev execution:then ?step } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                      ?w planning:by/planning:from ?parent . ?parent planning:by ?was }
         BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""))) AS ?step)
         BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?parent), "^.*/", ""))) AS ?prev) } ;
INSERT { GRAPH ?cat { $plan a planning:PlanGraph ; orexis:arrivedBy orexis:Derived } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } } ;
INSERT { GRAPH ?cat { $plan a ?kind } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }
         GRAPH ?vocabulary { planning:PlanGraph rdfs:subClassOf ?kind } }"""


#  THE CHEAPEST WORLD WHERE THE WANT IS MET — the plan, where there is one.
_BEST_Q = """
SELECT ?w ?spent WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $want ; planning:met true ; planning:weighs ?w .
    OPTIONAL { ?w planning:spent ?s } OPTIONAL { ?w planning:minted ?m } }
  BIND(COALESCE(?s, 0.0) AS ?spent) BIND(COALESCE(?m, 0) AS ?minted) }
ORDER BY ?spent ?minted LIMIT 1"""

#  THE GROUND THE SEARCH STOOD IN, and what the search spent — every weighing but the
#  ground's — which is what tells the two silences apart where nothing was met.
_ROOT_Q = """
SELECT ?g (COUNT(?y) AS ?spent) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $want ; planning:weighs ?g . ?g a planning:GroundGraph .
    OPTIONAL { ?y a planning:Weighing ; planning:for $want ; planning:weighs ?w .
               FILTER NOT EXISTS { ?w a planning:GroundGraph } } } }
GROUP BY ?g"""


def extract_plan(store: ox.Store, want: str) -> str:
    """Mint `want`'s plan from what its search left, into its own graph. The graph's name.

    THE PLAN IS THE CHEAPEST WORLD THE WANT IS MET IN, read off the weighings, and its
    ancestry; where there is none, the plan is the empty ANSWER and `planning:outcome` says
    which of the two silences it is: NO CANDIDATE says no lever this agent holds points at
    this want (equip me), EXHAUSTED says levers exist and no bounded sequence of them lands
    inside the region. A candidate weighed is a candidate seen, so what the search spent
    says which. Handed the want and nothing else, because everything a plan is made of is
    what the search wrote.

    ONE UPDATE AND NOTHING ELSE READ OUT — see `_PLAN_U` for the five operations in it. What
    kept this in Python was ORDER: a plan is a chain, and a list seemed to be the only way to
    have one. It is not. A step follows the step of the world its world was taken in, so
    `execution:then` falls out of the ancestry and nothing counts.

    REPLACED WHOLE, so a second pass over one want leaves one plan and not two — which is the
    first reason a plan is a graph rather than a corner of one.
    """
    best = next(iter(rows(store, _BEST_Q, (), want=want)), None)
    if best is not None:
        world, outcome, cost = best["w"], SATISFIED, float(best["spent"])
    else:
        root = next(iter(rows(store, _ROOT_Q, (), want=want)), None)
        if root is None:
            raise LookupError(f"nothing was weighed for {want} — has its search begun?")
        world, cost = root["g"], None
        outcome = EXHAUSTED if int(root["spent"]) else NO_CANDIDATE
    graph = _plan_graph(want)
    clear_graph(store, graph)
    update(store, bind(_PLAN_U, plan=Raw(f"<{graph}>"), want=Raw(f"<{want}>"),
                       outcome=Raw(f"<{outcome}>"), world=Raw(f"<{world}>"),
                       costs=Raw(f' ; planning:costs "{cost}"^^xsd:decimal'
                                 if cost is not None else "")))
    return graph


def _plan_graph(want: str) -> str:
    """The graph one want's plan is written into — one per want, replaced whole."""
    return GRAPH_PREFIX + "plan/" + quote(local_of(want), safe="")
