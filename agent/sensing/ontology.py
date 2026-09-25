"""The words the sensing layer reads and writes, and the names it spells for eyes.

THE VOCABULARY IS SOSA'S AND SSN'S, AND THIS LAYER'S WHERE THEY HAVE NONE. A sensor
`sosa:observes` a property and `sosa:isHostedBy` what it is mounted in, and that pair is the
key an observation is written under; how often it reports is its `ssn-system:Frequency`, and
a range is SSN-System's. What this layer declares is in `ontology.ttl` beside this file — the
graph an observation is kept in, the silence, the three sides its rules conclude, and the
pipeline's concepts: a codec and a scaling, the binding of a sensor to one of each, the JSON
and identity members that ship, and the pointer — and nothing of the 0.1.0 packages' own: what an agent polled, what a sensor monitored or sampled,
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

#  THIS LAYER'S OWN: the graph an observation is kept in, the silence, the sides.
OBSERVATION_GRAPH = SENSING + "ObservationGraph"
SILENT_SINCE = SENSING + "silentSince"
BELOW = SENSING + "below"
INSIDE = SENSING + "inside"
ABOVE = SENSING + "above"

#  THE PIPELINE'S: the two families, a sensor's binding to a member of each, the members that
#  ship, and the pointer.
CODEC = SENSING + "Codec"
DECODED_BY = SENSING + "decodedBy"
JSON_CODEC = SENSING + "Json"
SCALING = SENSING + "Scaling"
SCALED_BY = SENSING + "scaledBy"
IDENTITY_SCALING = SENSING + "Identity"
READING_POINTER = SENSING + "readingPointer"

RECEIVED = OREXIS + "Received"
DERIVED = OREXIS + "Derived"
ASSERTED = OREXIS + "Asserted"


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def observation_of(feature: str, observed_property: str) -> str:
    """The node one (feature, property) pair owns: two properties, two nodes, and a probe that
    states a patch keys its node by the patch. Stable and distinct is all a reader relies on —
    it matches on `sosa:hasFeatureOfInterest` and `sosa:observedProperty`, never the name."""
    return f"{OREXIS}obs_{slug(feature)}_{slug(observed_property)}"


def observation_graph(agent_id: str, feature: str, observed_property: str) -> str:
    """Where one key's observation stands as the present."""
    return f"{GRAPH_PREFIX}observed/{agent_id}/{slug(feature)}_{slug(observed_property)}"


def silent_graph(agent_id: str, sensor: str) -> str:
    """Where a sensor's silence is said, while it lasts."""
    return f"{GRAPH_PREFIX}silent/{agent_id}/{slug(sensor)}"

