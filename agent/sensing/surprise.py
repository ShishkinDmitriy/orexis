"""`surprise`: whether a reading contradicts what was predicted for its instant — the one
question this layer answers upward, and it answers it before the ladder is rewritten.

**THE MIND WAKES ON CONTRADICTION, NOT ON TIME** (#632). A reading whose side of every region
is among the sides the prediction holding at its instant allowed for that region is the world
going on as believed, and nothing; one on a side no prediction allowed for some region is a
surprise, and the sentence says what contradicted what; a reading with nothing predicted for
it — the first of its key, or one past the ladder — is news too, since nothing said it would
be so. What is done with the answer is the caller's: the container that revised the reading
wakes the planner on a sentence, and this layer marks nothing and judges nothing.

**ASKED BETWEEN `revise` AND `predict`.** The reading just written stands beside the ladder
the previous reading left; the prediction holding at the reading's instant — or the earliest
of the key, where it came before its window — is what it is held to, and `predict` then drops
that ladder and writes the reading's own. Asked after, there is nothing left to contradict.

A boundary crossed INSIDE the predicted set — a reading below a region where the set held
inside and below — is absorbed, which is the hysteresis a margin would have bought, without
the margin.
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.ontology import local_of
from agent.store import Raw, catalogue_of, remember, rows

log = logging.getLogger("surprise")

#  THE READING'S REVISIONS: its side of every region, in the graph of readings, and the
#  instant it was taken from the result beside it.
_READ_Q = """
SELECT ?region ?side ?taken WHERE {
  GRAPH $cat { ?reading a orexis:StateGraph }
  GRAPH ?reading { ?r a sensing:Revision ; sensing:ofSubject $feature ; sensing:ofProperty $property ;
                   sensing:ofRegion ?region ; sensing:side ?side }
  OPTIONAL { GRAPH $cat { ?result a sensing:ResultGraph }
             GRAPH ?result { ?m sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ;
                             sosa:resultTime ?taken } } }
ORDER BY ?region"""

#  WHETHER ANYTHING OF THE KEY STANDS AT ALL — a reading revised against no region is one too.
_STANDS_Q = """
SELECT ?reading WHERE {
  GRAPH $cat { ?reading a orexis:StateGraph }
  GRAPH ?reading { ?o sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property } }
LIMIT 1"""

#  EVERY PREDICTION OF THE KEY, with its window and the sides it allows per region.
_PREDICTED_Q = """
SELECT ?g ?start ?end ?region ?side WHERE {
  GRAPH $cat { ?g a orexis:PredictionGraph ; dcterms:temporal ?p . ?p orexis:start ?start .
               OPTIONAL { ?p orexis:end ?end } }
  GRAPH ?g { ?r a sensing:Revision ; sensing:ofSubject $feature ; sensing:ofProperty $property ;
             sensing:ofRegion ?region ; sensing:side ?side } }
ORDER BY ?start"""


def surprise(store: ox.Store, subject: str, observed_property: str, *, sample: str | None = None,
             memo=None) -> str | None:
    """Whether the reading of `subject` (or the `sample` a probe states) and
    `observed_property` standing now contradicts the prediction holding at its instant. The
    sentence that says so, or None where the world went on as believed — and None where no
    reading of the key stands at all."""
    feature = sample or subject
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    if not rows(store, _STANDS_Q, (), cat=cat, feature=feature, property=observed_property):
        return None
    read = rows(store, _READ_Q, (), cat=cat, feature=feature, property=observed_property)
    actual = {r["region"]: r["side"] for r in read}
    taken = next((datetime.fromisoformat(r["taken"]) for r in read if r.get("taken")), None)
    windows: dict = {}
    for r in rows(store, _PREDICTED_Q, (), cat=cat, feature=feature, property=observed_property):
        window = windows.setdefault(r["g"], {"start": datetime.fromisoformat(r["start"]),
                                             "end": datetime.fromisoformat(r["end"]) if r.get("end") else None,
                                             "allowed": {}})
        window["allowed"].setdefault(r["region"], set()).add(r["side"])
    what = f"{local_of(observed_property)} of {local_of(feature)}"
    said = ", ".join(f"{local_of(s)} {local_of(g)}" for g, s in sorted(actual.items())) or "against no region"
    if not windows:
        return f"{what} read {said} where nothing was predicted"
    holding = [w for w in windows.values()
               if taken is not None and w["start"] <= taken and (w["end"] is None or taken < w["end"])]
    expected = (holding or [min(windows.values(), key=lambda w: w["start"])])[0]["allowed"]
    contradicted = [(region, side) for region, side in sorted(actual.items())
                    if region in expected and side not in expected[region]]
    if not contradicted:
        return None
    return f"{what} read " + "; ".join(
        f"{local_of(side)} {local_of(region)} where {' or '.join(sorted(local_of(s) for s in expected[region]))} was expected"
        for region, side in contradicted)
