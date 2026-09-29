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
object, so the kernel names none of them. Emitting one calls every handler at once, on the one
thread, and answers the graphs they wrote, for the emitter to say it wrote them. A signal is not
stored: what it points at is, and a handler reads it there, so a restart loses nothing.
"""

from __future__ import annotations

#  HOW A RUN ENDS, said by whoever lets go of the agent last (`runtime.release`) — planning, when
#  every want is reached and no desire holds it, or when a want stands that nothing reaches — or
#  the runtime's own, when its passes run out.
MET, UNREACHABLE, UNFINISHED = "met", "unreachable", "unfinished"


class Signal:
    """One thing a package says happened, for whoever connects to hear it."""

    def __init__(self, name: str):
        self.name = name
        self._handlers: list = []

    def connect(self, handler) -> None:
        """Call `handler(**what)` — answering the graphs it wrote, or nothing — whenever this is emitted."""
        self._handlers.append(handler)

    @property
    def connected(self) -> bool:
        """Whether anything hears this."""
        return bool(self._handlers)

    def emit(self, **what) -> list[str]:
        """Call every handler at once; the graphs they wrote."""
        return [graph for handler in list(self._handlers) for graph in handler(**what) or ()]

    def __repr__(self) -> str:
        return f"Signal({self.name}, {len(self._handlers)} connected)"
