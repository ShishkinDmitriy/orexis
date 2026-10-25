"""`create`: the history part — created only where a history sink is loaded (`agent.series`).

LINKED, it connects to every signal of every part and of the runtime, and writes the point each
event it hears answers (`point()`) — or the points, where one event is several, a plan published
being a point per step — one event at a time as they happen, to its agent's sink; an event with no
`point` is passed over. A store that refuses a point is said in the log and costs the agent nothing.
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

    def _heard(self, event):
        said = getattr(event, "point", None)
        if callable(said) and (point := said()) and (to := sink(HISTORY, self.runtime.id)) is not None:
            to.write(point if isinstance(point, list) else [point])
        return ()


def create(runtime) -> _History:
    """The history part: every event that is a point, written as it is heard."""
    return _History(runtime)
