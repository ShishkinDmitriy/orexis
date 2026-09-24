"""The words the sensing layer reads and writes, and the names it spells for eyes.

THE VOCABULARY IS SOSA'S AND SSN'S, AND SIX WORDS OF THIS LAYER'S. A sensor `sosa:observes`
a property and `sosa:isHostedBy` what it is mounted in, and that pair is the key an
observation is written under; a range is SSN-System's. What this layer declares is in
`ontology.ttl` beside this file — the drift, the graph an observation is kept in, the pointer
and the three sides its rules conclude — and nothing of the 0.1.0 package's own: what an
agent polled, what a sensor monitored or sampled, a device's sense mode and a drift's
horizons were SSN restated or read by nothing, and 0.2.0 speaks none of them. Not one word
of any transport.

THE NAMES ARE FOR EYES. An observation's graph and its predictions' are spelled here for the
writer, from the one identifier a process is handed and the key an observation is written
under; every reader asks the catalogue by class and by pattern, and renaming one here would
change nothing a reader sees.
"""

from __future__ import annotations

import re

from agent.ontology import GRAPH_PREFIX, OREXIS

SENSING = "http://example.org/orexis/sensing#"
SOSA = "http://www.w3.org/ns/sosa/"
SSN = "http://www.w3.org/ns/ssn/"
SCHEMA = "https://schema.org/"
PROV = "http://www.w3.org/ns/prov#"
SH = "http://www.w3.org/ns/shacl#"
CODEC = "http://example.org/orexis/codec#"
SCALING = "http://example.org/orexis/scaling#"

#  THIS LAYER'S OWN: what a value does by itself while nobody acts, the graph an observation is
#  kept in, the pointer, and the three sides.
DRIFT = SENSING + "Drift"
OBSERVATION_GRAPH = SENSING + "ObservationGraph"
READING_POINTER = SENSING + "readingPointer"
BELOW = SENSING + "below"
INSIDE = SENSING + "inside"
ABOVE = SENSING + "above"

#  THE PIPELINE'S FAMILIES, whose words the codec and scaling packages own.
DECODED_BY = CODEC + "decodedBy"
JSON_CODEC = CODEC + "Json"
SCALED_BY = SCALING + "scaledBy"
IDENTITY_SCALING = SCALING + "Identity"

#  SOSA'S, on a sensor: what it observes and what it is mounted in, which together are the key.
OBSERVES = SOSA + "observes"
HOSTED_BY = SOSA + "isHostedBy"

#  SOSA'S, on an observation.
OBSERVATION = SOSA + "Observation"
FEATURE = SOSA + "hasFeatureOfInterest"
PROPERTY = SOSA + "observedProperty"
RESULT = SOSA + "hasSimpleResult"
RESULT_TIME = SOSA + "resultTime"
PHENOMENON_TIME = SOSA + "phenomenonTime"
MADE_BY = SOSA + "madeBySensor"
PROCEDURE = SOSA + "usedProcedure"
IS_SAMPLE_OF = SOSA + "isSampleOf"
GENERATED_BY = PROV + "wasGeneratedBy"

#  THE DRAFT'S graph kind the registered rules are kept in.
RULES_GRAPH = SH + "RulesGraph"

RECEIVED = OREXIS + "Received"
RECORDED = OREXIS + "Recorded"
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


def prediction_graph(agent_id: str, feature: str, observed_property: str, n: int) -> str:
    """The n-th prediction of one key, first stretch first."""
    return f"{GRAPH_PREFIX}predicted/{agent_id}/{slug(feature)}_{slug(observed_property)}/{n}"


def rules_graph() -> str:
    """Where this layer's registered rules are kept — one graph, the layer's own."""
    return f"{GRAPH_PREFIX}rules/sensing"
