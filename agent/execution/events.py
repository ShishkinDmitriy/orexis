"""What the executor says happened — every event its signals carry, what of each is reported, and
which are history.

An event is said whole, so a handler asks nobody: planning plans again on `IntentionResolved` and
checks a head on `Taking`, a transport sends a `Commanded`, speech believes and tells a `Said`. The metrics part tallies what a
class marks (`agent.metrics`), and the history part writes what an event answers as its `point()`
(`agent.history`); an event only they hear is made only where its signal is heard, so nothing is read
for it where no series store is loaded.

A STEP IS HISTORY TWICE, each an event in the journal (`agent/journal.py`) in execution's words: `execution:StepTaken`
when the executor records the `execution:Act`, `execution:taken` true, or false where the taker raised, at the act's
`execution:takenAt`; and `execution:StepAnswered` at the landing verdict, `execution:landed` true where the present came
to hold what the step predicted, false where the patience ran out on it or the want it was kept below as ended undone
— and then an `execution:StepFailed` too, a class beneath `orexis:Incident`, which keeps the minutes of log before it. A step that predicts nothing moves on as it
is taken and has no verdict, so its taking is the whole of it; so has a step not taken. AN INTENTION ENDED is history
too, `execution:IntentionResolved` with its `execution:outcome`, and an `execution:IntentionFailed`, an incident,
where it failed.

A step's event names the act recorded of it (`execution:act`), an intention's ended the intention
(`execution:intention`), and each carries what the agent holds of them as it stands — the act's triples, the step's
own as its plan states them, the action it fills and every value it takes in the domain's words, and the intention's,
the want it pursues and how it ended — so the journal is read without the beliefs.
Nothing here spells a domain word: the triples are copied, not named. On the metrics, a want's name is on no point —
the desire it was derived under is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.journal import literal
from agent.metrics import Flag, Level, Tag, Value

from .ontology import EXECUTION

_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_ACT, _INTENTION = ox.NamedNode(EXECUTION + "act"), ox.NamedNode(EXECUTION + "intention")


@dataclass(frozen=True)
class IntentionResolved:
    """An intention ended: the want it pursued and how — done, reached, failed, superseded,
    abandoned — by the desire the want was derived under."""
    metric = "intention"
    intention: str
    want: str | None
    outcome: Tag
    desire: Tag = None
    at: datetime | None = None
    said: tuple = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the intention as it ended, the want it pursued and how — an `execution:IntentionFailed`
        too where it failed."""
        out = [ox.Triple(node, _TYPE, ox.NamedNode(EXECUTION + "IntentionResolved")),
               ox.Triple(node, _INTENTION, ox.NamedNode(self.intention)), *self.said]
        if self.outcome == "failed":
            out.append(ox.Triple(node, _TYPE, ox.NamedNode(EXECUTION + "IntentionFailed")))
        return out


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
    action: Tag = None
    desire: Tag = None
    taken: Flag = True
    act: str | None = None
    said: tuple = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the act recorded — taken, or not — with what the agent holds of its step and intention."""
        return [ox.Triple(node, _TYPE, ox.NamedNode(EXECUTION + "StepTaken")), *_about(node, self)]


@dataclass(frozen=True)
class StepAnswered:
    """The verdict on a taken step at `at`: landed or not, how late the world answered it in the
    agent's seconds — the instant it was seen to, less the `landsAt` the plan placed — and whether
    the patience ran out on it."""
    metric = "landing"
    step: str
    at: datetime
    want: str | None = None
    action: Tag = None
    desire: Tag = None
    landed: Flag = False
    late_s: Value = None
    timed_out: Flag = False
    act: str | None = None
    said: tuple = ()

    def statements(self, node: ox.NamedNode) -> list[ox.Triple]:
        """In the journal: the verdict on the act, with what the agent holds of it — an `execution:StepFailed` too
        where it did not land."""
        out = [ox.Triple(node, _TYPE, ox.NamedNode(EXECUTION + "StepAnswered")),
               ox.Triple(node, ox.NamedNode(EXECUTION + "landed"), literal(bool(self.landed))), *_about(node, self)]
        if not self.landed:
            out.append(ox.Triple(node, _TYPE, ox.NamedNode(EXECUTION + "StepFailed")))
        return out


@dataclass(frozen=True)
class Walked:
    """How many intentions stand after a walk."""
    metric = "intentions"
    standing: Level = None


def _about(node: ox.NamedNode, event) -> list[ox.Triple]:
    return ([ox.Triple(node, _ACT, ox.NamedNode(event.act))] if event.act else []) + list(event.said)
