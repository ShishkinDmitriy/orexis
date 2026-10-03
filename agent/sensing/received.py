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
agent's, holding from its instant UNTIL THE NEXT IS DUE AND A GRACE PAST IT — the sensor's
`ssn-system:Frequency` past it (`cadence_of`), and `GRACE` of those cadences more, or with no end
where the world states none — and replacing whole the observation of the key before (#669's
invariant, kept at the writer), so a successor arriving on time or late ends it the moment it
lands. A reader asking at an instant past that is handed nothing: the observation's standing as
the present ends by the clock, `missed` says so when sensing's `start` asks every minute, and
nothing here keeps a timer.

**A READING LATE IS NOT A READING MISSING (#870).** Ended exactly at the next one's due instant, a
reading published a moment late — a board's radio, a broker, a simulator's loop — left the agent
with no present for that moment, and a step sized from the reading in it commanded nothing. The
grace is how late a reading may be and still be the same promise kept; past it the reading is
missing, and past `missed`'s limit the sensor is silent.

**A SERIES IS A FORECAST, ONE GRAPH PER STRETCH.** A sensor stating where the instants its values
are for are kept (`reads_series`) is read as a series: each value still ahead is written as its own
`sosa:Observation` into a graph of its own, `sensing:ForecastGraph`, holding during its stretch —
of what, which property, the number, the instant the forecast was issued, the start of its
stretch, the sensor — and every forecast graph the sensor wrote before is forgotten first, so the
next forecast replaces the last. A stretch already over when the forecast arrives is not written.
A forecast is a belief and not a reading, so it ends no silence and is said as no observation.

**A READING ENDS A SILENCE.** A sensor `missed` had said silent is silent no longer: the graph
saying so goes before the observation is written, found by the row's content and never by name.

**A NUMBER THAT NEVER CHANGES IS A SENSOR STUCK (#462).** Freshness was the one doubt the store
held about a reading, so a probe that lost half its wire at mounting and reported a plausible
number on time all night was believed all night. Each observation carries `sensing:unchangedSince`,
the instant of the earliest reading in the unbroken run of its number — its own where the number
differs from the one it replaced, the replaced one's where it is identical — so the run's start is
in the store and not in a count a restart loses. A sensor whose run has lasted its agent's `sensing:stuckAfter` of
its cadences (`STUCK_AFTER`, six, where the agent states none) is said `sensing:stuckSince` the run's start, once, in a graph of the agent's own
classified `orexis:StateGraph` as a silence is, holding from that instant; the first reading whose
number differs takes the graph back here, as a reading takes a silence back. Identical means the
raw number, the count the pointer found, since a clamp or a rescale can make two different counts
one reading; and a sensor stating no frequency is never said stuck, as it is never said silent.

**AND IT IS SAID.** The graph written is answered to whoever runs the transport, and sensing's
part, hearing an observation graph written, says it as an `Observed` (`events.py`), which history
writes as a point and metrics tallies: sensing decides what an observation is, so sensing says
what happened, and `received` writes to no series.

**NOTHING ELSE.** No side is drawn here: which side of its subject's ranges the number lies on
is a revision, concluded by the rules this layer ships and run by the deliberator when the
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

from agent.ontology import BELIEF, PUBLIC, STATE, local_of
from agent.store import Raw, catalogue_of, entry, forget_graph, graphs_of, remember, rows, update

from .cadence import cadence_of
from .ontology import (DERIVED, FORECAST_GRAPH, OBSERVATION_GRAPH, RECEIVED, earlier_graph, forecast_graph,
                       observation_by, observation_graph, observation_of, stuck_graph)
from .pipeline import decode, decode_series, reads_series

log = logging.getLogger("received")

#  HOW LATE A READING MAY BE, in its sensor's cadences: the observation before it stays the present
#  until its successor arrives or this long past the instant the successor was due.
GRACE = 1

#  HOW LONG A SENSOR'S NUMBER MAY STAY THE SAME before the sensor is said stuck, in its own cadences:
#  twice the silence limit. A live instrument's count moves by a bit within a few readings even in
#  still soil, and soil itself drifts within an hour, so a number unchanged through six cadences —
#  an hour at the greenhouse's ten minutes, two at the terrace's twenty — is the signature of a
#  frozen oscillator or a half-lost wire rather than of equilibrium; and the suspicion costs the
#  row alone, since the first reading that differs takes it back.
STUCK_AFTER = 6

#  HOW MANY CADENCES THIS AGENT ALLOWS before it says a sensor stuck — its own opinion, stated of it
#  in the documents it believes (`sensing:stuckAfter`), `STUCK_AFTER` where it states none.
_STUCK_AFTER_Q = "SELECT ?n WHERE { $me sensing:stuckAfter ?n }"


def _stuck_after(store, me: str, memo=None) -> int:
    """The limit, in a sensor's cadences, past which `me` says a sensor whose number has not changed
    is stuck: what the agent states of itself, or `STUCK_AFTER` where it states nothing. The figure
    is a belief and not a kernel constant — the agent's, as the patience is meant to be — so a world
    that knows its instruments jitter slowly says so of its agent, and the package's six stands
    only where nobody said otherwise."""
    def read():
        found = rows(store, _STUCK_AFTER_Q, graphs_of(store, PUBLIC, BELIEF), me=me)
        return int(found[0]["n"]) if found else STUCK_AFTER
    return remember(memo, ("stuck_after", me), read)

#  THE KEY: what the sensor observes, of what it is mounted in.
_KEY_Q = "SELECT ?feature ?property WHERE { $sensor sosa:observes ?property ; sosa:isHostedBy ?feature }"

#  THE SILENCE SAID OF THIS SENSOR, if any — the graph holding the row, found by its content.
_SILENCE_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { $sensor sensing:silentSince ?since } }"""

#  WHAT THIS SENSOR READ BEFORE: every observation graph of it, found by its content, with the
#  number it gave, when, and since when the number had been that — for the run to carry on from.
_OBSERVED_Q = """
SELECT ?g ?raw ?t ?since WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor
             OPTIONAL { ?o sensing:rawResult ?raw } OPTIONAL { ?o sosa:resultTime ?t }
             OPTIONAL { ?o sensing:unchangedSince ?since } } }
ORDER BY ?t"""

#  WHETHER THIS SENSOR IS SAID STUCK — the graph holding the row, found by its content.
_STUCK_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:StateGraph } GRAPH ?g { $sensor sensing:stuckSince ?since } }"""

#  THE FORECAST THIS SENSOR GAVE BEFORE: every graph of it, found by its content.
_FORECAST_Q = """
SELECT ?g WHERE { GRAPH $cat { ?g a sensing:ForecastGraph } GRAPH ?g { ?o sosa:madeBySensor $sensor } }"""


def received(store, me: str, sensor: str, payload: bytes, at: datetime, *,
             procedure: str | None = None, phenomenon_at: datetime | None = None, memo=None) -> list[str]:
    """Write what `sensor` read, `payload` decoded by its binding: the observation of the
    property it observes, of what it is hosted by, standing as the present from `at` until
    the next is due by the sensor's frequency and `GRACE` cadences past it, or until the next
    arrives — with no end where the world states none — or,
    for a sensor reading a series, one forecast per stretch still ahead. The graphs written,
    none where the sensor has no key or the payload holds nothing it reads.

    `me` is who holds it — the one identifier a process is handed — and is written as the
    observation's author and the graph's owner. `procedure` is the instrument's word about
    how it read; `phenomenon_at` the instant a device that speaks for itself says the result
    applies to (#101), where `at` is the arrival.
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
    #  THE RUN SO FAR: the number the latest observation replaced gave, and since when it had given
    #  it — read before the graph goes, since the run is the one thing the replacement carries over.
    run = None
    for old in rows(store, _OBSERVED_Q, (), cat=cat, sensor=sensor):
        if old.get("raw") is not None and old.get("t"):
            run = (float(old["raw"]), datetime.fromisoformat(old.get("since") or old["t"]))
        forget_graph(store, old["g"])
    #  EVERY READING THE MESSAGE CARRIES, oldest first, each placed that long before it arrived: an
    #  earlier one — a sentinel's last quiet sample before its alarm — holds only until the next one's
    #  instant, so it is a step in the history and, at the latest one's instant, nothing; the latest
    #  stands as the present until the next is due by the sensor's frequency, and a grace past it.
    #  Each carries on the run where its number is the one before, and starts one where it is not.
    instants = [at - timedelta(seconds=age) for _, age in readings]
    since = []
    for (number, _), when in zip(readings, instants):
        run = (round(float(number), 6), run[1] if run is not None and run[0] == round(float(number), 6) else when)
        since.append(run[1])
    written = []
    for n, ((number, _), when, then) in enumerate(zip(readings[:-1], instants[:-1], instants[1:])):
        graph = earlier_graph(local_of(me), sensor, n)
        _write(store, me, sensor, graph, f"{observation_by(sensor)}_earlier_{n}", number, when, then, since[n], procedure)
        written.append(graph)
    number, when = readings[-1][0], instants[-1]
    graph = observation_graph(local_of(me), sensor)
    cadence = cadence_of(store, sensor, memo)
    _write(store, me, sensor, graph, observation_by(sensor), number, when,
           when + timedelta(seconds=(1 + GRACE) * cadence) if cadence is not None else None, since[-1], procedure,
           phenomenon_at)
    log.info("%s: %s reads %s%s", local_of(me), local_of(sensor), number,
             "".join(f", and read {n:g} {a:g}s before" for n, a in readings[:-1]))
    _stuck(store, me, sensor, cat, since[-1], when, cadence, _stuck_after(store, me, memo))
    return [*written, graph]


def _stuck(store, me: str, sensor: str, cat: Raw, since: datetime, at: datetime, cadence: float | None,
           limit: int) -> None:
    """Say `sensor` stuck, once, where its number has been the same since `since` for `limit`
    cadences — the agent's own figure, `_stuck_after` — and more at `at`; take the saying back where it has not — the run having restarted
    with this reading, or the sensor stating no cadence to count in."""
    said = rows(store, _STUCK_Q, (), cat=cat, sensor=sensor)
    if cadence is None or at < since + timedelta(seconds=limit * cadence):
        for row in said:
            forget_graph(store, row["g"])
        return
    if said:
        return                                          # said already, and once is enough
    graph = stuck_graph(local_of(me), sensor)
    update(store, f"""
INSERT DATA {{
  GRAPH <{graph}> {{ <{sensor}> sensing:stuckSince "{since.isoformat()}"^^xsd:dateTime . }}
  {entry(store, graph, STATE, DERIVED, me, start=since)} }}""")
    log.warning("%s: %s stuck since %s, its number unchanged for %d cadences", local_of(me), local_of(sensor),
                since.isoformat(timespec="seconds"), limit)


def _write(store, me: str, sensor: str, graph: str, node: str, number: float, at: datetime,
           until: datetime | None, since: datetime, procedure: str | None = None,
           phenomenon_at: datetime | None = None) -> None:
    """One observation of what `sensor` gave, `number` at `at`, standing until `until` or for good,
    the number unchanged since `since`."""
    said = [f'<{node}> a sosa:Observation',
            f'<{node}> sensing:rawResult "{round(float(number), 6)}"^^xsd:decimal',
            f'<{node}> sensing:unchangedSince "{since.isoformat()}"^^xsd:dateTime',
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
