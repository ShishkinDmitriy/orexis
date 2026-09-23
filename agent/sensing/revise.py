"""`revise`: a reading arrived, and the belief base says what it is.

**ONE READING IS TWO GRAPHS, AND THE MIND READS ONE OF THEM.** The observation node — of
what, which property, and every band the domain says a reading with this number is — goes
into a graph of readings, `orexis:StateGraph`, the kind a plan forks and an effect rewrites.
The number, the instant, the instrument and its procedure go beside it into a graph of this
layer's own kind, `sensing:ResultGraph`, a belief every rule that wants the number may read
and no world is ever forked from. Both hold from the reading's instant until the HORIZON the
caller gives — the cadence with whatever tolerance the instrument earns — and a reader asking
at an instant past it is handed neither: the reading's standing as the present ends by the
clock, as every graph with a period does, and nothing here keeps a timer or writes a mark.

**ONE NODE PER SUBJECT AND PROPERTY**, replaced each reading (#669's invariant, kept at the
writer). The property is part of the identity because a pot with a probe and a thermometer
is one feature with two properties; the feature is the patch where a probe states one
(`sosa:Sample`, #98) and the subject otherwise. The node's IRI is minted from the two and
nothing looks it up by that spelling.

**THE BAND IS ENTAILED, NEVER COMPUTED HERE** (#576): the domain's definitions say what a
reading of this property IS, `entail` reads them as data, and this layer does no arithmetic
on the number at all — it only puts it where the entailment can read it.

The predecessor's writer put everything on one node in one graph with no period, and marked
staleness by a deadline landing on the loop; the number in the mind's world made every
reading a new world to the search, and the mark was a timer a restart lost.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.entail import entail
from agent.ontology import STATE, local_of
from agent.store import entry, forget_graph, update

from .ontology import (RECEIVED, RESULT_GRAPH, observation_of, reading_graph, result_graph)

log = logging.getLogger("revise")


def revise(store: ox.Store, me: str, subject: str, observed_property: str, value: float,
           at: datetime, horizon: float, *, sensor: str | None = None,
           procedure: str | None = None, sample: str | None = None,
           phenomenon_at: datetime | None = None, memo=None) -> str:
    """Write what a sensor read: the observation node keyed by `subject` (or the `sample` a
    probe states) and `observed_property`, typed with its bands, standing as the present from
    `at` for `horizon` seconds; and its result beside it. The node's IRI.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    reading's author and the graphs' owner. `sensor` and `procedure` are the instrument's
    word about itself and go with the result; `phenomenon_at` is the instant a device that
    speaks for itself says the result applies to (#101), where `at` is the arrival.
    """
    feature = sample or subject
    who = local_of(me)
    node = observation_of(feature, observed_property)
    reading = reading_graph(who, feature, observed_property)
    result = result_graph(who, feature, observed_property)
    forget_graph(store, reading)
    forget_graph(store, result)
    until = at + timedelta(seconds=float(horizon))
    said = [f'<{node}> sosa:hasSimpleResult "{round(float(value), 6)}"^^xsd:decimal',
            f'<{node}> sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
            f'<{node}> prov:wasGeneratedBy <{me}>']
    if phenomenon_at is not None:
        said.append(f'<{node}> sosa:phenomenonTime "{phenomenon_at.isoformat()}"^^xsd:dateTime')
    if sensor:
        said.append(f'<{node}> sosa:madeBySensor <{sensor}>')
    if procedure:
        said.append(f'<{node}> sosa:usedProcedure <{procedure}>')
    update(store, f"""
INSERT DATA {{
  GRAPH <{reading}> {{
    <{node}> a sosa:Observation ;
        sosa:hasFeatureOfInterest <{feature}> ;
        sosa:observedProperty <{observed_property}> . }}
  GRAPH <{result}> {{ {' . '.join(said)} . }}
  {entry(store, reading, STATE, RECEIVED, me, start=at, end=until)}
  {entry(store, result, RESULT_GRAPH, RECEIVED, me, start=at, end=until)} }}""")
    bands = entail(store, reading, of=[node], read=(reading, result), memo=memo)
    log.info("%s: %s of %s reads %s — %s", who, local_of(observed_property), local_of(feature),
             value, ", ".join(local_of(c.value) for _, c in bands) or "no band")
    return node
