"""InfluxDB = the series (the record). Every raw reading lands here."""

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


class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket

    def write_reading(self, plant_id: str, sensor: str, value: float,
                      observed_property: str,  # a term's LOCAL name, from the caller
                      at: datetime | None = None) -> None:
        """One reading, tagged with WHICH property it is.

        The property is not optional and not derivable from the number. A board reporting soil
        moisture and air humidity sends two fractions in the same 0-1 range, and nothing in
        either says which it is — so writing both into one measurement tagged only by plant and
        sensor put an air temperature of 21.4 into a series called `soil_moisture`, where every
        dashboard and every later query would read it as one.

        A tag is what a person filters a dashboard on, so it carries the term's LOCAL
        name rather than its IRI — shortened by the caller, which is where that helper lives.

        The measurement name is unchanged, because it is what the readings dashboards already
        filter on and what `infra/tests` asserts against. The tag is what separates them, and a
        query that does not filter on it now gets a series it can at least SEE is mixed.

        `at` is the caller's instant, and stating it matters more than it looks. Left unset, a
        point is stamped by InfluxDB on RECEIPT, so two values out of one message landed at two
        times and a third time appeared in the belief base — three clocks for one measurement.
        Passing it also means the series agrees with `sosa:resultTime`, which is what makes a
        dashboard and a query about the same reading comparable at all.
        """
        point = (
            Point("soil_moisture")
            .tag("plant", plant_id)
            .tag("sensor", sensor)
            .tag("property", observed_property)
            .field("value", float(value))
        )
        if at is not None:
            point.time(at)
        self.write_api.write(bucket=self.bucket, record=point)

    def write_agent_health(self, agent_id: str, fields: dict,
                           per_sensor: dict, belief_bytes: int | None = None) -> None:
        """One round of an agent's account of itself — see agent/metrics.py.

        Written in one call so a round is one round: a partial write would show as a moment when
        an agent had an uptime but no belief base.
        """
        agent_point = Point(AGENT_MEASUREMENT).tag("agent", agent_id)
        for name, value in fields.items():
            agent_point.field(name, value)
        if belief_bytes is not None:
            agent_point.field("belief_bytes", int(belief_bytes))

        points = [agent_point]
        for sensor, (total, age_s, acked_s) in per_sensor.items():
            p = Point(SENSOR_MEASUREMENT).tag("agent", agent_id).tag("sensor", sensor)
            p.field("readings_total", int(total))
            # Omitted until the sensor has delivered once. A missing field is a gap in the
            # series; a zero would be a claim that a reading had just arrived.
            if age_s is not None:
                p.field("reading_age_s", round(float(age_s), 1))
            # The board's own account of its rhythm (#135). Beside the commanded cadence this
            # is the #37 detector in series form: the two diverging IS the cleared or clamped
            # command, visible instead of silent. Absent for old firmware, which stays legal.
            if acked_s is not None:
                p.field("cadence_acked_s", int(acked_s))
            points.append(p)
        self.write_api.write(bucket=self.bucket, record=points)

    def write_events(self, agent_id: str, events: list[tuple]) -> None:
        """The story beside the figures (#125): transitions with their prose, as annotations.

        Each point is stamped with the instant the transition HAPPENED, never the write: events
        are drained on the reporter's tick, and a marker drawn at the tick would put the knee of
        a curve in the wrong place. `kind` and the other tags are what an annotation query
        filters and captions on; `text` is a string field holding prose for humans, under the
        same never-parse contract as `intention:becauseOf`, whose projection it is.
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
