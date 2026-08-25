"""The agent's own liveness — noticing that it is cut off, and resigning rather than enduring.

The fault this exists for cost two days (#53): an agent's MQTT session ended and never came
back, and every surface a person would look at said the system was healthy — the container up,
the broker up, the board publishing, the log quiet. The disconnect was counted and later
logged, but a metric is watched only after something has visibly gone wrong, and nothing had.
A permanently dead session looks exactly like a quiet one, from every side but the agent's own.

**In the kernel, not a capability**, by the argument `upkeep.py` settled: every agent has one
connection whatever else it can do, and noticing you are dead is not an ability whose *how*
could differ. And on a clock of its own — a `Timer` thread, deliberately independent of paho's
network thread, because the network thread is one of the things being watched.

Three checks, ordered by how wrong things are:

- **the network thread died** — an exception escaped into paho's loop and killed it. The
  callbacks are wrapped so this should be impossible, and "should be impossible" is precisely
  what a watchdog is for: the connected flag would stay stale-true forever, so this is checked
  before the flag is believed.
- **disconnected past the bound** — paho has been retrying against something that never
  answers for longer than `ag:resignAfterS`. A flapping link never meets this: the clock is
  continuous, and one successful reconnect resets it.
- **something I expected to hear has gone silent** — each module's `quiet()`, the self-applied
  freshness check. Said out loud on entry and recovery rather than every tick, because a lamp
  that repeats itself is one you stop reading. This one only speaks; the first two act.

**Resigning is SIGTERM to self, through the same door `podman stop` uses.** The signal is
blocked and pending, `run()`'s sigwait receives it, modules stop cleanly, the writer flushes,
and the container's `restart: unless-stopped` brings the process back to a fresh socket and a
fresh TLS session — which is what actually cured the incident. An agent that cannot reach its
society is not an agent holding on; it is a process worth being reborn.

The bound lives in the ontology (`ag:Agent ag:resignAfterS`), like the compaction ratio: what a
society tolerates, not how the code is written. See knowledge/decisions/
a-dead-session-is-resigned-not-endured.md.
"""

from __future__ import annotations

import logging
import os
import signal

from .module import Timer
from .store import bindings

log = logging.getLogger("watchdog")

# How often to look. Fast enough that a resignation lands within a minute of earning it, slow
# enough to cost nothing; the quiet() sweep underneath is a dict lookup per sensor.
EVERY_S = 60

_RESIGN_Q = """
SELECT ?s WHERE {
  GRAPH ?g { ag:Agent ag:resignAfterS ?s }
} LIMIT 1"""


class BusWatchdog:
    """Notice a dead connection and resign, on a clock no other thread owns."""

    def __init__(self, agent):
        self.agent = agent
        self._timer: Timer | None = None
        self._quiet: set[str] = set()  # what has already been said, so it is said once
        rows = bindings(agent.beliefs.query(_RESIGN_Q))
        if not rows:
            raise RuntimeError("the ontology states no ag:resignAfterS — re-run orexis-seed")
        self.resign_after_s = int(rows[0]["s"])

    def start(self) -> None:
        self._timer = Timer(EVERY_S, self.check)
        self._timer.start()

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()

    def check(self) -> None:
        """One look. Never raises — the watchdog must not be a way to die."""
        try:
            if self._thread_died():
                self._resign("the network thread is dead — no callback will ever fire again, "
                             "and the connected flag can no longer be believed")
                return
            cut_off = self.agent.metrics.disconnected_for_s()
            if cut_off is not None and cut_off > self.resign_after_s:
                self._resign(f"cut off from the bus for {cut_off:.0f}s, past the "
                             f"{self.resign_after_s}s this society tolerates")
                return
            self._sweep_quiet()
        except Exception as exc:
            log.error("%s: the watchdog could not look: %s", self.agent.id, exc)

    def _thread_died(self) -> bool:
        """True only when the link's own machinery demonstrably existed and is demonstrably
        dead — `Link.alive()` False, never None. How a transport knows is its own business
        (MQTT's watches paho's loop thread); a transport that cannot say degrades this check
        to never-true and the disconnect bound still stands guard behind it.
        """
        return self.agent.link.alive() is False

    def _sweep_quiet(self) -> None:
        """Say what has gone silent, once on entry and once on recovery — never per tick."""
        heard_nothing = {line for module in self.agent.modules for line in module.quiet()}
        for line in sorted(heard_nothing - self._quiet):
            log.warning("%s: %s", self.agent.id, line)
        for line in sorted(self._quiet - heard_nothing):
            log.info("%s: heard again — was: %s", self.agent.id, line)
        self._quiet = heard_nothing

    def _resign(self, why: str) -> None:
        """Exit through the front door: SIGTERM to self, pending until sigwait takes it.

        CRITICAL, because this line is the whole story the next reader gets — the restart that
        follows looks like any restart, and `uptime_s` resetting is how it shows in the series.
        """
        log.critical("%s: RESIGNING — %s. Stopping cleanly so the container brings me back "
                     "to a fresh session.", self.agent.id, why)
        os.kill(os.getpid(), signal.SIGTERM)
