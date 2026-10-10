"""Sensing's part: once started it asks every minute of the timeline what has fallen due, whether
or not anything arrived; and where anybody hears it, it says each observation written and how many
sensors are silent."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agent import clock
from agent.belief.revise import revise
from agent.ontology import PUBLIC
from agent.sensing.create import EVERY_S, create
from agent.sensing.events import Doubted, Observed, Silence
from agent.sensing.missed import SILENT_AFTER
from agent.sensing.ontology import OBSERVATION_GRAPH
from agent.sensing.received import GRACE, received
from agent.store import close_catalogue, document, graphs_of, put_document, rows

WORLD = Path(__file__).parent / "worlds" / "a_pot_and_its_probe.trig"
RULES = Path(__file__).parents[1] / "rules.ttl"
BELIEF = Path(__file__).parents[2] / "belief" / "ontology.ttl"
PROBE = "http://example.org/test#probe"
CADENCE = timedelta(seconds=900)


def test_its_part_asks_after_silence_every_minute(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW + CADENCE * (1 + GRACE + SILENT_AFTER))
    create(runtime).start(runtime)
    [(seconds, ask)] = runtime.timers
    assert seconds == EVERY_S and runtime.heard == [], "nobody hears an observation, so none is listened for"
    assert ask() == []
    said = rows(store, "SELECT ?s WHERE { GRAPH ?g { ?s sensing:silentSince ?t } }", ())
    assert [r["s"] for r in said] == [PROBE], "the probe, silent past its limit, is said so"


def test_where_heard_it_says_each_observation_with_its_interval_and_the_silence(monkeypatch, snapshots, stand_in_runtime):
    """The second reading a cadence and a half after the first, revised as belief's part revises it
    before this part hears it: said with that interval beside the cadence the world states, its point
    carrying the raw number beside the reading (#894); and once the probe is past its limit, one
    sensor silent — and WHICH, the probe, said silent and not stuck; a reading then takes the doubt
    back, and the next ask says so once, nought on both, and then nothing."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    put_document(store, document(BELIEF))          # what a revision is, so its row closes as a boot's does
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW)
    part = create(runtime)
    heard = []
    part.observed.connect(heard.append)
    part.silence.connect(heard.append)
    part.doubted.connect(heard.append)
    part.start(runtime)
    [(kind, observation)] = runtime.heard
    assert kind == OBSERVATION_GRAPH
    for at, value in ((snapshots.NOW, 0.2), (snapshots.NOW + CADENCE * 1.5, 0.3)):
        (graph,) = received(store, snapshots.ME, PROBE, f'{{"value": {value}}}'.encode(), at)
        revise(store, graph, read=graphs_of(store, PUBLIC))
        close_catalogue(store)
        observation(graph)
    first, second = heard
    assert isinstance(second, Observed) and first.interval_s is None
    assert (second.value, second.interval_s, second.cadence_s) == (0.3, 1350.0, 900.0)
    assert second.point()["measurement"] == "moisture" and second.point()["fields"] == {"value": 0.3, "raw": 0.3}
    runtime.now = snapshots.NOW + CADENCE * (2.5 + GRACE + SILENT_AFTER)
    [(_, ask)] = runtime.timers
    ask()
    assert heard[-2:] == [Silence(silent=1), Doubted(sensor="probe", silent=1, stuck=0)]
    (graph,) = received(store, snapshots.ME, PROBE, b'{"value": 0.4}', runtime.now)
    ask()
    assert heard[-2:] == [Silence(silent=0), Doubted(sensor="probe", silent=0, stuck=0)], "the doubt taken back, said once"
    ask()
    assert heard[-1] == Silence(silent=0), "and then nothing of a sensor nobody doubts"
