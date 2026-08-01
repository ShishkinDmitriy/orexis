"""InfluxDB = the series (the record). Every raw reading lands here."""

from __future__ import annotations

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


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

    def close(self) -> None:
        self.client.close()
