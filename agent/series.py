"""The series sink: points a package contributes, written to the store the agent is told of for
their purpose — and nothing about what the points are.

A SERIES IS WATCHED AND NEVER BELIEVED (knowledge/domain/kernel/series.md). What a person draws
of an agent lives in InfluxDB, in a bucket of the agent's own; nothing written there reaches a
plan. It has two purposes — HISTORY, what happened, and METRICS, how the agent is doing — and the
agent is told of a store for each apart, in environment keyed by the purpose:
`INFLUX_HISTORY_URL`, `INFLUX_HISTORY_ORG`, `INFLUX_HISTORY_BUCKET`, `INFLUX_HISTORY_TOKEN`, and
the same four under `INFLUX_METRICS_`. Two purposes may name one instance, by coincidence and not
by design; they name two buckets of it, one a record kept for good and the other the admins' figures.

A SINK IS LOADED WHERE THE ENVIRONMENT NAMES A STORE FOR ITS PURPOSE. `load` is the premise, read
off the environment rather than the world because a store is deployment; the runtime's `main`
calls it once. A purpose the environment does not name has no sink, and the client library is
imported where a sink is made and nowhere else, so an agent with no store never loads it.

THE PACKAGE THAT DECIDES A THING SHAPES IT, AND A PART WRITES IT
(metrics-and-history-are-what-events-say). Sensing says an observation and execution a step taken
and a landing verdict, each as an event answering its point — its measurement, its tags, its fields,
its instant — and the history part (`agent/history/`), hearing every signal, writes each to
`sink(HISTORY)`. The metrics part (`agent/metrics/`) tallies every reported event and writes the
window once a minute to `sink(METRICS)`. The runtime creates each only where its sink is loaded.
This module sits beneath them all and imports nothing of theirs, nor anything of `agent`: a point
is the client's own dict, handed through.

WHY A SINK IS FOUND HERE AND NOT HANDED DOWN. The two parts that write are created by the runtime
like any package's, so a sink handed down would be the runtime choosing, once more, who writes it;
the shape this has is logging's: whoever writes asks once where it goes, and whoever runs the
process decided that when it loaded the sinks.

A STORE THAT REFUSES a point is said in the log and costs the agent nothing.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("series")

HISTORY = "HISTORY"
METRICS = "METRICS"
PURPOSES = (HISTORY, METRICS)

#  WHAT NAMES A STORE FOR A PURPOSE: all four, under `INFLUX_<PURPOSE>_`.
_KEYS = ("URL", "ORG", "BUCKET", "TOKEN")

_sinks: dict[str, "Sink"] = {}


class Sink:
    """One purpose's bucket, and how a point reaches it: `write(bucket, record)`, the client's own
    call, handed the points as they were contributed."""

    def __init__(self, purpose: str, bucket: str, write):
        self.purpose, self.bucket, self._write = purpose, bucket, write

    @classmethod
    def from_environment(cls, purpose: str, environ=None) -> "Sink | None":
        """The store the environment names for `purpose`, or None where it names none. Where it
        names some of the four and not all, None too, said in the log: a store half-named is a
        deployment mistake, and a series is not worth an agent that will not start."""
        env = os.environ if environ is None else environ
        named = {key: env.get(f"INFLUX_{purpose}_{key}") for key in _KEYS}
        if not any(named.values()):
            return None
        if missing := [f"INFLUX_{purpose}_{key}" for key, value in named.items() if not value]:
            log.warning("a %s store is named without %s — nothing is written for it", purpose.lower(), ", ".join(missing))
            return None
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS

        client = InfluxDBClient(url=named["URL"], token=named["TOKEN"], org=named["ORG"])
        return cls(purpose, named["BUCKET"], client.write_api(write_options=SYNCHRONOUS).write)

    def write(self, points: list[dict]) -> int:
        """Write `points`; how many. A store that refuses is said in the log, never raised."""
        if not points:
            return 0
        try:
            self._write(bucket=self.bucket, record=points)
        except Exception as exc:                                   # noqa: BLE001
            log.warning("the %s store refused %d point(s): %s", self.purpose.lower(), len(points), exc)
            return 0
        return len(points)


def load(environ=None) -> tuple[str, ...]:
    """A sink for every purpose the environment names a store for; the purposes loaded."""
    for purpose in PURPOSES:
        install(purpose, Sink.from_environment(purpose, environ))
    return tuple(purpose for purpose in PURPOSES if purpose in _sinks)


def install(purpose: str, sink: "Sink | None") -> None:
    """Make `sink` the one points of `purpose` go to — or none, where `sink` is None."""
    if sink is None:
        _sinks.pop(purpose, None)
    else:
        _sinks[purpose] = sink


def sink(purpose: str) -> "Sink | None":
    """The sink points of `purpose` go to, or None where none is loaded — and then a contributor
    builds no point at all."""
    return _sinks.get(purpose)
