"""`start`: what speech does once the runtime starts it (a-package-starts-itself) — it hears what a
step said, believes the document as the agent said it (`said`), and tells each agent it is to,
through whichever transport reaches that agent. What a peer says to it, `heard` believes, called
by the transport.
"""

from __future__ import annotations

import pyoxigraph as ox

from agent.events import SAID, TOLD

from .said import said


def start(runtime) -> None:
    """Believe what a step said, and tell it to every agent it is to."""
    def spoken(document: ox.Store, to) -> list[str]:
        written = said(runtime.beliefs, runtime.me, document)
        payload = document.dump(format=ox.RdfFormat.TRIG)
        for agent in to:
            runtime.emit(TOLD, to=agent, document=payload)
        return written
    runtime.listen(SAID, spoken)
