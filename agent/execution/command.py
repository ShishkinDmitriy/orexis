"""`command`: what taking a step sends, sized from the present.

An action a device takes carries `execution:command`, a SELECT over the beliefs as they stand when
the step is taken, with the step's parameters as `$tokens`, `$me` and `$now`, answering `?actuator` and
`?payload`. The search never sizes an act — a dose's effect is the side it reaches, not litres —
so how much to pour, or how long to heat, is decided here, from the reading in hand, by the text
the domain declares. The answer is what the container hands the transport; execution names no
transport, and a step whose action carries no command sends nothing.
"""

from __future__ import annotations

import json
import logging

from agent import clock
from agent.ontology import ACTION, KNOWN
from agent.store import bind, graphs_of, instant, rows

log = logging.getLogger("command")

_COMMAND_Q = """
SELECT ?text (GROUP_CONCAT(STR(?takes); separator=" ") AS ?params) WHERE {
  $action execution:command ?text . OPTIONAL { $action orexis:takes ?takes } } GROUP BY ?text"""


def command(store, said: dict, me: str) -> list[tuple[str, dict]]:
    """Every `(actuator, payload)` the step `said` sends — the executor's rows for it, keyed by
    local part as `Executor.step_of` answers them — asked over the beliefs holding now. Empty
    where the action carries no command or its text answers nothing; a payload that is no JSON
    is refused in the log."""
    action = said.get("fills")
    if not action:
        return []
    found = rows(store, _COMMAND_Q, graphs_of(store, ACTION), action=action)
    if not found:
        return []
    now = clock.now()
    tokens = {"me": me, "now": instant(now)}
    for param in (found[0].get("params") or "").split():
        local = param.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        if local in said:
            tokens[local] = said[local]
    out = []
    for row in rows(store, bind(found[0]["text"], **tokens), graphs_of(store, *KNOWN, at=now, now=now)):
        try:
            out.append((row["actuator"], json.loads(row["payload"])))
        except (KeyError, ValueError) as exc:
            log.error("%s: its command answered no actuator and payload: %s", action.rsplit("#", 1)[-1], exc)
    return out
