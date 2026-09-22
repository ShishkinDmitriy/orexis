"""Reading a plan out of the worlds that were walked to find it.

A search leaves a tree of possible worlds in the imaginarium, each saying which world it was
forked from and which CANDIDATE made the fork. When one of them meets the want, the plan is
that world's ancestry: walk `prov:wasDerivedFrom` back to the ground the pass started in,
collect the candidates on the way, and mint one `execution:Step` per candidate, in order.

**THE CHAIN IS IN THE STORE, WHICH IS WHY THIS IS A FUNCTION OVER ONE.** It was a tuple each
search node carried — the candidates taken to reach it — so how a world had been reached was
known only to whatever Python object still held it, and only while the pass ran. Now the
worlds say it. A reader can ask the imaginarium how any world was reached, whether or not it
was the one a plan came from.

**A STEP IS MINTED HERE AND NOWHERE ELSE**, which is the whole difference between the two
words: a search walks candidates, and a candidate the search PICKED becomes a step. Each step
names the candidate it came from (`planning:of`), so the plan says not just what to do but
which of the moves considered at that world it was.

**THE STEPS ARE WRITTEN IN THE LEDGER'S WORDS.** A step is `execution:Step`, what it fills is
`execution:fills`, what follows it is `execution:then` — the execution layer's vocabulary,
because the ledger is where they are going and a step that arrived in this layer's words would
have to be translated on the way, which is a second place the two shapes could disagree.
`plans.copy_plan` is then a copy.

**THE PLAN ITSELF IS THIS LAYER'S**, and so is which want it is for and how the pass ended: a
plan is what a SEARCH found, and a ledger keeps commitments rather than the reasoning that
produced them. So the root is `planning:Plan` and the ledger reads past it to the steps.
"""

from __future__ import annotations

import pyoxigraph as ox

from orexis.agent.ontology import OREXIS, local_of
from orexis.agent.store import Raw, add_quads, bind, catalogue_of, classify, clear_graph, rows

from orexis.agent.execution.ontology import EXECUTION

from .ontology import COSTS, FOR_WANT, OF, OUTCOME, PLANNING, PLAN_GRAPH

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  ONE WORLD'S ANCESTRY, ONE HOP AT A TIME. A property path would read the whole chain in one
#  question and hand it back UNORDERED, and the order is the plan; so this walks, which is a
#  query per step and at most as many as the budget allows forks.
_BACK_Q = """
SELECT ?parent ?by WHERE {
  GRAPH $cat { $world prov:wasDerivedFrom ?parent .
               OPTIONAL { $world planning:by ?by } } }"""

#  WHAT A CANDIDATE IS FILLED WITH, which a step carries over unchanged: one triple per
#  parameter, under the parameter's own IRI. Its type and `planning:fills` are left out —
#  a step states both in the LEDGER's words instead, which is the only translation here.
_FILLING_Q = f"""
SELECT ?p ?v WHERE {{
  GRAPH $cat {{ $by ?p ?v .
                FILTER(?p != <{PLANNING}fills>
                       && ?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>) }} }}"""


def extract_plan(store: ox.Store, world: str, want: str, outcome: str,
                 cost: float | None) -> str:
    """Mint the plan that reached `world`, into its own graph. The graph's name.

    REPLACED WHOLE, so a second pass over one want leaves one plan and not two — which is the
    first reason a plan is a graph rather than a corner of one: clearing it is clearing a
    graph, where before it meant removing every subject a plan of up to sixty-four steps MIGHT
    have used, a count the writer had to guess at.

    WRITTEN WHATEVER THE PASS CONCLUDED. A plan with no steps is an ANSWER, and
    `planning:outcome` is which of the three it is: the want was already met, no candidate
    points at it, or none reached it inside the budget.
    """
    graph = plan_graph(want)
    clear_graph(store, graph)
    node, root = ox.NamedNode(graph), ox.NamedNode(graph)
    quads = [ox.Quad(root, _RDF_TYPE, ox.NamedNode(PLANNING + "Plan"), node),
             ox.Quad(root, ox.NamedNode(FOR_WANT), ox.NamedNode(want), node),
             ox.Quad(root, ox.NamedNode(OUTCOME), ox.NamedNode(outcome), node)]
    if cost is not None:
        quads.append(ox.Quad(root, ox.NamedNode(COSTS), _decimal(cost), node))

    picked = _ancestry(store, world)
    uris = [ox.NamedNode(f"{graph}.{n}") for n in range(len(picked))]
    for n, (uri, candidate) in enumerate(zip(uris, picked)):
        quads += [ox.Quad(uri, _RDF_TYPE, ox.NamedNode(EXECUTION + "Step"), node),
                  ox.Quad(uri, ox.NamedNode(EXECUTION + "fills"),
                          ox.NamedNode(candidate["action"]), node),
                  ox.Quad(uri, ox.NamedNode(EXECUTION + "partOf"), root, node),
                  ox.Quad(uri, ox.NamedNode(OF), ox.NamedNode(candidate["by"]), node)]
        if n + 1 < len(uris):
            quads.append(ox.Quad(uri, ox.NamedNode(EXECUTION + "then"), uris[n + 1], node))
        quads += [ox.Quad(uri, ox.NamedNode(p), _term(v), node)
                  for p, v in candidate["filling"]]
    add_quads(store, quads)
    classify(store, graph, PLAN_GRAPH, OREXIS + "Derived")
    return graph


def _ancestry(store: ox.Store, world: str) -> list[dict]:
    """The candidates walked to reach `world`, root first — each as its node, the action it
    fills and what it is filled with.

    IT STOPS WHERE THE CANDIDATES STOP, which is the ground the pass started in: a ground says
    `prov:wasDerivedFrom` the ground before it and no `planning:by`, so the walk reads one
    more row, finds no candidate, and ends. A ground's own ancestry is the timeline and not
    this plan's.
    """
    cat = Raw(f"<{catalogue_of(store)}>")
    out: list[dict] = []
    seen = {world}
    while True:
        found = rows(store, bind(_BACK_Q, cat=cat, world=Raw(f"<{world}>")))
        if not found or not found[0].get("by"):
            break
        by = found[0]["by"]
        filling = [(r["p"], r["v"]) for r in rows(store, bind(_FILLING_Q, cat=cat,
                                                              by=Raw(f"<{by}>")))]
        out.append({"by": by, "action": _action_of(store, cat, by),
                    "filling": filling})
        world = found[0]["parent"]
        if world in seen:                      # a cycle would be a bug, not a plan
            break
        seen.add(world)
    return list(reversed(out))


def _action_of(store: ox.Store, cat, by: str) -> str:
    (found,) = rows(store, bind(
        "SELECT ?a WHERE { GRAPH $cat { $by planning:fills ?a } }", cat=cat,
        by=Raw(f"<{by}>")))
    return found["a"]


def plan_graph(want: str) -> str:
    """The graph one want's plan is written into — one per want, replaced whole."""
    from urllib.parse import quote
    from orexis.agent.ontology import GRAPH_PREFIX
    return GRAPH_PREFIX + "plan/" + quote(local_of(want), safe="")


def _decimal(value: float) -> ox.Literal:
    return ox.Literal(str(value), datatype=ox.NamedNode(
        "http://www.w3.org/2001/XMLSchema#decimal"))


def _term(value: str):
    return ox.NamedNode(value) if "://" in value or value.startswith("urn:") \
        else ox.Literal(value)
