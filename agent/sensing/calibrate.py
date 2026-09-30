"""`calibrate`: the agent is told what a sensor is reading now, and revises what it believes of it.

A sensor whose number is not yet a quantity is read through the calibration points the agent
believes of it — each a number and the quantity it stands for, named by its label, `dry` or `wet` —
in a `sensing:CalibrationGraph` of the agent's own, by this layer's rule (rules.ttl). Being told "the probe is in dry air
now" is a revision of that belief: the point labelled `dry` takes the raw value of the sensor's
latest observation — the number `received` wrote (`sensing:rawResult`) — or the number the teller
says. No reflash, no edit of a document: the document under the world's
`beliefs/` is the belief the agent was born with, and a lived-in volume keeps the revised one.

The next reading is concluded through the revised points; the reading standing now keeps the
quantity it was revised to, since that was concluded under the calibration then believed.

RUN AGAINST THE AGENT'S OWN STORE, and only while the agent is stopped, since one process holds a
volume at a time: `python -m agent.sensing.calibrate <volume> <sensor-id> <reference> [--raw N]`,
inside the agent's own image so the store is opened by the engine that wrote it. `orexis-calibrate`
does that for a world's running agent.
"""

from __future__ import annotations

import argparse
import logging

import pyoxigraph as ox

from agent.ontology import PUBLIC
from agent.store import Raw, bind, graphs_of, rows, update

from .ontology import CALIBRATION_GRAPH, OBSERVATION_GRAPH

log = logging.getLogger("calibrate")

#  THE POINT A REFERENCE NAMES, in whichever calibration graph of the agent's holds it.
_POINT_Q = """
SELECT ?g ?point ?raw WHERE { GRAPH ?g { $sensor sensing:calibrationPoint ?point .
  ?point rdfs:label ?label ; sensing:raw ?raw FILTER(STR(?label) = $reference) } }"""

#  THE RAW VALUE THE SENSOR READS NOW: its latest observation's, kept beside the scaled result.
_NOW_Q = """
SELECT ?raw ?t WHERE { GRAPH ?o { ?obs sosa:madeBySensor $sensor ; sensing:rawResult ?raw ; sosa:resultTime ?t } }
ORDER BY DESC(?t) LIMIT 1"""

#  THE REVISION, the point found again by its label: a calibration point is a blank node, and a
#  blank node bound into an update is a fresh one, not the node it came from.
_REVISE_U = """
DELETE { GRAPH $graph { ?point sensing:raw ?old } }
INSERT { GRAPH $graph { ?point sensing:raw $raw } }
WHERE  { GRAPH $graph { $sensor sensing:calibrationPoint ?point .
                        ?point rdfs:label ?label ; sensing:raw ?old FILTER(STR(?label) = $reference) } }"""

_SENSOR_Q = """SELECT DISTINCT ?s WHERE { ?s a sosa:Sensor ; orexis:localId $id }"""


def calibrate(store, sensor: str, reference: str, raw: float | None = None) -> str:
    """Revise the calibration point labelled `reference` of `sensor` to `raw`, or to the raw value
    of the sensor's latest observation. The calibration graph revised. Refused — a `LookupError`
    naming what is missing — where the agent believes no such point, or `raw` is not given and no
    observation of the sensor kept a raw value."""
    found = rows(store, _POINT_Q, graphs_of(store, CALIBRATION_GRAPH), sensor=sensor, reference=ox.Literal(reference))
    if not found:
        raise LookupError(f"the agent believes no calibration point {reference!r} of {sensor}")
    if raw is None:
        now = rows(store, _NOW_Q, graphs_of(store, OBSERVATION_GRAPH), sensor=sensor)
        if not now:
            raise LookupError(f"{sensor} has no observation keeping a raw value to take as {reference!r}")
        raw = float(now[0]["raw"])
    point = found[0]
    update(store, bind(_REVISE_U, graph=point["g"], sensor=sensor, reference=ox.Literal(reference),
                       raw=Raw(f'"{round(float(raw), 6)}"^^xsd:decimal')))
    log.info("%s: %s was %s, is %s", sensor, reference, point["raw"], raw)
    return point["g"]


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m agent.sensing.calibrate",
                                     description="Tell a stopped agent what one of its sensors is reading now.")
    parser.add_argument("volume", help="the agent's store, as its container mounts it")
    parser.add_argument("sensor", help="the sensor's orexis:localId")
    parser.add_argument("reference", help="the calibration point's label, e.g. dry or wet")
    parser.add_argument("--raw", type=float, help="the raw value to take; the latest observation's where absent")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    store = ox.Store(args.volume)
    found = rows(store, _SENSOR_Q, graphs_of(store, PUBLIC), id=ox.Literal(args.sensor))
    if len(found) != 1:
        raise SystemExit(f"the world names {len(found)} sensors {args.sensor!r}")
    calibrate(store, found[0]["s"], args.reference, args.raw)
    store.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
