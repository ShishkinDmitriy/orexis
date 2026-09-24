"""The words the sensing layer reads and writes, and the names it spells for eyes.

THE VOCABULARY IS THE PACKAGE'S. `sensing:` is declared by `packages/orexis-capability-sensing/
ontology.ttl` — the drift and its horizons, the three side families, what a sensor monitors —
and this layer speaks it rather than restating it; the one word of its own is the kind of
graph the instrument's result is kept in (`ontology.ttl` beside this file). SOSA's words are
SOSA's.

THE NAMES ARE FOR EYES. A reading's graph, its result's and its predictions' are spelled here
for the writer, from the one identifier a process is handed and the key the reading is written
under; every reader asks the catalogue by class and by pattern, and renaming one here would
change nothing a reader sees.
"""

from __future__ import annotations

import re

from agent.ontology import GRAPH_PREFIX, OREXIS

SENSING = "http://example.org/orexis/sensing#"
SOSA = "http://www.w3.org/ns/sosa/"
PROV = "http://www.w3.org/ns/prov#"

#  WHAT THE WORLD DOES TO A READING WHILE NOBODY ACTS — a package's rule, and the horizons it
#  lists beside it, in the timeline's seconds after the reading in hand.
DRIFT = SENSING + "Drift"
AT_HORIZON = SENSING + "atHorizon"

#  THE THREE SIDES a range divides a property into; a member per (subject, property) is
#  minted beneath each, and a reading IS the member its number falls in.
BELOW = SENSING + "BelowRegion"
INSIDE = SENSING + "InRegion"
ABOVE = SENSING + "AboveRegion"
SIDES = (BELOW, INSIDE, ABOVE)

#  THE INSTRUMENT'S WORD, as a graph kind of this layer's own.
RESULT_GRAPH = SENSING + "ResultGraph"

OBSERVATION = SOSA + "Observation"
FEATURE = SOSA + "hasFeatureOfInterest"
PROPERTY = SOSA + "observedProperty"
RESULT = SOSA + "hasSimpleResult"
RESULT_TIME = SOSA + "resultTime"
PHENOMENON_TIME = SOSA + "phenomenonTime"
MADE_BY = SOSA + "madeBySensor"
PROCEDURE = SOSA + "usedProcedure"
GENERATED_BY = PROV + "wasGeneratedBy"
#  WHAT A PREDICTION MAY NOT CARRY: the words that belong to the instrument. A drift's construct
#  may emit them — a centre, an instant, the sensor it read — and the mind reads none, so the
#  layer takes them off the prediction once the centre's side is drawn from them.
RESULT_WORDS = (RESULT, RESULT_TIME, PHENOMENON_TIME, MADE_BY, PROCEDURE, GENERATED_BY)

RECEIVED = OREXIS + "Received"
RECORDED = OREXIS + "Recorded"


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def observation_of(feature: str, observed_property: str) -> str:
    """The node one (feature, property) pair owns: two properties, two nodes, and a probe that
    states a patch keys its node by the patch. Stable and distinct is all a reader relies on —
    it matches on `sosa:hasFeatureOfInterest` and `sosa:observedProperty`, never the name."""
    return f"{OREXIS}obs_{slug(feature)}_{slug(observed_property)}"


def reading_graph(agent_id: str, feature: str, observed_property: str) -> str:
    """Where one key's reading stands as the present: its node, key and sides."""
    return f"{GRAPH_PREFIX}sensed/{agent_id}/{slug(feature)}_{slug(observed_property)}"


def result_graph(agent_id: str, feature: str, observed_property: str) -> str:
    """Where the same reading's result is kept: the number, the instant, the instrument."""
    return f"{GRAPH_PREFIX}result/{agent_id}/{slug(feature)}_{slug(observed_property)}"


def prediction_graph(agent_id: str, feature: str, observed_property: str, n: int) -> str:
    """The n-th prediction of one key, first window first."""
    return f"{GRAPH_PREFIX}predicted/{agent_id}/{slug(feature)}_{slug(observed_property)}/{n}"
