"""`statements`: a document, as what was said — each graph a statement, whatever kind it said.

**WHAT A DOCUMENT SAYS ITS GRAPH IS, IS PART OF WHAT WAS SAID.** A peer's document names its graphs and
says in its default graph what each one is, and a world's files do the same; but a world's files are
asserted and a peer's are testimony. So every graph a document heard or said holds is a statement
(`speech:StatementGraph`), a kind no reader of the mind is handed, and a kind it says that is not beneath
that is not kept: whatever a peer types its graph as — an action graph, a world, a belief — it is read
by no planner, no executor and no rule as anything but what was said
(a-peers-word-is-testimony-and-a-rule-makes-it-a-belief). A kind a domain names beneath the statement —
the market's round, its claim — stays, since it lifts the graph into nothing. Every other row it states
of its graph, its period first, stays as it was said.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.store import closed, kinds_in

from .ontology import STATEMENT_GRAPH

_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def statements(store: ox.Store, doc: ox.Store) -> ox.Store:
    """`doc` with every graph it holds a statement: each said `speech:StatementGraph`, and each kind it
    said of one kept only where the vocabulary `store` holds puts that kind beneath the statement."""
    out = ox.Store()
    graphs = {ox.NamedNode(g) for g in kinds_in(doc)}
    for q in doc:
        if q.graph_name == ox.DefaultGraph() and q.subject in graphs and q.predicate == _TYPE:
            if STATEMENT_GRAPH not in closed(store, q.object.value):
                continue                      # a kind that would make what was said more than said
        out.add(q)
    for graph in graphs:
        out.add(ox.Quad(graph, _TYPE, ox.NamedNode(STATEMENT_GRAPH), ox.DefaultGraph()))
    return out
