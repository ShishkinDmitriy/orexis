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
        """Return True if this module took the message. Others are offered it regardless.

        It used to say "so no other module sees it", which was true and was the defect: the
        runtime returned on the first module that claimed a topic, and a second module
        subscribed to the same one never saw the message. Returning True is a report, not a
        claim — what it decides is whether the runtime warns that nobody wanted this.
        """
        return False

    def on_reading_recorded(self, subject_uri: str, observed_property: str, value: float) -> None:
        """This agent's perception recorded something new. Most modules do not care."""

    def on_belief_revised(self, belief_term: str, value) -> None:
        """One of my agent's beliefs has been re-picked. Take it up, if it is one of mine.

        A module reads its block once, at construction, into a frozen dataclass — which is right,
        because a belief changing under a running module would otherwise be a belief nobody could
        reason about. So a revision is announced rather than discovered, and acting on it is the
        module's own business. Most never hold a revisable figure and can ignore this.

        Note what is NOT here: a hook for contributing what to review. That is declared in the
        package's `ontology.ttl` and asked of it in its `review.rq`, so a capability needs no
        Python at all to be reviewable. See agora/review.py.
        """

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
    #
    # Both are asked about a (subject, property) pair rather than a subject. A stake is held in
    # a property — a band is a band of moisture — so a module handed a temperature must be able
    # to say it has no opinion, instead of judging it against the only scale it owns.

    def annotate(self, subject_uri: str, observed_property: str, value: float) -> dict:
        """What I can add to my agent's public announcement about a reading.

        Voluntary disclosure: this is the agent saying what it makes of its own state, so
        only a module that actually holds an opinion contributes one.
        """
        return {}

    def reports(self) -> dict:
        """Fields this module wants in its agent's own health series. Most have none.

        Here rather than in `metrics.py` because the kernel must not name a capability: a build
        without a package would otherwise import one that is not there, and the reporting code
        would carry a list of every capability that ever wanted a number. A module that is not
        loaded contributes no fields, and the ABSENCE of its lines is itself a reading — it says
        this agent was never granted that ability, rather than that it has had nothing to say.
        """
        return {}

    def urgency(self, subject_uri: str, observed_property: str,
                value: float | None) -> float | None:
        """How close this reading puts me to my own trouble: 0.0 (fine) to 1.0 (trouble).

        None means I have no stake in this subject and this property, and therefore no
        opinion. Perception uses it to decide how closely to watch — attention follows need,
        and need is not perception's to define.

        `value` may itself be None, and the question changes with it: not "how bad is this
        number" but "how urgent is it that I have no current number at all". Ignorance is a
        need like any other (#137) — a module with a stake in the property answers it, one
        with none stays silent, and the same max-of-answers resolves the choir either way.
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
