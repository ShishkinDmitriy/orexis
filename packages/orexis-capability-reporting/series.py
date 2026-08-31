"""The series store — InfluxDB — as the reporting capability writes to it.

Was `agent/influx_writer.py`, the kernel's. The record's SINK is reporting's business: one
credential, one writer, one clock, one write per tick — and the readings sensing records go
through the same writer, told through the choir (`record`), so one place knows Influx exists
(metrics-are-an-aspect). The measurement names are what the dashboards filter on and what
`infra/tests` asserts against; they did not move.
"""

from __future__ import annotations

from datetime import datetime

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Distinct from `soil_moisture` on purpose: the readings dashboards filter on measurement, so an
# agent's self-reporting must never appear in them. Separate measurements rather than one because
# each carries a different tag set — per-sensor figures a sensor tag, events a kind and its
# prose — and a measurement whose tag set varies row to row is one every query has to be careful
# around.
AGENT_MEASUREMENT = "agent_health"
SENSOR_MEASUREMENT = "agent_sensor_health"
EVENT_MEASUREMENT = "agent_events"


class SeriesWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket

    def write_reading(self, value: float, at: datetime | None = None, **tags: str) -> None:
        """One reading, with whatever TAGS the caller says it is about.

        The tags are the caller's — sensing's: `plant`, `sensor` and `property`, each a term's
        LOCAL name, because a tag is what a person filters a dashboard on. Which property a
        number is of is not optional and not derivable from the number (a board reporting soil
        moisture and air humidity sends two fractions in the same 0-1 range), and sensing
        fills it; the kernel's writer names no property of its own — this is a series surface
        (the-stake-is-sensings-want). The measurement name is unchanged, because it is what the
        readings dashboards filter on and what `infra/tests` asserts against.

        `at` is the caller's instant, and stating it matters more than it looks. Left unset, a
        point is stamped by InfluxDB on RECEIPT, so two values out of one message landed at two
        times and a third time appeared in the belief base — three clocks for one measurement.
        Passing it also means the series agrees with the reading's own result time, which is
        what makes a dashboard and a query about the same reading comparable at all.
        """
        point = Point("soil_moisture").field("value", float(value))
        for name, tag in tags.items():
            point = point.tag(name, tag)
        if at is not None:
            point.time(at)
        self.write_api.write(bucket=self.bucket, record=point)

    def write_agent_health(self, agent_id: str, fields: dict, belief_bytes=None,
                           tagged=None) -> None:
        """One health point per tick, and beside it every TAGGED row the modules contributed.

        `fields` is the merged answer to the choir's `reports()` — the kernel's own figures
        and every module's, one dict — and `tagged` the concatenated answer to `series()`:
        `(measurement, tags, fields)` rows, a property or a sensor as a TAG so one generic
        panel groups by it (metrics-are-an-aspect). Per-sensor health used to be a parameter of
        its own; it is sensing's `series()` rows now, because which sensors an agent has is
        sensing's to say.
        """
        agent_point = Point(AGENT_MEASUREMENT).tag("agent", agent_id)
        for name, value in fields.items():
            agent_point.field(name, value)
        if belief_bytes is not None:
            agent_point.field("belief_bytes", int(belief_bytes))
        points = [agent_point]
        for measurement, tags, row_fields in (tagged or []):
            p = Point(measurement).tag("agent", agent_id)
            for name, value in tags.items():
                p.tag(name, str(value))
            for name, value in row_fields.items():
                p.field(name, value)
            points.append(p)
        self.write_api.write(bucket=self.bucket, record=points)

    def write_events(self, agent_id: str, events: list[tuple]) -> None:
        """The story beside the figures (#125): transitions with their prose, as annotations.

        Each point is stamped with the instant the transition HAPPENED, never the write: events
        are drained on the reporter's tick, and a marker drawn at the tick would put the knee of
        a curve in the wrong place. `kind` and the other tags are what an annotation query
        filters and captions on; `text` is a string field holding prose for humans, under the
        same never-parse contract as `orexis:becauseOf`, whose projection it is.
        """
        points = []
        for at, kind, text, tags in events:
            p = Point(EVENT_MEASUREMENT).tag("agent", agent_id).tag("kind", kind)
            for name, value in tags.items():
                p.tag(name, str(value))
            points.append(p.field("text", str(text)).time(at))
        if points:
            self.write_api.write(bucket=self.bucket, record=points)

    def close(self) -> None:
        self.client.close()
