"""`received`: a transport hands sensing the bytes it read for a sensor, and a percept is written
— the callback, and the whole of the translation row.

**BYTES TO A NUMBER TO A PERCEPT PER READING.** The sensor is an IRI, and what it `sosa:observes`
and what it `sosa:isHostedBy` — the feature of interest, or a sample of one — is what its readings
are of, concluded by this layer's rules. The pipeline makes a number of the bytes by the codec and
the pointer the sensor's binding names; a payload that does not decode writes nothing, said in the
log, because a pointer that misses is not a measurement. Each reading is ONE `sosa:Observation`, in
SOSA's words — the number the sensor gave, the instant it arrived, the sensor, the procedure, the
instant the device says the result applies to where it says one — named for its sensor and its
instant, in a graph of its own, `sensing:ObservationGraph`, an `orexis:PerceptGraph`, received, the
agent's (knowledge/domain/sensing/percept.md, #944). A percept is no belief: no reader of the mind
is handed one, and what the mind reads of it is the subject belief a domain's transition makes when
it arrives.

**EACH LINKS TO THE ONE BEFORE IT, AND THE LATEST IS THE ONE NOTHING FOLLOWS.** A new percept says
`sensing:previous` of the sensor's latest — the percept no percept names as its previous — so a
sensor's percepts are a chain, newest first. The latest holds from its instant UNTIL THE NEXT IS DUE
AND A GRACE PAST IT — the sensor's `ssn-system:Frequency` past it (`cadence_of`), and `GRACE` of
those cadences more, or with no end where the world states none — and a successor arriving, on time
or late, ends it the moment it lands (`end_graph`), revisions and all. So a reader standing at an
instant is handed one percept of a sensor, the one holding then, and a reader asking at an instant
past the last one's end is handed none: the percept's standing as the present ends by the clock,
`missed` says so when sensing's `start` asks every minute, and nothing here keeps a timer.

**A SENSOR'S LAST FEW ARE KEPT, AS DEEP AS SENSING'S RULES READ.** Its deepest rule is stuck's, which
reads a sensor's last `sensing:stuckAfter` readings — the agent's limit, a stance in its self graph,
`STUCK_AFTER` where it states none — so that many of a sensor's percepts are kept and the oldest past
them forgotten here, with what was concluded of each. Nothing else forgets a percept: no sweep drops
a graph because its period has ended, and a percept's ending says only that it is not the present.

**A READING LATE IS NOT A READING MISSING (#870).** Ended exactly at the next one's due instant, a
reading published a moment late — a board's radio, a broker, a simulator's loop — left the agent
with no present for that moment, and a step sized from the reading in it commanded nothing. The
grace is how late a reading may be and still be the same promise kept; past it the reading is
missing, and past `missed`'s limit the sensor is silent.

**THE READINGS ONE MESSAGE CARRIES ARE PERCEPTS IN THE CHAIN, OLDEST FIRST.** A sentinel's alarm
carries its watcher's last quiet sample before the reading that broke the window, each placed that
long before the message arrived: each is a percept of its own, linked to the one before it, an earlier
one holding only until the next one's instant — a step in the history, not a slope.

**A SERIES IS A FORECAST, ONE GRAPH PER STRETCH.** A sensor stating where the instants its values
are for are kept (`reads_series`) is read as a series: each value still ahead is written as its own
`sosa:Observation` into a graph of its own, `sensing:ForecastGraph`, holding during its stretch —
of what, which property, the number, the instant the forecast was issued, the start of its
stretch, the sensor — and every forecast graph the sensor wrote before is forgotten first, so the
next forecast replaces the last. A stretch already over when the forecast arrives is not written.
A forecast is a belief and not a reading, so it ends no silence, is kept as no percept and is said as
no observation.

**A READING ENDS A SILENCE.** A sensor `missed` had said silent is silent no longer: the graph
saying so goes before the percept is written, found by the row's content and never by name.

**AND IT IS SAID.** The graph written is answered to whoever runs the transport, and sensing's
part, hearing an observation graph written, says it as an `Observed` (`events.py`), which history
writes as a point and metrics tallies: sensing decides what an observation is, so sensing says
what happened, and `received` writes to no series.

**NOTHING ELSE.** Nothing is concluded here: what a percept is of, its quantity and whether its
sensor is stuck are revisions, concluded by the rules this layer ships and run by the deliberator
when the container says this graph changed — stuck from the percepts kept, so no run is counted
here and nothing about the past is carried onto the present (#462, #944). No prediction: that is the
prediction package's, over the latest percept. No want, no wake, no verdict on what was predicted.

**IT IS CALLED, NOT CALLING.** A transport's driver knows which message on which channel is
whose; it hands the bytes and the sensor here and learns nothing of what they meant.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from agent.ontology import PUBLIC, local_of
from agent.stance import stance
from agent.store import Raw, catalogue_of, end_graph, entry, forget_graph, graphs_of, rows, update

from .cadence import cadence_of
from .ontology import (FORECAST_GRAPH, OBSERVATION_GRAPH, RECEIVED, STUCK_AFTER_TERM, forecast_graph,
                       observation_of, percept_graph, percept_of)
from .pipeline import decode, decode_series, reads_series

log = logging.getLogger("received")

#  HOW LATE A READING MAY BE, in its sensor's cadences: the percept before it stays the present
#  until its successor arrives or this long past the instant the successor was due. NOT A STANCE:
#  how late a reading arrives is the instrument's and the path its bytes take, not the agent's word
#  about itself, and it is written into the percept's period, which is what the percept IS
#  to every reader after; were it ever to vary, the world would state it of the sensor
#  (knowledge/domain/kernel/stance.md).
GRACE = 1

#  HOW MANY READINGS OF ONE NUMBER SAY A SENSOR STUCK, and so how many of a sensor's percepts are
#  kept, where the agent's self graph states no `sensing:stuckAfter`: twice the silence limit. A live
#  instrument's count moves by a bit within a few readings even in still soil, and soil itself
#  drifts within an hour, so six readings of one number — an hour at the greenhouse's ten minutes,
#  two at the terrace's twenty — are the signature of a frozen oscillator or a half-lost wire rather
#  than of equilibrium; and the suspicion costs one row alone, since the first reading that differs
#  ends it. Sensing's stuck rule (`rules.ttl`) reads the same stance with this figure where none is
#  stated, and `tests/test_received.py` holds the two to one figure.
STUCK_AFTER = 6

#  THE KEY: what the sensor observes, of what it is mounted in — read for a series alone, which names
#  its stretches by it.
_KEY_Q = "SELECT ?feature ?property WHERE { $sensor sosa:observes ?property ; sosa:isHostedBy ?feature }"

#  THE SILENCE SAID OF THIS SENSOR, if any — the graph holding the row, found by its content.
_SILENCE_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { $sensor sensing:silentSince ?since } }"""

#  EVERY PERCEPT OF THIS SENSOR KEPT, newest first: its graph, its node, and whether a percept names
#  it as its previous — the latest is the one none does.
_KEPT_Q = """
SELECT ?g ?o ?t (BOUND(?later) AS ?followed) WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor OPTIONAL { ?o sosa:resultTime ?t } }
  OPTIONAL { GRAPH ?h { ?later sensing:previous ?o } GRAPH $cat { ?h a sensing:ObservationGraph } } }
ORDER BY DESC(?t) DESC(?g)"""

#  WHETHER A GRAPH OF THIS NAME IS ALREADY SAID — a second reading of one sensor at one instant.
_SAID_Q = "SELECT ?p WHERE { GRAPH $cat { $g ?p ?o } } LIMIT 1"

#  THE FORECAST THIS SENSOR GAVE BEFORE: every graph of it, found by its content.
_FORECAST_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a sensing:ForecastGraph } GRAPH ?g { ?o sosa:madeBySensor $sensor } }"""


def received(store, me: str, sensor: str, payload: bytes, at: datetime, *,
             procedure: str | None = None, phenomenon_at: datetime | None = None, memo=None) -> list[str]:
    """Write what `sensor` read, `payload` decoded by its binding: a percept per reading, oldest
    first, each linked to the one before it, the latest standing as the present from its instant
    until the next is due by the sensor's frequency and `GRACE` cadences past it, or until the next
    arrives — with no end where the world states none — or, for a sensor reading a series, one
    forecast per stretch still ahead. The graphs written, none where the payload holds nothing it
    reads.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    percept's author and the graph's owner. `procedure` is the instrument's word about how it
    read; `phenomenon_at` the instant a device that speaks for itself says the result applies to
    (#101), where `at` is the arrival.
    """
    if reads_series(store, sensor):
        keys = rows(store, _KEY_Q, graphs_of(store, PUBLIC), sensor=sensor)
        if len(keys) != 1:
            log.warning("%s has no key: one property observed of one host makes one, and the world states %d", local_of(sensor), len(keys))
            return []
        return _forecast(store, me, sensor, keys[0]["feature"], keys[0]["property"], payload, at)
    readings = decode(store, sensor, payload)
    if readings is None:
        return []
    cat = Raw(f"<{catalogue_of(store)}>")
    for silence in rows(store, _SILENCE_Q, (), cat=cat, sensor=sensor):
        forget_graph(store, silence["g"])
    kept = rows(store, _KEPT_Q, (), cat=cat, sensor=sensor)
    latest = next((r for r in kept if r.get("followed") != "true"), None)
    #  EVERY READING THE MESSAGE CARRIES, oldest first, each placed that long before it arrived: an
    #  earlier one holds only until the next one's instant; the latest stands as the present until
    #  the next is due by the sensor's frequency, and a grace past it. The percept before them ends
    #  where the first of them begins.
    instants = [at - timedelta(seconds=age) for _, age in readings]
    cadence = cadence_of(store, sensor, memo)
    if latest is not None:
        end_graph(store, latest["g"], instants[0])
    before = latest["o"] if latest is not None else None
    written = []
    for n, ((number, _), when) in enumerate(zip(readings, instants)):
        last = n == len(readings) - 1
        until = (when + timedelta(seconds=(1 + GRACE) * cadence) if cadence is not None else None) if last else instants[n + 1]
        node, graph = _named(store, cat, me, sensor, when)
        _write(store, me, sensor, graph, node, number, when, until, before, procedure,
               phenomenon_at if last else None)
        written.append(graph)
        before = node
    log.info("%s: %s reads %s%s", local_of(me), local_of(sensor), readings[-1][0],
             "".join(f", and read {n:g} {a:g}s before" for n, a in readings[:-1]))
    #  AS DEEP AS SENSING'S RULES READ: the sensor's last `stuckAfter` percepts, and never fewer than
    #  the latest — each one older forgotten, with what was concluded of it.
    depth = max(1, stance(store, STUCK_AFTER_TERM, STUCK_AFTER, memo))
    newest_first = [*reversed(written), *(r["g"] for r in kept)]
    for old in newest_first[depth:]:
        forget_graph(store, old)
    return [g for g in written if g in newest_first[:depth]]


def _named(store, cat: Raw, me: str, sensor: str, when: datetime) -> tuple[str, str]:
    """The node and the graph of the reading `sensor` made at `when` — the second of that instant
    named apart from the first, so a sensor read twice in one instant keeps both."""
    n = 1
    while rows(store, _SAID_Q, (), cat=cat, g=percept_graph(local_of(me), sensor, when, n)):
        n += 1
    return percept_of(sensor, when, n), percept_graph(local_of(me), sensor, when, n)


def _write(store, me: str, sensor: str, graph: str, node: str, number: float, at: datetime,
           until: datetime | None, before: str | None, procedure: str | None = None,
           phenomenon_at: datetime | None = None) -> None:
    """One percept of what `sensor` gave, `number` at `at`, standing until `until` or for good, the
    percept `before` it named as its previous."""
    said = [f'<{node}> a sosa:Observation',
            f'<{node}> sensing:rawResult "{round(float(number), 6)}"^^xsd:decimal',
            f'<{node}> sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
            f'<{node}> sosa:madeBySensor <{sensor}>',
            f'<{node}> prov:wasGeneratedBy <{me}>']
    if before is not None:
        said.append(f'<{node}> sensing:previous <{before}>')
    if phenomenon_at is not None:
        said.append(f'<{node}> sosa:phenomenonTime "{phenomenon_at.isoformat()}"^^xsd:dateTime')
    if procedure:
        said.append(f'<{node}> sosa:usedProcedure <{procedure}>')
    update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ {' . '.join(said)} . }}
  {entry(store, graph, OBSERVATION_GRAPH, RECEIVED, me, start=at, end=until)} }}""")


def _forecast(store, me: str, sensor: str, feature: str, observed_property: str, payload: bytes,
              at: datetime) -> list[str]:
    """One forecast graph per stretch of the series still ahead at `at`, the sensor's earlier
    forecast forgotten first; the graphs, first stretch first."""
    stretches = decode_series(store, sensor, payload)
    if stretches is None:
        return []
    cat = Raw(f"<{catalogue_of(store)}>")
    for old in rows(store, _FORECAST_Q, (), cat=cat, sensor=sensor):
        forget_graph(store, old["g"])
    written = []
    for start, end, value in stretches:
        if end <= at:
            continue
        graph = forecast_graph(local_of(me), sensor, start)
        node = f"{observation_of(feature, observed_property)}_{start.strftime('%Y%m%dT%H%M%SZ')}"
        number = f"{round(value, 6) + 0.0:.6f}".rstrip("0")
        said = [f'<{node}> a sosa:Observation',
                f'<{node}> sosa:hasFeatureOfInterest <{feature}>',
                f'<{node}> sosa:observedProperty <{observed_property}>',
                f'<{node}> sosa:hasSimpleResult "{number}{"0" if number.endswith(".") else ""}"^^xsd:decimal',
                f'<{node}> sosa:resultTime "{at.isoformat()}"^^xsd:dateTime',
                f'<{node}> sosa:phenomenonTime "{start.isoformat()}"^^xsd:dateTime',
                f'<{node}> sosa:madeBySensor <{sensor}>',
                f'<{node}> prov:wasGeneratedBy <{me}>']
        update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ {' . '.join(said)} . }}
  {entry(store, graph, FORECAST_GRAPH, RECEIVED, me, start=start, end=end)} }}""")
        written.append(graph)
    log.info("%s: %s of %s forecast for %d stretch(es)%s", local_of(me), local_of(observed_property),
             local_of(feature), len(written), f" to {stretches[-1][1].isoformat(timespec='minutes')}" if written else "")
    return written
