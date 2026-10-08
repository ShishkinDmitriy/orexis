"""What the runtime and a package share about a package's life: how a package speaks — a `Signal`
it owns — and how a run ends.

A PACKAGE HAS A PART, AND A PART HAS A LIFE IN THREE PHASES (a-package-starts-itself). The runtime
calls `create(runtime)` of every package the agent loads that has a `create` module, keeping each
PART it answers by package; when all exist, `link(parts)` on each, so a part connects what it
needs of the others — every reference pointing down the stack, as an import does; then
`start(runtime)` on each, and `stop()`, the last first, when the run ends. A part that has nothing
to link or to stop simply has no such method.

A SIGNAL IS A PACKAGE'S OWN WORD FOR WHAT JUST HAPPENED — the Planner's `plan_published`, the
executor's `intention_resolved`, the deliberator's `revised` — and it lives on the package's own
object, so the kernel names none of them. What it carries is ONE EVENT, an instance of a class the
package declares beside it (`agent/<package>/events.py`): what happened, said whole, so a handler
needs to ask nobody. Emitting one calls every handler at once, on the one thread, and answers the
graphs they wrote, for the emitter to say it wrote them. An emitter whose event costs something to
make asks `connected` first, and makes nothing where nobody hears. A signal is not stored: what it
points at is, and a handler reads it there, so a restart loses nothing.

WHOEVER HEARS EVERY SIGNAL finds them on the parts (`signals_of`): metrics tallies each event its
class says is reported, and history writes each event that says it is a point, so neither knows any
package's words and no package imports either (`agent/metrics/`, `agent/history/`).
"""

from __future__ import annotations

#  HOW A RUN ENDS, said by whoever lets go of the agent last (`runtime.release`), where no desire
#  holds it — or the runtime's own, `unfinished`, when its passes run out. Planning says the rest:
#  - `met`: every want is reached, and none is walked;
#  - `planned`: every want standing has a plan published, and no part the agent runs will walk one —
#    an agent that is a planner and no executor (#928), whose plan is what it was declared for;
#  - `unreachable`: a want stands that nothing this agent holds reaches.
MET, PLANNED, UNREACHABLE, UNFINISHED = "met", "planned", "unreachable", "unfinished"


class Signal:
    """One thing a package says happened, for whoever connects to hear it: an event, emitted whole."""

    def __init__(self, name: str):
        self.name = name
        self._handlers: list = []

    def connect(self, handler) -> None:
        """Call `handler(event)` — answering the graphs it wrote, or nothing — whenever this is emitted."""
        self._handlers.append(handler)

    @property
    def connected(self) -> bool:
        """Whether anything hears this."""
        return bool(self._handlers)

    def emit(self, event) -> list[str]:
        """Call every handler with `event` at once; the graphs they wrote."""
        return [graph for handler in list(self._handlers) for graph in handler(event) or ()]

    def __repr__(self) -> str:
        return f"Signal({self.name}, {len(self._handlers)} connected)"


def signals_of(*holders) -> list[Signal]:
    """Every signal the `holders` own — each one's own attributes, and those of the objects it holds
    one step down, since a part holds its package's object and the object owns the signals — once
    each, in the order found."""
    found: dict[int, Signal] = {}
    for holder in holders:
        for value in _attributes(holder):
            for candidate in (value, *_attributes(value)):
                if isinstance(candidate, Signal):
                    found.setdefault(id(candidate), candidate)
    return list(found.values())


def _attributes(obj) -> list:
    return list(vars(obj).values()) if hasattr(obj, "__dict__") and not isinstance(obj, type) else []
