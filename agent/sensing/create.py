"""`create`: sensing's part, and what it does of its own accord once started (a-package-starts-itself) —
it asks, every `EVERY_S` of the one timeline, which readings have fallen due and says which
sensors have gone silent (`missed`), whether or not anything arrived (#843); and it reports its
gauge. What a transport hands it, `received` writes; nothing else here is called.
"""

from __future__ import annotations

from . import metrics
from .missed import missed

#  HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
EVERY_S = 60.0


class _Sensing:
    def start(self, runtime) -> None:
        def ask():
            missed(runtime.beliefs, runtime.me, runtime.now)
            return []
        runtime.every(EVERY_S, ask)
        runtime.gauge(lambda: metrics.gauges(runtime.beliefs))


def create(runtime) -> _Sensing:
    """Sensing's part: once started, it asks after what has fallen due every `EVERY_S` and reports its gauge."""
    return _Sensing()
