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
    """The second reading a cadence and a half after the first, revised as this part has belief's part
    revise it, into this layer's kind, before it says it: said with that interval beside the cadence the world states, its point
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
        revise(store, graph, read=graphs_of(store, PUBLIC), kind=OBSERVATION_GRAPH)
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


class _Belief:
    """Belief's part as sensing links to it: what it is handed to revise, and with which kind."""
    def __init__(self):
        self.handed: list[tuple[tuple, str]] = []

    def revise(self, graphs, *, kind):
        self.handed.append((tuple(graphs), kind))
        return []


def test_linked_to_belief_it_hands_in_each_observation_with_this_layers_kind(monkeypatch, snapshots, stand_in_runtime):
    """SENSING RUNS BELIEF'S REVISION OVER ITS OWN OBSERVATIONS (#944): belief, beneath, knows no kind
    of them, so this part hands belief's part every observation nothing was concluded of when it starts,
    and each one written after, as it is written — saying its revision is of this layer's kind, so it
    reaches no reader of the mind — and before it says the observation, so the rules have concluded
    of it by then."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    put_document(store, document(RULES))
    (before,) = received(store, snapshots.ME, PROBE, b'{"value": 0.2}', snapshots.NOW)
    (concluded,) = received(store, snapshots.ME, PROBE, b'{"value": 0.21}', snapshots.NOW + CADENCE)
    revise(store, concluded, read=graphs_of(store, PUBLIC), kind=OBSERVATION_GRAPH)
    runtime = stand_in_runtime(store, snapshots.ME, snapshots.NOW + CADENCE)
    part, belief = create(runtime), _Belief()
    part.observed.connect(lambda event: None)
    part.link({"sensing": part, "belief": belief})
    part.start(runtime)
    assert belief.handed == [((before,), OBSERVATION_GRAPH)], "the one nothing was concluded of, at start"
    assert [kind for kind, _ in runtime.heard] == [OBSERVATION_GRAPH, OBSERVATION_GRAPH], \
        "handing it in is heard first, and saying it after"
    (written,) = received(store, snapshots.ME, PROBE, b'{"value": 0.22}', snapshots.NOW + 2 * CADENCE)
    assert runtime.heard[0][1](written) == []
    assert belief.handed[-1] == ((written,), OBSERVATION_GRAPH)
