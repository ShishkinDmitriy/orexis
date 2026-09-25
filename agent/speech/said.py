"""`said`: what this agent told a peer, believed as told."""

from __future__ import annotations

import pyoxigraph as ox

from agent.ontology import OREXIS, local_of
from agent.store import DocumentRefused, kinds_in, put_document, rows

RECORDED = OREXIS + "Recorded"

_ARRIVED_Q = """
SELECT ?arrival ?owner WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph orexis:arrivedBy ?arrival .
                                            OPTIONAL { $graph orexis:beliefsOf ?owner } } }"""


def said(store: ox.Store, me: str, doc: ox.Store) -> list[str]:
    """Believe the document `doc` as this agent said it: every graph put in, recorded and its
    own, each replacing what it said under that name before. The names written, sorted. A graph
    of the name that arrived any other way is refused — what the agent was told or what its
    world asserts is not rewritten by its own word — and so is the whole document with it."""
    for graph in kinds_in(doc):
        for r in rows(store, _ARRIVED_Q, (), graph=graph):
            if r["arrival"] != RECORDED or r.get("owner") != me:
                raise DocumentRefused(f"{local_of(me)} cannot say {graph} again: it arrived "
                                      f"{local_of(r['arrival'])}, not as this agent's word")
    return put_document(store, doc, owner=me, arrival=RECORDED, close=True)
