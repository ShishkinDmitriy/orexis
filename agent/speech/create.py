"""`create`: speech's part (a-package-starts-itself) — it says what a step said, as the agent said it
(`said`), and tells each agent it is to, by its own `told` signal, carrying a `Told`. Linked, it connects
`told` to every transport — a part that can tell a peer. What a peer says to it, `heard` believes, called by the
transport.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.lifecycle import Signal

from .events import Told
from .said import said


class _Speech:
    def __init__(self, runtime):
        self.runtime = runtime
        #  WHAT SPEECH SAYS HAPPENED: a document for a peer (`events.Told`).
        self.told = Signal("told")

    def link(self, parts) -> None:
        for part in parts.values():
            if callable(getattr(part, "tell_to", None)):         # a transport: what reaches a peer
                self.told.connect(lambda told, tell=part.tell_to: tell(told.to, told.document))

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
