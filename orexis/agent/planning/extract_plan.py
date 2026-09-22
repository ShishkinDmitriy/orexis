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
from orexis.agent.store import Raw, bind, catalogue_of, classify, clear_graph, update

from .ontology import PLAN_GRAPH

#  THE PLAN'S ROOT, and the three updates below it. Each is one statement the ENGINE runs
#  over its own graphs: nothing is read into Python, ordered there and written back.
_ROOT_U = """
INSERT {{ GRAPH $plan {{ $plan a planning:Plan ; planning:forWant $want ;
                                planning:outcome $outcome{costs} }} }}
WHERE  {{}}"""

#  A STEP PER CANDIDATE ON THE ANCESTRY. `prov:wasDerivedFrom*` walks the worlds back from the
#  one that met the want — the zero-length case is that world itself — and a ground ends the
#  walk by carrying no `planning:by`, exactly as the hand-written loop ended. The step's IRI is
#  its world's, because a world has one candidate and a name is for eyes.
_STEPS_U = """
INSERT {{ GRAPH $plan {{ ?step a execution:Step ; execution:partOf $plan ;
                                execution:fills ?action ; planning:of ?by }} }}
WHERE  {{ GRAPH $cat {{ $world prov:wasDerivedFrom* ?w . ?w planning:by ?by .
                        ?by planning:fills ?action
                        BIND(IRI(CONCAT(STR(?w), "#step")) AS ?step) }} }}"""

#  THE CHAIN, OFF THE SAME ANCESTRY. A step follows the step of the world its world was forked
#  from, so the order is the worlds' and nothing counts. This is the whole reason the walk
#  could stop being Python: ORDER was the one thing a list seemed to be needed for.
_CHAIN_U = """
INSERT {{ GRAPH $plan {{ ?prev execution:then ?step }} }}
WHERE  {{ GRAPH $cat {{ $world prov:wasDerivedFrom* ?w . ?w planning:by ?by .
                        ?w prov:wasDerivedFrom ?parent . ?parent planning:by ?was
                        BIND(IRI(CONCAT(STR(?w), "#step")) AS ?step)
                        BIND(IRI(CONCAT(STR(?parent), "#step")) AS ?prev) }} }}"""

#  WHAT EACH IS FILLED WITH, carried over unchanged: one triple per parameter under the
#  parameter's own IRI. The type and `planning:fills` are left out — a step states both in the
#  LEDGER's words instead, which is the only translation here.
_FILLING_U = """
INSERT {{ GRAPH $plan {{ ?step ?p ?v }} }}
WHERE  {{ GRAPH $cat {{ $world prov:wasDerivedFrom* ?w . ?w planning:by ?by . ?by ?p ?v .
                        FILTER(?p != planning:fills && ?p != rdf:type)
                        BIND(IRI(CONCAT(STR(?w), "#step")) AS ?step) }} }}"""


def extract_plan(store: ox.Store, world: str, want: str, outcome: str,
                 cost: float | None) -> str:
    """Mint the plan that reached `world`, into its own graph. The graph's name.

    FOUR UPDATES AND NOTHING READ OUT. It was a Python walk — one query per hop back up the
    ancestry, another per candidate for its filling, then quads built in a loop and written —
    and every part of that is something the engine does over its own graphs. What kept it in
    Python was ORDER: a plan is a chain, and a list seemed to be the only way to have one. It
    is not. A step follows the step of the world its world was forked from, so
    `execution:then` falls out of `prov:wasDerivedFrom` and nothing counts.

    REPLACED WHOLE, so a second pass over one want leaves one plan and not two — which is the
    first reason a plan is a graph rather than a corner of one: clearing it is clearing a
    graph, where before it meant removing every subject a plan of up to sixty-four steps MIGHT
    have used, a count the writer had to guess at.

    WRITTEN WHATEVER THE PASS CONCLUDED. A plan with no steps is an ANSWER, and
    `planning:outcome` is which of the three it is: the want was already met, no candidate
    points at it, or none reached it inside the budget. The three step updates then match
    nothing, which is how an answer comes to hold no steps without a branch.
    """
    graph = _plan_graph(want)
    clear_graph(store, graph)
    plan, cat = Raw(f"<{graph}>"), Raw(f"<{catalogue_of(store)}>")
    update(store, bind(_ROOT_U.format(
        costs=f' ; planning:costs "{cost}"^^xsd:decimal' if cost is not None else ""),
        plan=plan, want=Raw(f"<{want}>"), outcome=Raw(f"<{outcome}>")))
    for text in (_STEPS_U, _CHAIN_U, _FILLING_U):
        update(store, bind(text.format(), plan=plan, cat=cat, world=Raw(f"<{world}>")))
    classify(store, graph, PLAN_GRAPH, OREXIS + "Derived")
    return graph


def _plan_graph(want: str) -> str:
    """The graph one want's plan is written into — one per want, replaced whole."""
    from urllib.parse import quote
    from orexis.agent.ontology import GRAPH_PREFIX
    return GRAPH_PREFIX + "plan/" + quote(local_of(want), safe="")
