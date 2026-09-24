"""`received`: a transport hands sensing the bytes it read for a sensor, and an observation is
written — the callback, and the whole of the translation row.

**BYTES TO A NUMBER TO ONE OBSERVATION.** The pipeline makes a quantity of the bytes by the
codec, the pointer and the scaling the sensor's binding names; a payload that does not decode
writes nothing, said in the log, because a pointer that misses is not a measurement. What is
written is one `sosa:Observation` in SOSA's words — of what, which property, the result, the
instant it arrived, the sensor, the procedure and the instant the device says the result
applies to where it says one — into the graph of this key, `sensing:ObservationGraph`,
received, the agent's, holding from its instant to the HORIZON the caller gives, and replacing
whole the observation of the key before (#669's invariant, kept at the writer). A reader asking
at an instant past the horizon is handed nothing: the observation's standing as the present
ends by the clock, and nothing here keeps a timer or writes a mark.

**NOTHING ELSE.** No side is drawn here: which side of its subject's ranges the number lies on
is a revision, concluded by the rules this layer registers and run by the deliberator when the
container says this graph changed. No want, no wake, no verdict on what was predicted: a
reading either lands where the stretch holding at its instant said it would or it does not,
and that is the planner's re-root by hash to tell — `predict` then rewrites the key's future.

**IT IS CALLED, NOT CALLING.** A transport's driver knows which message on which channel is
whose; it hands the bytes and the sensor here and learns nothing of what they meant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.ontology import local_of
from agent.store import entry, forget_graph, update

from .ontology import OBSERVATION_GRAPH, RECEIVED, observation_graph, observation_of
from .pipeline import decode

log = logging.getLogger("received")


def received(store, me: str, sensor, payload: bytes, at: datetime, *, horizon: float,
             procedure: str | None = None, phenomenon_at: datetime | None = None) -> str | None:
    """Write what `sensor` read, `payload` decoded by its binding: the observation of its
    feature and property, standing as the present from `at` for `horizon` seconds. The
    graph's name, or None where the payload holds no reading.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    observation's author and the graph's owner. `procedure` is the instrument's word about
    how it read; `phenomenon_at` the instant a device that speaks for itself says the result
    applies to (#101), where `at` is the arrival.
    """
    value = decode(sensor, payload)
    if value is None:
        return None
    feature, observed_property = sensor.feature, sensor.observes
    node = observation_of(feature, observed_property)
    graph = observation_graph(local_of(me), feature, observed_property)
    forget_graph(store, graph)
    until = at + timedelta(seconds=float(horizon))
    said = [f'<{node}> a sosa:Observation',
            f'<{node}> sosa:hasFeatureOfInterest <{feature}>',
            f'<{node}> sosa:observedProperty <{observed_property}>',
            f'<{node}> sosa:hasSimpleResult "{round(float(value), 6)}"^^xsd:decimal',
            f'<{node}> sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
            f'<{node}> sosa:madeBySensor <{sensor.uri}>',
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
