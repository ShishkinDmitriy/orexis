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

    def write_reading(self, plant_id: str, sensor: str, value: float) -> None:
        point = (
            Point("soil_moisture")
            .tag("plant", plant_id)
            .tag("sensor", sensor)
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
