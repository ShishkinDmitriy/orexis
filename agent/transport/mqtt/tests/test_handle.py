"""`handle`: one message on a topic becomes one observation per sensor of the agent's that
publishes there, and nothing for a topic that is nobody's of the agent's."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.transport.mqtt.handle import handle
from agent.store import rows

WORLD = Path(__file__).parent / "worlds" / "a_board_on_a_bus.trig"
OBSERVED = "http://example.org/orexis/graph/observed/keeper/"
BOARD_MESSAGE = b'{"temperature": 21.5, "humidity": 0.61}'

_RESULTS_Q = "SELECT ?p ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:observedProperty ?p ; sosa:hasSimpleResult ?v } } ORDER BY ?p"


def _results(store):
    return [(r["p"].rsplit("#", 1)[-1], float(r["v"])) for r in rows(store, _RESULTS_Q, ())]


def test_one_message_on_the_boards_topic_is_two_observations(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    written = handle(store, snapshots.ME, "sensors/board/reading", BOARD_MESSAGE, snapshots.NOW)
    assert written == [OBSERVED + "zamioculcas_humidity", OBSERVED + "zamioculcas_warmth"]
    assert _results(store) == [("humidity", 0.61), ("warmth", 21.5)]


def test_a_neighbours_message_on_the_same_broker_is_not_received(monkeypatch, snapshots):
    """The lamp's photometer publishes for a fern the keeper does not act for: the broker may
    deliver it, and it is nobody's of the keeper's."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    assert handle(store, snapshots.ME, "sensors/lamp/reading", b'{"value": 300}', snapshots.NOW) == []
    assert handle(store, snapshots.ME, "sensors/nowhere", BOARD_MESSAGE, snapshots.NOW) == []
    assert _results(store) == []


def test_a_message_a_sensor_cannot_read_writes_nothing_for_it(monkeypatch, snapshots, caplog):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(WORLD)
    with caplog.at_level("WARNING", logger="pipeline"):
        written = handle(store, snapshots.ME, "sensors/board/reading", b'{"temperature": 21.5}', snapshots.NOW)
    assert written == [OBSERVED + "zamioculcas_warmth"], "the hygrometer's field is missing, the thermometer's is there"
    assert "unread" in caplog.text
