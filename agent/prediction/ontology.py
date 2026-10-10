"""The words the prediction package reads and writes, and the names it spells for eyes.

ITS OWN WORDS, the drift and what it says, declared in `ontology.ttl` beside this file; everything else
it speaks is the kernel's — the graph kinds and the arrival — and SOSA's, on the observation
it reads and the one it predicts. Not one word of sensing's: the observation a sensor last
made is found by the kernel's kind, `orexis:StateGraph`, and by `sosa:madeBySensor`.

THE NAMES ARE FOR EYES. A prediction's graph is spelled here for the writer, from the one
identifier a process is handed and the key of the observation it is derived from; every
reader asks the catalogue by class and by pattern, and renaming one here would change nothing
a reader sees.
"""

from __future__ import annotations

import re

from agent.ontology import GRAPH_PREFIX, OREXIS

PREDICTION = "http://example.org/orexis/prediction#"
SOSA = "http://www.w3.org/ns/sosa/"

#  THIS PACKAGE'S OWN: one thing that moves a value while nobody acts, the property it moves,
#  and the select answering how fast.
DRIFT = PREDICTION + "Drift"
MOVES = PREDICTION + "moves"
RATE = PREDICTION + "rate"

#  HOW FAR PAST AN OBSERVATION THE AGENT LOOKS: a stance the agent states of itself in its self
#  graph, read by `predict` (knowledge/domain/kernel/stance.md).
HORIZON_TERM = PREDICTION + "horizonS"

#  SOSA'S, on an observation — the key a drift's answer is matched by, and the number.
FEATURE = SOSA + "hasFeatureOfInterest"
PROPERTY = SOSA + "observedProperty"
RESULT = SOSA + "hasSimpleResult"

RECORDED = OREXIS + "Recorded"


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def prediction_graph(agent_id: str, feature: str, observed_property: str, n: int) -> str:
    """The n-th prediction of one key, first stretch first — the ordinal joined by an
    underscore, since a slash cannot sit in a prefixed name's local part and a case would
    have to spell the graph in full."""
    return f"{GRAPH_PREFIX}predicted/{agent_id}/{slug(feature)}_{slug(observed_property)}_{n}"


def predicted_of(feature: str, observed_property: str, n: int) -> str:
    """The node the n-th prediction of one key says the reading of its stretch is — its own, and never
    the percept's it was made from, which is what a sensor said at an instant and crosses into no
    ground (#944). Distinct is all a reader relies on: it matches the key, never the name."""
    return f"{OREXIS}predicted_{slug(feature)}_{slug(observed_property)}_{n}"
