"""InfluxDB = the series (the record). Every raw reading lands here."""

from __future__ import annotations

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Distinct from `soil_moisture` on purpose: the readings dashboards filter on measurement, so an
# agent's self-reporting must never appear in them. Two measurements rather than one because the
# per-sensor figures carry a sensor tag and the agent-level ones do not, and a measurement whose
# tag set varies row to row is one every query has to be careful around.
AGENT_MEASUREMENT = "agent_health"
SENSOR_MEASUREMENT = "agent_sensor_health"


class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket

    def write_reading(self, plant_id: str, sensor: str, value: float,
                      observed_property: str) -> None:  # a term's LOCAL name, from the caller
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
        """
        point = (
            Point("soil_moisture")
            .tag("plant", plant_id)
            .tag("sensor", sensor)
            .tag("property", observed_property)
            .field("value", float(value))
        )
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
        for sensor, (total, age_s) in per_sensor.items():
            p = Point(SENSOR_MEASUREMENT).tag("agent", agent_id).tag("sensor", sensor)
            p.field("readings_total", int(total))
            # Omitted until the sensor has delivered once. A missing field is a gap in the
            # series; a zero would be a claim that a reading had just arrived.
            if age_s is not None:
                p.field("reading_age_s", round(float(age_s), 1))
            points.append(p)
        self.write_api.write(bucket=self.bucket, record=points)

    def close(self) -> None:
        self.client.close()
