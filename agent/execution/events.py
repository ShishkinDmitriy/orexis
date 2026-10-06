"""What the executor says happened — every event its signals carry, what of each is reported, and
which are history.

An event is said whole, so a handler asks nobody: planning plans again on `IntentionResolved` and
checks a head on `Taking`, a transport sends a `Commanded`, speech believes and tells a `Said`. The metrics part tallies what a
class marks (`agent.metrics`), and the history part writes what an event answers as its `point()`
(`agent.history`); an event only they hear is made only where its signal is heard, so nothing is read
for it where no series store is loaded.

A STEP IS HISTORY TWICE, both points measured `Step` — execution's word for what they are about:
TAKEN, when the executor records the `execution:Act`, field `taken`, true, or false where the taker
raised, at the act's `execution:takenAt`; and ANSWERED at the landing verdict, field `landed`, true
where the present came to hold what the step predicted, false where the patience ran out on it or the
want it was kept below as ended undone, at the instant the verdict was reached. A step that predicts
nothing moves on as it is taken and has no verdict, so its taken point is the whole of it; so has a
step not taken, whose `taken` is false.

Each is tagged `action` — the local name of the action the step fills — `want`, the local name of
the want its intention pursues, and one tag per parameter the action takes, keyed by the parameter's
local name, which is the predicate the step is written under (an-action-takes-parameters): an IRI's
local name, a literal's text. Every one of those names is read off the step and its action, so this
module spells no domain word; a parameter named `action` or `want` is shadowed by execution's own
tag. On the metrics, a want's name is on no point — the desire it was derived under is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent.metrics import Flag, Level, Tag, Value
from agent.ontology import local_of

from .ontology import EXECUTION

MEASUREMENT = local_of(EXECUTION + "Step")


@dataclass(frozen=True)
class IntentionResolved:
    """An intention ended: the want it pursued and how — done, reached, failed, superseded,
    abandoned — by the desire the want was derived under."""
    metric = "intention"
    intention: str
    want: str | None
    outcome: Tag
    desire: Tag = None


@dataclass(frozen=True)
class Commanded:
    """A step's command, sized from the present when it was taken, for whatever reaches the device."""
    actuator: str
    payload: object


@dataclass(frozen=True)
class Said:
    """A document a step said, and the agents it is to."""
    document: object
    to: tuple


@dataclass(frozen=True)
class Taking:
    """A head about to be handed to its taker at `at`, said before it is: whoever judges whether the
    present still admits it says so now, and the executor takes no step whose intention that ended."""
    step: str
    at: datetime


@dataclass(frozen=True)
class StepTaken:
    """A step taken — or not, where its taker raised — at `at`, recorded as an act."""
    metric = "act"
    step: str
    at: datetime
    want: str | None = None
    parameters: tuple = ()
    action: Tag = None
    desire: Tag = None
    taken: Flag = True

    def point(self) -> dict:
        return _point(self, {"taken": self.taken})


@dataclass(frozen=True)
class StepAnswered:
    """The verdict on a taken step at `at`: landed or not, how late the world answered it in the
    agent's seconds — the instant it was seen to, less the `landsAt` the plan placed — and whether
    the patience ran out on it."""
    metric = "landing"
    step: str
    at: datetime
    want: str | None = None
    parameters: tuple = ()
    action: Tag = None
    desire: Tag = None
    landed: Flag = False
    late_s: Value = None
    timed_out: Flag = False

    def point(self) -> dict:
        return _point(self, {"landed": self.landed})


@dataclass(frozen=True)
class Walked:
    """How many intentions stand after a walk."""
    metric = "intentions"
    standing: Level = None


def _point(event, fields: dict) -> dict:
    tags = dict(event.parameters)
    if event.action:
        tags["action"] = event.action
    if event.want:
        tags["want"] = local_of(event.want)
    return {"measurement": MEASUREMENT, "tags": tags, "fields": fields, "time": event.at}
