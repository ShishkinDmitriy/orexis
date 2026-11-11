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
its instant — and the history part (`orexis-history/`), hearing every signal, writes each to
`sink(HISTORY)`. The metrics part (`orexis-metrics/`) tallies every reported event and writes the
window once a minute to `sink(METRICS)`. The runtime creates each only where its sink is loaded.
This module sits beneath them all and imports nothing of theirs, nor anything of `agent`: a point
is the client's own dict, handed through.

WHY A SINK IS FOUND HERE AND NOT HANDED DOWN. The two parts that write are created by the runtime
like any package's, so a sink handed down would be the runtime choosing, once more, who writes it;
the shape this has is logging's: whoever writes asks once where it goes, and whoever runs the
process decided that when it loaded the sinks.

A SINK MAY BE INSTALLED FOR ONE AGENT, where a process runs several — a world's test walking two
couriers in one interpreter, recording each apart (`orexis-history`). A deployed agent is one per
process, its bucket its own, so a point names no agent; whoever writes asks for its agent's sink, and
is answered the process's where none is installed for it.

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

#  EVERY SINK, by purpose and the agent it is for — None for every agent the process runs, as a
#  deployed one runs one.
_sinks: dict[tuple[str, str | None], "Sink"] = {}


class Sink:
    """One purpose's bucket, and how a point reaches it: `write(bucket, record)`, the client's own
    call, handed the points as they were contributed."""

    def __init__(self, purpose: str, bucket: str, write, read=None):
        self.purpose, self.bucket, self._write, self._read = purpose, bucket, write, read


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








