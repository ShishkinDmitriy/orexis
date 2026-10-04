"""What sensing says happened — the events its part's signals carry, what of each is reported, and
which is history.

AN OBSERVATION IS HISTORY: one point per observation written, measured under the observed property's
own name — its local name, so a temperature is `AirTemperature` and this module names no property —
with field `value`, tagged `feature` (what the observation is of, `sosa:hasFeatureOfInterest`) and
`sensor` (what made it, `sosa:madeBySensor`), each the local name of its IRI (`tag_of`), and stamped
with the reading's own `sosa:resultTime`, so the series and the belief agree on when. THE TAGS ARE
NAMED FOR THE SOSA ROLES AND SPELL NO DOMAIN WORD: the subject's tag was `plant` once, the same
defect #822 took out of the measurement, and #834 renamed it. THE TAG IS THE IRI'S LOCAL NAME AND
NEVER A STATED `orexis:localId`: tagged by the stated id, a sensor stating none was not tagged at
all, and the one world whose sensors state none — the greenhouse, which names its devices by the
topics its society wires — wrote points no panel could filter for and got no readings dashboard
(#885); in every world that did state one it equalled the local name, and the id is the agent's, the
one short string a process is handed. The dashboards filter on `sensor` alone. `orexis-dashboards`
asks `measurement_of`, `tag_of` and `FIELD` here, so a panel cannot query a name or a tag sensing
does not write.

THE POINT CARRIES THE RAW COUNT BESIDE THE READING (#894): field `raw`, the number the sensor gave
(`sensing:rawResult`), where the observation has one. Reflection reads the series and never the
beliefs, and two of its questions — a count that has not moved for days, a reading past a
calibration point — could be asked of the reading alone only through the very scaling under doubt.
The dashboards keep drawing `value`; a point written before carries `value` alone.

AND IT IS A METRIC: how long after the reading it replaced it came, in the agent's seconds, beside
the cadence the world states, tagged by the sensor. So is how many sensors are said silent now, which
is made only where heard — and WHICH sensors the agent doubts, `Doubted`, a level per sensor tagged
`sensor`: silent, stuck, each as it stands at the ask. `silence` counts; `doubted` names.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agent.metrics import Level, Tag, Value
from agent.ontology import local_of

FIELD = "value"
RAW = "raw"


def measurement_of(prop: str) -> str:
    """The measurement an observation of `prop` is written under: the property's local name."""
    return local_of(prop)


def tag_of(iri: str) -> str:
    """The tag a sensor or a subject goes by in the series: the local name of its IRI, which every
    document gives it, where a stated `orexis:localId` is an agent's and a board's."""
    return local_of(iri)


@dataclass(frozen=True)
class Observed:
    """An observation of `observed_property` by the sensor, reading `value` at `at`: the sensor's and
    its feature of interest's tags, the local names of their IRIs, the raw number the sensor gave
    where the observation has one, and how long after the reading it replaced it came beside the
    cadence the world states, where either is known."""
    metric = "received"
    observed_property: str
    value: float
    at: datetime
    sensor: Tag = None
    sensor_id: str | None = None
    feature_id: str | None = None
    interval_s: Value = None
    cadence_s: Value = None
    raw: float | None = None

    def point(self) -> dict:
        tags = {}
        if self.feature_id:
            tags["feature"] = self.feature_id
        if self.sensor_id:
            tags["sensor"] = self.sensor_id
        fields = {FIELD: float(self.value)}
        if self.raw is not None:
            fields[RAW] = float(self.raw)
        return {"measurement": measurement_of(self.observed_property), "tags": tags, "fields": fields, "time": self.at}


@dataclass(frozen=True)
class Silence:
    """How many sensors are said silent now: `sensing:silentSince` in a state graph of the agent's,
    which `missed` writes once a sensor is past its limit of cadences and `received` takes back when a
    reading ends it."""
    metric = "silence"
    silent: Level = None


@dataclass(frozen=True)
class Doubted:
    """A sensor the agent doubts, as it stands at the ask: said silent (`sensing:silentSince`), said
    stuck (`sensing:stuckSince`), each one or nought; and nought on both once, for a sensor doubted
    at the last ask and no longer. Named by the sensor, so the series says WHICH where `silence` says
    how many."""
    metric = "doubted"
    sensor: Tag
    silent: Level = 0
    stuck: Level = 0
