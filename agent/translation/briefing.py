"""`briefing`: what the model is handed before a person's words — who the agent is, what the chat lets it read, and
what it holds now (knowledge/domain/translation/briefing.md).

**SMALL, AND SCOPED BY THE CHAT.** It carries no vocabulary and no world: it names the vocabularies the chat may
read, by the name the model loads each by, and the kinds of graph its queries read, and the model loads and asks
for what the question needs. The self graph is in it where the chat reads it. A chat that reads nothing is briefed
with who the agent is and its status alone, and its model has the askables.

**TWO BLOCKS, THE FIRST CACHED.** Who the agent is and what the chat reads change when a document does; the
status, apart, changes with every reading.

**IT IS READ ON THE RUNTIME'S THREAD**, as every read of the store is, and handed to the model's thread as text.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.ontology import SELF_GRAPH, local_of
from agent.store import NAMESPACES, graphs_of


def briefing(store: ox.Store, me: str, reads, listing: str, status: str) -> tuple[str, str]:
    """Who the agent is and what the chat lets the model read, then what it holds now: the two blocks."""
    selves = graphs_of(store, SELF_GRAPH)
    who = f"YOU SPEAK FOR {local_of(me)}."
    if reads and set(selves) <= set(graphs_of(store, *reads)):
        who += " Its self graph:\n\n" + _turtle(store, selves)
    if reads:
        who += ("\n\nWHAT THIS CHAT LETS YOU READ: every graph of " + ", ".join(local_of(k) for k in reads) +
                ". Load a vocabulary to learn its terms before you query them:\n" + listing)
    else:
        who += "\n\nThis chat lets you read nothing of the agent's store beyond the questions offered as tools."
    return who, "WHAT IT HOLDS NOW:\n\n" + status


def _turtle(store: ox.Store, graphs) -> str:
    out = ox.Store()
    for graph in graphs:
        out.extend(ox.Quad(q.subject, q.predicate, q.object) for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
    return ox.serialize(out, format=ox.RdfFormat.TURTLE, prefixes=NAMESPACES).decode()
