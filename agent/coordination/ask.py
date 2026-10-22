"""`ask`: the questions an agent says to the peers it believes in range, one per peer and constraint
(knowledge/domain/coordination/question.md).

**WHEN.** A peer is in range where it acts for a thing the agent believes NOW to hold a value on a
constraint's key — what is out of range is believed nowhere, so believing it is the whole of attention
(knowledge/domain/courier/contact.md is one way a world makes it so). The agent asks only under a
constraint it holds, and only where its walking plans give its own things values on that key: an agent
going nowhere asks nothing.

**WHAT.** The constraint, and the asker's holdings under it, said in the question's graph, which is named
for the asker, the peer and the constraint and said again each time the holdings change — never when
they have not, so a question costs one document per change and not one per pass.
"""

from __future__ import annotations

from datetime import datetime

import pyoxigraph as ox

from agent.ontology import BELIEF, SELF_GRAPH
from agent.store import graphs_of, rows

from .holdings import _heard, _key_of, _present, _said, holdings
from .ontology import COORDINATION, CONSTRAINT_GRAPH, QUESTION, QUESTION_GRAPH, question_graph

#  THE CONSTRAINTS THE AGENT HOLDS.
_HELD_Q = "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c"
#  EVERY OTHER AGENT, and each thing it acts for.
_PEERS_Q = "SELECT ?peer ?t WHERE { ?me a orexis:Self . ?peer a orexis:Agent ; orexis:actsFor ?t . FILTER(?peer != ?me) } ORDER BY ?peer ?t"
_HOLDS_Q = "SELECT ?v WHERE { $thing $p ?v } LIMIT 1"


def ask(store: ox.Store, me: str, at: datetime) -> list[tuple[str, ox.Store]]:
    """Every question the self `me` of `store` has to say at `at`, with the peer it is to: one per peer in
    range and constraint held, where the agent's holdings under it are not what it last asked."""
    held = [r["c"] for r in rows(store, _HELD_Q, [*graphs_of(store, CONSTRAINT_GRAPH), *graphs_of(store, SELF_GRAPH)])]
    out = []
    for constraint in held:
        mine = holdings(store, constraint, at)
        if not mine:
            continue
        for peer in _in_range(store, me, _key_of(store, constraint), at):
            graph = question_graph(me, peer, constraint)
            if set(_heard(store, graph)) == set(mine):
                continue
            about = [("http://www.w3.org/1999/02/22-rdf-syntax-ns#type", ox.NamedNode(QUESTION)),
                     (COORDINATION + "asks", ox.NamedNode(me)), (COORDINATION + "over", ox.NamedNode(constraint))]
            out.append((peer, _said(graph, QUESTION_GRAPH, graph, about, mine)))
    return out


def _in_range(store: ox.Store, me: str, key: frozenset[str], at: datetime) -> list[str]:
    """Every peer acting for a thing the agent believes now to hold a value on `key`."""
    present = _present(store, at)
    common = graphs_of(store, BELIEF, common=True)
    found = []
    for r in rows(store, _PEERS_Q, [*common, *graphs_of(store, SELF_GRAPH)]):
        if r["peer"] not in found and any(rows(store, _HOLDS_Q, present, thing=r["t"], p=p) for p in sorted(key)):
            found.append(r["peer"])
    return found
