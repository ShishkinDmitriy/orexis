"""`received`: a transport hands sensing the bytes it read for a sensor, and an observation is
written — the callback, and the whole of the translation row.

**BYTES TO A NUMBER TO ONE OBSERVATION.** The sensor is an IRI, and what it `sosa:observes`
and what it `sosa:isHostedBy` — the feature of interest, or a sample of one — is the KEY,
read off public knowledge; a sensor stating no property or no host, or several, has no key
and writes nothing. The pipeline makes a quantity of the bytes by the codec, the pointer and
the scaling the sensor's binding names; a payload that does not decode writes nothing, said in
the log, because a pointer that misses is not a measurement. What is written is one
`sosa:Observation` in SOSA's words — of what, which property, the result, the instant it
arrived, the sensor, the procedure and the instant the device says the result applies to
where it says one — into the graph of this key, `sensing:ObservationGraph`, received, the
agent's, holding from its instant UNTIL THE NEXT IS DUE — the sensor's `ssn-system:Frequency`
past it (`cadence_of`), or with no end where the world states none — and replacing whole the
observation of the key before (#669's invariant, kept at the writer). A reader asking at an
instant past that is handed nothing: the observation's standing as the present ends by the
clock, `missed` says so on the container's tick, and nothing here keeps a timer.

**A READING ENDS A SILENCE.** A sensor `missed` had said silent is silent no longer: the graph
saying so goes before the observation is written, found by the row's content and never by name.

**NOTHING ELSE.** No side is drawn here: which side of its subject's ranges the number lies on
is a revision, concluded by the rules this layer registers and run by the deliberator when the
container says this graph changed. No prediction: that is the prediction package's, over the
observation written here. No want, no wake, no verdict on what was predicted: a reading either
lands where the stretch holding at its instant said it would or it does not, and that is the
planner's re-root by hash to tell.

**IT IS CALLED, NOT CALLING.** A transport's driver knows which message on which channel is
whose; it hands the bytes and the sensor here and learns nothing of what they meant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.ontology import PUBLIC, local_of
from agent.store import Raw, catalogue_of, entry, forget_graph, graphs_of, rows, update

from .cadence import cadence_of
from .ontology import OBSERVATION_GRAPH, RECEIVED, observation_graph, observation_of
from .pipeline import decode

log = logging.getLogger("received")

#  THE KEY: what the sensor observes, of what it is mounted in.
_KEY_Q = "SELECT ?feature ?property WHERE { $sensor sosa:observes ?property ; sosa:isHostedBy ?feature }"

#  THE SILENCE SAID OF THIS SENSOR, if any — the graph holding the row, found by its content.
_SILENCE_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { $sensor sensing:silentSince ?since } }"""


def received(store, me: str, sensor: str, payload: bytes, at: datetime, *,
             procedure: str | None = None, phenomenon_at: datetime | None = None, memo=None) -> str | None:
    """Write what `sensor` read, `payload` decoded by its binding: the observation of the
    property it observes, of what it is hosted by, standing as the present from `at` until
    the next is due by the sensor's frequency — with no end where the world states none. The
    graph's name, or None where the sensor has no key or the payload holds no reading.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    observation's author and the graph's owner. `procedure` is the instrument's word about
    how it read; `phenomenon_at` the instant a device that speaks for itself says the result
    applies to (#101), where `at` is the arrival.
    """
    keys = rows(store, _KEY_Q, graphs_of(store, PUBLIC), sensor=sensor)
    if len(keys) != 1:
        log.warning("%s has no key: one property observed of one host makes one, and the world states %d", local_of(sensor), len(keys))
        return None
    value = decode(store, sensor, payload)
    if value is None:
        return None
    feature, observed_property = keys[0]["feature"], keys[0]["property"]
    node = observation_of(feature, observed_property)
    graph = observation_graph(local_of(me), feature, observed_property)
    forget_graph(store, graph)
    cat = Raw(f"<{catalogue_of(store)}>")
    for silence in rows(store, _SILENCE_Q, (), cat=cat, sensor=sensor):
        forget_graph(store, silence["g"])
    cadence = cadence_of(store, sensor, memo)
    until = at + timedelta(seconds=cadence) if cadence is not None else None
    said = [f'<{node}> a sosa:Observation',
            f'<{node}> sosa:hasFeatureOfInterest <{feature}>',
            f'<{node}> sosa:observedProperty <{observed_property}>',
            f'<{node}> sosa:hasSimpleResult "{round(float(value), 6)}"^^xsd:decimal',
            f'<{node}> sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
            f'<{node}> sosa:madeBySensor <{sensor}>',
            f'<{node}> prov:wasGeneratedBy <{me}>']
    if phenomenon_at is not None:
        said.append(f'<{node}> sosa:phenomenonTime "{phenomenon_at.isoformat()}"^^xsd:dateTime')
    if procedure:
        said.append(f'<{node}> sosa:usedProcedure <{procedure}>')
    update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ {' . '.join(said)} . }}
  {entry(store, graph, OBSERVATION_GRAPH, RECEIVED, me, start=at, end=until)} }}""")
    log.info("%s: %s of %s reads %s", local_of(me), local_of(observed_property), local_of(feature), value)
    return graph
