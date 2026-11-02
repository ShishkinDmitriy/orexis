"""`briefing`: what the model is handed before a person's words — who the agent is, the world as it believes it,
and what it holds now (knowledge/domain/translation/briefing.md).

**TWO BLOCKS, THE FIRST CACHED.** `briefing` answers the self graph and the common beliefs as Turtle with the
store's prefixes, the world's documents and the vocabularies they speak with their comments, which change when a
document does; and the status, which changes with every reading, apart, so the first is one prefix the provider
may cache across a conversation's turns and the questions of a few minutes.

**IT IS READ ON THE RUNTIME'S THREAD**, as every read of the store is, and handed to the model's thread as text.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.ontology import BELIEF, SELF_GRAPH
from agent.store import NAMESPACES, graphs_of


def _turtle(store: ox.Store, graphs) -> str:
    """Every triple of `graphs` as one Turtle document, with the store's prefixes."""
    out = ox.Store()
    for graph in graphs:
        out.extend(ox.Quad(q.subject, q.predicate, q.object) for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
    return ox.serialize(out, format=ox.RdfFormat.TURTLE, prefixes=NAMESPACES).decode()


def briefing(store: ox.Store, status: str) -> tuple[str, str]:
    """Who the agent is and the world as it believes it, then what it holds now: the two blocks of the briefing."""
    world = ("WHO YOU SPEAK FOR, its self graph:\n\n" + _turtle(store, graphs_of(store, SELF_GRAPH)) +
             "\n\nTHE WORLD AS IT BELIEVES IT: its places, devices and society, and the vocabularies it speaks, whose "
             "comments say what each term means:\n\n" + _turtle(store, graphs_of(store, BELIEF, common=True)))
    return world, "WHAT IT HOLDS NOW:\n\n" + status
