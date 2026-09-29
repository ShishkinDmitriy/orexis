"""What sensing says happened — the events its part's signals carry, what of each is reported, and
which is history.

AN OBSERVATION IS HISTORY: one point per observation written, measured under the observed property's
own name — its local name, so a temperature is `AirTemperature` and this module names no property —
with field `value`, tagged `plant` (the subject's `orexis:localId`) and `sensor` (the sensor's), and
stamped with the reading's own `sosa:resultTime`, so the series and the belief agree on when. A
subject or a sensor stating no `orexis:localId` is not tagged. The `plant` tag is a domain word in
sensing's code, carried over as it stood, and #834 renames it for its SOSA role; the dashboards
filter on `sensor` alone. `orexis-dashboards` asks `measurement_of` and `FIELD` here, so a panel
cannot query a name sensing does not write.

AND IT IS A METRIC: how long after the reading it replaced it came, in the agent's seconds, beside
the cadence the world states, tagged by the sensor. So is how many sensors are said silent now, which
is made only where heard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent.metrics import Level, Tag, Value
from agent.ontology import local_of

FIELD = "value"


def measurement_of(prop: str) -> str:
    """The measurement an observation of `prop` is written under: the property's local name."""
    return local_of(prop)


@dataclass(frozen=True)
class Observed:
    """An observation of `observed_property` by the sensor, reading `value` at `at`: the sensor's and
    its subject's ids where the world states them, and how long after the reading it replaced it came
    beside the cadence the world states, where either is known."""
    metric = "received"
    observed_property: str
    value: float
    at: datetime
    sensor: Tag = None
    sensor_id: str | None = None
    subject_id: str | None = None
    interval_s: Value = None
    cadence_s: Value = None

    def point(self) -> dict:
        tags = {}
        if self.subject_id:
            tags["plant"] = self.subject_id
        if self.sensor_id:
            tags["sensor"] = self.sensor_id
        return {"measurement": measurement_of(self.observed_property), "tags": tags,
                "fields": {FIELD: float(self.value)}, "time": self.at}


@dataclass(frozen=True)
class Silence:
    """How many sensors are said silent now: `sensing:silentSince` in a state graph of the agent's,
    which `missed` writes once a sensor is past its limit of cadences and `received` takes back when a
    reading ends it."""
    metric = "silence"
    silent: Level = None
