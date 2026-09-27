"""What sensing contributes to history: an observation, as the point a person draws.

One point per observation, contributed by `received` as it writes the `sosa:Observation`
(a-documents-kind-says-who-reads-it, §5). Measured under the observed property's own name — its
local name, so a temperature is `AirTemperature` and this module names no property — with field
`value`, tagged `plant` (the subject's `orexis:localId`) and `sensor` (the sensor's), and stamped
with the reading's own `sosa:resultTime`, so the series and the belief agree on when.

The `plant` tag is a domain word in sensing's code, carried over from the runtime's writer as it
stood, and #834 renames it for its SOSA role; the dashboards filter on `sensor` alone.

`orexis-dashboards` asks `measurement_of` and `FIELD` here, so a panel cannot query a name sensing
does not write. 0.1.0 wrote every point as `soil_moisture`, and those stay under that name in a
bucket that had them (#822).
"""

from __future__ import annotations

from datetime import datetime

from agent.ontology import PUBLIC, local_of
from agent.store import graphs_of, rows

FIELD = "value"

_IDS_Q = """
SELECT ?subject ?sensor WHERE { OPTIONAL { $feature orexis:localId ?subject } OPTIONAL { $sensor orexis:localId ?sensor } }"""


def measurement_of(prop: str) -> str:
    """The measurement an observation of `prop` is written under: the property's local name."""
    return local_of(prop)


def observation_point(store, feature: str, observed_property: str, sensor: str, value: float, at: datetime) -> dict:
    """The point an observation of `observed_property` of `feature` by `sensor`, reading `value`
    at `at`, is written as. A subject or a sensor stating no `orexis:localId` is not tagged."""
    ids = (rows(store, _IDS_Q, graphs_of(store, PUBLIC), feature=feature, sensor=sensor) or [{}])[0]
    tags = {}
    if ids.get("subject"):
        tags["plant"] = ids["subject"]
    if ids.get("sensor"):
        tags["sensor"] = ids["sensor"]
    return {"measurement": measurement_of(observed_property), "tags": tags,
            "fields": {FIELD: float(value)}, "time": at}
