"""`surprise`: whether the number just received contradicts what was predicted for its
instant — the one question this layer answers upward, and it answers it before the ladder
is rewritten.

**THE MIND WAKES ON CONTRADICTION, NOT ON TIME** (#632), and a contradiction is a range bound
between the number received and the number predicted. Against every range the subject states
for the property, the two are compared bound by bound: on the same side of every bound is the
world going on as believed, and nothing; on different sides of one is a surprise, and the
sentence says which bound and what was expected. A number with nothing predicted for it — the
first of its key, or one past the ladder — is news too, since nothing said it would be so.
What is done with the answer is the caller's: the container that received the reading wakes
the planner on a sentence, and this layer marks nothing and concludes nothing.

**ASKED BETWEEN `received` AND `predict`.** The observation just written stands beside the
ladder the previous one left; the prediction holding at the observation's instant — or the
earliest of the key, where it came before its stretch — is what it is held to, and `predict`
then drops that ladder and writes the observation's own.
"""

from __future__ import annotations

import logging
from datetime import datetime

from agent.ontology import local_of
from agent.store import Raw, catalogue_of, remember, rows

from .ranges import ranges_of

log = logging.getLogger("surprise")

#  THE OBSERVATION: its number and the instant it was taken, in the graph of this key.
_OBSERVATION_Q = """
SELECT ?value ?taken WHERE {
  GRAPH $cat { ?graph a sensing:ObservationGraph }
  GRAPH ?graph { ?node sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ;
                 sosa:hasSimpleResult ?value . OPTIONAL { ?node sosa:resultTime ?taken } } }
LIMIT 1"""

#  EVERY PREDICTION OF THE KEY, with its stretch and the number it carries.
_PREDICTED_Q = """
SELECT ?g ?start ?end ?value WHERE {
  GRAPH $cat { ?g a orexis:PredictionGraph ; dcterms:temporal ?p . ?p orexis:start ?start .
               OPTIONAL { ?p orexis:end ?end } }
  GRAPH ?g { ?node sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ;
             sosa:hasSimpleResult ?value } }
ORDER BY ?start"""


def surprise(store, sensor, *, memo=None) -> str | None:
    """Whether the observation of `sensor`'s key standing now contradicts the prediction
    holding at its instant. The sentence that says so, or None where the world went on as
    believed — and None where no observation of the key stands at all."""
    feature, observed_property = sensor.feature, sensor.observes
    cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
    read = next(iter(rows(store, _OBSERVATION_Q, (), cat=cat, feature=feature, property=observed_property)), None)
    if read is None:
        return None
    value = float(read["value"])
    taken = datetime.fromisoformat(read["taken"]) if read.get("taken") else None
    what = f"{local_of(observed_property)} of {local_of(feature)}"
    windows = [{"start": datetime.fromisoformat(r["start"]),
                "end": datetime.fromisoformat(r["end"]) if r.get("end") else None,
                "value": float(r["value"])}
               for r in rows(store, _PREDICTED_Q, (), cat=cat, feature=feature, property=observed_property)]
    if not windows:
        return f"{what} read {value:g} where nothing was predicted"
    holding = [w for w in windows
               if taken is not None and w["start"] <= taken and (w["end"] is None or taken < w["end"])]
    expected = (holding or [min(windows, key=lambda w: w["start"])])[0]["value"]
    for r in ranges_of(store, sensor.subject, observed_property, memo):
        got, foreseen = r.side(value), r.side(expected)
        if got == foreseen:
            continue
        where = {-1: "under the floor of", 0: "inside", 1: "over the ceiling of"}[got]
        return f"{what} read {value:g}, {where} {local_of(r.uri)}, where {expected:g} was expected"
    return None
