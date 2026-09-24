"""`surprise`: whether a reading contradicts what was predicted for its instant — the one
question this layer answers upward, and it answers it before the ladder is rewritten.

**THE MIND WAKES ON CONTRADICTION, NOT ON TIME** (#632). A reading inside the sides the
prediction holding at its instant said it may be in is the world going on as believed, and
nothing; one sharing no side with them is a surprise, and the sentence says what contradicted
what; a reading with nothing predicted for it — the first of its key, or one past the ladder
— is news too, since nothing said it would be so. What is done with the answer is the caller's:
the container that revised the reading wakes the planner on a sentence, and this layer marks
nothing and judges nothing.

**ASKED BETWEEN `revise` AND `predict`.** The reading just written stands beside the ladder
the previous reading left; the prediction holding at the reading's instant — or the earliest
of the key, where it came before its window — is what it is held to, and `predict` then drops
that ladder and writes the reading's own. Asked after, there is nothing left to contradict.

A boundary crossed INSIDE the predicted set — a reading below where the set held the region and
the side below — is absorbed, which is the hysteresis a margin would have bought, without the
margin.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import local_of
from agent.store import Raw, catalogue_of, graphs_of, remember, rows
from agent.ontology import PUBLIC

from .ontology import SIDES

log = logging.getLogger("surprise")

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  THE READING: its node's types in the graph of readings, and the instant it was taken.
_READING_Q = """
SELECT ?node ?t ?taken WHERE {
  GRAPH $cat { ?reading a orexis:StateGraph }
  GRAPH ?reading { ?node sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ; a ?t }
  OPTIONAL { GRAPH $cat { ?result a sensing:ResultGraph }
             GRAPH ?result { ?node sosa:resultTime ?taken } } }"""

#  EVERY PREDICTION OF THE KEY, with its window and the sides it types the node with.
_PREDICTED_Q = """
SELECT ?g ?start ?end ?t WHERE {
  GRAPH $cat { ?g a orexis:PredictionGraph ; dcterms:temporal ?p . ?p orexis:start ?start .
               OPTIONAL { ?p orexis:end ?end } }
  GRAPH ?g { ?node sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ; a ?t } }
ORDER BY ?start"""

_SIDES_Q = """
SELECT DISTINCT ?b WHERE { VALUES ?f { $families } ?b rdfs:subClassOf+ ?f }"""


def surprise(store: ox.Store, subject: str, observed_property: str, *, sample: str | None = None,
             memo=None) -> str | None:
    """Whether the reading of `subject` (or the `sample` a probe states) and
    `observed_property` standing now contradicts the prediction holding at its instant. The
    sentence that says so, or None where the world went on as believed — and None where no
    reading of the key stands at all."""
    feature = sample or subject
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    read = rows(store, _READING_Q, (), cat=cat, feature=feature, property=observed_property)
    if not read:
        return None
    sides = remember(memo, ("sides",), lambda: frozenset(SIDES) | frozenset(
        r["b"] for r in rows(store, _SIDES_Q, graphs_of(store, PUBLIC),
                             families=Raw(" ".join(f"<{f}>" for f in SIDES)))))
    actual = frozenset(r["t"] for r in read if r["t"] in sides)
    taken = next((datetime.fromisoformat(r["taken"]) for r in read if r.get("taken")), None)
    windows: dict = {}
    for r in rows(store, _PREDICTED_Q, (), cat=cat, feature=feature, property=observed_property):
        window = windows.setdefault(r["g"], {"start": datetime.fromisoformat(r["start"]),
                                             "end": datetime.fromisoformat(r["end"]) if r.get("end") else None,
                                             "sides": set()})
        if r["t"] in sides:
            window["sides"].add(r["t"])
    what = f"{local_of(observed_property)} of {local_of(feature)}"
    said = ", ".join(sorted(local_of(b) for b in actual)) or "no side"
    if not windows:
        return f"{what} read {said} where nothing was predicted"
    holding = [w for w in windows.values()
               if taken is not None and w["start"] <= taken and (w["end"] is None or taken < w["end"])]
    expected = (holding or [min(windows.values(), key=lambda w: w["start"])])[0]["sides"]
    if actual & expected:
        return None
    return (f"{what} read {said} where "
            f"{', '.join(sorted(local_of(b) for b in expected)) or 'nothing'} was expected")
