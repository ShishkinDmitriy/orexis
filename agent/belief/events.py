"""What the deliberator says happened — the events its signals carry, and what of each is reported.

`Revised` is heard by the executor, which walks, since what it waits on is the present; the metrics
part tallies what a class marks (`agent.metrics`). `RevisionsHeld` only metrics hears, so it is made
only where heard.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.metrics import Level, Value


@dataclass(frozen=True)
class Revised:
    """A revision pass: the sources it revised or transitioned on, how many it was handed, the rule
    executions it spent on both, how many it left cut short for the next pass, and its real seconds."""
    metric = "revise"
    graphs: tuple
    sources: Value = None
    executions: Value = None
    cut: Value = None
    duration_s: Value = None


@dataclass(frozen=True)
class RevisionsHeld:
    """The revisions the belief base's catalogue describes, and how many a budget cut short — settled
    false, which the next pass continues. A revision unsettled window after window is a rule set that
    never settles."""
    metric = "revisions"
    revisions: Level = None
    unsettled: Level = None
