"""`heard`: a peer's document, kept as what was said — or refused whole."""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.ontology import RECEIVED, local_of
from agent.store import DocumentRefused, document_of, kinds_in, put_document, rows

from .statements import statements

log = logging.getLogger("speech")

_ARRIVED_Q = """
SELECT ?arrival WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph orexis:arrivedBy ?arrival } }"""


def heard(store: ox.Store, me: str, payload: bytes) -> list[str]:
    """Keep the document `payload` holds as a peer said it: every graph it names a statement
    (`statements`), each replacing what a peer said under that name before, received and this agent's.
    The names written, sorted — and none, said in the log, where the document is no document, a graph of
    its name arrived another way, or it says whose a graph is or who the self is: the loader's refusal
    (`refuse_the_sovereigns`), since the hearer owns what it hears and no peer tells this agent who it is.
    No kind it says is refused: whatever it says, what is kept is what was said, and what the agent comes
    to believe of it is what its extractions conclude (`extract`, #958)."""
    try:
        doc = document_of(payload)
        for graph in kinds_in(doc):
            arrived = [r["arrival"] for r in rows(store, _ARRIVED_Q, (), graph=graph)]
            if arrived and arrived != [RECEIVED]:
                raise DocumentRefused(f"{graph} is not a peer's to say again — it arrived "
                                      f"{', '.join(local_of(a) for a in arrived)}")
    except DocumentRefused as exc:
        log.warning("%s: a document heard and not kept: %s", local_of(me), exc)
        return []
    return put_document(store, statements(store, doc), owner=me, arrival=RECEIVED, close=True)
