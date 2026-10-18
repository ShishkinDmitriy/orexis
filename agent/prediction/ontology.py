"""The words the prediction package reads and writes, and the names it spells for eyes.

ITS OWN WORDS, the flow and what it says, declared in `ontology.ttl` beside this file; everything else
it speaks is the kernel's — the graph kinds and the arrival — SOSA's, on the observation it reads
and the one it predicts, and ONE of sensing's: the kind an observation is kept in,
`sensing:ObservationGraph`, by which the observation a sensor last made is found. Prediction sits
above sensing — it predicts what a sensor will read, and with no sensing there is nothing to predict
— so it may speak sensing's word, and it imports none of sensing's code (#944).

THE ONE NAME IS FOR EYES. The predicted observation of a key is a node of its own, spelled here from
the key; a reader matches the key, never the name. No graph is named: a forecast of the predictor's own
is no graph of the belief base since #1000, its foresight being the grounds the planner lays.
"""

from __future__ import annotations

import re

from agent.ontology import OREXIS

PREDICTION = "http://example.org/orexis/prediction#"
SOSA = "http://www.w3.org/ns/sosa/"
SENSING = "http://example.org/orexis/sensing#"

#  THIS PACKAGE'S OWN: one thing that moves a value while nobody acts, the property it moves,
#  and the select answering how fast.
FLOW = PREDICTION + "Flow"
MOVES = PREDICTION + "moves"
RATE = PREDICTION + "rate"

#  HOW FAR PAST AN OBSERVATION THE AGENT LOOKS: a stance the agent states of itself in its self
#  graph, read by `predict` (knowledge/domain/kernel/stance.md).
HORIZON_TERM = PREDICTION + "horizonS"

#  SOSA'S, on an observation — the key a flow's answer is matched by, and the number.
FEATURE = SOSA + "hasFeatureOfInterest"
PROPERTY = SOSA + "observedProperty"
RESULT = SOSA + "hasSimpleResult"

#  SENSING'S, the package beneath: the kind an observation and what the rules concluded of it are kept
#  in — a percept, which no reader of the mind is handed and this estimator reads at the boundary.
OBSERVATION_GRAPH = SENSING + "ObservationGraph"


def slug(iri: str) -> str:
    """The local name of a term, safe to paste into an IRI."""
    return re.sub(r"[^A-Za-z0-9_]", "_", re.split(r"[#/]", iri.rstrip("#/"))[-1])


def predicted_of(feature: str, observed_property: str) -> str:
    """The node every prediction of one key says the reading of its stretch is — ONE per key, as a
    fluent is, so a later stretch's graph states the same node's number and instant and the planner
    laying its ground replaces the earlier stretch's by subject and predicate (#988); its own, and
    never the percept's it was made from, which is what a sensor said at an instant and crosses into
    no ground (#944). A reader matches the key, never the name."""
    return f"{OREXIS}predicted_{slug(feature)}_{slug(observed_property)}"
