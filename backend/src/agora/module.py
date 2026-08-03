"""What every capability module is.

The contract is deliberately small: say which topics you want, handle the ones that are
yours, and start/stop cleanly. A module reads its parameters from the agent's beliefs, its
wiring from the agent's `Self`, and nothing else — in particular it never reaches for another
agent, and never writes a topic or an identifier that is not in the graph.

It does not reach for another *module* by name either. Where one capability needs something
only another can supply, it asks the agent for whoever provides a **capability family**
(`agent.provider`) or invites every sibling to contribute (`annotate`, `urgency`). Both are
resolved through the T-Box, so no capability package ever imports another's Python — which is
what lets one be added or removed without touching the rest.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

import json
import logging
import threading


class Module:
    """Base class. Subclasses set CAPABILITY to the ontology term that activates them."""

    CAPABILITY: str = ""
    name: str = "module"

    def __init__(self, agent):
        self.agent = agent  # the runtime.Agent hosting this module
        self.me = agent.me  # my wiring, from the world
        self.log = logging.getLogger(f"{agent.id}.{self.name}")

    # --- lifecycle ---

    def subscriptions(self) -> list[str]:
        """Topics this module needs. All of them come from the graph."""
        return []

    def handle(self, topic: str, payload: bytes) -> bool:
        """Return True if this module owns the message, so no other module sees it."""
        return False

    def on_reading_recorded(self, subject_uri: str, value: float) -> None:
        """This agent's perception recorded something new. Most modules do not care."""

    def start(self) -> None:
        """Called once the connection is up."""

    def stop(self) -> None:
        """Release timers and threads."""

    # --- what I can contribute to my siblings ---
    #
    # These exist so that a capability which HOLDS a judgment need not be imported by one that
    # merely needs it. Perception knows how to look; it does not know what counts as trouble,
    # because trouble is a fact about a stake, and the stake belongs to whoever holds the band.
    # So perception asks, and whoever can, answers.

    def annotate(self, subject_uri: str, value: float) -> dict:
        """What I can add to my agent's public announcement about a reading.

        Voluntary disclosure: this is the agent saying what it makes of its own state, so
        only a module that actually holds an opinion contributes one.
        """
        return {}

    def urgency(self, subject_uri: str, value: float) -> float | None:
        """How close this reading puts me to my own trouble: 0.0 (fine) to 1.0 (trouble).

        None means I have no stake in this subject and therefore no opinion. Perception uses
        it to decide how closely to watch — attention follows need, and need is not
        perception's to define.
        """
        return None

    # --- helpers every module wants ---

    @staticmethod
    def parse(payload: bytes) -> dict | None:
        try:
            doc = json.loads(payload)
            return doc if isinstance(doc, dict) else None
        except (ValueError, TypeError):
            return None

    def publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        self.agent.publish(topic, payload, retain)


class Timer:
    """A cancellable repeating timer — used by modules that act on their own schedule."""

    def __init__(self, interval_s: float, fn):
        self.interval_s = interval_s
        self.fn = fn
        self._timer: threading.Timer | None = None
        self._stopped = False

    def start(self) -> None:
        if self._stopped:
            return
        self._timer = threading.Timer(self.interval_s, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self) -> None:
        try:
            self.fn()
        finally:
            self.start()

    def stop(self) -> None:
        self._stopped = True
        if self._timer:
            self._timer.cancel()
