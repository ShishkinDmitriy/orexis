"""The series store: every observation the agent receives, written where the dashboards draw it.

What an agent believes lives in its store; what a person watches lives in InfluxDB, in the agent's
own bucket, granted by `orexis-influx`. The runtime hands this each observation graph sensing just
wrote, and it writes one point per observation, measured under the observed property's own name —
its local name, read off `sosa:observedProperty`, so a temperature is `AirTemperature` and this
module names no property — with field `value`, tagged `plant` (the subject's `orexis:localId`) and
`sensor` (the sensor's), and stamped with the reading's own `sosa:resultTime`, so the series and
the belief agree on when. Only readings: 0.2.0 reports nothing of its own health.

0.1.0 wrote every point as `soil_moisture`, whatever it observed, with the property in a tag; the
shape was one property's, and the terrace's air temperature landed as soil moisture (#822). The
tag went with it, since it said what the measurement now says.

The client library is imported where the writer is brought up from the environment, and nowhere
else, so an agent with no series store never loads it.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from agent.ontology import PUBLIC, local_of
from agent.store import graphs_of, rows

log = logging.getLogger("series")

FIELD = "value"


def measurement_of(prop: str) -> str:
    """The measurement an observation of `prop` is written under: the property's local name.
    `orexis-dashboards` asks this too, so a panel cannot query a name the agent does not write."""
    return local_of(prop)

_READING_Q = """
SELECT ?value ?at ?property ?subject ?sensor WHERE {
  GRAPH $graph { ?o sosa:hasSimpleResult ?value ; sosa:resultTime ?at ;
                    sosa:observedProperty ?property ; sosa:hasFeatureOfInterest ?feature .
                 OPTIONAL { ?o sosa:madeBySensor ?by } }
  OPTIONAL { ?feature orexis:localId ?subject }
  OPTIONAL { ?by orexis:localId ?sensor } }"""


class Series:
    """One bucket, and how a point reaches it: `write(bucket, record)`, the client's own call."""

    def __init__(self, bucket: str, write):
        self.bucket, self._write = bucket, write

    @classmethod
    def from_environment(cls, environ=None) -> "Series | None":
        """The agent's bucket and token, and where the store is — `INFLUX_URL`, `INFLUX_ORG`,
        `INFLUX_BUCKET`, `INFLUX_TOKEN` — or None where the environment names no store."""
        env = os.environ if environ is None else environ
        if not env.get("INFLUX_TOKEN") or not env.get("INFLUX_BUCKET"):
            return None
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS

        client = InfluxDBClient(url=env.get("INFLUX_URL", "http://localhost:8086"),
                                token=env["INFLUX_TOKEN"], org=env.get("INFLUX_ORG", "orexis"))
        return cls(env["INFLUX_BUCKET"], client.write_api(write_options=SYNCHRONOUS).write)

    def record(self, store, graph: str) -> int:
        """Write the observation `graph` holds; how many points. A store that refuses the write is
        said in the log and costs the agent nothing — a series is watched, never believed."""
        points = []
        for r in rows(store, _READING_Q, graphs_of(store, PUBLIC), graph=graph):
            tags = {}
            if r.get("subject"):
                tags["plant"] = r["subject"]
            if r.get("sensor"):
                tags["sensor"] = r["sensor"]
            points.append({"measurement": measurement_of(r["property"]), "tags": tags,
                           "fields": {FIELD: float(r["value"])},
                           "time": datetime.fromisoformat(r["at"])})
        if not points:
            return 0
        try:
            self._write(bucket=self.bucket, record=points)
        except Exception as exc:                                   # noqa: BLE001
            log.warning("the series store refused %d point(s): %s", len(points), exc)
            return 0
        return len(points)
