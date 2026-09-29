"""`create`: the metrics part — created only where a metrics sink is loaded (`agent.series`), since a
premise read off the environment is the only one a store has.

LINKED, it connects to every signal of every part and of the runtime (`agent.lifecycle.signals_of`)
and tallies each event its class says is reported (`window.tally`); an event reporting nothing is
passed over. It writes the window when it hears the runtime's pass end, on the first pass by which
the window has run its length, so a window holds whole passes, the pass's own event among them;
STOPPED, it writes the last, since a stop is an exit and would lose up to a window of metrics.
"""

from __future__ import annotations

from agent.lifecycle import signals_of

from . import window


class _Metrics:
    def __init__(self, runtime):
        self.runtime = runtime

    def link(self, parts) -> None:
        for signal in signals_of(self.runtime, *parts.values()):
            signal.connect(self._heard)
        self.runtime.passed.connect(self._window)          # after the pass is tallied

    @staticmethod
    def _heard(event):
        window.tally(event)
        return ()

    @staticmethod
    def _window(passed):
        if window.due():
            window.flush()
        return ()

    def stop(self) -> None:
        window.flush()


def create(runtime) -> _Metrics:
    """The metrics part: every reported event tallied, and written once a window."""
    return _Metrics(runtime)
