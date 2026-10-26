"""`create`: the history part — created where a history sink is loaded (`agent.series`) or a journal is kept
(`agent.journal`).

LINKED, it connects to every signal of every part and of the runtime, and writes what each event it hears answers,
one event at a time as they happen: the point it answers (`point()`), to its agent's history sink — an observation,
which the series store draws — and the triples it states (`statements(node)`), to its agent's journal, as an entry
named by a node minted for it — a plan published, a step taken and answered, what coordination held and concluded. An
event answering neither is passed over. A store that refuses is said in the log and costs the agent nothing.
"""

from __future__ import annotations

import logging

from agent.journal import journal, mint
from agent.lifecycle import signals_of
from agent.series import HISTORY, sink

log = logging.getLogger("history")


class _History:
    def __init__(self, runtime):
        self.runtime = runtime

    def link(self, parts) -> None:
        for signal in signals_of(self.runtime, *parts.values()):
            signal.connect(self._heard)

    def _heard(self, event):
        said = getattr(event, "point", None)
        if callable(said) and (to := sink(HISTORY, self.runtime.id)) is not None and (point := said()):
            to.write(point if isinstance(point, list) else [point])
        stated = getattr(event, "statements", None)
        if callable(stated) and (kept := journal(self.runtime.id)) is not None:
            node = mint()
            try:
                kept.record(node, stated(node), getattr(event, "at", None))
            except Exception as exc:                                       # noqa: BLE001
                log.warning("the journal refused %s: %s", type(event).__name__, exc)
        return ()


def create(runtime) -> _History:
    """The history part: every event that is a point or triples, written as it is heard."""
    return _History(runtime)
