"""`mint`: the secret an agent draws its numbers from, minted the first time the package starts
(two-agents-that-want-one-resource-ask-each-other-and-draw-lots-for-it).

**ONE SECRET, NEVER SAID.** Random, kept in a belief of the agent's own (`secret_graph`), derived and
stamped, and in no document a peer could read: a draw's number is a hash of it and the draw's name, so
nothing is kept per draw, both agents compute the same winner from the same documents, and a test that
states the secret fixes every number. A volume lived in keeps it, so a restarted agent draws as it did.
"""

from __future__ import annotations

import secrets

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, DERIVED
from agent.store import entry, graphs_of, rows, update

from .ontology import SECRET, secret_graph

_HELD_Q = "SELECT ?s WHERE { ?me a orexis:Self ; coordination:secret ?s } LIMIT 1"


def mint(store: ox.Store, me: str) -> list[str]:
    """Mint the secret of the self `me` of `store` where it holds none; the graph written, or none."""
    if rows(store, _HELD_Q, graphs_of(store, BELIEF)):
        return []
    graph = secret_graph(me)
    update(store, f"""INSERT DATA {{ GRAPH <{graph}> {{ <{me}> <{SECRET}> "{secrets.token_hex(32)}" }}
  {entry(store, graph, BELIEF, DERIVED, me)} }}""")
    hash_named_graph(store, graph)
    return [graph]
