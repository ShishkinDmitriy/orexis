"""`create`: speech's part (a-package-starts-itself) — it says what a step said, as the agent said it
(`said`), and tells each agent it is to, by its own `told` signal, carrying a `Told`. Linked, it connects
`told` to every transport — a part that can tell a peer. What a peer says to it, `heard` keeps, called by the
transport.

STARTED, IT EXTRACTS WHAT IS BELIEVED OF EVERY STATEMENT WRITTEN (#958). It hears its own kind, heard
or said alike, and `extract` writes what the extractions conclude of it into a belief graph, which the
runtime then hands whoever revises beliefs: so the agent comes to believe its own round as its bidders
believe the round they heard, by one path, and speech names no package above it. A statement written
before this part started — a volume lived in — is extracted from at start where nothing was.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.lifecycle import Signal

from agent.store import Raw, catalogue_of, rows

from .events import Told
from .extract import extract
from .ontology import STATEMENT_GRAPH
from .said import said

#  EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
_UNEXTRACTED_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a speech:StatementGraph FILTER NOT EXISTS { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g"""


class _Speech:
    def __init__(self, runtime):
        self.runtime = runtime
        #  WHAT SPEECH SAYS HAPPENED: a document for a peer (`events.Told`).
        self.told = Signal("told")

    def link(self, parts) -> None:
        for part in parts.values():
            if callable(getattr(part, "tell_to", None)):         # a transport: what reaches a peer
                self.told.connect(lambda told, tell=part.tell_to: tell(told.to, told.document))

    def start(self, runtime) -> None:
        cat = catalogue_of(runtime.beliefs)
        if cat is not None:
            for r in rows(runtime.beliefs, _UNEXTRACTED_Q, (), cat=Raw(f"<{cat}>")):
                runtime.wrote(extract(runtime.beliefs, r["g"]))
        runtime.on(STATEMENT_GRAPH, lambda graph: extract(runtime.beliefs, graph))

    def say(self, document: ox.Store, to) -> list[str]:
        """Believe `document` as the agent said it, and tell it to every agent it is `to`; the graphs believed."""
        written = said(self.runtime.beliefs, self.runtime.me, document)
        payload = document.dump(format=ox.RdfFormat.TRIG)
        for agent in to:
            self.told.emit(Told(agent, payload))
        return written


def create(runtime) -> _Speech:
    """Speech's part: what says a document and tells it."""
    return _Speech(runtime)
