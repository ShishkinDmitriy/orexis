"""The words the sensing layer reads and writes, and the names it spells for eyes.

THE VOCABULARY IS SOSA'S AND SSN'S, AND THIS LAYER'S WHERE THEY HAVE NONE. A sensor
`sosa:observes` a property and `sosa:isHostedBy` what it is mounted in, and that pair is the
key an observation is written under; how often it reports is its `ssn-system:Frequency`, and
a range is SSN-System's. What this layer declares is in `ontology.ttl` beside this file — the
graph an observation is kept in and a forecast's, the silence, the three sides its rules
conclude, and the pipeline's concepts: a codec, the binding of a sensor to one, the JSON member
that ships, the pointer and the two a series is read by, the number a sensor gave, and the
scaling and calibration the rules make a quantity of it by — and nothing of the 0.1.0 packages' own: what an agent polled, what a sensor monitored or sampled,
a device's sense mode and a drift's horizons were SSN restated or read by nothing, and 0.2.0
speaks none of them. The drift is the prediction package's. Not one word of any transport.

THE NAMES ARE FOR EYES. An observation's graph and a silence's are spelled here for the
writer, from the one identifier a process is handed and the key an observation is written
under; every reader asks the catalogue by class and by pattern, and renaming one here would
change nothing a reader sees.
"""

from __future__ import annotations

import re

from agent.ontology import GRAPH_PREFIX, OREXIS

SENSING = "http://example.org/orexis/sensing#"

#  THIS LAYER'S OWN: the graph an observation is kept in and a forecast's, the silence, the sides.
OBSERVATION_GRAPH = SENSING + "ObservationGraph"
FORECAST_GRAPH = SENSING + "ForecastGraph"
SILENT_SINCE = SENSING + "silentSince"
BELOW = SENSING + "below"
INSIDE = SENSING + "inside"
ABOVE = SENSING + "above"

#  THE PIPELINE'S: the codec family, a sensor's binding to a member, the member that ships, the
#  pointers, the number a sensor gave, and the scaling and calibration the rules make a quantity of it by.
CODEC = SENSING + "Codec"
DECODED_BY = SENSING + "decodedBy"
JSON_CODEC = SENSING + "Json"
TWO_POINT_SCALING = SENSING + "TwoPointScaling"
TWO_POINT_CALIBRATION = SENSING + "TwoPointCalibration"
RAW_RESULT = SENSING + "rawResult"
SCALED_RESULT = SENSING + "scaledResult"
READING_POINTER = SENSING + "readingPointer"
STARTS_POINTER = SENSING + "startsPointer"
ENDS_POINTER = SENSING + "endsPointer"

RECEIVED = OREXIS + "Received"
DERIVED = OREXIS + "Derived"
ASSERTED = OREXIS + "Asserted"


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def observation_of(feature: str, observed_property: str) -> str:
    """The node one (feature, property) pair owns — what a forecast's stretches are named from, a
    series being read whole. Stable and distinct is all a reader relies on — it matches on
    `sosa:hasFeatureOfInterest` and `sosa:observedProperty`, never the name."""
    return f"{OREXIS}obs_{slug(feature)}_{slug(observed_property)}"


def observation_by(sensor: str) -> str:
    """The node one sensor's latest observation is: what it gave, and — concluded by this layer's
    rules — what that is an observation of. Stable and distinct is all a reader relies on; it
    matches on SOSA's pattern, never the name."""
    return f"{OREXIS}obs_{slug(sensor)}"


def observation_graph(agent_id: str, sensor: str) -> str:
    """Where one sensor's latest observation stands as the present."""
    return f"{GRAPH_PREFIX}observed/{agent_id}/{slug(sensor)}"


def silent_graph(agent_id: str, sensor: str) -> str:
    """Where a sensor's silence is said, while it lasts."""
    return f"{GRAPH_PREFIX}silent/{agent_id}/{slug(sensor)}"



def forecast_graph(agent_id: str, sensor: str, starts) -> str:
    """Where one stretch of a sensor's forecast stands, named by the sensor and the stretch's
    start."""
    return f"{GRAPH_PREFIX}forecast/{agent_id}/{slug(sensor)}_{starts.strftime('%Y%m%dT%H%M%SZ')}"
