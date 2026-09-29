"""`create`: the history part — created only where a history sink is loaded (`agent.series`).

LINKED, it connects to every signal of every part and of the runtime, and writes the point each
event it hears answers (`point()`), one at a time as they happen; an event with no `point` is
passed over. A store that refuses a point is said in the log and costs the agent nothing.
"""

from __future__ import annotations

from agent.lifecycle import signals_of
from agent.series import HISTORY, sink


class _History:
    def __init__(self, runtime):
        self.runtime = runtime

    def link(self, parts) -> None:
        for signal in signals_of(self.runtime, *parts.values()):
            signal.connect(self._heard)

    @staticmethod
    def _heard(event):
        said = getattr(event, "point", None)
        if callable(said) and (point := said()) is not None and (to := sink(HISTORY)) is not None:
            to.write([point])
        return ()


def create(runtime) -> _History:
    """The history part: every event that is a point, written as it is heard."""
    return _History(runtime)
