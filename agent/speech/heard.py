"""`heard`: a peer's document, believed as it stands — or refused whole."""

from __future__ import annotations

import logging

import pyoxigraph as ox

from agent.ontology import OREXIS, STATE, local_of
from agent.store import DocumentRefused, closed, document_of, kinds_in, put_document, rows

log = logging.getLogger("speech")

RECEIVED = OREXIS + "Received"

_ARRIVED_Q = """
SELECT ?arrival WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph orexis:arrivedBy ?arrival } }"""


def heard(store: ox.Store, me: str, payload: bytes) -> list[str]:
    """Believe the document `payload` holds, as a peer said it: every graph it names put in, each
    replacing what a peer said under that name before, received and this agent's. The names
    written, sorted — and none, said in the log, where the document is no document, a graph is
    no state or a graph of its name arrived another way."""
    try:
        doc = document_of(payload)
        for graph, kinds in kinds_in(doc).items():
            if not any(STATE in closed(store, kind) for kind in kinds):
                raise DocumentRefused(f"{graph} is no state of the world — a peer says what is, "
                                      f"never a desire, an action or a rule")
            arrived = [r["arrival"] for r in rows(store, _ARRIVED_Q, (), graph=graph)]
            if arrived and arrived != [RECEIVED]:
                raise DocumentRefused(f"{graph} is not a peer's to say again — it arrived "
                                      f"{', '.join(local_of(a) for a in arrived)}")
    except DocumentRefused as exc:
        log.warning("%s: a document heard and not believed: %s", local_of(me), exc)
        return []
    return put_document(store, doc, owner=me, arrival=RECEIVED, close=True)
