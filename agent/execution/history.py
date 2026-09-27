"""What execution contributes to history: a step taken, and how it ended.

Two points per step held to the world, both measured `Step` — execution's word for what they are
about — and contributed by the executor as it decides each (a-documents-kind-says-who-reads-it,
§5):

- **TAKEN**, when `drain` records the `execution:Act`: field `taken`, true, or false where the
  taker raised, at the act's `execution:takenAt`;
- **LANDED OR FAILED**, at the landing verdict: field `landed`, true where the present came to hold
  what the step predicted, false where the patience ran out on it or the want it was kept below as
  ended undone, at the instant the verdict was reached.

A step that predicts nothing moves on as it is taken and has no verdict, so its taken point is the
whole of it; so has a step not taken, whose `taken` is false.

Each is tagged `action` — the local name of the action the step fills — `want`, the local name of
the want its intention pursues, and one tag per parameter the action takes, keyed by the
parameter's local name, which is the predicate the step is written under
(an-action-takes-parameters): an IRI's local name, a literal's text. Every one of those names is
read off the step and its action, so this module spells no domain word; a parameter named
`action` or `want` is shadowed by execution's own tag.
"""

from __future__ import annotations

from datetime import datetime

from agent.ontology import ACTION, local_of
from agent.store import graphs_of, rows

from .ontology import EXECUTION

MEASUREMENT = local_of(EXECUTION + "Step")

_TAKES_Q = """SELECT ?takes WHERE { $action orexis:takes ?takes }"""


def step_point(store, said: dict, want: str | None, at: datetime, fields: dict) -> dict:
    """The point a step is written as: `said` its rows as `Executor.step_of` answers them, `want`
    what its intention pursues, `fields` what happened to it at `at`. An action or a want not
    known is not tagged."""
    action = said.get("fills")
    tags = {}
    if action:
        for r in rows(store, _TAKES_Q, graphs_of(store, ACTION), action=action):
            parameter = local_of(r["takes"])
            if parameter in said:
                value = said[parameter]
                tags[parameter] = local_of(value) if "://" in value else value
        tags["action"] = local_of(action)
    if want:
        tags["want"] = local_of(want)
    return {"measurement": MEASUREMENT, "tags": tags, "fields": dict(fields), "time": at}
