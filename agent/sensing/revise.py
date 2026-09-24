"""`revise`: a reading arrived, and the belief base says what it is.

**ONE READING IS TWO GRAPHS, AND THE MIND READS ONE OF THEM.** The observation node — of
what, which property — and the REVISIONS drawn from it go into a graph of readings,
`orexis:StateGraph`, the kind a plan forks and an effect rewrites. The number, the instant,
the instrument and its procedure go beside it into a graph of this layer's own kind,
`sensing:ResultGraph`, on a node of its own carrying the same key: a belief every rule that
wants the number may read and no world is ever forked from. Both hold from the reading's
instant until the HORIZON the caller gives — the cadence with whatever tolerance the
instrument earns — and a reader asking at an instant past it is handed neither: the reading's
standing as the present ends by the clock, as every graph with a period does, and nothing
here keeps a timer or writes a mark.

**A REVISION IS THE VERDICT AGAINST ONE REGION, AND NOTHING IS MINTED** (#785). A region is
any range the world states for the property, on the subject or on an instrument monitoring
it — SSN's operating and survival ranges, a domain's own — and for every one that applies the
one classification below writes one `sensing:Revision`: of this subject and property,
compared with this region, below it, inside it or above it. One query for every subject,
property and region there is; no class per combination, no intersection at genesis, since the
desire quantifies over the revisions and an action names the regions it cares about. A
property no region is stated for is written and revised against nothing.

**IDENTITY IS BY CONTENT.** The observation node and every revision are blank nodes, because
the hash and the executor's verifier compare a blank node by what is said about it and an IRI
by its name: a revision a drift or a dose constructs and one written here are the same fact,
and a look predicting an observation with this key is answered by the one that arrives.

**ONE NODE PER SUBJECT AND PROPERTY**, replaced each reading (#669's invariant, kept at the
writer). The property is part of the identity because a pot with a probe and a thermometer
is one feature with two properties; the feature is the patch where a probe states one
(`sosa:Sample`, #98) and the subject otherwise, and the regions are the subject's.

The predecessor's writer put everything on one node in one graph with no period, typed it
with a class minted per subject, property and side, and marked staleness by a deadline
landing on the loop; the number in the mind's world made every reading a new world to the
search, and the mark was a timer a restart lost.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from agent.ontology import PUBLIC, STATE, local_of
from agent.store import Raw, bind, entry, forget_graph, graphs_of, rows, update

from .ontology import RECEIVED, RESULT_GRAPH, reading_graph, result_graph

log = logging.getLogger("revise")

#  THE CLASSIFICATION: one revision per region that applies to the reading's subject and
#  property, from the number the result graph holds. The regions are read off public
#  knowledge — `USING` merges the public graphs and the result graph as the default graph,
#  since an update's WHERE reads nothing else — and a region is the condition of a range the
#  subject states or an instrument monitoring it states, for this property. A blank node in
#  the template is a new node per solution, which is the one revision per region.
_CLASSIFY_U = """
INSERT { GRAPH $reading { _:revision a sensing:Revision ; sensing:ofSubject $feature ;
                          sensing:ofProperty $property ; sensing:ofRegion ?region ;
                          sensing:side ?side } }
$using
WHERE {
  ?measured sosa:hasFeatureOfInterest $feature ; sosa:observedProperty $property ;
            sosa:hasSimpleResult ?value .
  { $subject ssn-system:hasOperatingRange|ssn-system:hasSurvivalRange ?range }
  UNION
  { ?instrument sensing:monitors $subject ;
                ssn-system:hasOperatingRange|ssn-system:hasSurvivalRange ?range }
  ?range ssn-system:inCondition ?region .
  ?region ssn:forProperty $property ; schema:minValue ?low ; schema:maxValue ?high .
  BIND(IF(?value < ?low, sensing:Below, IF(?value > ?high, sensing:Above, sensing:Inside)) AS ?side) }"""

_SIDES_Q = """
SELECT ?region ?side WHERE {
  GRAPH $reading { ?r a sensing:Revision ; sensing:ofRegion ?region ; sensing:side ?side } }
ORDER BY ?region"""


def revise(store: ox.Store, me: str, subject: str, observed_property: str, value: float,
           at: datetime, horizon: float, *, sensor: str | None = None,
           procedure: str | None = None, sample: str | None = None,
           phenomenon_at: datetime | None = None, memo=None) -> str:
    """Write what a sensor read: the observation of `subject` (or the `sample` a probe
    states) and `observed_property`, with one revision per region that applies, standing as
    the present from `at` for `horizon` seconds; and its result beside it. The graph the
    reading stands in.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    reading's author and the graphs' owner. `sensor` and `procedure` are the instrument's
    word about itself and go with the result; `phenomenon_at` is the instant a device that
    speaks for itself says the result applies to (#101), where `at` is the arrival.
    """
    feature = sample or subject
    who = local_of(me)
    reading = reading_graph(who, feature, observed_property)
    result = result_graph(who, feature, observed_property)
    forget_graph(store, reading)
    forget_graph(store, result)
    until = at + timedelta(seconds=float(horizon))
    said = [f'sosa:hasSimpleResult "{round(float(value), 6)}"^^xsd:decimal',
            f'sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
            f'prov:wasGeneratedBy <{me}>']
    if phenomenon_at is not None:
        said.append(f'sosa:phenomenonTime "{phenomenon_at.isoformat()}"^^xsd:dateTime')
    if sensor:
        said.append(f'sosa:madeBySensor <{sensor}>')
    if procedure:
        said.append(f'sosa:usedProcedure <{procedure}>')
    update(store, f"""
INSERT DATA {{
  GRAPH <{reading}> {{
    _:reading a sosa:Observation ;
        sosa:hasFeatureOfInterest <{feature}> ;
        sosa:observedProperty <{observed_property}> . }}
  GRAPH <{result}> {{
    _:result a sosa:Observation ;
        sosa:hasFeatureOfInterest <{feature}> ;
        sosa:observedProperty <{observed_property}> ;
        {' ; '.join(said)} . }}
  {entry(store, reading, STATE, RECEIVED, me, start=at, end=until)}
  {entry(store, result, RESULT_GRAPH, RECEIVED, me, start=at, end=until)} }}""")
    using = " ".join(f"USING <{g}>" for g in [*graphs_of(store, PUBLIC), result])
    update(store, bind(_CLASSIFY_U, reading=Raw(f"<{reading}>"), feature=feature, subject=subject,
                       property=observed_property, using=Raw(using)))
    sides = rows(store, _SIDES_Q, (), reading=Raw(f"<{reading}>"))
    log.info("%s: %s of %s reads %s — %s", who, local_of(observed_property), local_of(feature), value,
             ", ".join(f"{local_of(r['side'])} {local_of(r['region'])}" for r in sides) or "no region to compare with")
    return reading
