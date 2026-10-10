"""`command`: what taking a step sends, sized from the present.

An action a device takes has an `execution:Command` among its operations, an `sh:select` over the
beliefs as they stand when the step is taken, with the step's parameters as `$tokens` and `$now`,
asking the self (`?me a orexis:Self`) where it means the agent, answering `?actuator` and `?payload`. The search never sizes an act — a dose's effect is the side it reaches, not litres —
so how much to pour, or how long to heat, is decided here, from the reading in hand, by the text
the domain declares. THE READING IN HAND IS AN OBSERVATION, which is no belief, and this package is
handed none and names none: a command sizing a step as it is taken is one of the readers at the
boundary, and its TEXT names the kind its observation is kept in, sensing's, in its own `GRAPH`
clauses joined with the catalogue, and the one holding at `$now` — a sensor's latest, since each ends
where the next begins (#944). The text is handed the beliefs as its default graph as every operation
is, and a `GRAPH` clause reaches past them. The answer is what the container hands the transport;
execution names no transport, and a step whose action carries no command sends nothing.
"""

from __future__ import annotations

import json
import logging

from agent import clock
from agent.ontology import ACTION, KNOWN
from agent.store import bind, graphs_of, instant, rows

from .implementation import COMMAND, operations

log = logging.getLogger("command")

_TAKES_Q = """SELECT ?takes WHERE { $action orexis:takes ?takes }"""


def command(store, said: dict, *, order: float | None = None) -> list[tuple[str, dict]]:
    """Every `(actuator, payload)` the step `said` sends — the executor's rows for it, keyed by
    local part as `Executor.step_of` answers them — asked over the beliefs holding now: every
    command of the action's implementation, or those of one `order`. Empty where it has none or
    its texts answer nothing; a payload that is no JSON is refused in the log."""
    action = said.get("fills")
    if not action:
        return []
    texts = [op.text for op in operations(store, action)
             if op.kind == COMMAND and op.text and (order is None or op.order == order)]
    if not texts:
        return []
    now = clock.now()
    tokens = {"now": instant(now)}
    for r in rows(store, _TAKES_Q, graphs_of(store, ACTION), action=action):
        local = r["takes"].rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        if local in said:
            tokens[local] = said[local]
    out = []
    for text in texts:
        for row in rows(store, bind(text, **tokens), graphs_of(store, *KNOWN, at=now, now=now)):
            try:
                out.append((row["actuator"], json.loads(row["payload"])))
            except (KeyError, ValueError) as exc:
                log.error("%s: its command answered no actuator and payload: %s", action.rsplit("#", 1)[-1], exc)
    return out
